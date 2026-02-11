#!/usr/bin/env python3
"""
FCC ULS/ELS Worker

Fetches experimental licenses and Universal Licensing System records for AST SpaceMobile.
Stores filings with filing_system='ELS' in the fcc_filings table.

Sources:
1. fcc.report ELS pages for experimental licenses
2. Known experimental call signs and file numbers

Usage:
    python3 uls_worker.py              # Standard run
    python3 uls_worker.py --backfill   # Process all filings
    python3 uls_worker.py --dry-run    # Don't write to database
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
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Set

from storage_utils import (
    upload_fcc_filing,
    upload_fcc_attachment,
    compute_hash,
    FCC_BUCKET,
    log,
)
from pdf_extractor import extract_pdf_text


# ============================================================================
# Configuration
# ============================================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# FCC.report base URL
FCC_REPORT_BASE = "https://fcc.report"

# AST SpaceMobile search patterns
AST_SEARCH_PATTERNS = [
    "AST SpaceMobile",
    "AST & Science",
    "AST Science",
    "BlueWalker",
    "BlueBird",
]

# Known AST SpaceMobile experimental licenses (seed data)
KNOWN_ELS_FILINGS = [
    # BlueWalker 3 experimental
    {"file_number": "0284-EX-CN-2025", "description": "V-band experimental license", "year": 2025},
    {"file_number": "0413-EX-CN-2021", "description": "BlueWalker 3 experimental", "year": 2021},
    {"file_number": "0010538493", "description": "ULS experimental license", "year": 2021},

    # BlueBird experimental
    {"file_number": "0514-EX-CN-2024", "description": "BlueBird experimental license", "year": 2024},
]

# Rate limits
RATE_LIMIT_SECONDS = 1.5


# ============================================================================
# HTTP Utilities
# ============================================================================

def fetch_url(url: str, headers: Optional[Dict] = None, retries: int = 3) -> str:
    """Fetch URL content with retry logic."""
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Short Gravity Research"
    }
    if headers:
        default_headers.update(headers)

    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=default_headers)
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

    raise last_error


def fetch_bytes(url: str, retries: int = 3) -> bytes:
    """Fetch binary content."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Short Gravity Research"
    }

    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as response:
                return response.read()
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

    raise last_error


# ============================================================================
# Supabase Operations
# ============================================================================

def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
    """Make Supabase REST API request."""
    if not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_SERVICE_KEY not set")

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


def get_existing_els_filings() -> Set[str]:
    """Get existing ELS filing file_numbers from database."""
    try:
        result = supabase_request("GET", "fcc_filings?filing_system=eq.ELS&select=file_number")
        return {r["file_number"] for r in result if r.get("file_number")}
    except Exception as e:
        log(f"Error fetching existing ELS filings: {e}")
        return set()


def upsert_fcc_filing(filing: Dict) -> Dict:
    """Insert or update FCC filing."""
    file_number = filing.get("file_number")
    filing_system = filing.get("filing_system", "ELS")

    # URL encode the file number for query
    encoded_fn = urllib.parse.quote(file_number, safe="")

    # Check if exists
    existing = supabase_request(
        "GET",
        f"fcc_filings?file_number=eq.{encoded_fn}&filing_system=eq.{filing_system}&select=id"
    )

    if existing:
        return supabase_request(
            "PATCH",
            f"fcc_filings?file_number=eq.{encoded_fn}&filing_system=eq.{filing_system}",
            filing
        )
    else:
        return supabase_request("POST", "fcc_filings", filing)


# ============================================================================
# FCC.report ELS Scraping
# ============================================================================

def search_fcc_report_els(query: str) -> List[Dict]:
    """Search fcc.report for experimental licenses."""
    encoded = urllib.parse.quote(query)
    url = f"{FCC_REPORT_BASE}/ELS/Search?q={encoded}"

    try:
        html = fetch_url(url)

        # Extract ELS file numbers (format: NNNN-EX-XX-YYYY or similar)
        patterns = [
            r'(\d{4}-EX-[A-Z]{2}-\d{4})',  # Standard ELS format
            r'(\d{10})',  # ULS format (10-digit)
        ]

        filings = []
        seen = set()

        for pattern in patterns:
            matches = re.findall(pattern, html)
            for file_number in matches:
                if file_number not in seen:
                    seen.add(file_number)
                    filings.append({
                        "file_number": file_number,
                        "source": "fcc.report_els_search",
                    })

        return filings

    except Exception as e:
        log(f"fcc.report ELS search error: {e}")
        return []


