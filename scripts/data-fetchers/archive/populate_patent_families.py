#!/usr/bin/env python3
"""
Populate patent_families junction table.

The patent_families table maps family_id -> patent_number (with jurisdiction).
Groups patents by EPO family_id, title matching, or as singletons.

Usage:
    python3 populate_patent_families.py           # Populate
    python3 populate_patent_families.py --dry-run  # Preview
"""

from __future__ import annotations
import json
import os
import re
import sys
import urllib.request
import urllib.error
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Set

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

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def supabase_get(endpoint: str) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        log(f"  GET error {e.code}: {e.read().decode()[:200]}")
        return []


def supabase_post(table: str, rows: list) -> int:
    if not rows:
        return 0
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    count = 0
    for i in range(0, len(rows), 50):
        batch = rows[i:i + 50]
        body = json.dumps(batch).encode()
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            urllib.request.urlopen(req, timeout=30)
            count += len(batch)
        except urllib.error.HTTPError as e:
            err = e.read().decode()[:300]
            log(f"  Insert error {e.code}: {err}")
    return count


def get_country(patent_number: str) -> str:
    m = re.match(r'^([A-Z]{2})', patent_number)
    return m.group(1) if m else "??"


def run(dry_run: bool = False):
    log("=" * 60)
    log("PATENT FAMILIES POPULATION (junction table)")
    log("=" * 60)

    if not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    # Get all patents
    patents = supabase_get(
        "patents?select=patent_number,title,family_id&order=patent_number.asc"
    )
    log(f"Total patents: {len(patents)}")

    # Get existing family mappings
    existing = supabase_get("patent_families?select=patent_number,family_id")
    existing_set = {r["patent_number"] for r in existing}
    log(f"Existing family mappings: {len(existing_set)}")

    # Group by family_id
    family_groups: Dict[str, List[Dict]] = defaultdict(list)
    orphans: List[Dict] = []

    for p in patents:
        fid = p.get("family_id")
        if fid:
            family_groups[str(fid)].append(p)
        else:
            orphans.append(p)

    log(f"With family_id: {sum(len(v) for v in family_groups.values())} in {len(family_groups)} families")
    log(f"Orphans: {len(orphans)}")

    # Group orphans by title
    title_groups: Dict[str, List[Dict]] = defaultdict(list)
    for p in orphans:
        title = (p.get("title") or "").strip().lower()
        if title:
            title_groups[title].append(p)

    next_synthetic = 100000000
    remaining_orphans = []
    for title, members in title_groups.items():
        if len(members) > 1:
            fid = str(next_synthetic)
            family_groups[fid] = members
            next_synthetic += 1
        else:
            remaining_orphans.append(members[0])

    # Singletons
    for p in remaining_orphans:
        fid = f"S_{p['patent_number']}"
        family_groups[fid] = [p]

    log(f"Total families: {len(family_groups)}")

    # Build junction rows
    rows = []
    for fid, members in sorted(family_groups.items()):
        for p in members:
            pn = p["patent_number"]
            if pn in existing_set:
                continue
            rows.append({
                "family_id": fid,
                "patent_number": pn,
                "jurisdiction": get_country(pn),
            })

    log(f"New mappings to insert: {len(rows)}")

    if dry_run:
        # Show family summary
        for fid, members in sorted(family_groups.items(), key=lambda x: -len(x[1])):
            nums = [m["patent_number"] for m in members]
            title = (members[0].get("title") or "?")[:55]
            new = sum(1 for m in members if m["patent_number"] not in existing_set)
            if new > 0:
                log(f"  [{len(members):3d}] {fid:>15s}  {title}  (+{new} new)")
        log(f"\n[DRY RUN] Would insert {len(rows)} mappings")
        return

    # Insert
    count = supabase_post("patent_families", rows)
    log(f"Inserted: {count}")
    log(f"\n{'=' * 60}")
    log(f"DONE: {count} family mappings created across {len(family_groups)} families")
    log(f"{'=' * 60}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Populate patent families")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
