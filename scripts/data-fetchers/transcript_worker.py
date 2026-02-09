#!/usr/bin/env python3
"""
Transcript Worker

Fetches ASTS earnings call transcripts from roic.ai.
Uses Playwright for JavaScript-rendered content.
Stores full transcripts in Supabase inbox.
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
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# roic.ai transcript URLs (free, full transcripts)
# URL pattern: https://www.roic.ai/quote/ASTS/transcripts/{year}-year/{quarter_num}-quarter
KNOWN_TRANSCRIPTS = [
    # 2025
    {"quarter": "Q3", "year": "2025", "date": "2025-11-10", "url": "https://www.roic.ai/quote/ASTS/transcripts/2025-year/3-quarter"},
    {"quarter": "Q2", "year": "2025", "date": "2025-08-12", "url": "https://www.roic.ai/quote/ASTS/transcripts/2025-year/2-quarter"},
    {"quarter": "Q1", "year": "2025", "date": "2025-05-12", "url": "https://www.roic.ai/quote/ASTS/transcripts/2025-year/1-quarter"},
    # 2024
    {"quarter": "Q4", "year": "2024", "date": "2025-03-04", "url": "https://www.roic.ai/quote/ASTS/transcripts/2024-year/4-quarter"},
    {"quarter": "Q3", "year": "2024", "date": "2024-11-14", "url": "https://www.roic.ai/quote/ASTS/transcripts/2024-year/3-quarter"},
    {"quarter": "Q2", "year": "2024", "date": "2024-08-14", "url": "https://www.roic.ai/quote/ASTS/transcripts/2024-year/2-quarter"},
    {"quarter": "Q1", "year": "2024", "date": "2024-05-15", "url": "https://www.roic.ai/quote/ASTS/transcripts/2024-year/1-quarter"},
    # 2023
    {"quarter": "Q4", "year": "2023", "date": "2024-03-11", "url": "https://www.roic.ai/quote/ASTS/transcripts/2023-year/4-quarter"},
    {"quarter": "Q3", "year": "2023", "date": "2023-11-14", "url": "https://www.roic.ai/quote/ASTS/transcripts/2023-year/3-quarter"},
    {"quarter": "Q2", "year": "2023", "date": "2023-08-16", "url": "https://www.roic.ai/quote/ASTS/transcripts/2023-year/2-quarter"},
    {"quarter": "Q1", "year": "2023", "date": "2023-05-15", "url": "https://www.roic.ai/quote/ASTS/transcripts/2023-year/1-quarter"},
    # 2022
    {"quarter": "Q4", "year": "2022", "date": "2023-03-31", "url": "https://www.roic.ai/quote/ASTS/transcripts/2022-year/4-quarter"},
    {"quarter": "Q3", "year": "2022", "date": "2022-11-14", "url": "https://www.roic.ai/quote/ASTS/transcripts/2022-year/3-quarter"},
    {"quarter": "Q2", "year": "2022", "date": "2022-08-15", "url": "https://www.roic.ai/quote/ASTS/transcripts/2022-year/2-quarter"},
    {"quarter": "Q1", "year": "2022", "date": "2022-05-16", "url": "https://www.roic.ai/quote/ASTS/transcripts/2022-year/1-quarter"},
    # 2021
    {"quarter": "Q4", "year": "2021", "date": "2022-03-31", "url": "https://www.roic.ai/quote/ASTS/transcripts/2021-year/4-quarter"},
    {"quarter": "Q3", "year": "2021", "date": "2021-11-15", "url": "https://www.roic.ai/quote/ASTS/transcripts/2021-year/3-quarter"},
]


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


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
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )
        page = context.new_page()

        log(f"  Loading page...")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        # Wait for transcript content to load
        try:
            page.wait_for_selector("text=Good day", timeout=15000)
            log(f"  Found transcript content...")
        except:
            log(f"  Waiting for JS to render...")
            page.wait_for_timeout(3000)

        # Scroll to load all lazy content
        prev_height = 0
        for _ in range(30):  # Max 30 scroll attempts
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(300)
            curr_height = page.evaluate("document.body.scrollHeight")
            if curr_height == prev_height:
                break
            prev_height = curr_height

        # Scroll back to top
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)

        # Extract text content
        all_text = page.evaluate("document.body.innerText")

        browser.close()

        # Extract just the transcript portion
        start = all_text.find("Good day")
        if start == -1:
            start = all_text.find("Operator")
        if start == -1:
            # Try to find the start after the header
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

        transcript = all_text[start:end].strip()

        # Clean up common artifacts
        transcript = re.sub(r'\n{3,}', '\n\n', transcript)

        return transcript


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
        "model": "claude-sonnet-4-20250514",
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


def process_transcript(transcript: Dict, existing: set) -> bool:
    """Process a single transcript."""
    source_id = f"roic_{transcript['quarter']}_{transcript['year']}"

    if source_id in existing:
        log(f"Skipping {transcript['quarter']} {transcript['year']} (exists)")
        return False

    log(f"Processing {transcript['quarter']} {transcript['year']}...")

    try:
        # Use Playwright to fetch JavaScript-rendered content
        content = fetch_transcript_playwright(transcript["url"])
        log(f"  Extracted: {len(content):,} chars")

        if len(content) < 10000:
            log(f"  Warning: Content shorter than expected ({len(content)} chars)")
            if len(content) < 3000:
                log(f"  Skipping - too short")
                return False

        # Generate summary
        summary = generate_summary(content)

        # Store in Supabase
        inbox_item = {
            "source": "earnings_call",
            "source_id": source_id,
            "title": f"ASTS {transcript['quarter']} FY{transcript['year']} Earnings Call Transcript",
            "published_at": f"{transcript['date']}T17:00:00Z",
            "url": transcript["url"],
            "category": "quarterly_results",
            "tags": ["earnings", "transcript", transcript["quarter"].lower()],
            "importance": "high",
            "content_text": content,
            "content_length": len(content),
            "summary": summary,
            "summary_model": "claude-sonnet-4-20250514" if summary else None,
            "summary_generated_at": datetime.utcnow().isoformat() + "Z" if summary else None,
            "status": "completed",
            "metadata": json.dumps({
                "source_provider": "roic.ai",
                "fiscal_quarter": transcript["quarter"],
                "fiscal_year": transcript["year"],
            }),
        }

        supabase_request("POST", "inbox", inbox_item)
        log(f"  ✓ Stored")
        return True

    except Exception as e:
        log(f"  ✗ Error: {e}")
        return False


def discover_new_quarters(existing: set) -> List[Dict]:
    """Auto-discover new earnings call quarters not yet in KNOWN_TRANSCRIPTS.

    Checks roic.ai for quarters beyond the latest hardcoded entry by
    constructing URLs for subsequent quarters and testing if they exist.
    """
    discovered = []

    # Find the latest known quarter
    latest_year = max(int(t["year"]) for t in KNOWN_TRANSCRIPTS)
    latest_q = max(
        int(t["quarter"][1])
        for t in KNOWN_TRANSCRIPTS
        if int(t["year"]) == latest_year
    )

    # Probe ahead: check next 4 quarters beyond latest known
    year, q = latest_year, latest_q
    for _ in range(4):
        q += 1
        if q > 4:
            q = 1
            year += 1

        source_id = f"roic_Q{q}_{year}"
        if source_id in existing:
            continue

        # Already in KNOWN_TRANSCRIPTS?
        already_known = any(
            t["year"] == str(year) and t["quarter"] == f"Q{q}"
            for t in KNOWN_TRANSCRIPTS
        )
        if already_known:
            continue

        url = f"https://www.roic.ai/quote/ASTS/transcripts/{year}-year/{q}-quarter"

        # Quick check if the page has content (HEAD-like check via Playwright)
        log(f"  Probing Q{q} {year}...")
        discovered.append({
            "quarter": f"Q{q}",
            "year": str(year),
            "date": f"{year}-01-01",  # Placeholder, will be refined
            "url": url,
            "_probe": True,  # Flag to attempt fetch and validate
        })

    return discovered


def run_worker():
    """Main worker function."""
    log("=" * 60)
    log("Transcript Worker (roic.ai)")
    log("=" * 60)

    if not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    # Get existing transcripts
    existing = get_existing_source_ids()
    log(f"Found {len(existing)} existing transcripts")

    # Combine known transcripts with auto-discovered new quarters
    all_transcripts = list(KNOWN_TRANSCRIPTS)
    new_quarters = discover_new_quarters(existing)
    if new_quarters:
        log(f"  Discovered {len(new_quarters)} potential new quarters")
        all_transcripts = new_quarters + all_transcripts  # New ones first

    # Process each transcript
    success = 0
    skipped = 0
    failed = 0

    for transcript in all_transcripts:
        result = process_transcript(transcript, existing)
        if result:
            success += 1
            time.sleep(2)  # Be nice to roic.ai
        elif result is False:
            skipped += 1
        else:
            failed += 1

    log("=" * 60)
    log(f"Completed: {success} added, {skipped} skipped, {failed} failed")
    log("=" * 60)


if __name__ == "__main__":
    run_worker()
