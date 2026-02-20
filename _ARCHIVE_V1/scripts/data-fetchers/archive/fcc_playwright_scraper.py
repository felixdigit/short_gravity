#!/usr/bin/env python3
"""
FCC Filing Content Scraper using Playwright

Uses headless browser to fetch FCC filing content that blocks automated requests.
Extracts text from FCC.gov pages and updates fcc_filings.content_text.

Supports both ICFS (satellite licenses) and ECFS (docket comments).

Usage:
    python3 fcc_playwright_scraper.py [--limit N] [--dry-run]
    python3 fcc_playwright_scraper.py --filing-system ECFS --limit 500
    python3 fcc_playwright_scraper.py --filing-system ICFS --limit 100
"""

from __future__ import annotations
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from typing import Dict, List, Optional
from playwright.sync_api import sync_playwright, Browser, Page

from storage_utils import upload_fcc_filing, compute_hash

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


def log(msg: str):
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None) -> any:
    """Make Supabase REST API request."""
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
        with urllib.request.urlopen(req, timeout=60) as response:
            content = response.read().decode("utf-8")
            return json.loads(content) if content else {}
    except Exception as e:
        log(f"Supabase error: {e}")
        raise


def get_filings_without_content(limit: int = 100, filing_system: Optional[str] = None) -> List[Dict]:
    """Get FCC filings that don't have content_text or have very short content."""
    # Base query: NULL content or very short content (< 200 chars)
    base = "fcc_filings?select=id,file_number,filing_system,title,source_url,metadata&order=filed_date.desc"

    # Filter by filing system if specified
    if filing_system:
        base += f"&filing_system=eq.{filing_system}"

    # Query for NULL content
    null_endpoint = f"{base}&content_text=is.null&limit={limit}"
    null_filings = supabase_request("GET", null_endpoint)

    # Also query for very short content (likely extraction failures)
    # This catches filings marked as processed but with minimal content
    if len(null_filings) < limit:
        remaining = limit - len(null_filings)
        # Get filings with content < 200 chars
        short_endpoint = f"{base}&content_text=neq.&limit={remaining}"
        short_filings = supabase_request("GET", short_endpoint)
        # Filter to only short content
        short_filings = [f for f in short_filings if len(f.get("content_text", "") or "") < 200]
        null_filings.extend(short_filings[:remaining])

    return null_filings


def update_filing_content(file_number: str, updates: Dict):
    """Update FCC filing with extracted content."""
    endpoint = f"fcc_filings?file_number=eq.{file_number}"
    supabase_request("PATCH", endpoint, updates)


def normalize_file_number(file_number: str) -> str:
    """Convert file number to FCC format (remove dashes)."""
    # SAT-LOA-20200727-00088 -> SATLOA2020072700088
    return file_number.replace("-", "")


def fetch_fcc_report_content(page: Page, file_number: str) -> Optional[str]:
    """Fetch filing content from fcc.report."""
    normalized = normalize_file_number(file_number)
    url = f"https://fcc.report/IBFS/{normalized}"

    try:
        page.goto(url, timeout=30000)
        page.wait_for_load_state("domcontentloaded")

        # Extract all text content from the page
        content = page.inner_text("body")

        # Clean up the content
        content = clean_content(content)

        if len(content) > 200:
            return content

    except Exception as e:
        log(f"    fcc.report error: {e}")

    return None


def fetch_fcc_gov_content(page: Page, file_number: str) -> Optional[str]:
    """Fetch filing content from FCC.gov ICFS."""
    normalized = normalize_file_number(file_number)
    url = f"https://licensing.fcc.gov/myibfs/displayLicense.do?fiession={normalized}"

    try:
        page.goto(url, timeout=30000)
        page.wait_for_load_state("domcontentloaded")

        # Check for access denied
        if "Access Denied" in page.content():
            return None

        # Extract all text content
        content = page.inner_text("body")
        content = clean_content(content)

        if len(content) > 200:
            return content

    except Exception as e:
        log(f"    FCC.gov error: {e}")

    return None


