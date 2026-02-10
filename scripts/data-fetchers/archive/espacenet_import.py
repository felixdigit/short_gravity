#!/usr/bin/env python3
"""
Espacenet Patent Import

Parses CSV export from Espacenet and imports to Supabase.
Updates existing patents table with family metadata and adds international patents.

Run: python3 espacenet_import.py
"""

from __future__ import annotations
import csv
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Optional, Any

# Supabase config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# CSV file path
CSV_FILE = os.path.join(os.path.dirname(__file__), "espacenet_export.csv")

# Target table - using existing patents table
PATENTS_TABLE = "patents"


def log(msg: str):
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Any:
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
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        log(f"Supabase error: {e.code} - {error_body}")
        raise


def parse_publication_numbers(pub_str: str) -> List[Dict]:
    """Parse publication numbers into list with country codes."""
    if not pub_str:
        return []

    publications = []
    # Split by newline or space
    parts = re.split(r'[\n\s]+', pub_str.strip())

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Extract country code (first 2 chars usually)
        # Format: US12345678B1, EP1234567A1, WO2018123456A1, etc.
        match = re.match(r'^([A-Z]{2})(\d+)([A-Z]\d?)?$', part)
        if match:
            country = match.group(1)
            number = match.group(2)
            kind = match.group(3) or ""
            publications.append({
                "country": country,
                "number": number,
                "kind": kind,
                "full": part
            })
        else:
            # Try simpler pattern
            if len(part) > 2 and part[:2].isalpha():
                publications.append({
                    "country": part[:2],
                    "number": part[2:],
                    "kind": "",
                    "full": part
                })

    return publications


def parse_inventors(inv_str: str) -> List[Dict]:
    """Parse inventors string into list of dicts."""
    if not inv_str:
        return []

    inventors = []
    # Split by newline
    lines = inv_str.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Format: "LASTNAME FIRSTNAME [COUNTRY]"
        match = re.match(r'^(.+?)\s+\[([A-Z]{2})\]$', line)
        if match:
            name = match.group(1).strip()
            country = match.group(2)
            # Split name (usually LAST FIRST or LAST FIRST MIDDLE)
            name_parts = name.split()
            if len(name_parts) >= 2:
                inventors.append({
                    "last": name_parts[0],
                    "first": " ".join(name_parts[1:]),
                    "country": country
                })
            else:
                inventors.append({
                    "name": name,
                    "country": country
                })
        else:
            inventors.append({"name": line})

    return inventors


def parse_cpc_codes(cpc_str: str) -> List[str]:
    """Parse CPC codes into list."""
    if not cpc_str:
        return []

    codes = set()
    # Split by newline
    lines = cpc_str.strip().split('\n')

    for line in lines:
        # Extract code before parentheses
        match = re.match(r'^([A-Z]\d{2}[A-Z]\d+/?[\d]*)', line.strip())
        if match:
            codes.add(match.group(1))

    return list(codes)


def parse_dates(date_str: str) -> List[str]:
    """Parse date string (may have multiple dates)."""
    if not date_str:
        return []

    dates = []
    parts = re.split(r'[\n\s]+', date_str.strip())

    for part in parts:
        part = part.strip()
        if re.match(r'^\d{4}-\d{2}-\d{2}$', part):
            dates.append(part)

    return dates


def get_country_breakdown(publications: List[Dict]) -> Dict[str, int]:
    """Get count of publications by country."""
    breakdown = {}
    for pub in publications:
        country = pub.get("country", "")
        if country:
            breakdown[country] = breakdown.get(country, 0) + 1
    return breakdown


def parse_csv() -> List[Dict]:
    """Parse Espacenet CSV export."""
    patents = []

    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';')

        # Skip header rows (first 7 rows are metadata)
        for _ in range(7):
            next(reader, None)

        # Get column headers (row 8)
        headers = next(reader, None)
        if not headers:
            log("No headers found")
            return []

        # Clean headers
        headers = [h.strip().lower().replace(' ', '_') for h in headers]
        log(f"Headers: {headers}")

        # Parse data rows
        for row in reader:
            if not row or not row[0].strip():
                continue

            # Map row to dict
            data = {}
            for i, val in enumerate(row):
                if i < len(headers):
                    data[headers[i]] = val.strip() if val else ""

            if not data.get("title"):
                continue

            # Parse fields
            publications = parse_publication_numbers(data.get("publication_number", ""))
            inventors = parse_inventors(data.get("inventors", ""))
            cpc_codes = parse_cpc_codes(data.get("cpc", ""))
            pub_dates = parse_dates(data.get("publication_date", ""))

            # Get primary publication (usually US or EP)
            primary_pub = None
            for pub in publications:
                if pub["country"] == "US":
                    primary_pub = pub
                    break
            if not primary_pub and publications:
                primary_pub = publications[0]

            patent = {
                "family_number": data.get("family_number", ""),
                "title": data.get("title", ""),
                "applicants": data.get("applicants", ""),
                "earliest_priority": data.get("earliest_priority", "") or None,
                "earliest_publication": data.get("earliest_publication", "") or None,
                "publication_dates": pub_dates,
                "publications": publications,
                "primary_publication": primary_pub["full"] if primary_pub else None,
                "primary_country": primary_pub["country"] if primary_pub else None,
                "inventors": inventors,
                "cpc_codes": cpc_codes,
                "ipc_codes": [c.strip() for c in data.get("ipc", "").split('\n') if c.strip()],
                "country_breakdown": get_country_breakdown(publications),
            }

            patents.append(patent)

    return patents


