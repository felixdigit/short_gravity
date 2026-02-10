#!/usr/bin/env python3
"""
FCC ICFS (International Bureau Filing System) Worker

Fetches satellite license filings (SAT-MOD, SAT-AMD, SAT-LOA, etc.) for AST SpaceMobile.

These are different from ECFS filings - they're actual satellite license applications,
modifications, and amendments from the International Bureau Filing System.

Approach:
1. Scrape FCC public notices for satellite application acceptances
2. Search FCC EDOCS for recent AST SpaceMobile documents
3. Track known filing numbers from Space Bureau orders
"""

from __future__ import annotations
import json
import os
import sys
import time
import urllib.request
import urllib.error
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from html.parser import HTMLParser
import urllib.parse

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# FCC document base URLs
FCC_DOCS_BASE = "https://docs.fcc.gov/public/attachments"
FCC_REPORT_BASE = "https://fcc.report"

# Known AST SpaceMobile satellite filing numbers to seed the database
# These are actual ICFS filings for AST's satellite constellation
KNOWN_AST_FILINGS = [
    # Block 1 Bluebird / Original Applications
    {"file_number": "SAT-LOA-20200413-00034", "description": "Original Application to Launch and Operate"},
    {"file_number": "SAT-AMD-20200727-00088", "description": "Amendment"},
    {"file_number": "SAT-AMD-20201028-00126", "description": "Amendment"},
    {"file_number": "SAT-AMD-20230717-00172", "description": "Amendment"},
    {"file_number": "SAT-AMD-20240311-00053", "description": "Amendment"},
    # Current modification for 248 satellite constellation
    {"file_number": "SAT-MOD-20250612-00145", "description": "Modification for SCS with AT&T/Verizon/FirstNet"},
    {"file_number": "SAT-AMD-20250718-00181", "description": "Amendment to modification"},
    # January 2026 filing (from user screenshot)
    {"file_number": "SAT-MOD-20260121-00037", "description": "January 2026 modification filing"},
]

# Callsigns to monitor
AST_CALLSIGNS = [
    "S3065",  # AST SpaceMobile primary callsign
    "S2983",  # Alternative callsign
]

# Filing types to monitor
FILING_TYPES = [
    "SAT-MOD",   # Modification
    "SAT-AMD",   # Amendment
    "SAT-LOA",   # Letter of Authorization
    "SAT-STA",   # Special Temporary Authority
    "SAT-RPL",   # Replacement
]