def fetch_ecfs_via_api(filing_id: str, api_key: str, max_retries: int = 3) -> tuple[Optional[str], Optional[bytes]]:
    """
    Fetch ECFS document content via API (preferred method).

    First checks API for filing details. If it's an express comment with no
    attachments, returns empty. If it has documents, tries to download them.

    Returns: (text_content, pdf_bytes)
    """
    import urllib.request
    import urllib.error

    text_content = None
    pdf_bytes = None

    # Query ECFS API for filing details with retry logic
    api_url = f"https://publicapi.fcc.gov/ecfs/filings/{filing_id}?api_key={api_key}"

    data = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(api_url, headers={
                "User-Agent": "Short Gravity Research",
                "Accept": "application/json"
            })
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            break  # Success, exit retry loop
        except urllib.error.HTTPError as e:
            if e.code == 429:
                # Rate limited - exponential backoff
                wait_time = 30 * (2 ** attempt)  # 30s, 60s, 120s
                log(f"    Rate limited (429). Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                log(f"    API error: {e}")
                return None, None
        except Exception as e:
            log(f"    API error: {e}")
            return None, None

    if not data:
        log(f"    API failed after {max_retries} retries")
        return None, None

    try:

        # Check if this is an express comment with no content
        express = data.get("express_comment", 0)
        documents = data.get("documents", [])
        attachments = data.get("attachments", [])
        text_data = data.get("text_data", "")

        # If it has text_data, use that
        if text_data:
            log(f"    Found text_data: {len(text_data)} chars")
            return text_data, None

        # If express comment with no documents, it's an empty submission
        if express and not documents and not attachments:
            log(f"    Express comment with no content")
            # Return a marker indicating this is intentionally empty
            return "[EXPRESS_COMMENT_NO_CONTENT]", None

        # Try to get document PDFs
        for doc in documents:
            src = doc.get("src", "")
            filename = doc.get("filename", "")

            log(f"    Document: {filename}")

            # Method 1: Use the direct files.fcc.gov URL from API (most reliable)
            if src and "files.fcc.gov" in src:
                try:
                    req = urllib.request.Request(src, headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                    })
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        pdf_bytes = resp.read()
                        if pdf_bytes and len(pdf_bytes) > 1000:
                            log(f"    Downloaded from files.fcc.gov: {len(pdf_bytes):,} bytes")
                            return None, pdf_bytes
                except Exception as e:
                    log(f"    files.fcc.gov failed: {e}")

            # Method 2: Try ecfsapi URL pattern as fallback
            if filename.lower().endswith(".pdf"):
                import urllib.parse
                encoded_filename = urllib.parse.quote(filename)
                ecfsapi_url = f"https://ecfsapi.fcc.gov/file/{filing_id}/{encoded_filename}"
                try:
                    req = urllib.request.Request(ecfsapi_url, headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                    })
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        pdf_bytes = resp.read()
                        if pdf_bytes and len(pdf_bytes) > 1000:
                            log(f"    Downloaded from ecfsapi: {len(pdf_bytes):,} bytes")
                            return None, pdf_bytes
                except Exception as e:
                    log(f"    ecfsapi failed: {e}")

        # If we get here, we couldn't extract content but the filing exists
        # Return indicator that we tried but got nothing
        return None, None

    except Exception as e:
        log(f"    Processing error: {e}")
        return None, None


