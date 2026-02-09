#!/usr/bin/env python3
"""
Cash Position Historical Backfill

Extracts cash/liquidity data from ALL historic 10-Q and 10-K filings.
Uses the same extraction logic as cash_position_worker.py.
"""

from __future__ import annotations
import os
import sys

# Load env
if not os.environ.get("SUPABASE_SERVICE_KEY"):
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()

sys.path.insert(0, os.path.dirname(__file__))

import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

# Import extraction function from cash_position_worker
from cash_position_worker import extract_cash_data, supabase_request, check_existing, store_cash_position


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def get_all_quarterly_filings():
    """Get all 10-Q and 10-K filings with content."""
    params = urllib.parse.urlencode({
        "select": "accession_number,form,filing_date,content_text",
        "form": "in.(10-Q,10-K,10-Q/A,10-K/A)",
        "status": "eq.completed",
        "content_text": "not.is.null",
        "order": "filing_date.asc",
    })
    result = supabase_request(f"filings?{params}")
    return result or []


def main():
    log("=" * 60)
    log("CASH POSITION HISTORICAL BACKFILL")
    log("=" * 60)

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        log("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY")
        sys.exit(1)

    filings = get_all_quarterly_filings()
    log(f"Found {len(filings)} quarterly filings")

    success = 0
    skipped = 0
    failed = 0

    for i, filing in enumerate(filings):
        form = filing["form"]
        date = filing["filing_date"]
        acc = filing["accession_number"]
        content = filing.get("content_text", "")

        if not content or len(content) < 1000:
            log(f"  [{i+1}] {form} {date}: No content, skipping")
            skipped += 1
            continue

        if check_existing(date):
            log(f"  [{i+1}] {form} {date}: Already exists")
            skipped += 1
            continue

        log(f"  [{i+1}] {form} {date} ({acc})")
        data = extract_cash_data(content, form, date, acc)

        if not data.get("cash_and_equivalents") and not data.get("available_liquidity"):
            log(f"    No cash data extracted")
            failed += 1
            continue

        store_cash_position(data)
        success += 1

    log(f"\n{'=' * 60}")
    log(f"DONE: {success} new, {skipped} skipped, {failed} failed")
    log(f"{'=' * 60}")


if __name__ == "__main__":
    main()
