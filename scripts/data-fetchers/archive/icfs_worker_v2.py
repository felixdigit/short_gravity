#!/usr/bin/env python3
"""
FCC ICFS (International Bureau Filing System) Worker v2

Comprehensive ICFS worker that discovers ALL AST SpaceMobile satellite filings
via multiple sources and stores full documents in Supabase Storage.

Sources:
1. FCC LMS (License Management System) API - authoritative source
2. fcc.report scraping - historical coverage
3. Known filings list - seed data
4. Call sign lookup - catch-all

Usage:
    # Standard run (incremental)
    python3 icfs_worker_v2.py

    # Full backfill (all historical)
    python3 icfs_worker_v2.py --backfill

    # Dry run
    python3 icfs_worker_v2.py --dry-run
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
import re
from datetime import datetime
from typing import Dict, List, Optional, Set
from html.parser import HTMLParser

# Import storage utilities
from storage_utils import (
    upload_fcc_filing,
    upload_fcc_attachment,
    compute_hash,
    FCC_BUCKET,
    log,
)


# ============================================================================
# Configuration
# ============================================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# AST SpaceMobile identifiers
AST_COMPANY_NAMES = [
    "AST SpaceMobile",
    "AST & Science",
    "AST Science",
    "AST & Science, LLC",
    "AST SpaceMobile, Inc.",
]

AST_CALLSIGNS = [
    "S3065",   # Primary satellite callsign
    "S2983",   # Secondary
]

# FCC URLs
FCC_LMS_API = "https://licensing.fcc.gov/myibfs/api"
FCC_REPORT_BASE = "https://fcc.report"
FCC_ICFS_BASE = "https://licensing.fcc.gov/cgi-bin/ws.exe/prod/ib/forms/reports/swr031b.hts"

# Filing type descriptions
FILING_TYPES = {
    "SAT-LOA": "Launch and Operate Authorization",
    "SAT-MOD": "License Modification",
    "SAT-AMD": "Application Amendment",
    "SAT-STA": "Special Temporary Authority",
    "SAT-RPL": "License Replacement",
    "SAT-T/C": "Transfer of Control",
    "SAT-ASG": "Assignment",
    "SES-LIC": "Earth Station License",
    "SES-MOD": "Earth Station Modification",
    "SES-STA": "Earth Station STA",
}

# Known AST SpaceMobile filings (seed data)
KNOWN_FILINGS = [
    # Primary constellation license
    {"file_number": "SAT-LOA-20200413-00034", "description": "Original SpaceMobile constellation application", "year": 2020},
    {"file_number": "SAT-AMD-20200727-00088", "description": "Amendment to original application", "year": 2020},
    {"file_number": "SAT-AMD-20201028-00126", "description": "Amendment to application", "year": 2020},
    {"file_number": "SAT-AMD-20230717-00172", "description": "Amendment for BlueBird deployment", "year": 2023},
    {"file_number": "SAT-AMD-20240311-00053", "description": "Amendment for 248-satellite constellation", "year": 2024},

    # Modifications
    {"file_number": "SAT-MOD-20250612-00145", "description": "SCS modification with AT&T/Verizon/FirstNet", "year": 2025},
    {"file_number": "SAT-AMD-20250718-00181", "description": "Amendment to SCS modification", "year": 2025},
    {"file_number": "SAT-MOD-20260121-00037", "description": "January 2026 modification", "year": 2026},

    # BlueWalker 3 experimental
    {"file_number": "SAT-STA-20220414-00040", "description": "BlueWalker 3 STA", "year": 2022},
    {"file_number": "SAT-STA-20220801-00087", "description": "BlueWalker 3 operations STA", "year": 2022},

    # Earth stations
    {"file_number": "SES-LIC-20200522-00563", "description": "Gateway earth station license", "year": 2020},
    {"file_number": "SES-MOD-20230915-01234", "description": "Gateway modification", "year": 2023},
]

# Rate limits
RATE_LIMIT_SECONDS = 1.0


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


def fetch_json(url: str) -> Dict:
    """Fetch JSON from URL."""
    content = fetch_url(url, {"Accept": "application/json"})
    return json.loads(content)


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


def get_existing_fcc_filings() -> Set[str]:
    """Get existing FCC filing file_numbers from database."""
    try:
        result = supabase_request("GET", "fcc_filings?select=file_number")
        return {r["file_number"] for r in result if r.get("file_number")}
    except Exception as e:
        log(f"Error fetching existing FCC filings: {e}")
        return set()


def upsert_fcc_filing(filing: Dict) -> Dict:
    """Insert or update FCC filing."""
    file_number = filing.get("file_number")
    filing_system = filing.get("filing_system", "ICFS")

    # Check if exists
    existing = supabase_request(
        "GET",
        f"fcc_filings?file_number=eq.{file_number}&filing_system=eq.{filing_system}&select=id"
    )

    if existing:
        return supabase_request(
            "PATCH",
            f"fcc_filings?file_number=eq.{file_number}&filing_system=eq.{filing_system}",
            filing
        )
    else:
        return supabase_request("POST", "fcc_filings", filing)


def insert_fcc_attachment(attachment: Dict) -> Dict:
    """Insert FCC attachment record."""
    return supabase_request("POST", "fcc_filing_attachments", attachment)


# ============================================================================
# FCC API / Scraping
# ============================================================================

def search_fcc_report(query: str) -> List[Dict]:
    """Search fcc.report for filings."""
    encoded = urllib.parse.quote(query)
    url = f"{FCC_REPORT_BASE}/IBFS/Search?q={encoded}"

    try:
        html = fetch_url(url)

        # Extract SAT-* and SES-* filing patterns
        filing_pattern = r'((?:SAT|SES)-[A-Z/]+-\d{8}-\d+)'
        matches = set(re.findall(filing_pattern, html))

        filings = []
        for file_number in matches:
            filings.append({
                "file_number": file_number,
                "source": "fcc.report_search",
            })

        return filings
    except Exception as e:
        log(f"fcc.report search error: {e}")
        return []


def fetch_fcc_report_company_filings(company_slug: str) -> List[Dict]:
    """Fetch all filings for a company from fcc.report."""
    url = f"{FCC_REPORT_BASE}/company/{company_slug}"

    try:
        html = fetch_url(url)

        # Find all IBFS filing links
        pattern = r'href="/IBFS/((?:SAT|SES)-[^"]+)"'
        matches = set(re.findall(pattern, html))

        filings = []
        for file_number in matches:
            filings.append({
                "file_number": file_number,
                "source": "fcc.report_company",
            })

        return filings
    except Exception as e:
        log(f"fcc.report company fetch error: {e}")
        return []


def fetch_fcc_report_callsign(callsign: str) -> List[Dict]:
    """Fetch filings for a specific callsign from fcc.report."""
    url = f"{FCC_REPORT_BASE}/IBFS/Callsign/{callsign}"

    try:
        html = fetch_url(url)

        filings = []
        pattern = r'href="/IBFS/((?:SAT|SES)-[A-Z/]+-\d{8}-\d+)"'
        matches = set(re.findall(pattern, html))

        for file_number in matches:
            filings.append({
                "file_number": file_number,
                "callsign": callsign,
                "source": "fcc.report_callsign",
            })

        return filings
    except Exception as e:
        log(f"fcc.report callsign fetch error for {callsign}: {e}")
        return []


def fetch_filing_details_fcc_report(file_number: str) -> Dict:
    """Fetch detailed information about a filing from fcc.report."""
    url = f"{FCC_REPORT_BASE}/IBFS/{file_number}"

    try:
        html = fetch_url(url)

        details = {
            "file_number": file_number,
            "source_url": url,
        }

        # Extract applicant/licensee
        applicant_patterns = [
            r'Applicant[:\s]*</[^>]+>\s*<[^>]+>\s*([^<]+)',
            r'Licensee[:\s]*</[^>]+>\s*<[^>]+>\s*([^<]+)',
            r'<td[^>]*>Applicant</td>\s*<td[^>]*>([^<]+)',
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
            (r'Received[:\s]*</[^>]+>\s*<[^>]+>\s*(\d{4}-\d{2}-\d{2})', "filed_date"),
            (r'Granted?[:\s]*</[^>]+>\s*<[^>]+>\s*(\d{4}-\d{2}-\d{2})', "grant_date"),
            (r'Expiration[:\s]*</[^>]+>\s*<[^>]+>\s*(\d{4}-\d{2}-\d{2})', "expiration_date"),
        ]
        for pattern, field in date_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                details[field] = match.group(1)

        # Fallback: extract date from file number
        if "filed_date" not in details:
            parts = file_number.split("-")
            if len(parts) >= 3 and len(parts[2]) == 8 and parts[2].isdigit():
                details["filed_date"] = f"{parts[2][:4]}-{parts[2][4:6]}-{parts[2][6:8]}"

        # Extract status
        status_match = re.search(r'Status[:\s]*</[^>]+>\s*<[^>]+>\s*([^<]+)', html, re.IGNORECASE)
        if status_match:
            details["application_status"] = status_match.group(1).strip()

        # Extract description/purpose
        desc_match = re.search(r'Purpose[:\s]*</[^>]+>\s*<[^>]+>\s*([^<]+)', html, re.IGNORECASE)
        if desc_match:
            details["description"] = desc_match.group(1).strip()

        # Find attached documents
        doc_patterns = [
            r'href="([^"]+\.pdf)"',
            r'href="(/IBFS/[^"]+/attachment/[^"]+)"',
        ]
        attachment_urls = []
        for pattern in doc_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                if match.startswith("/"):
                    attachment_urls.append(FCC_REPORT_BASE + match)
                elif match.startswith("http"):
                    attachment_urls.append(match)

        if attachment_urls:
            details["attachment_urls"] = list(set(attachment_urls))[:10]

        return details

    except Exception as e:
        log(f"Error fetching filing details for {file_number}: {e}")
        return {"file_number": file_number, "source_url": url}


def search_fcc_icfs_direct(applicant_name: str) -> List[Dict]:
    """
    Search FCC ICFS directly via the web interface.
    This is a more authoritative source than fcc.report.
    """
    # FCC ICFS search URL
    encoded_name = urllib.parse.quote(applicant_name)
    url = f"https://licensing.fcc.gov/cgi-bin/ws.exe/prod/ib/forms/reports/swr031b.hts?applicant={encoded_name}"

    try:
        html = fetch_url(url)

        filings = []
        # Parse the results table
        pattern = r'((?:SAT|SES)-[A-Z/]+-\d{8}-\d+)'
        matches = set(re.findall(pattern, html))

        for file_number in matches:
            filings.append({
                "file_number": file_number,
                "filer_name": applicant_name,
                "source": "fcc_icfs_direct",
            })

        return filings
    except Exception as e:
        log(f"FCC ICFS direct search error: {e}")
        return []


# ============================================================================
# AI Summary
# ============================================================================

def generate_fcc_summary(filing: Dict) -> str:
    """Generate AI summary for an FCC filing."""
    if not ANTHROPIC_API_KEY:
        return ""

    file_number = filing.get("file_number", "Unknown")
    filing_type = file_number.split("-")[0] + "-" + file_number.split("-")[1] if "-" in file_number else "Unknown"
    type_desc = FILING_TYPES.get(filing_type, filing_type)

    prompt = f"""You are analyzing an FCC satellite/earth station filing for AST SpaceMobile.

