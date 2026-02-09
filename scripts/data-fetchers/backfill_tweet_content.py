#!/usr/bin/env python3
"""
Backfill x_posts that have t.co-only content with actual tweet text.

Uses fxtwitter (free, no auth) to fetch the real tweet content and
replaces bare t.co links with expanded URLs and full tweet text.

Usage:
    export $(grep -v '^#' .env | xargs)
    python3 backfill_tweet_content.py [--dry-run] [--limit 100] [--batch 50]
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

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY")
    sys.exit(1)


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def supabase_get(path: str) -> list:
    """GET from Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def supabase_patch(table: str, row_id: int, data: dict) -> bool:
    """PATCH a single row in Supabase."""
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


def fetch_fxtwitter(tweet_id: str) -> dict | None:
    """Fetch tweet via fxtwitter API (free, no auth)."""
    url = f"https://api.fxtwitter.com/status/{tweet_id}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "ShortGravityBot/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("tweet", data)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        log(f"  fxtwitter failed for {tweet_id}: {e}")
        return None


def is_tco_only(text: str) -> bool:
    """Check if content is essentially just t.co links with minimal text."""
    # Strip t.co links
    stripped = re.sub(r'https?://t\.co/\S+', '', text).strip()
    # If what remains is very short (< 20 chars) or empty, it's t.co-only
    return len(stripped) < 20


def extract_tweet_id(url: str) -> str | None:
    """Extract tweet ID from x.com/twitter.com URL."""
    match = re.search(r'/status/(\d+)', url or "")
    return match.group(1) if match else None


def backfill(dry_run: bool = False, limit: int = 500, batch_size: int = 50) -> None:
    """Main backfill loop."""
    total_updated = 0
    total_skipped = 0
    total_failed = 0
    offset = 0

    while total_updated + total_skipped + total_failed < limit:
        # Fetch batch of posts with t.co content
        remaining = min(batch_size, limit - (total_updated + total_skipped + total_failed))
        path = (
            f"x_posts?select=id,tweet_id,content_text,url,author_username"
            f"&order=published_at.desc"
            f"&limit={remaining}&offset={offset}"
        )
        rows = supabase_get(path)
        if not rows:
            log("No more rows to process.")
            break

        # Filter to rows that actually need backfill
        needs_backfill = [r for r in rows if is_tco_only(r.get("content_text", ""))]
        offset += len(rows)

        if not needs_backfill:
            # Skip batches where all content is already good
            if len(rows) < remaining:
                break
            continue

        log(f"Batch: {len(needs_backfill)}/{len(rows)} need backfill")

        for row in needs_backfill:
            tweet_id = row.get("tweet_id") or extract_tweet_id(row.get("url", ""))
            if not tweet_id:
                log(f"  SKIP id={row['id']}: no tweet_id")
                total_skipped += 1
                continue

            # Rate limit: fxtwitter is generous but don't hammer
            time.sleep(0.3)

            tweet = fetch_fxtwitter(tweet_id)
            if not tweet or not tweet.get("text"):
                log(f"  FAIL @{row.get('author_username', '?')}: tweet {tweet_id} — no content from fxtwitter")
                total_failed += 1
                continue

            new_content = tweet["text"]

            # Skip if fxtwitter returned the same t.co content
            if is_tco_only(new_content):
                log(f"  SKIP @{row.get('author_username', '?')}: tweet {tweet_id} — fxtwitter also t.co only")
                total_skipped += 1
                continue

            old_preview = (row.get("content_text", ""))[:60]
            new_preview = new_content[:60]

            if dry_run:
                log(f"  [DRY RUN] @{row.get('author_username', '?')}: \"{old_preview}\" → \"{new_preview}\"")
                total_updated += 1
            else:
                ok = supabase_patch("x_posts", row["id"], {"content_text": new_content})
                if ok:
                    log(f"  UPDATED @{row.get('author_username', '?')}: \"{old_preview}\" → \"{new_preview}\"")
                    total_updated += 1
                else:
                    total_failed += 1

        if len(rows) < remaining:
            break

    log(f"\nDone. Updated: {total_updated}, Skipped: {total_skipped}, Failed: {total_failed}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    limit_val = 500
    batch_val = 50

    for i, arg in enumerate(sys.argv):
        if arg == "--limit" and i + 1 < len(sys.argv):
            limit_val = int(sys.argv[i + 1])
        if arg == "--batch" and i + 1 < len(sys.argv):
            batch_val = int(sys.argv[i + 1])

    log(f"Backfill tweet content — dry_run={dry_run}, limit={limit_val}, batch={batch_val}")
    backfill(dry_run=dry_run, limit=limit_val, batch_size=batch_val)
