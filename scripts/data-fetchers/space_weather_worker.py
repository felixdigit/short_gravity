#!/usr/bin/env python3
"""
Space Weather Worker
Fetches solar flux (F10.7), Kp, Ap, and sunspot data from CelesTrak.
Source: https://celestrak.org/SpaceData/SW-Last5Years.csv (free, no auth)
Backfill: https://celestrak.org/SpaceData/SW-All.csv

Upserts into space_weather table keyed by date.
"""

import csv
import io
import json
import os
import ssl
import sys
import time
import urllib.request
import urllib.error

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

SW_LAST5 = "https://celestrak.org/SpaceData/SW-Last5Years.csv"
SW_ALL = "https://celestrak.org/SpaceData/SW-All.csv"


def supabase_request(method, path, data=None, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal,resolution=merge-duplicates",
    }

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode()[:200]}")
        return e.code


def fetch_csv(url, retries=3):
    """Fetch CSV data with retry logic."""
    for attempt in range(retries):
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(url, headers={"User-Agent": "ShortGravity/1.0"})
            with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:
            print(f"  Fetch attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch {url} after {retries} attempts")


def safe_float(val):
    """Parse a float, returning None on failure or empty."""
    if val is None:
        return None
    val = val.strip()
    if not val:
        return None
    try:
        v = float(val)
        return v if v >= 0 else None
    except ValueError:
        return None


def safe_int(val):
    """Parse an int, returning None on failure or empty."""
    f = safe_float(val)
    return int(f) if f is not None else None


def parse_sw_csv(csv_text):
    """
    Parse CelesTrak space weather CSV.
    Header-based CSV with columns:
    DATE,BSRN,ND,KP1..KP8,KP_SUM,AP1..AP8,AP_AVG,CP,C9,ISN,
    F10.7_OBS,F10.7_ADJ,F10.7_DATA_TYPE,F10.7_OBS_CENTER81,...
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    records = []

    for row in reader:
        date_str = row.get("DATE", "").strip()
        if not date_str or len(date_str) < 10:
            continue

        # Validate date format YYYY-MM-DD
        try:
            year = int(date_str[:4])
            if year < 1957 or year > 2100:
                continue
        except ValueError:
            continue

        kp_sum = safe_float(row.get("KP_SUM"))
        ap_avg = safe_float(row.get("AP_AVG"))
        f107_obs = safe_float(row.get("F10.7_OBS"))
        f107_adj = safe_float(row.get("F10.7_ADJ"))
        f107_center81 = safe_float(row.get("F10.7_OBS_CENTER81"))
        sunspot = safe_int(row.get("ISN"))
        data_type = row.get("F10.7_DATA_TYPE", "").strip() or None

        record = {
            "date": date_str,
            "kp_sum": kp_sum,
            "ap_avg": round(ap_avg, 2) if ap_avg is not None else None,
            "f107_obs": f107_obs,
            "f107_adj": f107_adj,
            "f107_center81": round(f107_center81, 1) if f107_center81 is not None else None,
            "sunspot_number": sunspot,
            "data_type": data_type,
        }

        records.append(record)

    return records


def upsert_batch(records, batch_size=500):
    """Upsert records in batches."""
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        status = supabase_request(
            "POST",
            "space_weather?on_conflict=date",
            data=batch,
        )
        if status and status < 300:
            total += len(batch)
            print(f"  Upserted batch {i // batch_size + 1}: {len(batch)} records")
        else:
            print(f"  Failed batch {i // batch_size + 1}")

    return total


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY required")
        sys.exit(1)

    backfill = "--backfill" in sys.argv or "--full" in sys.argv

    url = SW_ALL if backfill else SW_LAST5
    label = "SW-All (full archive)" if backfill else "SW-Last5Years"
    print(f"[space-weather] Fetching {label}...")

    csv_text = fetch_csv(url)
    records = parse_sw_csv(csv_text)
    print(f"[space-weather] Parsed {len(records)} records")

    if not records:
        print("[space-weather] No records parsed — check CSV format")
        sys.exit(1)

    total = upsert_batch(records)
    print(f"[space-weather] Done: {total}/{len(records)} upserted")


if __name__ == "__main__":
    main()
