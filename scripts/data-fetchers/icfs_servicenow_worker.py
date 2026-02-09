#!/usr/bin/env python3
"""
FCC ICFS ServiceNow Worker — Scrapes the new FCC ICFS portal for AST SpaceMobile filings.

The FCC migrated IBFS to a ServiceNow-based platform at:
  fccprod.servicenowservices.com/icfs

Discovery strategy:
  1. Seed from known anchor filings (SAT-LOA-20200413-00034 for S3065, etc.)
  2. Navigate to each anchor's detail page → "Related Filings" tab
  3. Paginate through all related filings to discover file numbers
  4. Scrape detail page for each new filing

Usage:
    python3 icfs_servicenow_worker.py                  # Incremental
    python3 icfs_servicenow_worker.py --backfill        # Re-scrape all filings
    python3 icfs_servicenow_worker.py --dry-run         # Preview only

Environment:
    SUPABASE_URL, SUPABASE_SERVICE_KEY — Database
    ANTHROPIC_API_KEY — For AI summaries (optional)

Requires: playwright (pip install playwright && playwright install chromium)
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

# =============================================================================
# Configuration
# =============================================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

ICFS_BASE = "https://fccprod.servicenowservices.com/icfs"
ICFS_DETAIL_URL = f"{ICFS_BASE}?id=ibfs_application_summary&number="

# Seed anchor filings — one per call sign; "Related Filings" tab reveals all others
ANCHOR_FILINGS = [
    "SAT-LOA-20200413-00034",   # S3065 (primary NGSO license)
    "SAT-MOD-20241104-00251",   # S2983/3018
]

FILING_NUMBER_RE = re.compile(r'((?:SAT|SES)-[A-Z/]+-\d{8}-\d{3,5})')

RATE_LIMIT_SECONDS = 2.0


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# =============================================================================
# Supabase utilities
# =============================================================================

def supabase_headers() -> Dict:
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def supabase_get(endpoint: str) -> List[Dict]:
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    try:
        req = urllib.request.Request(url, headers=supabase_headers())
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error = e.read().decode() if e.fp else ""
        log(f"  Supabase GET error {e.code}: {error[:200]}")
        return []


def supabase_upsert(table: str, rows: List[Dict], on_conflict: str = "file_number,filing_system") -> int:
    if not rows:
        return 0
    url = f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={on_conflict}"
    headers = supabase_headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"

    count = 0
    for i in range(0, len(rows), 50):
        batch = rows[i:i + 50]
        try:
            body = json.dumps(batch).encode()
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            urllib.request.urlopen(req, timeout=30)
            count += len(batch)
        except urllib.error.HTTPError as e:
            error = e.read().decode() if e.fp else ""
            log(f"  Upsert error {e.code}: {error[:300]}")
    return count


def get_existing_file_numbers() -> Set[str]:
    rows = supabase_get("fcc_filings?select=file_number&filing_system=eq.ICFS")
    return {r["file_number"] for r in rows if r.get("file_number")}


def generate_ai_summary(title: str, content: str) -> Optional[str]:
    if not ANTHROPIC_API_KEY or not content:
        return None
    try:
        body = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 300,
            "messages": [{
                "role": "user",
                "content": (
                    "Summarize this FCC filing in 2-3 sentences for an $ASTS investor. "
                    "Focus on what changed or was requested.\n\n"
                    f"Title: {title}\n\nContent:\n{content[:3000]}"
                ),
            }]
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return data.get("content", [{}])[0].get("text", "")
    except Exception as e:
        log(f"  AI summary error: {e}")
        return None


# =============================================================================
# Playwright scraping
# =============================================================================

def discover_related_filings(page: Any, anchor: str) -> Set[str]:
    """Navigate to an anchor filing and extract all Related Filings via pagination."""
    url = f"{ICFS_DETAIL_URL}{anchor}"
    log(f"  Discovering filings from anchor: {anchor}")
    discovered: Set[str] = set()

    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(3)

        # Click "Related Filings" tab via JS (bypasses SPA visibility issues)
        page.evaluate("""() => {
            const links = document.querySelectorAll('a');
            for (const a of links) {
                if (a.textContent.trim() === 'Related Filings') {
                    a.click();
                    break;
                }
            }
        }""")
        time.sleep(3)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        # Extract filing numbers from current page
        text = page.evaluate("() => document.body?.innerText || ''")
        found = set(FILING_NUMBER_RE.findall(text))
        discovered.update(found)

        # Handle pagination — ServiceNow uses AngularJS setPageNum() links
        # Find numbered page buttons (e.g., "2", "3") that are not active
        max_pages = 10
        current_page = 1
        while current_page < max_pages:
            next_page = current_page + 1
            # Find the page button for Related Filings section
            # The buttons have text matching the page number and ng-click="setPageNum($index)"
            page_btns = page.query_selector_all(f'a.btn.btn-default:has-text("{next_page}")')

            clicked = False
            for btn in page_btns:
                ng_click = btn.get_attribute("ng-click") or ""
                if "setPageNum" in ng_click:
                    try:
                        page.evaluate("(el) => el.click()", btn)
                    except Exception:
                        break
                    time.sleep(2)
                    try:
                        page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        pass
                    text = page.evaluate("() => document.body?.innerText || ''")
                    new_found = set(FILING_NUMBER_RE.findall(text))
                    before = len(discovered)
                    discovered.update(new_found)
                    if len(discovered) == before:
                        break  # No new filings, stop paginating
                    clicked = True
                    break

            if not clicked:
                break
            current_page = next_page

        log(f"  Found {len(discovered)} related filings from {anchor}")

    except Exception as e:
        log(f"  Discovery error for {anchor}: {e}")

    return discovered


def parse_detail_text(text: str) -> Dict[str, str]:
    """Parse structured innerText from a filing detail page into field dict."""
    fields: Dict[str, str] = {}

    # The ServiceNow page renders labels and values as separate text blocks.
    # Pattern: "Label\nValue\n" or "Label\nValue "
    label_patterns = {
        "file_number": r"File Number\n(.+?)(?:\n|$)",
        "last_action": r"Last Action\n(.+?)(?:\n|$)",
        "application_status": r"Application Status\n(.+?)(?:\n|$)",
        "call_sign": r"Call Sign\n(.+?)(?:\n|$)",
        "last_action_date": r"Last Action Date\n(.+?)(?:\n|$)",
        "status_date": r"Status Date\n(.+?)(?:\n|$)",
        "da_number": r"DA Number\n(.+?)(?:\n|$)",
        "grant_date": r"Grant Date\n(.+?)(?:\n|$)",
        "date_filed": r"Date Filed\n(.+?)(?:\n|$)",
        "service_type": r"Service Type\n(.+?)(?:\n|$)",
        "streamlined": r"Streamlined\n(.+?)(?:\n|$)",
    }

    for key, pattern in label_patterns.items():
        match = re.search(pattern, text)
        if match:
            val = match.group(1).strip()
            if val and val != "—" and val != "-":
                fields[key] = val

    # Extract the filing subtype description (appears right after "Application Information")
    sub_match = re.search(r"Application Information\n\n(.+?)(?:\n|$)", text)
    if sub_match:
        fields["filing_subtype"] = sub_match.group(1).strip()

    # Extract applicant name from "Applicant Info" section
    app_match = re.search(r"FRN\(s\):\n\n(\d+)\n(.+?)(?:\n|$)", text)
    if app_match:
        fields["frn"] = app_match.group(1).strip()
        fields["filer_name"] = app_match.group(2).strip()

    return fields


def scrape_filing_detail(page: Any, file_number: str) -> Optional[Dict]:
    """Navigate to a filing detail page and extract all metadata."""
    url = f"{ICFS_DETAIL_URL}{file_number}"
    log(f"  Fetching: {file_number}")

    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(2)

        # Get all visible text — well-structured on ICFS detail pages
        text = page.evaluate("() => document.body?.innerText || ''")
        if not text or "Application Information" not in text:
            log(f"    No application data found")
            return None

        fields = parse_detail_text(text)

        # Parse dates
        filed_date = None
        raw_filed = fields.get("date_filed", "")
        if raw_filed:
            # Format: "2025-12-10 19:50:47" or "2025-12-10"
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    filed_date = datetime.strptime(raw_filed.strip(), fmt).strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue

        grant_date = None
        raw_grant = fields.get("grant_date", "")
        if raw_grant:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"):
                try:
                    grant_date = datetime.strptime(raw_grant.strip(), fmt).strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue

        # Derive filing type from file number
        filing_type = ""
        type_match = re.match(r'((?:SAT|SES)-[A-Z/]+)', file_number)
        if type_match:
            filing_type = type_match.group(1)

        filing_type_desc = {
            "SAT-LOA": "Launch & Operate",
            "SAT-MOD": "Modification",
            "SAT-AMD": "Amendment",
            "SAT-STA": "Special Temporary Authority",
            "SAT-RPL": "Replacement",
            "SAT-T/C": "Transfer of Control",
            "SES-LIC": "Earth Station License",
            "SES-MOD": "Earth Station Modification",
            "SES-STA": "Earth Station STA",
        }.get(filing_type, filing_type)

        filer = fields.get("filer_name", "AST & Science, LLC")
        title = f"{filer}: {filing_type_desc}"
        subtype = fields.get("filing_subtype", "")
        if subtype:
            title = f"{filer}: {filing_type_desc} — {subtype}"

        description = fields.get("last_action", "")
        call_sign = fields.get("call_sign", "")
        status = fields.get("application_status", "")

        # Build searchable content text (clean page text, truncated)
        page_text = re.sub(r'\s+', ' ', text).strip()[:10000]

        filing = {
            "file_number": file_number,
            "filing_system": "ICFS",
            "filer_name": filer,
            "call_sign": call_sign,
            "title": title,
            "description": description,
            "filing_type": filing_type or "ICFS",
            "filed_date": filed_date,
            "grant_date": grant_date,
            "application_status": status,
            "content_text": page_text,
            "source_url": url,
        }

        # AI summary for filings with substantive content
        if ANTHROPIC_API_KEY and page_text and len(page_text) > 200:
            summary = generate_ai_summary(title, page_text)
            if summary:
                filing["ai_summary"] = summary
                log(f"    AI summary generated")
            time.sleep(RATE_LIMIT_SECONDS)

        return filing

    except Exception as e:
        log(f"    Detail error: {e}")
        return None


# =============================================================================
# Main
# =============================================================================

def run(backfill: bool = False, dry_run: bool = False):
    log("=" * 60)
    log("ICFS SERVICENOW WORKER")
    log(f"  Mode: {'BACKFILL' if backfill else 'INCREMENTAL'}")
    log(f"  Dry run: {dry_run}")
    log("=" * 60)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    existing = set() if backfill else get_existing_file_numbers()
    log(f"  Existing ICFS filings in DB: {len(existing)}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()

        # Phase 1: Discover filings via "Related Filings" on anchor pages
        log("\n--- PHASE 1: DISCOVERY ---")
        all_discovered: Set[str] = set()
        for anchor in ANCHOR_FILINGS:
            related = discover_related_filings(page, anchor)
            all_discovered.update(related)
            time.sleep(RATE_LIMIT_SECONDS)

        log(f"\n  Total unique filings discovered: {len(all_discovered)}")

        # Filter to new filings only
        new_filings = sorted(all_discovered - existing)
        log(f"  New filings to process: {len(new_filings)}")

        if dry_run:
            for fn in new_filings:
                log(f"  [DRY RUN] {fn}")
            browser.close()
            return

        # Phase 2: Fetch detail for each new filing
        log("\n--- PHASE 2: DETAIL FETCH ---")
        upsert_rows = []
        for fn in new_filings:
            detail = scrape_filing_detail(page, fn)
            if detail:
                upsert_rows.append(detail)
                log(f"    {fn} — {detail.get('title', '?')[:60]}")
            else:
                log(f"    {fn} — SKIP (no data)")
            time.sleep(RATE_LIMIT_SECONDS)

        browser.close()

    # Phase 3: Upsert
    if upsert_rows:
        log(f"\n--- PHASE 3: DATABASE UPSERT ---")
        count = supabase_upsert("fcc_filings", upsert_rows)
        log(f"  Upserted {count} filings")
    else:
        log("\n  No new filings to upsert")

    log(f"\n{'=' * 60}")
    log(f"DONE: {len(upsert_rows)} filings processed")
    log(f"{'=' * 60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FCC ICFS ServiceNow Worker")
    parser.add_argument("--backfill", action="store_true", help="Re-scrape all filings")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    run(backfill=args.backfill, dry_run=args.dry_run)
