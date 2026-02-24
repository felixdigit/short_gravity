#!/usr/bin/env python3
"""
Transcript Worker

Fetches ASTS earnings call transcripts from roic.ai.
Uses Playwright for JavaScript-rendered content.
Stores full transcripts in Supabase inbox.

Auto-discovers new quarters by checking roic.ai URL pattern.
Skips transcripts already stored in Supabase.

Usage:
    python3 transcript_worker.py              # Fetch new transcripts only
    python3 transcript_worker.py --force      # Re-fetch all transcripts

Environment:
    SUPABASE_URL, SUPABASE_SERVICE_KEY — Database
    ANTHROPIC_API_KEY — For AI summaries (optional)
"""

from __future__ import annotations
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Optional
import re

# Playwright import (installed separately)
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

ROIC_BASE = "https://www.roic.ai/quote/ASTS/transcripts"

# First known quarter (Q3 2021 — earliest ASTS earnings as public company)
FIRST_YEAR = 2021
FIRST_QUARTER = 3


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def generate_transcript_urls() -> List[Dict]:
    """Generate all possible transcript URLs from first quarter through current."""
    now = datetime.utcnow()
    current_year = now.year
    # Earnings calls happen ~6 weeks after quarter end,
    # so Q4 of previous year might be reported in Feb/Mar
    current_quarter = (now.month - 1) // 3 + 1

    transcripts = []
    year = FIRST_YEAR
    quarter = FIRST_QUARTER

    while True:
        if year > current_year or (year == current_year and quarter > current_quarter):
            break

        transcripts.append({
            "quarter": f"Q{quarter}",
            "year": str(year),
            "url": f"{ROIC_BASE}/{year}-year/{quarter}-quarter",
        })

        quarter += 1
        if quarter > 4:
            quarter = 1
            year += 1

    return transcripts


def fetch_transcript_playwright(url: str) -> str:
    """Fetch transcript using Playwright (handles JavaScript rendering)."""
    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install chromium")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )
        try:
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
            )
            page = context.new_page()
            page.set_default_navigation_timeout(60000)
            page.set_default_timeout(15000)

            log(f"  Loading page...")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Wait for transcript content to load — try multiple fallback selectors
            content_found = False
            selectors = [
                ("text=Good day", "Good day"),
                ("text=Operator", "Operator"),
                ("text=Earnings Call", "Earnings Call"),
                (".transcript-content", ".transcript-content CSS"),
            ]
            for selector, label in selectors:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    log(f"  Found transcript content via '{label}' selector")
                    content_found = True
                    break
                except Exception:
                    continue

            if not content_found:
                log(f"  No known selector matched, waiting for JS to render...")
                page.wait_for_timeout(5000)

            # Scroll to load all lazy content
            prev_height = 0
            for _ in range(30):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(300)
                curr_height = page.evaluate("document.body.scrollHeight")
                if curr_height == prev_height:
                    break
                prev_height = curr_height

            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(500)

            all_text = page.evaluate("document.body.innerText")

            # Extract just the transcript portion
            start = all_text.find("Good day")
            if start == -1:
                start = all_text.find("Operator")
            if start == -1:
                start = all_text.find("Earnings Call Transcript")
                if start != -1:
                    start = all_text.find("\n", start) + 1

            if start == -1:
                start = 0

            # Find end markers
            end_markers = ["Feedback", "Sign up", "Log in", "Company Search"]
            end = len(all_text)
            for marker in end_markers:
                pos = all_text.rfind(marker)
                if pos > start and pos < end:
                    end = pos

            log(f"  Extraction range: start={start}, end={end}, total_page_chars={len(all_text)}")

            transcript = all_text[start:end].strip()
            transcript = re.sub(r'\n{3,}', '\n\n', transcript)

            log(f"  Extracted transcript: {len(transcript):,} chars")

            # Quality check: very short transcripts are likely failed extractions
            if len(transcript) < 1000:
                log(f"  WARNING: Transcript too short ({len(transcript)} chars), likely a failed extraction")
                try:
                    page.screenshot(path=f"/tmp/debug_transcript_{int(time.time())}.png")
                    log(f"  DEBUG: Screenshot saved for transcript failure analysis")
                except Exception:
                    pass
                return ""

            return transcript

        except Exception as e:
            try:
                page.screenshot(path=f"/tmp/debug_transcript_{int(time.time())}.png")
                log(f"  DEBUG: Screenshot saved for failure analysis")
            except Exception:
                pass
            raise
        finally:
            browser.close()


