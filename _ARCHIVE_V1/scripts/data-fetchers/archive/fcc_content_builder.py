#!/usr/bin/env python3
"""
FCC Filing Content Builder

Since FCC filing PDFs aren't directly accessible, this script builds
searchable content from the available metadata for RAG/search purposes.

For each filing, creates a structured content document combining:
- Filing number and type
- Title and description
- Dates (filed, granted, expiration)
- Status
- Filer information
- Call sign

Usage:
    python3 fcc_content_builder.py [--limit N]
"""

from __future__ import annotations
import json
import os
import sys
import urllib.request
from datetime import datetime
from typing import Dict, List, Optional

from storage_utils import upload_fcc_filing, compute_hash

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Filing type descriptions
FILING_TYPES = {
    "SAT-LOA": "Satellite Launch and Operating Authority Application",
    "SAT-MOD": "Satellite Modification Application",
    "SAT-AMD": "Satellite Application Amendment",
    "SAT-STA": "Satellite Special Temporary Authority",
    "SAT-ASG": "Satellite Assignment Application",
    "SAT-T/C": "Satellite Transfer of Control",
    "SAT-RPL": "Satellite Replacement Application",
    "SES-LIC": "Earth Station License Application",
    "SES-MOD": "Earth Station Modification",
    "SES-AMD": "Earth Station Amendment",
    "SES-STA": "Earth Station Special Temporary Authority",
    "SES-ASG": "Earth Station Assignment",
    "SES-T/C": "Earth Station Transfer of Control",
    "SES-REG": "Earth Station Registration",
    "SES-RWL": "Earth Station Renewal",
}


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None) -> any:
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as response:
        content = response.read().decode("utf-8")
        return json.loads(content) if content else {}


def get_all_fcc_filings(limit: int = 1000) -> List[Dict]:
    """Get all FCC filings."""
    endpoint = f"fcc_filings?select=*&order=filed_date.desc&limit={limit}"
    return supabase_request("GET", endpoint)


def build_filing_content(filing: Dict) -> str:
    """Build searchable content document from filing metadata."""
    file_number = filing.get("file_number", "")
    filing_type = filing.get("filing_type", "")
    type_desc = FILING_TYPES.get(filing_type, filing_type)

    parts = []

    # Header
    parts.append(f"FCC Filing: {file_number}")
    parts.append(f"Filing Type: {type_desc}")
    parts.append("")

    # Title and description
    title = filing.get("title")
    if title:
        parts.append(f"Title: {title}")

    description = filing.get("description")
    if description:
        parts.append(f"Description: {description}")

    parts.append("")

    # Applicant info
    filer = filing.get("filer_name")
    if filer:
        parts.append(f"Applicant: {filer}")

    call_sign = filing.get("call_sign")
    if call_sign:
        parts.append(f"Call Sign: {call_sign}")

    parts.append("")

    # Dates
    filed_date = filing.get("filed_date")
    if filed_date:
        parts.append(f"Filed Date: {filed_date}")

    grant_date = filing.get("grant_date")
    if grant_date:
        parts.append(f"Grant Date: {grant_date}")

    expiration_date = filing.get("expiration_date")
    if expiration_date:
        parts.append(f"Expiration Date: {expiration_date}")

    # Status
    status = filing.get("application_status")
    if status:
        parts.append(f"Status: {status}")

    parts.append("")

    # Filing system info
    system = filing.get("filing_system", "ICFS")
    parts.append(f"Filing System: FCC {system}")

    # Source
    source_url = filing.get("source_url")
    if source_url:
        parts.append(f"Source: {source_url}")

    # Metadata
    metadata = filing.get("metadata")
    if metadata:
        try:
            meta_dict = json.loads(metadata) if isinstance(metadata, str) else metadata
            if meta_dict.get("source"):
                parts.append(f"Data Source: {meta_dict.get('source')}")
        except:
            pass

    # Add context about what this filing type means
    parts.append("")
    parts.append("---")
    parts.append("Filing Type Context:")

    if "LOA" in filing_type:
        parts.append("This is a Launch and Operating Authority application, requesting FCC permission to launch and operate satellites.")
    elif "MOD" in filing_type:
        parts.append("This is a Modification application, requesting changes to an existing authorization.")
    elif "AMD" in filing_type:
        parts.append("This is an Amendment to a pending application, updating or correcting previously filed information.")
    elif "STA" in filing_type:
        parts.append("This is a Special Temporary Authority request, seeking short-term permission for specific operations.")
    elif "ASG" in filing_type:
        parts.append("This is an Assignment application, transferring license rights to another entity.")
    elif "T/C" in filing_type:
        parts.append("This is a Transfer of Control application, indicating a change in ownership or control.")
    elif "LIC" in filing_type:
        parts.append("This is a License application for operating an earth station.")
    elif "REG" in filing_type:
        parts.append("This is a Registration for an earth station.")

    if "SAT" in filing_type:
        parts.append("This filing relates to satellite operations under FCC Part 25 rules.")
    elif "SES" in filing_type:
        parts.append("This filing relates to earth station operations under FCC Part 25 rules.")

    return "\n".join(parts)


def update_filing_content(file_number: str, content_text: str):
    """Update filing with built content."""
    content_hash = compute_hash(content_text)

    endpoint = f"fcc_filings?file_number=eq.{file_number}"
    supabase_request("PATCH", endpoint, {
        "content_text": content_text,
        "content_hash": content_hash,
        "file_size_bytes": len(content_text.encode("utf-8")),
    })


def run_builder(limit: int = 1000):
    """Build content for all FCC filings."""
    log("=" * 60)
    log("FCC Filing Content Builder")
    log("=" * 60)

    if not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    log(f"Fetching FCC filings (limit {limit})...")
    filings = get_all_fcc_filings(limit)
    log(f"Found {len(filings)} filings")

    success = 0
    for i, filing in enumerate(filings):
        file_number = filing.get("file_number")

        try:
            content = build_filing_content(filing)
            update_filing_content(file_number, content)
            success += 1

            if (i + 1) % 50 == 0:
                log(f"Progress: {i+1}/{len(filings)}")

        except Exception as e:
            log(f"Error processing {file_number}: {e}")

    log("=" * 60)
    log(f"Built content for {success}/{len(filings)} filings")
    log("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FCC Filing Content Builder")
    parser.add_argument("--limit", type=int, default=1000, help="Max filings to process")
    args = parser.parse_args()
    run_builder(limit=args.limit)
