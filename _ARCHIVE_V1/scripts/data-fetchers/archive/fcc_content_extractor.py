#!/usr/bin/env python3
"""
FCC Filing Content Extractor

Downloads FCC filing PDFs and extracts text content for RAG/search.
Updates fcc_filings.content_text with extracted content.

Usage:
    python3 fcc_content_extractor.py [--limit N] [--dry-run]
"""

from __future__ import annotations
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, List, Optional

from pdf_extractor import extract_pdf_text
from storage_utils import upload_fcc_filing, compute_hash

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

RATE_LIMIT_SECONDS = 1.5


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
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        log(f"Supabase error: {e.code} - {error_body}")
        raise


def get_filings_without_content(limit: int = 100) -> List[Dict]:
    """Get FCC filings that don't have content_text."""
    endpoint = f"fcc_filings?content_text=is.null&select=id,file_number,filing_system,title,attachment_urls,source_url&order=filed_date.desc&limit={limit}"
    return supabase_request("GET", endpoint)


def update_filing_content(file_number: str, updates: Dict):
    """Update FCC filing with extracted content."""
    endpoint = f"fcc_filings?file_number=eq.{file_number}"
    supabase_request("PATCH", endpoint, updates)


def fetch_pdf(url: str) -> Optional[bytes]:
    """Fetch PDF from URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Short Gravity Research"
    }
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return response.read()
    except Exception as e:
        log(f"    Error fetching PDF: {e}")
        return None


def get_fcc_report_pdf_url(file_number: str) -> Optional[str]:
    """Get PDF URL from fcc.report."""
    # fcc.report provides PDF downloads for ICFS filings
    # Format: https://fcc.report/IBFS/{file_number}
    try:
        url = f"https://fcc.report/IBFS/{file_number}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Short Gravity Research"
        }
        req = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode("utf-8")

        # Look for PDF link in the page
        import re
        pdf_match = re.search(r'href="([^"]+\.pdf)"', html, re.IGNORECASE)
        if pdf_match:
            pdf_path = pdf_match.group(1)
            if pdf_path.startswith("http"):
                return pdf_path
            else:
                return f"https://fcc.report{pdf_path}"

        # Try direct PDF download
        return f"https://fcc.report/IBFS/{file_number}/download"

    except Exception as e:
        return None


def process_filing(filing: Dict, dry_run: bool = False) -> bool:
    """Process a single FCC filing - download PDF and extract content."""
    file_number = filing.get("file_number")
    filing_system = filing.get("filing_system", "ICFS")

    if not file_number:
        return False

    log(f"  {file_number}")

    # Get attachment URLs
    attachment_urls_raw = filing.get("attachment_urls")
    if attachment_urls_raw:
        try:
            attachment_urls = json.loads(attachment_urls_raw) if isinstance(attachment_urls_raw, str) else attachment_urls_raw
        except:
            attachment_urls = []
    else:
        attachment_urls = []

    # Try to find a PDF URL
    pdf_url = None

    # Method 1: Use attachment URLs if available
    for url in attachment_urls:
        if url and ('.pdf' in url.lower() or 'document' in url.lower()):
            pdf_url = url
            break

    # Method 2: Try fcc.report
    if not pdf_url:
        pdf_url = get_fcc_report_pdf_url(file_number)

    # Method 3: Use source_url
    if not pdf_url:
        source_url = filing.get("source_url")
        if source_url and '.pdf' in source_url.lower():
            pdf_url = source_url

    if not pdf_url:
        log(f"    No PDF URL found")
        return False

    if dry_run:
        log(f"    [DRY RUN] Would fetch: {pdf_url[:60]}...")
        return True

    # Fetch PDF
    log(f"    Fetching PDF...")
    pdf_bytes = fetch_pdf(pdf_url)

    if not pdf_bytes:
        return False

    log(f"    Downloaded {len(pdf_bytes):,} bytes")

    # Extract text
    log(f"    Extracting text...")
    content_text = extract_pdf_text(pdf_bytes)

    if not content_text or len(content_text) < 100:
        log(f"    No text extracted (possibly image-only PDF)")
        # Still update with empty content to mark as processed
        update_filing_content(file_number, {
            "content_text": "",
            "file_size_bytes": len(pdf_bytes),
        })
        return True

    log(f"    Extracted {len(content_text):,} chars")

    # Upload to storage
    content_hash = compute_hash(content_text)
    storage_result = upload_fcc_filing(
        filing_system=filing_system,
        file_number=file_number,
        content=content_text,
        filename="content.txt",
    )

    storage_path = storage_result.get("path") if storage_result.get("success") else None
    if storage_path:
        log(f"    Stored: {storage_path}")

    # Update database
    update_filing_content(file_number, {
        "content_text": content_text,
        "storage_path": storage_path,
        "content_hash": content_hash,
        "file_size_bytes": len(pdf_bytes),
    })

    log(f"    Database updated")
    return True


def run_extractor(limit: int = 100, dry_run: bool = False):
    """Run content extraction for FCC filings."""
    log("=" * 60)
    log("FCC Filing Content Extractor")
    log("=" * 60)

    if dry_run:
        log("DRY RUN MODE")

    if not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    # Get filings without content
    log(f"Fetching filings without content (limit {limit})...")
    filings = get_filings_without_content(limit)
    log(f"Found {len(filings)} filings to process")

    if not filings:
        log("No filings need content extraction. Done.")
        return

    success = 0
    failed = 0

    for i, filing in enumerate(filings):
        log(f"[{i+1}/{len(filings)}]")

        try:
            if process_filing(filing, dry_run):
                success += 1
            else:
                failed += 1
        except Exception as e:
            log(f"    Error: {e}")
            failed += 1

        # Rate limit
        if not dry_run:
            time.sleep(RATE_LIMIT_SECONDS)

        # Progress report
        if (i + 1) % 10 == 0:
            log(f"Progress: {i+1}/{len(filings)} ({success} success, {failed} failed)")

    log("=" * 60)
    log(f"Completed: {success} success, {failed} failed")
    log("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FCC Filing Content Extractor")
    parser.add_argument("--limit", type=int, default=100, help="Max filings to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't make changes")

    args = parser.parse_args()
    run_extractor(limit=args.limit, dry_run=args.dry_run)
