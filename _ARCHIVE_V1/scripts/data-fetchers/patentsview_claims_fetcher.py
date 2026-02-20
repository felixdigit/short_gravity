#!/usr/bin/env python3
"""
PatentsView Claims Fetcher

Fetches full claim text for US patents from PatentsView API (g_claim endpoint).
This fills the gap where Google Patents returns 404 for many US B1/B2 patents.

PatentsView has complete USPTO data - no indexing gaps.

Usage:
    python3 patentsview_claims_fetcher.py
    python3 patentsview_claims_fetcher.py --dry-run
    python3 patentsview_claims_fetcher.py --patent US10892818B1

Requirements: PATENTSVIEW_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY in .env
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Optional, Any

# Configuration
API_BASE_URL = "https://search.patentsview.org"
PATENTSVIEW_API_KEY = os.environ.get("PATENTSVIEW_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Rate limiting: 45 requests/minute
RATE_LIMIT_DELAY = 1.5


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def patentsview_request(endpoint: str, query: Dict, fields: List[str], size: int = 200) -> Dict:
    """Make PatentsView API request."""
    if not PATENTSVIEW_API_KEY:
        raise ValueError("PATENTSVIEW_API_KEY not set")

    url = f"{API_BASE_URL}/api/v1/{endpoint}/"
    headers = {
        "X-Api-Key": PATENTSVIEW_API_KEY,
        "Content-Type": "application/json",
    }

    body = {"q": query, "f": fields, "o": {"size": size}}
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        log(f"API error: {e.code} - {error_body[:200]}")
        return {"error": True}


def supabase_request(method: str, endpoint: str, data: Optional[Any] = None) -> Any:
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
            return json.loads(content) if content else []
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        raise Exception(f"Supabase {e.code}: {error_body[:200]}")


def patent_number_to_id(patent_number: str) -> str:
    """
    Convert DB patent number to PatentsView patent_id.
    US10892818B1 -> 10892818
    US20210044349A1 -> (skip applications)
    """
    if not patent_number.startswith("US"):
        return ""

    # Strip US prefix
    rest = patent_number[2:]

    # Extract just the number (remove kind code like B1, B2, A1)
    match = re.match(r'^(\d+)', rest)
    if match:
        return match.group(1)

    return ""


def parse_claim_type(claim_text: str) -> str:
    """Determine if claim is independent or dependent."""
    if not claim_text:
        return "independent"

    text_lower = claim_text.lower().strip()

    dependent_patterns = [
        r'^the .* of claim \d+',
        r'^a .* according to claim \d+',
        r'^the .* as claimed in claim \d+',
        r'^the .* as recited in claim \d+',
        r'^\d+\.\s*the .* of claim \d+',
    ]

    for pattern in dependent_patterns:
        if re.search(pattern, text_lower):
            return "dependent"

    return "independent"


def parse_depends_on(claim_text: str) -> Optional[List[int]]:
    """Extract claim numbers this claim depends on."""
    if not claim_text:
        return None

    matches = re.findall(r'claim[s]?\s+(\d+(?:\s*[-,]\s*\d+)*)', claim_text.lower())
    if not matches:
        return None

    depends = set()
    for match in matches:
        if '-' in match:
            parts = match.split('-')
            try:
                start = int(parts[0].strip())
                end = int(parts[1].strip())
                depends.update(range(start, end + 1))
            except ValueError:
                pass
        else:
            for num in re.findall(r'\d+', match):
                depends.add(int(num))

    return list(sorted(depends)) if depends else None


def get_us_patents_missing_claims() -> List[Dict]:
    """Get US patents that don't have claims in patent_claims table."""
    # Get all US patents
    patents = supabase_request(
        "GET",
        "patents?select=patent_number&patent_number=like.US*&limit=500"
    )

    # Get patents that already have claims
    existing = supabase_request(
        "GET",
        "patent_claims?select=patent_number"
    )
    existing_numbers = set(c["patent_number"] for c in existing)

    # Filter to granted patents only (B1, B2) - skip applications (A1)
    missing = []
    for p in patents:
        pn = p["patent_number"]
        if pn in existing_numbers:
            continue
        # Only include granted patents (B1, B2), not applications (A1)
        if re.search(r'B\d$', pn):
            missing.append(p)
        # Also include design patents if any (D)
        elif pn.startswith("USD") and pn.endswith("S"):
            missing.append(p)

    return missing