def get_existing_patent_numbers() -> set:
    """Get patent numbers already in database."""
    try:
        result = supabase_request("GET", f"{PATENTS_TABLE}?select=patent_number")
        return {r["patent_number"] for r in result}
    except Exception as e:
        log(f"Error fetching existing patents: {e}")
        return set()


def insert_patent(patent: Dict) -> bool:
    """Insert patent into Supabase."""
    try:
        supabase_request("POST", PATENTS_TABLE, patent)
        return True
    except Exception as e:
        log(f"Error inserting patent {patent.get('patent_number')}: {e}")
        return False


def update_patent(patent_number: str, updates: Dict) -> bool:
    """Update existing patent in Supabase."""
    try:
        endpoint = f"{PATENTS_TABLE}?patent_number=eq.{patent_number}"
        supabase_request("PATCH", endpoint, updates)
        return True
    except Exception as e:
        log(f"Error updating patent {patent_number}: {e}")
        return False


def run_import(dry_run: bool = False):
    """Main import function."""
    log("=" * 60)
    log("Espacenet Patent Import")
    log("=" * 60)

    if not os.path.exists(CSV_FILE):
        log(f"ERROR: CSV file not found: {CSV_FILE}")
        sys.exit(1)

    # Parse CSV
    families = parse_csv()
    log(f"Parsed {len(families)} patent families from CSV")

    if not families:
        log("No patents to import")
        return

    # Analyze data
    all_countries = {}
    total_publications = 0

    for p in families:
        for country, count in p.get("country_breakdown", {}).items():
            all_countries[country] = all_countries.get(country, 0) + count
            total_publications += count

    log("\nCountry breakdown (publications):")
    for country, count in sorted(all_countries.items(), key=lambda x: -x[1]):
        log(f"  {country}: {count}")
    log(f"  TOTAL: {total_publications}")

    # Print sample
    log("\nSample patent family:")
    sample = families[0]
    log(f"  Family: {sample['family_number']}")
    log(f"  Title: {sample['title'][:60]}...")
    log(f"  Priority: {sample['earliest_priority']}")
    log(f"  Publications: {len(sample['publications'])}")
    log(f"  Countries: {list(sample['country_breakdown'].keys())}")

    if dry_run:
        log("\n[DRY RUN] Would insert to Supabase")
        return families

    if not SUPABASE_SERVICE_KEY:
        log("\nERROR: SUPABASE_SERVICE_KEY not set")
        log("Run with --dry-run to see parsed data without storing")
        sys.exit(1)

    # Get existing patents
    log("\nChecking Supabase...")
    existing = get_existing_patent_numbers()
    log(f"Found {len(existing)} existing patents in database")

    # Process each family - add primary publication if not exists
    inserted = 0
    updated = 0
    skipped = 0

    for family in families:
        primary_pub = family.get("primary_publication")
        if not primary_pub:
            skipped += 1
            continue

        # Normalize patent number format
        patent_number = primary_pub

        if patent_number in existing:
            # Update with family metadata
            updates = {
                "cpc_codes": family["cpc_codes"],
                "ipc_codes": family["ipc_codes"] if family["ipc_codes"] else None,
                "inventors": family["inventors"],
                "source": "espacenet",
            }
            if update_patent(patent_number, updates):
                updated += 1
        else:
            # Insert new patent record
            db_record = {
                "patent_number": patent_number,
                "title": family["title"],
                "assignee": family["applicants"].replace(" [US]", ""),
                "grant_date": family["earliest_publication"],
                "inventors": family["inventors"],
                "cpc_codes": family["cpc_codes"],
                "status": "granted" if "B" in patent_number else "pending",
                "source": "espacenet",
            }

            if insert_patent(db_record):
                inserted += 1
                existing.add(patent_number)

    log(f"\nInserted: {inserted}")
    log(f"Updated: {updated}")
    log(f"Skipped: {skipped}")

    # Summary
    log("\n" + "=" * 60)
    log("SUMMARY")
    log("=" * 60)
    log(f"Total patent families: {len(families)}")
    log(f"Total publications: {total_publications}")
    log(f"Jurisdictions: {len(all_countries)}")
    log("=" * 60)

    return families


def print_report():
    """Print detailed report without storing."""
    log("=" * 60)
    log("Espacenet Patent Report")
    log("=" * 60)

    patents = parse_csv()

    # Aggregate stats
    all_countries = {}
    all_inventors = {}

    for p in patents:
        for country, count in p.get("country_breakdown", {}).items():
            all_countries[country] = all_countries.get(country, 0) + count

        for inv in p.get("inventors", []):
            name = inv.get("name") or f"{inv.get('last', '')} {inv.get('first', '')}".strip()
            if name:
                all_inventors[name] = all_inventors.get(name, 0) + 1

    log(f"\nTotal patent families: {len(patents)}")

    log("\n--- JURISDICTION BREAKDOWN ---")
    for country, count in sorted(all_countries.items(), key=lambda x: -x[1]):
        log(f"  {country}: {count} publications")

    log("\n--- TOP INVENTORS ---")
    for name, count in sorted(all_inventors.items(), key=lambda x: -x[1])[:10]:
        log(f"  {name}: {count} families")

    log("\n--- ALL PATENT FAMILIES ---")
    for i, p in enumerate(patents, 1):
        title = p["title"][:50] + "..." if len(p["title"]) > 50 else p["title"]
        pubs = ", ".join(list(p["country_breakdown"].keys())[:5])
        log(f"  {i}. {p['family_number']} | {title}")
        log(f"      Priority: {p['earliest_priority']} | Countries: {pubs}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--report":
            print_report()
        elif sys.argv[1] == "--dry-run":
            run_import(dry_run=True)
        else:
            log("Usage: python3 espacenet_import.py [--report|--dry-run]")
    else:
        run_import()
