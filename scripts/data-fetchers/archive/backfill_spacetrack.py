#!/usr/bin/env python3
"""
Space-Track Historical Backfill — 90-day GP history into tle_history.

One-time script to populate tle_history with Space-Track's gp_history class.
Uses existing .env credentials. Inserts with source='spacetrack',
unique constraint skips duplicates.

Run:
  cd scripts/data-fetchers
  export $(grep -v '^#' .env | xargs)
  python3 backfill_spacetrack.py
"""

from __future__ import annotations
import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# ============================================================================
# CONFIGURATION
# ============================================================================

ASTS_SATELLITES = {
    "67232": "BLUEWALKER 3-FM1",
    "61046": "BLUEBIRD 5",
    "61049": "BLUEBIRD 4",
    "61045": "BLUEBIRD 3",
    "61048": "BLUEBIRD 2",
    "61047": "BLUEBIRD 1",
    "53807": "BLUEWALKER 3",
}

NORAD_IDS = list(ASTS_SATELLITES.keys())

SPACE_TRACK_BASE = "https://www.space-track.org"
SPACE_TRACK_USER = os.environ.get("SPACE_TRACK_USERNAME", "")
SPACE_TRACK_PASS = os.environ.get("SPACE_TRACK_PASSWORD", "")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

BACKFILL_DAYS = 90

session_cookie: Optional[str] = None


# ============================================================================
# UTILITIES
# ============================================================================

def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def safe_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


# ============================================================================
# SPACE-TRACK API
# ============================================================================

def space_track_login() -> str:
    global session_cookie

    if not SPACE_TRACK_USER or not SPACE_TRACK_PASS:
        raise ValueError("SPACE_TRACK_USERNAME and SPACE_TRACK_PASSWORD must be set")

    log(f"Logging into Space-Track as {SPACE_TRACK_USER[:5]}...")

    url = f"{SPACE_TRACK_BASE}/ajaxauth/login"
    data = urllib.parse.urlencode({
        "identity": SPACE_TRACK_USER,
        "password": SPACE_TRACK_PASS,
    }).encode()

    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=30) as resp:
        cookies = resp.headers.get("Set-Cookie", "")
        if "chocolatechip=" not in cookies:
            raise ValueError("Login failed - no session cookie")
        for part in cookies.split(";"):
            if "chocolatechip=" in part:
                session_cookie = part.strip()
                break

    log("Login successful")
    return session_cookie


def space_track_request(endpoint: str, retries: int = 3) -> List[Dict]:
    global session_cookie

    if not session_cookie:
        space_track_login()

    url = f"{SPACE_TRACK_BASE}{endpoint}"
    log(f"  Fetching: {endpoint[:100]}...")

    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"Cookie": session_cookie})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
                log(f"  -> {len(data)} records")
                return data
        except urllib.error.HTTPError as e:
            if e.code == 401:
                log("  Session expired, re-authenticating...")
                session_cookie = None
                space_track_login()
                continue
            if e.code == 429:
                wait = 2 ** (attempt + 2)
                log(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            raise
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                log(f"  Error: {e}, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise

    return []


# ============================================================================
# SUPABASE
# ============================================================================

def supabase_upsert(records: List[Dict]) -> int:
    """Batch upsert to tle_history. Returns count of records sent."""
    if not records:
        return 0

    url = f"{SUPABASE_URL}/rest/v1/tle_history"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal,resolution=merge-duplicates",
    }

    # Batch in chunks of 100
    total = 0
    for i in range(0, len(records), 100):
        chunk = records[i:i + 100]
        body = json.dumps(chunk).encode()
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                total += len(chunk)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            if e.code == 409:
                # Duplicates — expected, count as success
                total += len(chunk)
            else:
                log(f"  Supabase error {e.code}: {error_body[:200]}")
                raise

    return total


# ============================================================================
# BACKFILL
# ============================================================================

def backfill():
    log("=" * 60)
    log("SPACE-TRACK 90-DAY HISTORICAL BACKFILL")
    log(f"Satellites: {len(ASTS_SATELLITES)}")
    log("=" * 60)

    if not SPACE_TRACK_USER or not SPACE_TRACK_PASS:
        log("ERROR: SPACE_TRACK_USERNAME and SPACE_TRACK_PASSWORD required")
        sys.exit(1)
    if not SUPABASE_URL or not SUPABASE_KEY:
        log("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY required")
        sys.exit(1)

    now = datetime.now(tz=__import__('datetime').timezone.utc)
    end_date = now.strftime("%Y-%m-%d")
    start_date = (now - timedelta(days=BACKFILL_DAYS)).strftime("%Y-%m-%d")

    total_inserted = 0

    for norad_id, name in ASTS_SATELLITES.items():
        log(f"\n{name} ({norad_id})")
        log(f"  Range: {start_date} to {end_date}")

        endpoint = (
            f"/basicspacedata/query/class/gp_history"
            f"/NORAD_CAT_ID/{norad_id}"
            f"/EPOCH/{start_date}--{end_date}"
            f"/orderby/EPOCH%20asc/format/json"
        )

        gp_records = space_track_request(endpoint)

        if not gp_records:
            log(f"  No records found")
            continue

        # Transform to tle_history rows
        rows = []
        for gp in gp_records:
            rows.append({
                "norad_id": str(gp["NORAD_CAT_ID"]),
                "epoch": gp.get("EPOCH"),
                "tle_line0": gp.get("TLE_LINE0"),
                "tle_line1": gp.get("TLE_LINE1"),
                "tle_line2": gp.get("TLE_LINE2"),
                "bstar": gp.get("BSTAR"),
                "mean_motion": gp.get("MEAN_MOTION"),
                "mean_motion_dot": gp.get("MEAN_MOTION_DOT"),
                "apoapsis_km": gp.get("APOAPSIS"),
                "periapsis_km": gp.get("PERIAPSIS"),
                "eccentricity": gp.get("ECCENTRICITY"),
                "inclination": gp.get("INCLINATION"),
                "semimajor_axis": gp.get("SEMIMAJOR_AXIS"),
                "period_minutes": gp.get("PERIOD"),
                "rev_at_epoch": safe_int(gp.get("REV_AT_EPOCH")),
                "source": "spacetrack",
                "raw_gp": gp,
            })

        inserted = supabase_upsert(rows)
        log(f"  Upserted {inserted} records")
        total_inserted += inserted

        # Rate limit between satellites
        time.sleep(3)

    log("")
    log("=" * 60)
    log(f"BACKFILL COMPLETE: {total_inserted} total records upserted")
    log("=" * 60)


if __name__ == "__main__":
    backfill()