def fetch_ecfs_document_content(page: Page, filing_id: str) -> tuple[Optional[str], Optional[bytes]]:
    """
    Fetch ECFS document content via Playwright browser (fallback method).

    ECFS URLs like fcc.gov/ecfs/document/XXXXX/1 are web pages, not direct PDFs.
    This function navigates to the page and either:
    1. Extracts text content from the page
    2. Finds and downloads embedded PDF attachment

    Returns: (text_content, pdf_bytes)
    """
    import urllib.request

    # Primary URL format
    url = f"https://www.fcc.gov/ecfs/document/{filing_id}/1"

    text_content = None
    pdf_bytes = None

    try:
        log(f"    Navigating to ECFS document page...")
        page.goto(url, timeout=45000, wait_until="domcontentloaded")

        # Wait for content to load
        page.wait_for_timeout(2000)

        # Check for various content types

        # 1. Look for embedded PDF viewer or download link
        pdf_links = page.locator('a[href*=".pdf"], a[href*="attachment"], a:has-text("Download"), a:has-text("View Document")')
        pdf_count = pdf_links.count()

        if pdf_count > 0:
            # Get the first PDF link
            href = pdf_links.first.get_attribute("href")
            if href:
                # Make absolute URL
                if href.startswith("/"):
                    href = f"https://www.fcc.gov{href}"
                elif not href.startswith("http"):
                    href = f"https://www.fcc.gov/ecfs/{href}"

                log(f"    Found PDF link: {href[:60]}...")

                # Check if it's a direct docs.fcc.gov PDF
                if "docs.fcc.gov" in href and href.lower().endswith(".pdf"):
                    # Direct download
                    try:
                        req = urllib.request.Request(href, headers={
                            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                        })
                        with urllib.request.urlopen(req, timeout=30) as resp:
                            pdf_bytes = resp.read()
                            log(f"    Downloaded PDF: {len(pdf_bytes):,} bytes")
                    except Exception as e:
                        log(f"    PDF download error: {e}")
                else:
                    # Navigate to the link and extract content
                    try:
                        page.goto(href, timeout=30000, wait_until="domcontentloaded")
                        page.wait_for_timeout(1000)
                        text_content = page.inner_text("body")
                    except Exception as e:
                        log(f"    Link navigation error: {e}")

        # 2. If no PDF found, extract text from the page itself
        if not text_content and not pdf_bytes:
            # Look for main content area
            selectors = [
                "div.filing-content",
                "div.document-content",
                "main",
                "article",
                "#content",
                ".content",
                "body",
            ]

            for selector in selectors:
                try:
                    elem = page.locator(selector).first
                    if elem.count() > 0:
                        text = elem.inner_text()
                        if len(text) > 200:
                            text_content = text
                            log(f"    Extracted text from {selector}")
                            break
                except:
                    continue

        # 3. Fallback: get full page text
        if not text_content and not pdf_bytes:
            text_content = page.inner_text("body")

    except Exception as e:
        log(f"    ECFS page error: {e}")

    return text_content, pdf_bytes


def clean_content(text: str) -> str:
    """Clean extracted web content."""
    import re

    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)

    # Remove common navigation elements
    lines = text.split('\n')
    cleaned_lines = []
    skip_patterns = [
        'Toggle navigation', 'navbar', 'Skip to', 'Cookie',
        'Google Analytics', 'Contact', 'About', 'Search',
        'FCC.report', 'FCC ID', 'IBFS', 'ELS',
    ]

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if any(pattern.lower() in line.lower() for pattern in skip_patterns):
            continue
        if len(line) < 3:
            continue
        cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