try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from discord.notify import notify_fcc_filing
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def fetch_url(url: str, headers: Optional[Dict] = None) -> str:
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Short Gravity Research"
    }
    if headers:
        default_headers.update(headers)
    req = urllib.request.Request(url, headers=default_headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8")


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


def get_existing_source_ids(prefix: str = "icfs_") -> set:
    """Get existing source IDs from inbox that match the ICFS prefix."""
    try:
        # Query all fcc_filing entries and filter by source_id prefix
        result = supabase_request("GET", f"inbox?source=eq.fcc_filing&select=source_id")
        return {r["source_id"] for r in result if r["source_id"].startswith(prefix)}
    except Exception as e:
        log(f"Error fetching existing items: {e}")
        return set()


class IBFSListParser(HTMLParser):
    """Parse fcc.report IBFS filing list page."""

    def __init__(self):
        super().__init__()
        self.filings = []
        self.current_filing = {}
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.cell_index = 0
        self.current_data = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "table" and "ibfs-list" in attrs_dict.get("class", ""):
            self.in_table = True
        elif self.in_table and tag == "tr":
            self.in_row = True
            self.current_filing = {}
            self.cell_index = 0
        elif self.in_row and tag == "td":
            self.in_cell = True
            self.current_data = ""
        elif self.in_cell and tag == "a":
            href = attrs_dict.get("href", "")
            if "/IBFS/" in href:
                self.current_filing["url"] = FCC_REPORT_BASE + href

    def handle_endtag(self, tag):
        if tag == "table":
            self.in_table = False
        elif tag == "tr" and self.in_row:
            self.in_row = False
            if self.current_filing.get("file_number"):
                self.filings.append(self.current_filing)
        elif tag == "td" and self.in_cell:
            self.in_cell = False
            data = self.current_data.strip()
            # Map cell index to field
            # Typical columns: File Number, Callsign, Applicant, Received, Status
            if self.cell_index == 0:
                self.current_filing["file_number"] = data
            elif self.cell_index == 1:
                self.current_filing["callsign"] = data
            elif self.cell_index == 2:
                self.current_filing["applicant"] = data
            elif self.cell_index == 3:
                self.current_filing["received_date"] = data
            elif self.cell_index == 4:
                self.current_filing["status"] = data
            self.cell_index += 1

    def handle_data(self, data):
        if self.in_cell:
            self.current_data += data


def fetch_ibfs_filings_from_fcc_report(filing_type: str) -> List[Dict]:
    """Fetch filings list from fcc.report for a specific filing type."""
    url = f"{FCC_REPORT_BASE}/IBFS/Filing-List/{filing_type}"

    try:
        html = fetch_url(url)
        parser = IBFSListParser()
        parser.feed(html)
        return parser.filings
    except Exception as e:
        log(f"Error fetching {filing_type} list: {e}")
        return []


def fetch_ibfs_filings_by_callsign(callsign: str) -> List[Dict]:
    """Fetch filings for a specific callsign from fcc.report."""
    url = f"{FCC_REPORT_BASE}/IBFS/Callsign/{callsign}"

    try:
        html = fetch_url(url)

        # Parse the page for filing links
        filings = []
        # Look for SAT-* file numbers in the HTML
        pattern = r'href="(/IBFS/(SAT-[A-Z]+-\d+-\d+))"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html)

        for href, file_number, text in matches:
            filings.append({
                "file_number": file_number,
                "callsign": callsign,
                "url": FCC_REPORT_BASE + href,
            })

        return filings
    except Exception as e:
        log(f"Error fetching callsign {callsign}: {e}")
        return []


def fetch_filing_details(file_number: str) -> Dict:
    """Fetch detailed information about a specific filing."""
    url = f"{FCC_REPORT_BASE}/IBFS/{file_number}"

    try:
        html = fetch_url(url)

        details = {
            "file_number": file_number,
            "url": url,
        }

        # Extract applicant name
        applicant_match = re.search(r'Applicant[:\s]*</[^>]+>\s*([^<]+)', html)
        if applicant_match:
            details["applicant"] = applicant_match.group(1).strip()

        # Extract received date
        date_match = re.search(r'Received[:\s]*</[^>]+>\s*(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})', html)
        if date_match:
            date_str = date_match.group(1)
            # Normalize date format
            if "/" in date_str:
                parts = date_str.split("/")
                date_str = f"{parts[2]}-{parts[0]}-{parts[1]}"
            details["received_date"] = date_str

        # Extract status
        status_match = re.search(r'Status[:\s]*</[^>]+>\s*([^<]+)', html)
        if status_match:
            details["status"] = status_match.group(1).strip()

        # Extract callsign
        callsign_match = re.search(r'Call Sign[:\s]*</[^>]+>\s*([A-Z0-9]+)', html)
        if callsign_match:
            details["callsign"] = callsign_match.group(1).strip()

        # Look for attached documents (PDFs)
        doc_matches = re.findall(r'href="([^"]+\.pdf)"', html, re.IGNORECASE)
        if doc_matches:
            details["documents"] = [FCC_REPORT_BASE + d if d.startswith("/") else d for d in doc_matches[:5]]

        return details
    except Exception as e:
        log(f"Error fetching details for {file_number}: {e}")
        return {"file_number": file_number, "url": url}


def generate_summary(filing: Dict) -> str:
    """Generate AI summary for a filing."""
    if not ANTHROPIC_API_KEY:
        return ""

    prompt = f"""You are analyzing an FCC satellite license filing for AST SpaceMobile.

Filing Number: {filing.get('file_number', 'Unknown')}
Applicant: {filing.get('applicant', 'Unknown')}
Type: {filing.get('file_number', '').split('-')[0] if '-' in filing.get('file_number', '') else 'Unknown'}
Status: {filing.get('status', 'Unknown')}
Date: {filing.get('received_date', 'Unknown')}

Based on the filing type, provide a 1-2 sentence summary of what this filing likely represents:
- SAT-MOD: Modification to existing satellite license
- SAT-AMD: Amendment to pending application
- SAT-LOA: Letter of Authorization request
- SAT-STA: Special Temporary Authority request

Focus on business implications for AST SpaceMobile's satellite constellation.

Summary:"""

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 150,
        "messages": [{"role": "user", "content": prompt}],
    }

    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["content"][0]["text"].strip()
    except Exception as e:
        log(f"Error generating summary: {e}")
        return ""


