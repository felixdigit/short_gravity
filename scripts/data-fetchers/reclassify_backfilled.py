#!/usr/bin/env python3
"""
Reclassify X posts that were backfilled with new content.

Finds posts where the summary is stale (contains t.co links, "Unable to classify",
"Link-only tweet", etc.) but content_text has been updated with real content.
Re-runs Haiku classification to generate proper summaries.

Usage:
    export $(grep -v '^#' .env | xargs)
    python3 reclassify_backfilled.py [--dry-run] [--limit 500] [--batch 20]
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY")
    sys.exit(1)

if not ANTHROPIC_API_KEY:
    print("ERROR: Set ANTHROPIC_API_KEY for classification")
    sys.exit(1)


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def supabase_get(path: str) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def supabase_patch(table: str, row_id: int, data: dict) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{row_id}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method="PATCH", headers={
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status in (200, 204)
    except urllib.error.HTTPError as e:
        log(f"  PATCH failed: {e.status} {e.read().decode()[:200]}")
        return False


def classify_tweet(text: str, author: str) -> dict | None:
    """Classify tweet using Haiku."""
    if len(text) < 20:
        return None

    prompt = f"""You are classifying tweets from the $ASTS (AST SpaceMobile) investor community for a research intelligence database.

CONTEXT: AST SpaceMobile is building a space-based cellular broadband network using BlueBird satellites in low Earth orbit.

KNOWN VOICES:
- @AST_SpaceMobile, @AbelAvellan → official company/CEO accounts
- @CatSE___ApeX___ → deep regulatory/FCC analyst
- @thekookreport → community analyst, tracks catalysts
- @spacanpanman → aggregator/narrator of ASTS developments

Tweet by @{author}:
"{text}"

Classify into this exact JSON:
{{"sentiment":"...","signal_type":"...","category":"...","tags":[...],"summary":"..."}}

sentiment: "bullish", "bearish", "neutral", or "informational"
signal_type: "official", "insider_signal", "breaking_news", "analyst_take", or "community"
category: "satellite_launch", "spectrum", "regulatory", "partnership", "technology", "financing", "earnings", "competitive", or "general"
tags: relevant entities as lowercase strings
summary: One sentence capturing the key intelligence value.

JSON only:"""

    body = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 200,
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
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            raw = result["content"][0]["text"].strip()
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
    except Exception as e:
        log(f"  Classification error: {e}")
    return None


def is_tco_only(text: str) -> bool:
    stripped = re.sub(r'https?://t\.co/\S+', '', text).strip()
    return len(stripped) < 20


def needs_reclassification(row: dict) -> bool:
    """Check if this post has good content but a stale summary."""
    content = row.get("content_text", "")
    summary = row.get("summary", "") or ""

    # Content must be substantive (not still t.co-only)
    if is_tco_only(content):
        return False

    # Summary is stale if it contains t.co, or these known stale patterns
    stale_patterns = [
        "t.co/",
        "Unable to classify",
        "Link-only tweet",
        "content unavailable",
        "no visible text",
        "contains only a URL",
    ]
    for pattern in stale_patterns:
        if pattern.lower() in summary.lower():
            return True

    # Also reclassify if summary is empty but content is good
    if not summary.strip() and len(content) > 30:
        return True

    return False


def reclassify(dry_run: bool = False, limit: int = 500, batch_size: int = 20) -> None:
    total_updated = 0
    total_skipped = 0
    total_failed = 0
    offset = 0

    while total_updated + total_skipped + total_failed < limit:
        remaining = min(batch_size, limit - (total_updated + total_skipped + total_failed))
        path = (
            f"x_posts?select=id,content_text,author_username,summary"
            f"&order=published_at.desc"
            f"&limit={remaining * 3}&offset={offset}"
        )
        rows = supabase_get(path)
        if not rows:
            log("No more rows.")
            break

        candidates = [r for r in rows if needs_reclassification(r)]
        offset += len(rows)

        if not candidates:
            if len(rows) < remaining * 3:
                break
            continue

        log(f"Batch: {len(candidates)} need reclassification")

        for row in candidates[:remaining]:
            if total_updated + total_skipped + total_failed >= limit:
                break

            content = row["content_text"]
            author = row.get("author_username", "unknown")

            # Rate limit Haiku calls
            time.sleep(0.5)

            classification = classify_tweet(content, author)
            if not classification:
                log(f"  FAIL @{author}: classification returned None")
                total_failed += 1
                continue

            old_summary = (row.get("summary") or "")[:50]
            new_summary = (classification.get("summary") or "")[:50]

            if dry_run:
                log(f"  [DRY RUN] @{author}: \"{old_summary}\" → \"{new_summary}\"")
                total_updated += 1
            else:
                ok = supabase_patch("x_posts", row["id"], {
                    "summary": classification.get("summary"),
                    "sentiment": classification.get("sentiment"),
                    "signal_type": classification.get("signal_type"),
                    "category": classification.get("category"),
                    "tags": classification.get("tags", []),
                })
                if ok:
                    log(f"  UPDATED @{author}: \"{old_summary}\" → \"{new_summary}\"")
                    total_updated += 1
                else:
                    total_failed += 1

        if len(rows) < remaining * 3:
            break

    log(f"\nDone. Reclassified: {total_updated}, Skipped: {total_skipped}, Failed: {total_failed}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    limit_val = 500
    batch_val = 20

    for i, arg in enumerate(sys.argv):
        if arg == "--limit" and i + 1 < len(sys.argv):
            limit_val = int(sys.argv[i + 1])
        if arg == "--batch" and i + 1 < len(sys.argv):
            batch_val = int(sys.argv[i + 1])

    log(f"Reclassify backfilled tweets — dry_run={dry_run}, limit={limit_val}, batch={batch_val}")
    reclassify(dry_run=dry_run, limit=limit_val, batch_size=batch_val)