def fetch_fcc_report_els_company(company_slug: str) -> List[Dict]:
    """Fetch all ELS filings for a company from fcc.report."""
    url = f"{FCC_REPORT_BASE}/ELS/{company_slug}"

    try:
        html = fetch_url(url)

        # Find all ELS filing links
        patterns = [
            r'href="/ELS/(\d{4}-EX-[A-Z]{2}-\d{4})"',
            r'href="/ULS/(\d{10})"',
        ]

        filings = []
        seen = set()

        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for file_number in matches:
                if file_number not in seen:
                    seen.add(file_number)
                    filings.append({
                        "file_number": file_number,
                        "source": "fcc.report_els_company",
                    })

        return filings

    except Exception as e:
        log(f"fcc.report ELS company fetch error: {e}")
        return []


def fetch_els_details(file_number: str) -> Dict:
    """Fetch detailed information about an ELS filing."""
    # Try ELS page first
    url = f"{FCC_REPORT_BASE}/ELS/{file_number}"

    try:
        html = fetch_url(url)

        details = {
            "file_number": file_number,
            "source_url": url,
        }

        # Extract licensee/applicant
        applicant_patterns = [
            r'Licensee[:\s]*</[^>]+>\s*<[^>]+>\s*([^<]+)',
            r'Applicant[:\s]*</[^>]+>\s*<[^>]+>\s*([^<]+)',
            r'<td[^>]*>Licensee</td>\s*<td[^>]*>([^<]+)',
        ]
        for pattern in applicant_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                details["filer_name"] = match.group(1).strip()
                break

        # Extract call sign
        callsign_match = re.search(r'Call Sign[:\s]*</[^>]+>\s*<[^>]+>\s*([A-Z0-9]+)', html, re.IGNORECASE)
        if callsign_match:
            details["call_sign"] = callsign_match.group(1).strip()

        # Extract dates
        date_patterns = [
            (r'Grant Date[:\s]*</[^>]+>\s*<[^>]+>\s*(\d{4}-\d{2}-\d{2})', "grant_date"),
            (r'Expiration[:\s]*</[^>]+>\s*<[^>]+>\s*(\d{4}-\d{2}-\d{2})', "expiration_date"),
            (r'Effective[:\s]*</[^>]+>\s*<[^>]+>\s*(\d{4}-\d{2}-\d{2})', "filed_date"),
        ]
        for pattern, field in date_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                details[field] = match.group(1)

        # Extract status
        status_match = re.search(r'Status[:\s]*</[^>]+>\s*<[^>]+>\s*([^<]+)', html, re.IGNORECASE)
        if status_match:
            details["application_status"] = status_match.group(1).strip()

        # Extract purpose/description
        purpose_match = re.search(r'Purpose[:\s]*</[^>]+>\s*<[^>]+>\s*([^<]+)', html, re.IGNORECASE)
        if purpose_match:
            details["description"] = purpose_match.group(1).strip()

        # Extract frequency bands
        freq_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:MHz|GHz)', html, re.IGNORECASE)
        if freq_matches:
            details["frequencies"] = freq_matches[:10]

        # Find PDF attachments
        pdf_pattern = r'href="([^"]+\.pdf)"'
        pdf_matches = re.findall(pdf_pattern, html, re.IGNORECASE)
        if pdf_matches:
            attachment_urls = []
            for pdf_url in pdf_matches[:5]:
                if pdf_url.startswith("/"):
                    attachment_urls.append(FCC_REPORT_BASE + pdf_url)
                elif pdf_url.startswith("http"):
                    attachment_urls.append(pdf_url)
            if attachment_urls:
                details["attachment_urls"] = attachment_urls

        return details

    except Exception as e:
        log(f"Error fetching ELS details for {file_number}: {e}")
        return {"file_number": file_number, "source_url": url}


