#!/usr/bin/env python3
"""
Backfill Storage for Existing SEC Filings

Uploads content_text from existing filings to Supabase Storage
and updates storage_path, full_content_hash, filing_size_bytes fields.

Run: python3 backfill_storage.py [--limit N] [--dry-run]
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

from storage_utils import upload_sec_filing, compute_hash

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


def log(msg: str):
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


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
        with urllib.request.urlopen(req, timeout=60) as response:
            content = response.read().decode("utf-8")
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        log(f"Supabase error: {e.code} - {error_body}")
        raise


def get_filings_without_storage(limit: int = 100) -> List[Dict]:
    """Get filings that don't have storage_path set."""
    endpoint = f"filings?storage_path=is.null&content_text=not.is.null&select=id,accession_number,form,content_text&order=filing_date.desc&limit={limit}"
    return supabase_request("GET", endpoint)


def update_filing(accession_number: str, updates: Dict) -> Dict:
    """Update filing in Supabase."""
    endpoint = f"filings?accession_number=eq.{accession_number}"
    return supabase_request("PATCH", endpoint, updates)


def backfill_filing(filing: Dict, dry_run: bool = False) -> bool:
    """Backfill storage for a single filing."""
    accession = filing["accession_number"]
    form = filing["form"]
    content = filing["content_text"]

    if not content:
        log(f"  Skipping {accession}: no content")
        return False

    content_bytes = content.encode("utf-8")
    content_hash = compute_hash(content_bytes)
    content_size = len(content_bytes)

    log(f"  {form} {accession}: {content_size:,} bytes")

    if dry_run:
        log(f"    [DRY RUN] Would upload to storage")
        return True

    # Upload to storage
    result = upload_sec_filing(
        accession_number=accession,
        form_type=form,
        content=content,
        document_name="primary.txt",
    )

    if not result.get("success"):
        log(f"    Upload failed: {result.get('error')}")
        return False

    storage_path = result.get("path")
    log(f"    Uploaded: {storage_path}")

    # Update database
    updates = {
        "storage_path": storage_path,
        "full_content_hash": content_hash,
        "filing_size_bytes": content_size,
    }

    update_filing(accession, updates)
    log(f"    Updated database")

    return True


def run_backfill(limit: int = 100, dry_run: bool = False):
    """Run storage backfill."""
    log("=" * 60)
    log("SEC Filing Storage Backfill")
    log("=" * 60)

    if dry_run:
        log("DRY RUN MODE - no changes will be made")

    if not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    # Get filings without storage
    log(f"Fetching up to {limit} filings without storage...")
    filings = get_filings_without_storage(limit)
    log(f"Found {len(filings)} filings to backfill")

    if not filings:
        log("No filings need backfill. Done.")
        return

    success = 0
    failed = 0

    for i, filing in enumerate(filings):
        log(f"[{i+1}/{len(filings)}] Processing {filing['accession_number']}")

        try:
            if backfill_filing(filing, dry_run):
                success += 1
            else:
                failed += 1
        except Exception as e:
            log(f"    Error: {e}")
            failed += 1

        # Rate limit
        if not dry_run:
            time.sleep(0.5)

    log("=" * 60)
    log(f"Completed: {success} success, {failed} failed")
    log("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Backfill storage for SEC filings")
    parser.add_argument("--limit", type=int, default=100, help="Max filings to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't make changes")
    args = parser.parse_args()

    run_backfill(limit=args.limit, dry_run=args.dry_run)
