#!/usr/bin/env python3
"""
TLE Worker — Space-Track Data Pipeline

Fetches complete GP (General Perturbations) data from Space-Track,
stores in Supabase with full JSONB for future analysis.

Features:
- Full GP data (40 fields) stored as JSONB
- Extracted key fields for fast queries
- Historical backfill capability
- Conjunction monitoring

Run manually: python3 tle_worker.py
Run backfill: python3 tle_worker.py --backfill
Run as cron:  0 */4 * * * cd /path/to/scripts && python3 tle_worker.py
"""

from __future__ import annotations
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

# ============================================================================
# CONFIGURATION
# ============================================================================

# ASTS Constellation - ordered newest to oldest
ASTS_SATELLITES = {
    "67232": {"name": "BLUEWALKER 3-FM1", "launch": "2025-01-14"},
    "61046": {"name": "BLUEBIRD 5", "launch": "2024-09-12"},
    "61049": {"name": "BLUEBIRD 4", "launch": "2024-09-12"},
    "61045": {"name": "BLUEBIRD 3", "launch": "2024-09-12"},
    "61048": {"name": "BLUEBIRD 2", "launch": "2024-09-12"},
    "61047": {"name": "BLUEBIRD 1", "launch": "2024-09-12"},
    "53807": {"name": "BLUEWALKER 3", "launch": "2022-09-10"},
}

NORAD_IDS = list(ASTS_SATELLITES.keys())

# Space-Track
SPACE_TRACK_BASE = "https://www.space-track.org"
SPACE_TRACK_USER = os.environ.get("SPACE_TRACK_USERNAME", "")
SPACE_TRACK_PASS = os.environ.get("SPACE_TRACK_PASSWORD", "")

# Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Session management
session_cookie: Optional[str] = None

try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from discord.notify import notify_orbital
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False


# ============================================================================
# UTILITIES
# ============================================================================

def log(msg: str):
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def safe_decimal(value: Any) -> Optional[Decimal]:
    """Convert to Decimal, handling None and empty strings."""
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except:
        return None