Filing Number: {file_number}
Filing Type: {type_desc}
Applicant: {filing.get('filer_name', 'AST SpaceMobile')}
Status: {filing.get('application_status', 'Unknown')}
Call Sign: {filing.get('call_sign', 'Unknown')}
Filed Date: {filing.get('filed_date', 'Unknown')}
Description: {filing.get('description', 'No description available')}

Based on this information, provide a 1-2 sentence summary of what this filing likely represents and its business implications for AST SpaceMobile's direct-to-device satellite constellation.

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

def discover_all_filings() -> List[Dict]:
    """Discover all AST SpaceMobile FCC filings from multiple sources."""
    all_filings = {}  # file_number -> filing dict

    log("Discovering FCC filings...")

    # Source 1: Known filings (seed data)
    log("  [1/5] Loading known filings...")
    for known in KNOWN_FILINGS:
        fn = known["file_number"]
        if fn not in all_filings:
            all_filings[fn] = {
                "file_number": fn,
                "description": known.get("description"),
                "source": "known_list",
            }
    log(f"       Found {len(KNOWN_FILINGS)} known filings")

    # Source 2: fcc.report company page
    log("  [2/5] Searching fcc.report company pages...")
    for slug in ["Ast-Spacemobile", "Ast-Science"]:
        filings = fetch_fcc_report_company_filings(slug)
        for f in filings:
            fn = f["file_number"]
            if fn not in all_filings:
                all_filings[fn] = f
        time.sleep(RATE_LIMIT_SECONDS)
    log(f"       Total: {len(all_filings)} filings")

    # Source 3: fcc.report search
    log("  [3/5] Searching fcc.report...")
    for query in AST_COMPANY_NAMES[:2]:  # Limit to avoid rate limiting
        filings = search_fcc_report(query)
        for f in filings:
            fn = f["file_number"]
            if fn not in all_filings:
                all_filings[fn] = f
        time.sleep(RATE_LIMIT_SECONDS)
    log(f"       Total: {len(all_filings)} filings")

    # Source 4: Callsign lookup
    log("  [4/5] Looking up by callsign...")
    for callsign in AST_CALLSIGNS:
        filings = fetch_fcc_report_callsign(callsign)
        for f in filings:
            fn = f["file_number"]
            if fn not in all_filings:
                all_filings[fn] = f
            elif "callsign" not in all_filings[fn]:
                all_filings[fn]["call_sign"] = callsign
        time.sleep(RATE_LIMIT_SECONDS)
    log(f"       Total: {len(all_filings)} filings")

    # Source 5: Direct FCC ICFS search
    log("  [5/5] Searching FCC ICFS directly...")
    for name in ["AST SpaceMobile", "AST & Science"]:
        filings = search_fcc_icfs_direct(name)
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
    """Process a single FCC filing."""
    file_number = filing.get("file_number")
    if not file_number:
        return False

    log(f"Processing: {file_number}")

    if dry_run:
        log("  [DRY RUN] Would process this filing")
        return True

    try:
        # Fetch detailed information
        details = fetch_filing_details_fcc_report(file_number)
        filing.update(details)
        time.sleep(RATE_LIMIT_SECONDS)

        # Determine filing type
        parts = file_number.split("-")
        filing_type = f"{parts[0]}-{parts[1]}" if len(parts) >= 2 else "SAT"
        type_desc = FILING_TYPES.get(filing_type, filing_type)

        # Build title
        filer = filing.get("filer_name", "AST SpaceMobile")
        desc = filing.get("description", type_desc)
        title = f"{filer}: {desc}"

        # Generate summary (skip if --no-summary)
        summary = ""
        if not no_summary:
            log("  Generating summary...")
            summary = generate_fcc_summary(filing)
            if summary:
                log(f"  Summary: {summary[:60]}...")
            time.sleep(RATE_LIMIT_SECONDS)

        # Prepare database record
        db_record = {
            "filing_system": "ICFS",
            "file_number": file_number,
            "call_sign": filing.get("call_sign"),
            "filing_type": filing_type,
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

        # Upsert to database
        upsert_fcc_filing(db_record)
        log(f"  ✓ Database updated")

        # Process attachments (PDFs)
        attachment_urls = filing.get("attachment_urls", [])
        if attachment_urls:
            process_attachments(file_number, attachment_urls, dry_run)

        return True

    except Exception as e:
        log(f"  ✗ Error: {e}")
        return False


def process_attachments(file_number: str, urls: List[str], dry_run: bool = False) -> int:
    """Download and store filing attachments."""
    if dry_run:
        log(f"  [DRY RUN] Would process {len(urls)} attachments")
        return 0

    processed = 0
    for i, url in enumerate(urls[:5]):  # Limit to 5 attachments
        try:
            # Determine filename
            filename = url.split("/")[-1]
            if not filename or filename == "":
                filename = f"attachment_{i+1}.pdf"

            log(f"  Downloading: {filename}")
            content = fetch_bytes(url)
            time.sleep(RATE_LIMIT_SECONDS)

            # Determine content type
            content_type = "application/pdf" if filename.lower().endswith(".pdf") else "application/octet-stream"

            # Upload to storage
            storage_result = upload_fcc_attachment(
                file_number=file_number,
                attachment_number=i + 1,
                content=content,
                filename=filename,
                content_type=content_type,
            )

            if storage_result.get("success"):
                # Insert attachment record
                attachment_record = {
                    "file_number": file_number,
                    "attachment_number": i + 1,
                    "filename": filename,
                    "content_type": content_type,
                    "file_size_bytes": len(content),
                    "storage_path": storage_result.get("path"),
                    "content_hash": storage_result.get("hash"),
                    "source_url": url,
                    "fetched_at": datetime.utcnow().isoformat() + "Z",
                }
                insert_fcc_attachment(attachment_record)
                processed += 1
                log(f"    ✓ Stored")

        except Exception as e:
            log(f"    ✗ Error: {e}")

    return processed


# ============================================================================
# Main
# ============================================================================

def run_worker(args):
    """Main worker function."""
    log("=" * 60)
    log("FCC ICFS Worker v2")
    log("=" * 60)

    if not args.dry_run and not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    # Discover all filings
    all_filings = discover_all_filings()
    log(f"Total filings discovered: {len(all_filings)}")

    # Get existing filings
    existing = get_existing_fcc_filings()
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

    # Sort by date (oldest first for backfill)
    to_process.sort(key=lambda x: x.get("file_number", ""))

    log("-" * 60)
    success = 0
    failed = 0

    for i, filing in enumerate(to_process):
        log(f"[{i+1}/{len(to_process)}]")

        if process_filing(filing, dry_run=args.dry_run, no_summary=args.no_summary):
            success += 1
        else:
            failed += 1

        # Progress report
        if (i + 1) % 10 == 0:
            log(f"Progress: {i+1}/{len(to_process)} ({success} success, {failed} failed)")

    log("=" * 60)
    log(f"Completed: {success} success, {failed} failed")
    log("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FCC ICFS Worker v2")
    parser.add_argument("--backfill", action="store_true", help="Process all filings (not just new)")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to database")
    parser.add_argument("--no-summary", action="store_true", help="Skip AI summary generation")

    args = parser.parse_args()
    run_worker(args)
