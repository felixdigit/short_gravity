#!/usr/bin/env python3
"""
Populate earnings_calls table with historical ASTS earnings data.

ASTS went public via SPAC merger on April 6, 2021.
Dates sourced from SEC 8-K filings.
"""

import json
import os
import urllib.request
from datetime import datetime

SUPABASE_URL = "https://dviagnysjftidxudeuyo.supabase.co"
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Historical ASTS earnings calls - dates from SEC 8-K filings
EARNINGS_CALLS = [
    # 2021 (first year as public company)
    {
        "fiscal_year": 2021,
        "fiscal_quarter": 2,
        "call_date": "2021-08-16",
        "status": "transcript_pending",
    },
    {
        "fiscal_year": 2021,
        "fiscal_quarter": 3,
        "call_date": "2021-11-15",
        "status": "transcript_pending",
    },
    {
        "fiscal_year": 2021,
        "fiscal_quarter": 4,
        "call_date": "2022-03-31",  # FY2021 Q4 reported March 2022
        "status": "transcript_pending",
    },
    # 2022
    {
        "fiscal_year": 2022,
        "fiscal_quarter": 1,
        "call_date": "2022-05-16",
        "status": "transcript_pending",
    },
    {
        "fiscal_year": 2022,
        "fiscal_quarter": 2,
        "call_date": "2022-08-15",
        "status": "transcript_pending",
    },
    {
        "fiscal_year": 2022,
        "fiscal_quarter": 3,
        "call_date": "2022-11-14",
        "status": "transcript_pending",
    },
    {
        "fiscal_year": 2022,
        "fiscal_quarter": 4,
        "call_date": "2023-03-31",  # FY2022 Q4 reported March 2023
        "status": "transcript_pending",
    },
    # 2023
    {
        "fiscal_year": 2023,
        "fiscal_quarter": 1,
        "call_date": "2023-05-15",
        "status": "transcript_pending",
    },
    {
        "fiscal_year": 2023,
        "fiscal_quarter": 2,
        "call_date": "2023-08-14",
        "status": "transcript_pending",
    },
    {
        "fiscal_year": 2023,
        "fiscal_quarter": 3,
        "call_date": "2023-11-14",
        "status": "transcript_pending",
    },
    {
        "fiscal_year": 2023,
        "fiscal_quarter": 4,
        "call_date": "2024-04-01",  # FY2023 Q4 reported April 2024
        "status": "transcript_pending",
    },
    # 2024
    {
        "fiscal_year": 2024,
        "fiscal_quarter": 1,
        "call_date": "2024-05-15",
        "status": "transcript_pending",
    },
    {
        "fiscal_year": 2024,
        "fiscal_quarter": 2,
        "call_date": "2024-08-14",
        "status": "transcript_pending",
    },
    {
        "fiscal_year": 2024,
        "fiscal_quarter": 3,
        "call_date": "2024-11-14",
        "status": "transcript_pending",
    },
    {
        "fiscal_year": 2024,
        "fiscal_quarter": 4,
        "call_date": "2025-03-04",  # FY2024 Q4 reported March 2025
        "status": "transcript_pending",
    },
    # 2025
    {
        "fiscal_year": 2025,
        "fiscal_quarter": 1,
        "call_date": "2025-05-12",
        "status": "transcript_pending",
    },
    {
        "fiscal_year": 2025,
        "fiscal_quarter": 2,
        "call_date": "2025-08-11",
        "status": "transcript_pending",
    },
    {
        "fiscal_year": 2025,
        "fiscal_quarter": 3,
        "call_date": "2025-11-10",
        "status": "transcript_pending",
    },
]


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def supabase_request(endpoint: str, method: str = "GET", data: dict = None):
    """Make request to Supabase REST API."""
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
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        log(f"HTTP Error {e.code}: {error_body}")
        return None


def check_existing():
    """Check what earnings calls already exist."""
    result = supabase_request("earnings_calls?select=fiscal_year,fiscal_quarter")
    if result:
        return {(r["fiscal_year"], r["fiscal_quarter"]) for r in result}
    return set()


def insert_earnings_call(call: dict):
    """Insert a single earnings call."""
    result = supabase_request("earnings_calls", method="POST", data=call)
    return result is not None


def main():
    if not SUPABASE_SERVICE_KEY:
        log("Error: SUPABASE_SERVICE_KEY not set")
        return

    log("Checking existing earnings calls...")
    existing = check_existing()
    log(f"Found {len(existing)} existing records")

    inserted = 0
    skipped = 0

    for call in EARNINGS_CALLS:
        key = (call["fiscal_year"], call["fiscal_quarter"])
        if key in existing:
            log(f"  Skipping Q{call['fiscal_quarter']} {call['fiscal_year']} (exists)")
            skipped += 1
            continue

        log(f"  Inserting Q{call['fiscal_quarter']} {call['fiscal_year']} ({call['call_date']})...")
        if insert_earnings_call(call):
            inserted += 1
        else:
            log(f"    Failed to insert")

    log(f"\nDone: {inserted} inserted, {skipped} skipped")
    log(f"Total earnings calls in database: {len(existing) + inserted}")


if __name__ == "__main__":
    main()