def process_filing(page: Page, filing: Dict, dry_run: bool = False, fcc_api_key: str = "") -> bool:
    """Process a single FCC filing."""
    file_number = filing.get("file_number")
    filing_system = filing.get("filing_system", "ICFS")

    if not file_number:
        return False

    log(f"  {file_number} ({filing_system})")

    if dry_run:
        log(f"    [DRY RUN] Would fetch content")
        return True

    content = None
    pdf_bytes = None
    source = None

    # Route based on filing system
    if filing_system == "ECFS":
        # ECFS filings: try API first (faster, more reliable)
        if fcc_api_key:
            content, pdf_bytes = fetch_ecfs_via_api(file_number, fcc_api_key)
            source = "ecfs-api"

            # Handle express comments with no content
            if content == "[EXPRESS_COMMENT_NO_CONTENT]":
                # Mark as intentionally empty (not an error)
                update_filing_content(file_number, {
                    "content_text": "[Express comment - no document content]",
                })
                log(f"    Marked as express comment (no content)")
                return True

        # If API didn't get content, try Playwright (fallback)
        if not content and not pdf_bytes:
            content, pdf_bytes = fetch_ecfs_document_content(page, file_number)
            source = "ecfs-playwright"

        # If we got PDF bytes, extract text
        if pdf_bytes and not content:
            try:
                from pdf_extractor import extract_pdf_text
                content = extract_pdf_text(pdf_bytes)
                source = "ecfs-pdf"
                log(f"    Extracted PDF text: {len(content):,} chars")
            except Exception as e:
                log(f"    PDF extraction error: {e}")

    else:
        # ICFS/ELS filings: use existing fcc.report/fcc.gov scrapers
        content = fetch_fcc_report_content(page, file_number)
        source = "fcc.report"

        if not content:
            log(f"    Trying FCC.gov...")
            content = fetch_fcc_gov_content(page, file_number)
            source = "fcc.gov"

    # Clean content if we have text
    if content:
        content = clean_content(content)

    if not content or len(content) < 100:
        log(f"    No content extracted")
        # Mark as processed with empty content to avoid reprocessing
        update_filing_content(file_number, {
            "content_text": "",
        })
        return False

    log(f"    Extracted {len(content):,} chars from {source}")

    # Compute hash and upload to storage
    content_hash = compute_hash(content)
    storage_result = upload_fcc_filing(
        filing_system=filing_system,
        file_number=file_number,
        content=content,
        filename="content.txt",
    )

    storage_path = storage_result.get("path") if storage_result.get("success") else None

    # Update database
    update_filing_content(file_number, {
        "content_text": content,
        "storage_path": storage_path,
        "content_hash": content_hash,
    })

    log(f"    Database updated")
    return True


def run_scraper(limit: int = 100, dry_run: bool = False, filing_system: Optional[str] = None):
    """Run content scraping for FCC filings."""
    log("=" * 60)
    log("FCC Filing Content Scraper (Playwright)")
    if filing_system:
        log(f"Filing System: {filing_system}")
    log("=" * 60)

    if dry_run:
        log("DRY RUN MODE")

    if not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    # Get FCC API key for ECFS
    fcc_api_key = os.environ.get("FCC_API_KEY", "")
    if filing_system == "ECFS" and fcc_api_key:
        log(f"FCC API Key: {fcc_api_key[:10]}...")

    # Get filings without content
    log(f"Fetching filings without content (limit {limit})...")
    filings = get_filings_without_content(limit, filing_system)
    log(f"Found {len(filings)} filings to process")

    if not filings:
        log("No filings need content extraction. Done.")
        return

    success = 0
    failed = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()

        for i, filing in enumerate(filings):
            log(f"[{i+1}/{len(filings)}]")

            try:
                if process_filing(page, filing, dry_run, fcc_api_key):
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                log(f"    Error: {e}")
                failed += 1

            # Rate limit - FCC API allows ~30 req/min, so 2s delay minimum
            if not dry_run:
                time.sleep(2.5)  # 24 requests/min, stays under 30/min limit

            # Progress report
            if (i + 1) % 10 == 0:
                log(f"Progress: {i+1}/{len(filings)} ({success} success, {failed} failed)")

        browser.close()

    log("=" * 60)
    log(f"Completed: {success} success, {failed} failed")
    log("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FCC Filing Content Scraper")
    parser.add_argument("--limit", type=int, default=100, help="Max filings to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't make changes")
    parser.add_argument("--filing-system", choices=["ECFS", "ICFS", "ELS"], help="Filter by filing system")

    args = parser.parse_args()
    run_scraper(limit=args.limit, dry_run=args.dry_run, filing_system=args.filing_system)