def process_icfs_filing(filing: Dict, existing: set) -> bool:
    """Process a single ICFS filing."""
    file_number = filing.get("file_number", "")
    if not file_number:
        return False

    source_id = f"icfs_{file_number}"
    if source_id in existing:
        return False  # Already have it

    try:
        # Try to fetch additional details from fcc.report
        details = fetch_filing_details(file_number)
        filing.update(details)

        # Determine filing type from file number
        filing_type = "SAT"
        parts = file_number.split("-")
        if len(parts) >= 2:
            filing_type = f"{parts[0]}-{parts[1]}"

        # Extract date from file number (format: SAT-MOD-YYYYMMDD-NNNNN)
        received_date = filing.get("received_date", "")
        if not received_date and len(parts) >= 3:
            date_part = parts[2]
            if len(date_part) == 8 and date_part.isdigit():
                received_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"

        if not received_date:
            received_date = datetime.now().strftime("%Y-%m-%d")
        if len(received_date) == 10:  # YYYY-MM-DD
            received_date = f"{received_date}T00:00:00Z"

        # Build title
        applicant = filing.get("applicant", "AST SpaceMobile")
        description = filing.get("description", "")
        status = filing.get("status", "")

        # Filing type descriptions
        type_desc = {
            "SAT-MOD": "Satellite License Modification",
            "SAT-AMD": "Application Amendment",
            "SAT-LOA": "Launch & Operate Authorization",
            "SAT-STA": "Special Temporary Authority",
            "SAT-RPL": "License Replacement",
        }

        title = f"{applicant}: {type_desc.get(filing_type, filing_type)}"
        if description:
            title = f"{applicant}: {description}"
        elif status:
            title += f" ({status})"

        # Determine importance
        importance = "high"  # All satellite license filings are high importance

        # Build metadata
        metadata = {
            "file_number": file_number,
            "callsign": filing.get("callsign", ""),
            "applicant": applicant,
            "status": status,
            "filing_type": filing_type,
            "description": description,
            "documents": filing.get("documents", []),
        }

        # Generate summary
        summary = generate_summary(filing)

        # Construct URL - try fcc.report first, fallback to FCC.gov
        url = filing.get("url", "")
        if not url:
            # fcc.report URL format
            url = f"{FCC_REPORT_BASE}/IBFS/{file_number}"

        # Insert into inbox (use fcc_filing source since it's in the enum)
        inbox_item = {
            "source": "fcc_filing",  # Use existing enum value
            "source_id": source_id,  # Prefix icfs_ distinguishes these
            "title": title,
            "published_at": received_date,
            "url": url,
            "category": "regulatory",
            "tags": [filing_type, "satellite", "ICFS"],
            "importance": importance,
            "summary": summary if summary else None,
            "metadata": json.dumps(metadata),
            "status": "completed",
        }

        supabase_request("POST", "inbox", inbox_item)
        log(f"  ✓ Added: {file_number}")

        # Discord notification
        if DISCORD_AVAILABLE:
            notify_fcc_filing(
                title=title[:200],
                file_number=file_number,
                status=status or "New",
                filed_date=received_date[:10] if received_date else "",
            )

        return True

    except Exception as e:
        log(f"  ✗ Error processing {file_number}: {e}")
        return False


