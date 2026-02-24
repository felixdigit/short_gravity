#!/usr/bin/env python3
"""
SOCRATES Conjunction Worker
Fetches close approach data from CelesTrak SOCRATES for AST SpaceMobile satellites.
Source: https://celestrak.org/SOCRATES/search-results.php (free, no auth)

Upserts into conjunctions table keyed by cdm_id.
"""

import csv
import hashlib
import io
import json
import os
import ssl
import sys
import time
import urllib.parse
import urllib.request
import urllib.error

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# AST SpaceMobile NORAD IDs
ASTS_NORAD_IDS = ["67232", "61046", "61049", "61045", "61048", "61047", "53807"]

SATELLITE_NAMES = {
    "67232": "FM1",
    "61046": "BB5",
    "61049": "BB4",
    "61045": "BB3",
    "61048": "BB2",
    "61047": "BB1",
    "53807": "BW3",
}

# CelesTrak SOCRATES raw CSV — full dataset, filter locally for our sats
SOCRATES_CSV_URL = "https://celestrak.org/SOCRATES/sort-minRange.csv"


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


def fetch_socrates_csv(retries=3):
    """Fetch the full SOCRATES CSV dataset from CelesTrak."""
    for attempt in range(retries):
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(
                SOCRATES_CSV_URL,
                headers={"User-Agent": "ShortGravity/1.0"},
            )
            with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:
            print(f"  Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return None


def parse_and_filter(csv_text):
    """
    Parse SOCRATES CSV, filter for AST SpaceMobile satellites.
    CSV columns: NORAD_CAT_ID_1, OBJECT_NAME_1, DSE_1,
                 NORAD_CAT_ID_2, OBJECT_NAME_2, DSE_2,
                 TCA, TCA_RANGE, TCA_RELATIVE_SPEED, MAX_PROB, DILUTION
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    norad_set = set(ASTS_NORAD_IDS)
    records = []

    for row in reader:
        try:
            sat1_id = row.get("NORAD_CAT_ID_1", "").strip()
            sat2_id = row.get("NORAD_CAT_ID_2", "").strip()

            # Skip if neither object is one of ours
            if sat1_id not in norad_set and sat2_id not in norad_set:
                continue

            sat1_name = row.get("OBJECT_NAME_1", "").strip()
            sat2_name = row.get("OBJECT_NAME_2", "").strip()
            tca = row.get("TCA", "").strip()
            min_range_str = row.get("TCA_RANGE", "").strip()
            rel_vel_str = row.get("TCA_RELATIVE_SPEED", "").strip()
            max_prob_str = row.get("MAX_PROB", "").strip()

            if not tca or not min_range_str:
                continue

            min_range_km = float(min_range_str)
            rel_vel_kms = float(rel_vel_str) if rel_vel_str else None
            collision_prob = float(max_prob_str) if max_prob_str else None

            # Determine which is ours
            if sat1_id in norad_set:
                primary_id, primary_name = sat1_id, sat1_name
                secondary_id, secondary_name = sat2_id, sat2_name
            else:
                primary_id, primary_name = sat2_id, sat2_name
                secondary_id, secondary_name = sat1_id, sat1_name

            # Stable cdm_id
            cdm_raw = f"{sat1_id}_{sat2_id}_{tca}"
            cdm_id = hashlib.md5(cdm_raw.encode()).hexdigest()[:16]

            records.append({
                "cdm_id": f"SOCRATES-{cdm_id}",
                "sat1_norad_id": primary_id,
                "sat1_name": SATELLITE_NAMES.get(primary_id, primary_name),
                "sat2_norad_id": secondary_id,
                "sat2_name": secondary_name,
                "tca": tca,
                "min_range_km": min_range_km,
                "relative_speed_kms": rel_vel_kms,
                "collision_probability": collision_prob,
                "source": "socrates",
                "raw_cdm": dict(row),
            })

        except (ValueError, KeyError):
            continue

    return records


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY required")
        sys.exit(1)

    print(f"[socrates] Fetching full SOCRATES dataset...")
    csv_text = fetch_socrates_csv()
    if not csv_text:
        print("[socrates] Failed to fetch CSV")
        sys.exit(1)

    total_lines = csv_text.count("\n") - 1
    print(f"[socrates] Downloaded {total_lines} total conjunctions, filtering for AST sats...")

    records = parse_and_filter(csv_text)
    print(f"[socrates] Found {len(records)} conjunctions involving AST satellites")

    if not records:
        print("[socrates] No AST conjunctions in current SOCRATES window")
        return

    # Upsert
    batch_size = 50
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        status = supabase_request(
            "POST",
            "conjunctions?on_conflict=cdm_id",
            data=batch,
        )
        if status and status < 300:
            total += len(batch)
            print(f"  Upserted batch: {len(batch)} records")
        else:
            print(f"  Failed batch at offset {i}")

    print(f"[socrates] Done: {total}/{len(records)} upserted")


if __name__ == "__main__":
    main()
