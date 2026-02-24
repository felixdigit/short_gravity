#!/usr/bin/env python3
"""
Press Release Worker v3

Strategy:
  1. Playwright loads IR page once → captures all AccessWire storyIds
  2. Plain HTTP fetches full content from AccessWire getStory.json API
  3. Stores in Supabase `press_releases` table

No stealth needed. AccessWire API is public, just needs the storyIds.
"""

from __future__ import annotations
import json
import os
import sys
import time
import urllib.request
import urllib.error
import re
import hashlib
from datetime import datetime
from typing import Dict, List, Optional


# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

ACCESSWIRE_STORY_URL = "https://www.accesswire.com/qm/data/getStory.json"
IR_PAGE = "https://investors.ast-science.com/press-releases"

# Only ingest official ASTS sources, not third-party mentions
ALLOWED_SOURCES = {"Business Wire", "GlobeNewsWire", "AccessWire", "PR Newswire"}


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None):
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode("utf-8")
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        log(f"Supabase error: {e.code} - {error_body}")
        raise


def get_existing_ids() -> set:
    try:
        result = supabase_request("GET", "press_releases?select=source_id")
        return {r["source_id"] for r in result}
    except Exception as e:
        log(f"Error fetching existing: {e}")
        return set()


# ── Phase 1: Capture storyIds from IR page ───────────────────────────


def discover_story_ids() -> List[str]:
    """Load IR page once via Playwright, capture all AccessWire storyIds."""
    log("Launching Playwright to capture storyIds from IR page...")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("ERROR: Playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    story_ids = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled'],
        )
        page = browser.new_page()
        page.set_default_navigation_timeout(30000)
        page.set_default_timeout(20000)

        def on_request(request):
            if "getStory.json" in request.url:
                m = re.search(r'storyId=(\d+)', request.url)
                if m:
                    story_ids.append(m.group(1))

        page.on("request", on_request)

        try:
            page.goto(IR_PAGE, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=20000)
            # Give extra time for all stories to load
            page.wait_for_timeout(5000)
        except Exception as e:
            try:
                page.screenshot(path=f"/tmp/debug_press_release_{int(time.time())}.png")
                log(f"  DEBUG: Screenshot saved for failure analysis")
            except Exception:
                pass
            log(f"  Page load error: {e}")
        finally:
            browser.close()

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for sid in story_ids:
        if sid not in seen:
            seen.add(sid)
            unique.append(sid)

    log(f"  Captured {len(unique)} unique storyIds")
    return unique


# ── Phase 2: Fetch full content via AccessWire API ───────────────────


def strip_html(html: str) -> str:
    """Strip HTML tags and clean up text."""
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    for entity, char in [("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                          ("&gt;", ">"), ("&#x2013;", "\u2013"), ("&#x2019;", "\u2019"),
                          ("&#xA0;", " ")]:
        text = text.replace(entity, char)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_story(story_id: str) -> Optional[Dict]:
    """Fetch a single story from AccessWire API."""
    url = f"{ACCESSWIRE_STORY_URL}?storyId={story_id}&newslang=en"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        log(f"    Fetch error for {story_id}: {e}")
        return None

    story_wrapper = data.get("qmcistory", {})
    source_raw = story_wrapper.get("source", "")
    # Normalize source: "Business Wire via QuoteMedia" -> "Business Wire"
    source = source_raw.split(" via ")[0].strip()

    qmstory = story_wrapper.get("qmnews", {}).get("qmstory", {})
    title = qmstory.get("qmheadline", "")
    dt = qmstory.get("datetime", "")
    html_content = qmstory.get("qmtext", "")
    summary_raw = qmstory.get("qmsummary", "")

    if not title:
        return None

    content = strip_html(html_content)
    # Remove the story wrapper div class
    content = re.sub(r"^.*?(?=\S)", "", content)

    return {
        "story_id": story_id,
        "title": title,
        "source": source,
        "datetime": dt,
        "content": content[:100000],
        "summary_raw": strip_html(summary_raw)[:1000],
    }


# ── Processing ───────────────────────────────────────────────────────


def categorize(title: str, content: str) -> tuple:
    t = title.lower()
    c = (content or "").lower()

    category = "announcement"
    tags = []

    if any(w in t for w in ["launch", "satellite", "bluebird", "orbit", "bluewalker"]):
        category = "satellite_launch"
    elif any(w in t for w in ["partner", "agreement", "at&t", "verizon", "vodafone"]):
        category = "partnership"
    elif any(w in t for w in ["quarter", "q1", "q2", "q3", "q4", "financial", "results", "earnings"]):
        category = "quarterly_results"
    elif any(w in t for w in ["spectrum", "fcc", "license", "authorization", "sta "]):
        category = "regulatory"
    elif any(w in t for w in ["financing", "offering", "capital", "million", "billion", "pricing"]):
        category = "financing"
    elif any(w in t for w in ["contract", "defense", "military", "shield", "dod"]):
        category = "defense"

    for partner in ["at&t", "verizon", "vodafone", "rakuten", "bell", "telus",
                     "orange", "google", "spacex", "blue origin", "liberty latin"]:
        if partner in c or partner in t:
            tags.append(partner)

    if "bluebird" in c or "bluebird" in t:
        tags.append("bluebird")
    if "bluewalker" in c or "bluewalker" in t:
        tags.append("bluewalker")

    return category, list(set(tags))


def generate_summary(content: str, title: str) -> str:
    if not ANTHROPIC_API_KEY or not content or len(content) < 200:
        return ""

    truncated = content[:30000]
    prompt = f"""Summarize this AST SpaceMobile press release in 2-3 sentences. Focus on: the main announcement, business impact, specific numbers/dates/milestones.

Title: {title}

{truncated}

Summary:"""

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": prompt}],
    }

    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["content"][0]["text"].strip()
    except Exception as e:
        log(f"    Summary error: {e}")
        return ""