def safe_int(value: Any) -> Optional[int]:
    """Convert to int, handling None and empty strings."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except:
        return None


# ============================================================================
# SPACE-TRACK API
# ============================================================================

def space_track_login() -> str:
    """Login to Space-Track, return session cookie."""
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

        # Extract cookie
        for part in cookies.split(";"):
            if "chocolatechip=" in part:
                session_cookie = part.strip()
                break

    log("✓ Space-Track login successful")
    return session_cookie


def space_track_request(endpoint: str) -> List[Dict]:
    """Make authenticated request to Space-Track."""
    global session_cookie

    if not session_cookie:
        space_track_login()

    url = f"{SPACE_TRACK_BASE}{endpoint}"
    log(f"Fetching: {endpoint[:80]}...")

    req = urllib.request.Request(url, headers={"Cookie": session_cookie})

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            log(f"  → Received {len(data)} records")
            return data
    except urllib.error.HTTPError as e:
        if e.code == 401:
            log("Session expired, re-authenticating...")
            session_cookie = None
            space_track_login()
            return space_track_request(endpoint)
        raise


def fetch_current_gp(norad_ids: List[str]) -> List[Dict]:
    """Fetch current GP data for satellites."""
    ids_str = ",".join(norad_ids)
    endpoint = f"/basicspacedata/query/class/gp/NORAD_CAT_ID/{ids_str}/orderby/EPOCH%20desc/format/json"
    return space_track_request(endpoint)


def fetch_historical_gp(norad_id: str, start_date: str, end_date: str) -> List[Dict]:
    """Fetch historical GP data for a satellite within date range."""
    endpoint = f"/basicspacedata/query/class/gp_history/NORAD_CAT_ID/{norad_id}/EPOCH/{start_date}--{end_date}/orderby/EPOCH%20asc/format/json"
    return space_track_request(endpoint)


def fetch_conjunctions(norad_ids: List[str]) -> List[Dict]:
    """Fetch conjunction data for satellites."""
    # CDM data for our satellites (either as primary or secondary)
    ids_str = ",".join(norad_ids)
    # Note: CDM_PUBLIC may have limited data availability
    endpoint = f"/basicspacedata/query/class/cdm_public/SAT_1_ID/{ids_str}/orderby/TCA%20desc/limit/100/format/json"

    try:
        return space_track_request(endpoint)
    except Exception as e:
        log(f"  Warning: Could not fetch conjunctions - {e}")
        return []


# ============================================================================
# SUPABASE
# ============================================================================

def supabase_request(method: str, endpoint: str, data: Optional[Any] = None) -> Any:
    """Make Supabase REST API request."""
    if not SUPABASE_KEY:
        raise ValueError("SUPABASE_SERVICE_KEY not set")

    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation,resolution=merge-duplicates",
    }

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode()
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        log(f"Supabase error: {e.code} - {error_body[:200]}")
        raise


def upsert_satellite(gp: Dict):
    """Upsert satellite current state."""
    data = {
        "norad_id": str(gp["NORAD_CAT_ID"]),
        "name": gp.get("OBJECT_NAME", "").strip(),
        "tle_line0": gp.get("TLE_LINE0"),
        "tle_line1": gp.get("TLE_LINE1"),
        "tle_line2": gp.get("TLE_LINE2"),
        "tle_epoch": gp.get("EPOCH"),
        "bstar": gp.get("BSTAR"),
        "mean_motion": gp.get("MEAN_MOTION"),
        "mean_motion_dot": gp.get("MEAN_MOTION_DOT"),
        "mean_motion_ddot": gp.get("MEAN_MOTION_DDOT"),
        "inclination": gp.get("INCLINATION"),
        "eccentricity": gp.get("ECCENTRICITY"),
        "ra_of_asc_node": gp.get("RA_OF_ASC_NODE"),
        "arg_of_pericenter": gp.get("ARG_OF_PERICENTER"),
        "mean_anomaly": gp.get("MEAN_ANOMALY"),
        "semimajor_axis": gp.get("SEMIMAJOR_AXIS"),
        "period_minutes": gp.get("PERIOD"),
        "apoapsis_km": gp.get("APOAPSIS"),
        "periapsis_km": gp.get("PERIAPSIS"),
        "rev_at_epoch": safe_int(gp.get("REV_AT_EPOCH")),
        "object_type": gp.get("OBJECT_TYPE"),
        "rcs_size": gp.get("RCS_SIZE"),
        "country_code": gp.get("COUNTRY_CODE"),
        "launch_date": gp.get("LAUNCH_DATE"),
        "decay_date": gp.get("DECAY_DATE"),
        "raw_gp": gp,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }

    supabase_request("POST", "satellites?on_conflict=norad_id", data)


def insert_tle_history(gp: Dict) -> bool:
    """Insert TLE into history table. Returns True if inserted, False if duplicate."""
    data = {
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
        "raw_gp": gp,
    }

    try:
        supabase_request("POST", "tle_history", data)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 409:  # Conflict - duplicate
            return False
        raise


def insert_conjunction(cdm: Dict) -> bool:
    """Insert conjunction event."""
    # Convert min_range from meters or km based on value
    min_range = cdm.get("MIN_RNG")
    if min_range:
        min_range_km = float(min_range) / 1000 if float(min_range) > 1000 else float(min_range)
    else:
        min_range_km = None

    data = {
        "cdm_id": safe_int(cdm.get("CDM_ID")),
        "sat1_norad_id": str(cdm.get("SAT_1_ID", "")),
        "sat1_name": cdm.get("SAT_1_NAME"),
        "sat1_object_type": cdm.get("SAT1_OBJECT_TYPE"),
        "sat2_norad_id": str(cdm.get("SAT_2_ID", "")),
        "sat2_name": cdm.get("SAT_2_NAME"),
        "sat2_object_type": cdm.get("SAT2_OBJECT_TYPE"),
        "tca": cdm.get("TCA"),
        "min_range_km": min_range_km,
        "collision_probability": cdm.get("PC"),
        "emergency_reportable": cdm.get("EMERGENCY_REPORTABLE") == "Y",
        "raw_cdm": cdm,
    }

    try:
        supabase_request("POST", "conjunctions?on_conflict=cdm_id", data)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 409:
            return False
        raise


# ============================================================================
# WORKER FUNCTIONS
# ============================================================================

def sync_current_tles():
    """Fetch and store current TLEs for all ASTS satellites."""
    log("=" * 60)
    log("Syncing current TLEs...")
    log("=" * 60)

    gp_data = fetch_current_gp(NORAD_IDS)

    for gp in gp_data:
        norad_id = str(gp["NORAD_CAT_ID"])
        name = gp.get("OBJECT_NAME", "").strip()
        epoch = gp.get("EPOCH", "")[:19]

        log(f"  {name} ({norad_id}): epoch {epoch}")

        # Update current state
        upsert_satellite(gp)

        # Add to history
        if insert_tle_history(gp):
            log(f"    → New TLE added to history")
        else:
            log(f"    → TLE already in history")

    log(f"✓ Synced {len(gp_data)} satellites")


def sync_conjunctions():
    """Fetch and store conjunction warnings."""
    log("")
    log("Syncing conjunctions...")

    cdm_data = fetch_conjunctions(NORAD_IDS)

    if not cdm_data:
        log("  No conjunction data available")
        return

    new_count = 0
    for cdm in cdm_data:
        if insert_conjunction(cdm):
            new_count += 1
            sat1 = cdm.get("SAT_1_NAME", "?")
            sat2 = cdm.get("SAT_2_NAME", "?")
            tca = cdm.get("TCA", "")[:10]
            log(f"  New conjunction: {sat1} / {sat2} on {tca}")

            # Discord notification for conjunctions
            if DISCORD_AVAILABLE:
                pc = cdm.get("PC", "N/A")
                notify_orbital(
                    event=f"Conjunction: {sat1} / {sat2}",
                    details=f"TCA: {tca}, Collision probability: {pc}",
                )

    log(f"✓ {new_count} new conjunctions added")


def backfill_history():
    """Backfill complete TLE history since launch for all satellites."""
    log("=" * 60)
    log("BACKFILL: Fetching complete TLE history")
    log("=" * 60)

    today = datetime.now().strftime("%Y-%m-%d")
    total_inserted = 0

    for norad_id, info in ASTS_SATELLITES.items():
        name = info["name"]
        launch = info["launch"]

        log(f"\n{name} ({norad_id})")
        log(f"  Fetching from {launch} to {today}...")

        # Fetch all historical GP data
        gp_history = fetch_historical_gp(norad_id, launch, today)
        log(f"  → {len(gp_history)} TLEs from Space-Track")

        # Insert each TLE
        inserted = 0
        for gp in gp_history:
            if insert_tle_history(gp):
                inserted += 1

        log(f"  ✓ {inserted} new TLEs added ({len(gp_history) - inserted} duplicates)")
        total_inserted += inserted

        # Also update current satellite state with latest TLE
        if gp_history:
            upsert_satellite(gp_history[-1])

        # Rate limit: pause between satellites
        time.sleep(2)

    log("")
    log("=" * 60)
    log(f"BACKFILL COMPLETE: {total_inserted} total TLEs added")
    log("=" * 60)


def print_freshness_report():
    """Print TLE freshness status."""
    log("")
    log("TLE Freshness Report:")
    log("-" * 40)

    for norad_id, info in ASTS_SATELLITES.items():
        try:
            result = supabase_request("GET", f"satellites?norad_id=eq.{norad_id}&select=tle_epoch,updated_at")
            if result and len(result) > 0:
                epoch = result[0].get("tle_epoch")
                if epoch:
                    epoch_dt = datetime.fromisoformat(epoch.replace("Z", "+00:00"))
                    hours_old = (datetime.now(epoch_dt.tzinfo) - epoch_dt).total_seconds() / 3600
                    status = "FRESH" if hours_old < 6 else "OK" if hours_old < 12 else "STALE" if hours_old < 24 else "CRITICAL"
                    log(f"  {info['name'][:15]:15} {hours_old:5.1f}h old  [{status}]")
                else:
                    log(f"  {info['name'][:15]:15} NO DATA")
        except:
            log(f"  {info['name'][:15]:15} ERROR")


# ============================================================================
# MAIN
# ============================================================================

def run_worker():
    """Main worker entry point."""
    log("=" * 60)
    log("TLE Worker Started")
    log(f"Satellites: {len(ASTS_SATELLITES)}")
    log("=" * 60)

    # Validate environment
    if not SPACE_TRACK_USER or not SPACE_TRACK_PASS:
        log("ERROR: SPACE_TRACK_USERNAME and SPACE_TRACK_PASSWORD must be set")
        sys.exit(1)

    if not SUPABASE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    # Check for backfill flag
    if "--backfill" in sys.argv:
        backfill_history()
    else:
        # Normal sync
        sync_current_tles()
        sync_conjunctions()

    # Print status
    print_freshness_report()

    log("")
    log("✓ Worker complete")


if __name__ == "__main__":
    import urllib.parse
    run_worker()