# ============================================================================
# AI Summary
# ============================================================================

def generate_els_summary(filing: Dict) -> str:
    """Generate AI summary for an ELS filing."""
    if not ANTHROPIC_API_KEY:
        return ""

    prompt = f"""You are analyzing an FCC experimental license for AST SpaceMobile.

File Number: {filing.get('file_number', 'Unknown')}
Applicant: {filing.get('filer_name', 'AST SpaceMobile')}
Call Sign: {filing.get('call_sign', 'Unknown')}
Status: {filing.get('application_status', 'Unknown')}
Grant Date: {filing.get('grant_date', 'Unknown')}
Expiration: {filing.get('expiration_date', 'Unknown')}
Frequencies: {', '.join(filing.get('frequencies', [])) or 'Unknown'}
Description: {filing.get('description', 'No description available')}

Provide a 1-2 sentence summary explaining what this experimental license authorizes and its significance for AST SpaceMobile's direct-to-device satellite operations.

Summary:"""

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": 150,
        "messages": [{"role": "user", "content": prompt}],
    }

    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["content"][0]["text"].strip()
    except Exception as e:
        log(f"Summary generation error: {e}")
        return ""


# ============================================================================
# Filing Discovery
# ============================================================================

def discover_all_els_filings() -> List[Dict]:
    """Discover all AST SpaceMobile ELS filings from multiple sources."""
    all_filings = {}  # file_number -> filing dict

    log("Discovering ELS filings...")

    # Source 1: Known filings (seed data)
    log("  [1/3] Loading known ELS filings...")
    for known in KNOWN_ELS_FILINGS:
        fn = known["file_number"]
        if fn not in all_filings:
            all_filings[fn] = {
                "file_number": fn,
                "description": known.get("description"),
                "source": "known_list",
            }
    log(f"       Found {len(KNOWN_ELS_FILINGS)} known filings")

    # Source 2: fcc.report company page
    log("  [2/3] Searching fcc.report ELS pages...")
    for slug in ["AST-Spacemobile", "AST-Science"]:
        filings = fetch_fcc_report_els_company(slug)
        for f in filings:
            fn = f["file_number"]
            if fn not in all_filings:
                all_filings[fn] = f
        time.sleep(RATE_LIMIT_SECONDS)
    log(f"       Total: {len(all_filings)} filings")

    # Source 3: Search for related terms
    log("  [3/3] Searching fcc.report...")
    for query in AST_SEARCH_PATTERNS[:3]:
        filings = search_fcc_report_els(query)
        for f in filings:
            fn = f["file_number"]
            if fn not in all_filings:
                all_filings[fn] = f
        time.sleep(RATE_LIMIT_SECONDS)
    log(f"       Total: {len(all_filings)} filings")

    return list(all_filings.values())


# ============================================================================
# Filing Processing
# ============================================================================

