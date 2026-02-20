#!/usr/bin/env python3
"""
Launch Worker — Extract launch data from press releases, keep next_launches current.

Flow:
  1. Query press_releases for launch-related PRs (category=satellite_launch OR title matches)
  2. Send each PR to Claude Haiku to extract structured launch data
  3. Upsert into next_launches (match on mission name)
  4. Auto-mark past launches as LAUNCHED (7-day grace period)

Run: cd scripts/data-fetchers && export $(grep -v '^#' .env | xargs) && python3 launch_worker.py
"""

from __future__ import annotations
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

LAUNCH_KEYWORDS = ["launch", "bluebird", "bluewalker", "orbit", "liftoff", "mission"]

try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from discord.notify import notify_launch
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def supabase_request(path: str, method: str = "GET", data=None, headers_extra=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    if headers_extra:
        headers.update(headers_extra)
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode()
            return json.loads(content) if content else []
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()[:300]
        log(f"  Supabase {e.code}: {error_body}")
        raise


# ── Step 1: Fetch launch-related press releases ─────────────────────


def fetch_launch_prs() -> list:
    """Get press releases likely to contain launch info."""
    # Category match
    params = urllib.parse.urlencode({
        "select": "id,title,summary,content_text,published_at",
        "category": "eq.satellite_launch",
        "order": "published_at.desc",
        "limit": "50",
    })
    cat_results = supabase_request(f"press_releases?{params}") or []
    log(f"  Category=satellite_launch: {len(cat_results)} PRs")

    # Also grab PRs with launch keywords in title (may overlap)
    keyword_pattern = "|".join(LAUNCH_KEYWORDS)
    kw_params = urllib.parse.urlencode({
        "select": "id,title,summary,content_text,published_at",
        "title": f"ilike.*launch*",
        "order": "published_at.desc",
        "limit": "30",
    })
    kw_results = supabase_request(f"press_releases?{kw_params}") or []
    log(f"  Title contains 'launch': {len(kw_results)} PRs")

    # Deduplicate by id
    seen = set()
    combined = []
    for pr in cat_results + kw_results:
        if pr["id"] not in seen:
            seen.add(pr["id"])
            combined.append(pr)

    log(f"  Total unique launch PRs: {len(combined)}")
    return combined


# ── Step 2: Extract launch data via Claude ───────────────────────────


EXTRACTION_PROMPT = """Extract ALL satellite launch announcements from this AST SpaceMobile press release.

For each launch mentioned, return a JSON object with these fields:
- mission: Mission name (e.g. "FM2 BlueBird 7", "FM1 BlueBird-1"). Use the format "FM[N] BlueBird [N]" if possible.
- provider: Launch provider (e.g. "Blue Origin", "SpaceX", "ISRO")
- vehicle: Launch vehicle name (e.g. "New Glenn", "Falcon 9", "GSLV")
- site: Launch site (e.g. "Cape Canaveral, FL", "Sriharikota, India")
- target_date: Best estimate of launch date in YYYY-MM-DD format. If only a month is given, use the last day of that month. If "late February 2026", use "2026-02-28". If "Q2 2026", use "2026-06-30". If no date can be determined, use null.
- satellite_count: Number of satellites in this launch (integer), default 1
- notes: Brief note about the launch (vehicle, key details). Keep under 100 chars.

Return ONLY a JSON array. If no launches are found, return [].

Title: {title}

Summary: {summary}

Content (truncated):
{content}"""


def extract_launches_from_pr(pr: dict) -> list:
    """Use Claude Haiku to extract launch data from a press release."""
    if not ANTHROPIC_API_KEY:
        log("  SKIP: No ANTHROPIC_API_KEY")
        return []

    title = pr.get("title", "")
    summary = pr.get("summary", "") or ""
    content = (pr.get("content_text", "") or "")[:30000]

    prompt = EXTRACTION_PROMPT.format(
        title=title,
        summary=summary,
        content=content,
    )

    body = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}],
    }

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
    )

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                text = result["content"][0]["text"].strip()
                # Parse JSON from response (handle markdown code blocks)
                if text.startswith("```"):
                    text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                launches = json.loads(text)
                if isinstance(launches, list):
                    return launches
                return []
        except (urllib.error.HTTPError, json.JSONDecodeError, KeyError) as e:
            log(f"    Extraction attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                import time
                time.sleep(2 ** attempt)
    return []


# ── Step 3: Upsert into next_launches ────────────────────────────────


def upsert_launch(launch: dict, pr: dict) -> bool:
    """Upsert a launch record, matching on mission name."""
    mission = launch.get("mission", "").strip()
    if not mission:
        return False

    target_date = launch.get("target_date")
    if target_date:
        # Ensure it's a full timestamp
        if len(target_date) == 10:  # YYYY-MM-DD
            target_date = f"{target_date}T00:00:00Z"

    notes_parts = []
    if launch.get("vehicle"):
        notes_parts.append(launch["vehicle"])
    if launch.get("notes"):
        notes_parts.append(launch["notes"])
    notes = ", ".join(notes_parts)[:200] if notes_parts else None

    record = {
        "mission": mission,
        "provider": launch.get("provider"),
        "site": launch.get("site"),
        "target_date": target_date,
        "satellite_count": launch.get("satellite_count", 1),
        "notes": notes,
        "source_url": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Check if mission already exists
    check_params = urllib.parse.urlencode({
        "select": "id,mission,status",
        "mission": f"eq.{mission}",
        "limit": "1",
    })
    existing = supabase_request(f"next_launches?{check_params}")

    if existing and len(existing) > 0:
        row = existing[0]
        # Don't update if already marked LAUNCHED
        if row.get("status") == "LAUNCHED":
            log(f"    {mission}: already LAUNCHED, skipping")
            return False
        # PATCH existing row
        patch_path = f"next_launches?id=eq.{row['id']}"
        supabase_request(patch_path, method="PATCH", data=record)
        log(f"    {mission}: UPDATED")
    else:
        # INSERT new row
        record["status"] = "SCHEDULED"
        supabase_request("next_launches", method="POST", data=record)
        log(f"    {mission}: INSERTED")

        # Discord notification for new launches
        if DISCORD_AVAILABLE:
            notify_launch(mission=mission, date=target_date or "TBD",
                          status="SCHEDULED")

    return True


# ── Step 4: Auto-mark past launches ─────────────────────────────────


def mark_past_launches():
    """Mark launches with target_date > 7 days ago as LAUNCHED."""
    launches = supabase_request(
        "next_launches?status=eq.SCHEDULED&order=target_date.asc&select=id,mission,target_date"
    )
    if not launches:
        log("  No scheduled launches to check")
        return

    now = datetime.now(timezone.utc)
    marked = 0

    for launch in launches:
        target = launch.get("target_date")
        if not target:
            continue
        target_dt = datetime.fromisoformat(target.replace("Z", "+00:00"))
        if (now - target_dt).days > 7:
            supabase_request(
                f"next_launches?id=eq.{launch['id']}",
                method="PATCH",
                data={"status": "LAUNCHED", "updated_at": now.isoformat()},
            )
            log(f"    {launch['mission']}: auto-marked LAUNCHED (target was {target[:10]})")
            marked += 1

    log(f"  {len(launches)} scheduled, {marked} auto-marked as LAUNCHED")


# ── Main ─────────────────────────────────────────────────────────────


def run_worker():
    log("=" * 60)
    log("LAUNCH WORKER")
    log(f"  Extract launch data from press releases")
    log("=" * 60)

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        log("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY")
        sys.exit(1)

    if not ANTHROPIC_API_KEY:
        log("WARNING: No ANTHROPIC_API_KEY — extraction will be skipped")

    # Step 1: Fetch launch-related PRs
    log("\n[1/3] FETCHING LAUNCH-RELATED PRESS RELEASES")
    prs = fetch_launch_prs()

    if not prs:
        log("  No launch-related press releases found")
    else:
        # Step 2-3: Extract and upsert
        log(f"\n[2/3] EXTRACTING LAUNCH DATA VIA CLAUDE")
        total_extracted = 0
        total_upserted = 0

        for i, pr in enumerate(prs):
            title = pr.get("title", "")[:80]
            log(f"  [{i+1}/{len(prs)}] {title}")

            launches = extract_launches_from_pr(pr)
            if not launches:
                log(f"    No launches extracted")
                continue

            total_extracted += len(launches)
            for launch in launches:
                if upsert_launch(launch, pr):
                    total_upserted += 1

        log(f"\n  Extracted {total_extracted} launches, upserted {total_upserted}")

    # Step 4: Auto-mark past launches
    log(f"\n[3/3] CHECKING PAST LAUNCHES")
    mark_past_launches()

    log("\n" + "=" * 60)
    log("LAUNCH WORKER COMPLETE")
    log("=" * 60)


if __name__ == "__main__":
    run_worker()