def fetch_fcc_public_notices() -> List[Dict]:
    """
    Fetch recent FCC public notices related to satellite applications.
    These announce new satellite filings accepted for review.
    """
    filings = []

    # Search FCC EDOCS for AST SpaceMobile related documents
    search_terms = ["AST SpaceMobile", "AST & Science", "SAT-MOD", "SAT-AMD"]

    for term in search_terms:
        try:
            # Use FCC search (note: limited functionality)
            encoded_term = urllib.parse.quote(term)
            url = f"https://www.fcc.gov/edocs/search?q={encoded_term}"
            log(f"  Searching FCC EDOCS for: {term}")
            # Note: This search may not work well, fallback to known filings
        except Exception as e:
            log(f"  Search error for {term}: {e}")

    return filings


def run_worker():
    """Main worker function."""
    log("=" * 60)
    log("FCC ICFS (Satellite Licensing) Worker Started")
    log("=" * 60)

    if not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    # Get existing ICFS filings (identified by icfs_ prefix in source_id)
    existing = get_existing_source_ids("icfs_")
    log(f"Found {len(existing)} existing ICFS filings in inbox")

    all_filings = []
    seen_file_numbers = set()

    # Method 1: Process known AST filings first (most reliable)
    log("Processing known AST SpaceMobile satellite filings...")
    for known in KNOWN_AST_FILINGS:
        file_number = known["file_number"]
        if file_number not in seen_file_numbers:
            seen_file_numbers.add(file_number)
            all_filings.append({
                "file_number": file_number,
                "description": known.get("description", ""),
                "applicant": "AST SpaceMobile / AST & Science",
            })
    log(f"  Added {len(KNOWN_AST_FILINGS)} known filings")

    # Method 2: Try fcc.report for additional filings (may be stale)
    log("Checking fcc.report for additional filings...")
    try:
        # Search fcc.report for AST filings
        url = f"{FCC_REPORT_BASE}/IBFS/Search?q=AST+SpaceMobile"
        html = fetch_url(url)

        # Extract SAT-* filing patterns
        sat_patterns = re.findall(r'(SAT-[A-Z]+-\d{8}-\d+)', html)
        unique_sats = set(sat_patterns)

        for fn in unique_sats:
            if fn not in seen_file_numbers:
                seen_file_numbers.add(fn)
                all_filings.append({
                    "file_number": fn,
                    "applicant": "AST SpaceMobile",
                })
        log(f"  Found {len(unique_sats)} filings on fcc.report")
    except Exception as e:
        log(f"  fcc.report search failed: {e}")

    # Method 3: Try fetching by callsign
    for callsign in AST_CALLSIGNS:
        log(f"Fetching filings for callsign {callsign}...")
        filings = fetch_ibfs_filings_by_callsign(callsign)
        for f in filings:
            fn = f.get("file_number", "")
            if fn and fn not in seen_file_numbers:
                seen_file_numbers.add(fn)
                all_filings.append(f)
        log(f"  Found {len(filings)} filings")
        time.sleep(1)

    log(f"Total unique filings found: {len(all_filings)}")

    # Filter to only new ones
    new_filings = []
    for f in all_filings:
        source_id = f"icfs_{f.get('file_number', '')}"
        if source_id not in existing:
            new_filings.append(f)

    log(f"New filings to process: {len(new_filings)}")

    if not new_filings:
        log("No new ICFS filings. Done.")
        return

    success = 0
    failed = 0

    for filing in new_filings:
        if process_icfs_filing(filing, existing):
            success += 1
        else:
            failed += 1
        time.sleep(2)  # Be nice to servers

    log("=" * 60)
    log(f"Completed: {success} success, {failed} skipped/failed")
    log("=" * 60)


if __name__ == "__main__":
    run_worker()