def parse_iso_date(dt_str: str) -> Optional[str]:
    """Parse ISO datetime to simplified ISO."""
    if not dt_str:
        return None
    try:
        # "2026-01-22T07:00:00-05:00" -> "2026-01-22T12:00:00Z"
        dt_str_clean = re.sub(r'[+-]\d{2}:\d{2}$', '', dt_str)
        dt = datetime.fromisoformat(dt_str_clean)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        return None


# ── Main ─────────────────────────────────────────────────────────────


def run_worker():
    log("=" * 60)
    log("PRESS RELEASE WORKER v3")
    log("  AccessWire API + Playwright storyId discovery")
    log("=" * 60)

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    existing = get_existing_ids()
    log(f"Existing press releases in DB: {len(existing)}")

    # Phase 1: Get all storyIds from IR page
    story_ids = discover_story_ids()

    if not story_ids:
        log("No storyIds found. Exiting.")
        return

    # Phase 2: Fetch and process each story
    success = 0
    skipped = 0
    failed = 0
    filtered = 0

    for i, story_id in enumerate(story_ids):
        # Check if already exists
        source_id = f"aw_{story_id}"
        if source_id in existing:
            skipped += 1
            continue

        story = fetch_story(story_id)
        if not story:
            failed += 1
            continue

        # Filter: only official ASTS press releases
        source = story["source"]
        if not any(allowed in source for allowed in ALLOWED_SOURCES):
            filtered += 1
            continue

        title = story["title"]
        content = story["content"]
        log(f"[{i+1}/{len(story_ids)}] {title[:70]}...")
        log(f"    Source: {source} | Content: {len(content)} chars")

        category, tags = categorize(title, content)
        published_at = parse_iso_date(story["datetime"])

        # Generate summary
        summary = generate_summary(content, title)
        if summary:
            log(f"    Summary: {summary[:80]}...")

        try:
            record = {
                "source_id": source_id,
                "title": title,
                "published_at": published_at,
                "url": None,  # AccessWire doesn't give original BW URL
                "category": category,
                "tags": tags,
                "content_text": content,
                "summary": summary or story.get("summary_raw") or None,
                "status": "completed",
            }
            supabase_request("POST", "press_releases", record)
            success += 1
            log(f"    Saved")
        except Exception as e:
            log(f"    Error: {e}")
            failed += 1

        time.sleep(0.5)  # Gentle rate limit on AccessWire

    log("=" * 60)
    log(f"DONE: {success} saved, {skipped} already existed, {filtered} filtered (non-ASTS), {failed} failed")
    log("=" * 60)


if __name__ == "__main__":
    run_worker()
