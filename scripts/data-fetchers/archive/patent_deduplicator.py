#!/usr/bin/env python3
"""
Patent Deduplicator

Removes B1 patent records when B2 exists (B2 supersedes B1).
This eliminates duplicate counting of the same intellectual property.

B1 = granted without pre-grant publication
B2 = granted with pre-grant publication (newer, more common post-2001)

Usage:
    python3 patent_deduplicator.py          # Dry run (show what would be deleted)
    python3 patent_deduplicator.py --execute  # Actually delete

Requirements: SUPABASE_URL, SUPABASE_SERVICE_KEY in .env
"""

import argparse
import json
import os
import re
import urllib.request
import urllib.error
from datetime import datetime
from collections import defaultdict

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def supabase_request(method: str, endpoint: str, data=None):
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
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode("utf-8")
            return json.loads(content) if content else []
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        raise Exception(f"Supabase {e.code}: {error_body[:200]}")


def fetch_paginated(endpoint: str, fields: str):
    """Fetch all records with pagination."""
    all_records = []
    offset = 0
    batch_size = 1000

    while True:
        records = supabase_request(
            "GET",
            f"{endpoint}?select={fields}&limit={batch_size}&offset={offset}"
        )
        if not records:
            break
        all_records.extend(records)
        if len(records) < batch_size:
            break
        offset += batch_size

    return all_records


def find_b1_b2_pairs():
    """Find patents where both B1 and B2 versions exist."""
    patents = fetch_paginated("patents", "patent_number")

    # Group by base number
    by_base = defaultdict(list)
    for p in patents:
        pn = p["patent_number"]
        # Extract base number for US patents
        match = re.match(r'^(US\d+)(B\d)$', pn)
        if match:
            base, kind = match.groups()
            by_base[base].append(pn)

    # Find pairs where both B1 and B2 exist
    pairs = []
    for base, versions in by_base.items():
        b1 = f"{base}B1"
        b2 = f"{base}B2"
        if b1 in versions and b2 in versions:
            pairs.append((b1, b2))

    return pairs


def count_claims(patent_number: str) -> int:
    """Count claims for a patent."""
    result = supabase_request(
        "GET",
        f"patent_claims?patent_number=eq.{patent_number}&select=id"
    )
    return len(result)


def delete_patent(patent_number: str, execute: bool = False):
    """Delete a patent and its claims."""
    if execute:
        # Delete claims first
        supabase_request(
            "DELETE",
            f"patent_claims?patent_number=eq.{patent_number}"
        )
        # Delete patent
        supabase_request(
            "DELETE",
            f"patents?patent_number=eq.{patent_number}"
        )
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Deduplicate B1/B2 patent pairs")
    parser.add_argument("--execute", action="store_true", help="Actually delete (default: dry run)")
    args = parser.parse_args()

    log("=" * 60)
    log("PATENT DEDUPLICATOR")
    log("=" * 60)

    if not args.execute:
        log("DRY RUN MODE - No changes will be made")
        log("Use --execute to actually delete records")
    else:
        log("EXECUTE MODE - Records will be deleted!")

    log("")

    # Get current counts
    patents_before = len(fetch_paginated("patents", "patent_number"))
    claims_before = len(fetch_paginated("patent_claims", "patent_number"))
    log(f"Before: {patents_before} patents, {claims_before} claims")
    log("")

    # Find B1/B2 pairs
    pairs = find_b1_b2_pairs()
    log(f"Found {len(pairs)} B1/B2 pairs to deduplicate")
    log("")

    if not pairs:
        log("No duplicates found. Database is clean!")
        return

    # Process each pair
    total_patents_deleted = 0
    total_claims_deleted = 0

    log("B1 patents to delete (keeping B2):")
    for b1, b2 in pairs:
        b1_claims = count_claims(b1)
        b2_claims = count_claims(b2)

        log(f"  {b1} ({b1_claims} claims) -> keeping {b2} ({b2_claims} claims)")

        if args.execute:
            delete_patent(b1, execute=True)

        total_patents_deleted += 1
        total_claims_deleted += b1_claims

    log("")
    log("=" * 60)
    log("SUMMARY")
    log("=" * 60)
    log(f"B1 patents {'deleted' if args.execute else 'to delete'}: {total_patents_deleted}")
    log(f"B1 claims {'deleted' if args.execute else 'to delete'}: {total_claims_deleted}")

    if args.execute:
        # Verify final counts
        patents_after = len(fetch_paginated("patents", "patent_number"))
        claims_after = len(fetch_paginated("patent_claims", "patent_number"))
        log("")
        log(f"After: {patents_after} patents, {claims_after} claims")
        log(f"Removed: {patents_before - patents_after} patents, {claims_before - claims_after} claims")
    else:
        log("")
        log(f"Expected after: {patents_before - total_patents_deleted} patents, {claims_before - total_claims_deleted} claims")
        log("")
        log("Run with --execute to apply changes")

    log("=" * 60)


if __name__ == "__main__":
    main()