def process_filing(filing: Dict, dry_run: bool = False, no_summary: bool = False) -> bool:
    """Process a single ELS filing."""
    file_number = filing.get("file_number")
    if not file_number:
        return False

    log(f"Processing: {file_number}")

    if dry_run:
        log("  [DRY RUN] Would process this filing")
        return True

    try:
        # Fetch detailed information
        details = fetch_els_details(file_number)
        filing.update(details)
        time.sleep(RATE_LIMIT_SECONDS)

        # Build title
        filer = filing.get("filer_name", "AST SpaceMobile")
        desc = filing.get("description", "Experimental License")
        title = f"{filer}: {desc}"

        # Generate summary
        summary = ""
        if not no_summary:
            log("  Generating summary...")
            summary = generate_els_summary(filing)
            if summary:
                log(f"  Summary: {summary[:60]}...")
            time.sleep(RATE_LIMIT_SECONDS)

        # Prepare database record
        db_record = {
            "filing_system": "ELS",
            "file_number": file_number,
            "call_sign": filing.get("call_sign"),
            "filing_type": "Experimental License",
            "title": title,
            "description": filing.get("description"),
            "filer_name": filer,
            "filed_date": filing.get("filed_date"),
            "grant_date": filing.get("grant_date"),
            "expiration_date": filing.get("expiration_date"),
            "application_status": filing.get("application_status"),
            "source_url": filing.get("source_url"),
            "attachment_urls": json.dumps(filing.get("attachment_urls", [])),
            "metadata": json.dumps({
                "source": filing.get("source"),
                "frequencies": filing.get("frequencies", []),
                "discovered_at": datetime.utcnow().isoformat(),
            }),
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "status": "completed",
        }

        if summary:
            db_record.update({
                "ai_summary": summary,
                "ai_model": "claude-3-5-haiku-20241022",
                "ai_generated_at": datetime.utcnow().isoformat() + "Z",
            })

        # Process PDF attachments if available - do this BEFORE inserting to get content
        content_text = ""
        attachment_urls = filing.get("attachment_urls", [])
        if attachment_urls:
            _, content_text = process_attachments(file_number, attachment_urls)

        # Add content_text to record
        if content_text:
            db_record["content_text"] = content_text
            db_record["content_hash"] = compute_hash(content_text)
            log(f"  Total content: {len(content_text):,} chars")

        # Upsert to database
        upsert_fcc_filing(db_record)
        log(f"  ✓ Database updated")

        return True

    except Exception as e:
        log(f"  ✗ Error: {e}")
        return False


def process_attachments(file_number: str, urls: List[str]) -> tuple[int, str]:
    """Download and store filing attachments. Returns (count, combined_content_text)."""
    processed = 0
    all_content = []

    for i, url in enumerate(urls[:3]):  # Limit to 3 attachments
        try:
            filename = url.split("/")[-1]
            if not filename:
                filename = f"attachment_{i+1}.pdf"

            log(f"  Downloading: {filename}")
            content = fetch_bytes(url)
            time.sleep(RATE_LIMIT_SECONDS)

            # Extract text if PDF
            content_text = ""
            if filename.lower().endswith(".pdf"):
                content_text = extract_pdf_text(content)
                if content_text:
                    log(f"    Extracted {len(content_text):,} chars")
                    all_content.append(f"=== {filename} ===\n{content_text}")

            # Upload to storage
            storage_result = upload_fcc_attachment(
                file_number=file_number,
                attachment_number=i + 1,
                content=content,
                filename=filename,
                content_type="application/pdf",
            )

            if storage_result.get("success"):
                processed += 1
                log(f"    ✓ Stored")

        except Exception as e:
            log(f"    ✗ Error: {e}")

    combined_text = "\n\n".join(all_content) if all_content else ""
    return processed, combined_text


# ============================================================================
# Main
# ============================================================================

def run_worker(args):
    """Main worker function."""
    log("=" * 60)
    log("FCC ULS/ELS Worker")
    log("=" * 60)

    if not args.dry_run and not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    # Discover all filings
    all_filings = discover_all_els_filings()
    log(f"Total filings discovered: {len(all_filings)}")

    # Get existing filings
    existing = get_existing_els_filings()
    log(f"Already in database: {len(existing)}")

    # Determine what to process
    if args.backfill:
        to_process = all_filings
        log(f"Backfill mode: processing all {len(to_process)} filings")
    else:
        to_process = [f for f in all_filings if f["file_number"] not in existing]
        log(f"New filings to process: {len(to_process)}")

    if not to_process:
        log("Nothing to process. Done.")
        return

    log("-" * 60)
    success = 0
    failed = 0

    for i, filing in enumerate(to_process):
        log(f"[{i+1}/{len(to_process)}]")

        if process_filing(filing, dry_run=args.dry_run, no_summary=args.no_summary):
            success += 1
        else:
            failed += 1

        if (i + 1) % 10 == 0:
            log(f"Progress: {i+1}/{len(to_process)} ({success} success, {failed} failed)")

    log("=" * 60)
    log(f"Completed: {success} success, {failed} failed")
    log("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FCC ULS/ELS Worker")
    parser.add_argument("--backfill", action="store_true", help="Process all filings (not just new)")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to database")
    parser.add_argument("--no-summary", action="store_true", help="Skip AI summary generation")

    args = parser.parse_args()
    run_worker(args)
