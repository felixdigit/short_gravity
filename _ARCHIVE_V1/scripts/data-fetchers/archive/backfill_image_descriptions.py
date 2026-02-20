#!/usr/bin/env python3
"""
Backfill image descriptions for image-only X posts.

Finds posts where content_text is thin (mostly t.co links or short) but
media photos are attached. Uses Haiku vision to describe the image content
and appends it to content_text, then re-classifies.

Usage:
    export $(grep -v '^#' .env | xargs)
    python3 backfill_image_descriptions.py [--dry-run] [--limit 200] [--batch 20]
"""
from __future__ import annotations

import base64
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
    print("ERROR: Set ANTHROPIC_API_KEY for vision")
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


def is_thin_content(text: str) -> bool:
    """Check if content is too thin (mostly links/short)."""
    stripped = re.sub(r'https?://\S+', '', text).strip()
    stripped = re.sub(r'\[(photo|video|gif)[^\]]*\]', '', stripped).strip()
    return len(stripped) < 30


def already_has_image_desc(text: str) -> bool:
    return "[image content:" in text.lower()


def describe_image(image_url: str) -> str | None:
    """Use Haiku vision to describe an image."""
    try:
        req = urllib.request.Request(image_url, headers={
            "User-Agent": "ShortGravityBot/1.0",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            if not content_type.startswith("image/"):
                return None
            image_data = resp.read()
            if len(image_data) > 5_000_000:
                return None
            b64 = base64.b64encode(image_data).decode()
    except Exception as e:
        log(f"  Image fetch failed: {e}")
        return None

    body = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 300,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": content_type, "data": b64},
                },
                {
                    "type": "text",
                    "text": "Describe this image concisely for a research database. If it's a document, filing, chart, or screenshot, extract the key text/data. If it's a photo, describe what's shown. Focus on factual content. 2-3 sentences max.",
                },
            ],
        }],
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
            return result["content"][0]["text"].strip()
    except Exception as e:
        log(f"  Vision describe failed: {e}")
        return None


def classify_tweet(text: str, author: str) -> dict | None:
    """Re-classify tweet using Haiku."""
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
signal_type: "official", "insider_signal", "analyst_take", or "community"
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


def backfill(dry_run: bool = False, limit: int = 200, batch_size: int = 20) -> None:
    total_updated = 0
    total_skipped = 0
    total_failed = 0
    offset = 0

    while total_updated + total_skipped + total_failed < limit:
        remaining = min(batch_size, limit - (total_updated + total_skipped + total_failed))
        # Fetch posts that have media in metrics
        path = (
            f"x_posts?select=id,content_text,author_username,metrics,summary"
            f"&order=published_at.desc"
            f"&limit={remaining * 5}&offset={offset}"
        )
        rows = supabase_get(path)
        if not rows:
            log("No more rows.")
            break

        offset += len(rows)
        candidates = []
        for r in rows:
            content = r.get("content_text", "")
            if already_has_image_desc(content):
                continue
            if not is_thin_content(content):
                continue
            # Check for photo media
            metrics = r.get("metrics") or {}
            media = metrics.get("media") or []
            photos = [m for m in media if m.get("type") == "photo"]
            if not photos:
                continue
            photo_url = photos[0].get("url") or photos[0].get("preview_url")
            if not photo_url:
                continue
            candidates.append((r, photo_url))

        if not candidates:
            if len(rows) < remaining * 5:
                break
            continue

        log(f"Batch: {len(candidates)} candidates with images + thin content")

        for row, photo_url in candidates[:remaining]:
            if total_updated + total_skipped + total_failed >= limit:
                break

            author = row.get("author_username", "unknown")
            time.sleep(1)  # Rate limit vision calls

            desc = describe_image(photo_url)
            if not desc:
                log(f"  FAIL @{author}: vision returned None")
                total_failed += 1
                continue

            new_content = row["content_text"].rstrip() + f"\n[image content: {desc}]"

            # Also reclassify with enriched content
            time.sleep(0.5)
            classification = classify_tweet(new_content, author)

            if dry_run:
                log(f"  [DRY RUN] @{author}: +image desc: {desc[:60]}...")
                total_updated += 1
            else:
                update = {"content_text": new_content}
                if classification:
                    update["summary"] = classification.get("summary")
                    update["sentiment"] = classification.get("sentiment")
                    update["signal_type"] = classification.get("signal_type")
                    update["category"] = classification.get("category")
                    update["tags"] = classification.get("tags", [])

                ok = supabase_patch("x_posts", row["id"], update)
                if ok:
                    log(f"  UPDATED @{author}: +image: {desc[:60]}...")
                    total_updated += 1
                else:
                    total_failed += 1

        if len(rows) < remaining * 5:
            break

    log(f"\nDone. Updated: {total_updated}, Skipped: {total_skipped}, Failed: {total_failed}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    limit_val = 200
    batch_val = 20

    for i, arg in enumerate(sys.argv):
        if arg == "--limit" and i + 1 < len(sys.argv):
            limit_val = int(sys.argv[i + 1])
        if arg == "--batch" and i + 1 < len(sys.argv):
            batch_val = int(sys.argv[i + 1])

    log(f"Backfill image descriptions — dry_run={dry_run}, limit={limit_val}, batch={batch_val}")
    backfill(dry_run=dry_run, limit=limit_val, batch_size=batch_val)