def fetch_claims_for_patent(patent_id: str) -> List[Dict]:
    """Fetch claims for a single patent from PatentsView."""
    query = {"patent_id": patent_id}
    fields = ["patent_id", "claim_sequence", "claim_text"]

    result = patentsview_request("g_claim", query, fields, size=200)

    if result.get("error"):
        return []

    return result.get("g_claims", [])


def insert_claims(patent_number: str, claims: List[Dict]) -> int:
    """Insert claims into patent_claims table."""
    inserted = 0

    for claim in claims:
        claim_num = claim.get("claim_sequence")
        claim_text = claim.get("claim_text", "")

        if not claim_num or not claim_text:
            continue

        claim_type = parse_claim_type(claim_text)
        depends_on = parse_depends_on(claim_text)

        try:
            data = {
                "patent_number": patent_number,
                "claim_number": int(claim_num),
                "claim_text": claim_text,
                "claim_type": claim_type,
            }
            if depends_on:
                data["depends_on"] = depends_on

            supabase_request(
                "POST",
                "patent_claims?on_conflict=patent_number,claim_number",
                data
            )
            inserted += 1
        except Exception as e:
            if inserted == 0:
                log(f"    Error: {e}")

    return inserted


def run_fetcher(dry_run: bool = False, single_patent: str = None):
    """Main fetcher."""
    log("=" * 60)
    log("PATENTSVIEW CLAIMS FETCHER")
    log("=" * 60)

    if not PATENTSVIEW_API_KEY:
        log("ERROR: PATENTSVIEW_API_KEY not set")
        sys.exit(1)

    if not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    # Get patents to process
    if single_patent:
        patents = [{"patent_number": single_patent}]
        log(f"Processing single patent: {single_patent}")
    else:
        patents = get_us_patents_missing_claims()
        log(f"Found {len(patents)} US patents missing claims")

    if not patents:
        log("No patents to process!")
        return

    # Process each patent
    total_claims = 0
    success_count = 0
    error_count = 0
    skip_count = 0

    for i, p in enumerate(patents):
        patent_number = p["patent_number"]
        patent_id = patent_number_to_id(patent_number)

        log(f"  [{i+1}/{len(patents)}] {patent_number}")

        if not patent_id:
            log(f"    -> Skipped (not a valid US patent number)")
            skip_count += 1
            continue

        # Fetch claims from PatentsView
        claims = fetch_claims_for_patent(patent_id)

        if not claims:
            log(f"    -> No claims found")
            error_count += 1
            time.sleep(RATE_LIMIT_DELAY)
            continue

        log(f"    -> Found {len(claims)} claims")

        if dry_run:
            total_claims += len(claims)
            success_count += 1
        else:
            inserted = insert_claims(patent_number, claims)
            if inserted > 0:
                log(f"    -> Inserted {inserted} claims")
                total_claims += inserted
                success_count += 1
            else:
                error_count += 1

        time.sleep(RATE_LIMIT_DELAY)

    # Summary
    log("")
    log("=" * 60)
    log("SUMMARY")
    log("=" * 60)
    log(f"Patents processed: {len(patents)}")
    log(f"Success: {success_count}")
    log(f"No claims found: {error_count}")
    log(f"Skipped: {skip_count}")
    log(f"Total claims {'found' if dry_run else 'inserted'}: {total_claims}")

    if not dry_run:
        # Verify final count
        final = supabase_request("GET", "patent_claims?select=id&limit=1&offset=0")
        log(f"\nRun patent_coverage_report.py to see updated coverage")

    log("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Fetch US patent claims from PatentsView")
    parser.add_argument("--dry-run", action="store_true", help="Don't insert, just count")
    parser.add_argument("--patent", help="Process single patent (e.g., US10892818B1)")
    args = parser.parse_args()

    run_fetcher(dry_run=args.dry_run, single_patent=args.patent)


if __name__ == "__main__":
    main()
