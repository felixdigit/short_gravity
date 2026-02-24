#!/usr/bin/env python3
"""
Earnings Date Discovery Worker

Fetches upcoming earnings call dates from Finnhub and upserts into
the earnings_transcripts table. Dates only — EPS/revenue estimates are
out of scope (Thread 003 concern).

Schedule: Weekly Wednesday (same cadence as transcript_worker)

Usage:
    python3 earnings_worker.py
    python3 earnings_worker.py --dry-run
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, date
from typing import Dict, List, Optional

# ============================================================================
# Configuration
# ============================================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")

FINNHUB_BASE = "https://finnhub.io/api/v1"

# ASTS fiscal year = calendar year
SYMBOL = "ASTS"
COMPANY = "ASTS"


def log(msg: str):
    print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] {msg}")


# ============================================================================
# HTTP
# ============================================================================

def fetch_json(url: str, retries: int = 3) -> Optional[Dict]:
    """Fetch JSON with retry logic."""
    headers = {"Accept": "application/json"}
    last_error = None

    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code == 429:
                wait = 10 * (attempt + 1)
                log(f"  Rate limited (429). Waiting {wait}s...")
                time.sleep(wait)
            elif attempt < retries - 1:
                time.sleep(2 ** attempt)
        except urllib.error.URLError as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

    log(f"  Fetch failed after {retries} attempts: {last_error}")
    return None


def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[list]:
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
        error_body = e.read().decode("utf-8")
        log(f"  Supabase error: {e.code} - {error_body}")
        return None


# ============================================================================
# Finnhub Earnings Calendar
# ============================================================================

def fetch_earnings_calendar() -> List[Dict]:
    """Fetch upcoming earnings dates from Finnhub calendar endpoint."""
    today = date.today()
    # Look 2 years ahead for comprehensive coverage
    from_date = f"{today.year - 1}-01-01"
    to_date = f"{today.year + 1}-12-31"

    url = f"{FINNHUB_BASE}/calendar/earnings?symbol={SYMBOL}&from={from_date}&to={to_date}&token={FINNHUB_API_KEY}"
    log(f"Fetching Finnhub earnings calendar ({from_date} to {to_date})...")

    data = fetch_json(url)
    if not data:
        return []

    entries = data.get("earningsCalendar", [])
    log(f"  Received {len(entries)} earnings entries")
    return entries


# ============================================================================
# Main Logic
# ============================================================================

def get_existing_earnings() -> Dict[str, Dict]:
    """Get existing earnings_transcripts keyed by 'YYYY-Q#'."""
    result = supabase_request(
        "GET",
        f"earnings_transcripts?company=eq.{COMPANY}&select=id,fiscal_year,fiscal_quarter,call_date,status"
    )

    existing = {}
    for row in (result or []):
        key = f"{row['fiscal_year']}-Q{row['fiscal_quarter']}"
        existing[key] = row

    return existing


def run_worker(dry_run: bool = False):
    """Main worker: fetch Finnhub calendar, upsert into earnings_transcripts."""
    log("=" * 60)
    log("Earnings Date Discovery Worker")
    log("=" * 60)

    if not FINNHUB_API_KEY:
        log("ERROR: FINNHUB_API_KEY not set")
        sys.exit(1)

    if not dry_run and (not SUPABASE_URL or not SUPABASE_SERVICE_KEY):
        log("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    # Fetch from Finnhub
    calendar = fetch_earnings_calendar()
    if not calendar:
        log("No earnings data received. Exiting.")
        return

    # Get existing DB records
    existing = get_existing_earnings() if not dry_run else {}
    log(f"Existing earnings in DB: {len(existing)}")

    today_str = date.today().isoformat()
    created = 0
    updated = 0
    skipped = 0

    for entry in calendar:
        year = entry.get("year")
        quarter = entry.get("quarter")
        call_date = entry.get("date")
        hour = entry.get("hour", "")  # "bmo" (before market open), "amc" (after market close), ""

        if not year or not quarter or not call_date:
            continue

        key = f"{year}-Q{quarter}"

        # Map hour to call_time
        call_time = None
        if hour == "bmo":
            call_time = "08:30:00"
        elif hour == "amc":
            call_time = "17:00:00"

        # Determine status
        is_future = call_date >= today_str
        status = "scheduled" if is_future else None  # Don't touch past status

        if dry_run:
            flag = "FUTURE" if is_future else "PAST"
            log(f"  [{flag}] {key}: {call_date} ({hour or 'unknown time'})")
            continue

        db_row = existing.get(key)

        if db_row:
            # Existing record — respect immutable history rule
            if db_row.get("status") == "complete":
                skipped += 1
                continue

            # Check if date differs
            db_date = db_row.get("call_date")
            if db_date and db_date != call_date:
                log(f"  {key}: DB has {db_date}, Finnhub has {call_date} — updating")

            # Update date + time if record isn't complete
            update = {"call_date": call_date}
            if call_time:
                update["call_time"] = call_time
            if status:
                update["status"] = status

            result = supabase_request(
                "PATCH",
                f"earnings_transcripts?company=eq.{COMPANY}&fiscal_year=eq.{year}&fiscal_quarter=eq.{quarter}",
                update
            )
            if result is not None:
                updated += 1
                log(f"  ✓ Updated {key}: {call_date}")
            else:
                log(f"  ✗ Failed to update {key}")
        else:
            # New record — insert
            record = {
                "company": COMPANY,
                "fiscal_year": year,
                "fiscal_quarter": quarter,
                "call_date": call_date,
                "status": status or "scheduled",
                "timezone": "America/New_York",
            }
            if call_time:
                record["call_time"] = call_time

            result = supabase_request("POST", "earnings_transcripts", record)
            if result is not None:
                created += 1
                log(f"  ✓ Created {key}: {call_date}")
            else:
                log(f"  ✗ Failed to create {key}")

    log("=" * 60)
    log(f"Done: {created} created, {updated} updated, {skipped} skipped (complete)")
    log("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Earnings Date Discovery Worker")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to database")
    args = parser.parse_args()
    run_worker(dry_run=args.dry_run)