def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
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


def get_existing_source_ids() -> set:
    try:
        result = supabase_request("GET", "inbox?source=eq.earnings_call&select=source_id")
        return {r["source_id"] for r in result}
    except Exception as e:
        log(f"Error fetching existing: {e}")
        return set()


def generate_summary(content: str) -> Optional[str]:
    """Generate AI summary using Claude."""
    if not ANTHROPIC_API_KEY:
        return None

    content_truncated = content[:50000]

    prompt = f"""Summarize this AST SpaceMobile earnings call in 2-3 paragraphs. Focus on:
1. Key financials (revenue, cash, burn rate)
2. Satellite updates (BlueBird launches, deployments)
3. Commercial progress (partnerships, spectrum)
4. Guidance

{content_truncated}"""

    data = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}]
    }

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(data).encode(),
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST"
    )

    try:
        log("  Generating summary...")
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode())
            return result["content"][0]["text"]
    except Exception as e:
        log(f"  Summary error: {e}")
        return None


def process_transcript(transcript: Dict, existing: set, force: bool = False) -> bool:
    """Process a single transcript. Returns True if new, False if skipped, None on error."""
    source_id = f"roic_{transcript['quarter']}_{transcript['year']}"

    if source_id in existing and not force:
        log(f"Skipping {transcript['quarter']} {transcript['year']} (exists)")
        return False

    log(f"Processing {transcript['quarter']} {transcript['year']}...")

    try:
        content = fetch_transcript_playwright(transcript["url"])
        log(f"  Extracted: {len(content):,} chars")

        if len(content) < 3000:
            log(f"  Skipping - too short ({len(content)} chars, likely no transcript yet)")
            return False

        if len(content) < 10000:
            log(f"  Warning: Content shorter than expected ({len(content)} chars)")

        # Try to extract the date from the page content
        date_str = transcript.get("date") or datetime.utcnow().strftime("%Y-%m-%d")

        summary = generate_summary(content)

        inbox_item = {
            "source": "earnings_call",
            "source_id": source_id,
            "title": f"ASTS {transcript['quarter']} FY{transcript['year']} Earnings Call Transcript",
            "published_at": f"{date_str}T17:00:00Z",
            "url": transcript["url"],
            "category": "quarterly_results",
            "tags": ["earnings", "transcript", transcript["quarter"].lower()],
            "importance": "high",
            "content_text": content,
            "content_length": len(content),
            "summary": summary,
            "summary_model": "claude-sonnet-4-6" if summary else None,
            "summary_generated_at": datetime.utcnow().isoformat() + "Z" if summary else None,
            "status": "completed",
            "metadata": json.dumps({
                "source_provider": "roic.ai",
                "fiscal_quarter": transcript["quarter"],
                "fiscal_year": transcript["year"],
            }),
        }

        supabase_request("POST", "inbox", inbox_item)
        log(f"  Stored")
        return True

    except Exception as e:
        log(f"  Error: {e}")
        return False


def run_worker(force: bool = False):
    """Main worker function."""
    log("=" * 60)
    log("Transcript Worker (roic.ai)")
    log(f"  Mode: {'FORCE' if force else 'INCREMENTAL'}")
    log("=" * 60)

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY required")
        sys.exit(1)

    existing = get_existing_source_ids()
    log(f"Found {len(existing)} existing transcripts")

    transcripts = generate_transcript_urls()
    log(f"Checking {len(transcripts)} possible quarters (Q{FIRST_QUARTER} {FIRST_YEAR} – now)")

    success = 0
    skipped = 0
    failed = 0

    for transcript in transcripts:
        result = process_transcript(transcript, existing, force)
        if result is True:
            success += 1
            time.sleep(2)
        elif result is False:
            skipped += 1
        else:
            failed += 1

    log("=" * 60)
    log(f"Completed: {success} added, {skipped} skipped, {failed} failed")
    log("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch ASTS earnings call transcripts")
    parser.add_argument("--force", action="store_true", help="Re-fetch all transcripts")
    args = parser.parse_args()
    run_worker(force=args.force)
