#!/usr/bin/env python3
"""
SEC Exhibit Backfill — Downloads exhibits from EDGAR for existing filings.

Processes exhibits WITHOUT re-downloading full filing content.
Imports helper functions from sec_backfill.py.

Usage:
    python3 exhibit_backfill.py                      # High-value forms only
    python3 exhibit_backfill.py --all-forms           # All forms
    python3 exhibit_backfill.py --dry-run             # Preview only
    python3 exhibit_backfill.py --limit 20            # Process first N filings
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Set

# Load env if not already set
if not os.environ.get("SUPABASE_SERVICE_KEY"):
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()

# Now import from sec_backfill
sys.path.insert(0, os.path.dirname(__file__))
from sec_backfill import (
    fetch_filing_index,
    get_filing_url,
    fetch_bytes,
    extract_text_from_html,
    insert_exhibit,
    SEC_RATE_LIMIT_SECONDS,
)
from storage_utils import upload_sec_exhibit
from pdf_extractor import extract_pdf_text

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

HIGH_VALUE_FORMS = {"10-K", "10-Q", "8-K", "S-1", "424B5", "DEF 14A", "10-K/A", "S-1/A"}


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


def get_filings_needing_exhibits(forms: Set[str] | None = None) -> List[Dict]:
    """Get filings to process for exhibits."""
    endpoint = "filings?select=accession_number,form,filing_date&order=filing_date.desc"
    rows = supabase_get(endpoint)

    if forms:
        rows = [r for r in rows if r.get("form") in forms]

    return rows


def get_already_processed() -> Set[str]:
    """Get accession numbers that already have exhibits in sec_filing_exhibits."""
    rows = supabase_get("sec_filing_exhibits?select=accession_number")
    return {r["accession_number"] for r in rows if r.get("accession_number")}


def mark_exhibit_count(accession: str, count: int):
    """Update filing with exhibit count."""
    url = f"{SUPABASE_URL}/rest/v1/filings?accession_number=eq.{accession}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    body = json.dumps({"exhibit_count": count}).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="PATCH")
    try:
        urllib.request.urlopen(req, timeout=15)
    except Exception:
        pass


def process_exhibits(accession: str, form: str, dry_run: bool = False) -> int:
    """Process exhibits for a single filing."""
    index_items = fetch_filing_index(accession)
    if not index_items:
        return 0

    # Filter for exhibits — EDGAR filenames use patterns like:
    #   ex31_1.htm, asts-ex19_1.htm, exhibit21.htm, etc.
    EXHIBIT_RE = re.compile(r'(?:^|[-_])ex\d', re.IGNORECASE)
    exhibit_items = [
        item for item in index_items
        if EXHIBIT_RE.search(item.get("name", ""))
        or "exhibit" in item.get("name", "").lower()
        or "exhibit" in item.get("description", "").lower()
    ]

    if not exhibit_items:
        return 0

    log(f"  {len(exhibit_items)} exhibits found")
    processed = 0

    # Common SEC exhibit types
    EXHIBIT_TYPES = {
        "4": "Instruments defining rights of security holders",
        "10": "Material contracts",
        "19": "Insider trading policies",
        "21": "Subsidiaries of the registrant",
        "23": "Consents of experts and counsel",
        "31": "Rule 13a-14(a) Certifications",
        "32": "Section 1350 Certifications",
        "99": "Additional exhibits",
    }

    for item in exhibit_items[:10]:  # Max 10 per filing
        name = item.get("name", "")
        desc = item.get("description", "")
        # Derive exhibit type from filename if no description
        if not desc:
            ex_match = re.search(r'ex(\d+)', name, re.IGNORECASE)
            if ex_match:
                ex_num = ex_match.group(1)
                desc = f"Exhibit {ex_num}"
                for prefix, label in EXHIBIT_TYPES.items():
                    if ex_num.startswith(prefix):
                        desc = f"Exhibit {ex_num} - {label}"
                        break

        if dry_run:
            log(f"    [DRY RUN] {name}: {desc}")
            processed += 1
            continue

        try:
            url = get_filing_url(accession, name)
            content = fetch_bytes(url)
            time.sleep(SEC_RATE_LIMIT_SECONDS)

            content_type = "text/html"
            if name.lower().endswith(".pdf"):
                content_type = "application/pdf"
            elif name.lower().endswith(".xml"):
                content_type = "application/xml"

            # Upload to storage
            storage_result = upload_sec_exhibit(
                accession_number=accession,
                exhibit_number=name,
                content=content,
                content_type=content_type,
            )

            # Extract text
            extracted_text = None
            if content_type == "text/html":
                try:
                    html_content = content.decode("utf-8", errors="replace")
                    extracted_text = extract_text_from_html(html_content)[:50000]
                except Exception:
                    pass
            elif content_type == "application/pdf":
                try:
                    extracted_text = extract_pdf_text(content)[:50000]
                except Exception:
                    pass

            exhibit_record = {
                "accession_number": accession,
                "exhibit_number": name,
                "exhibit_type": desc or None,
                "description": desc or None,
                "filename": name,
                "file_size_bytes": len(content),
                "content_type": content_type,
                "storage_path": storage_result.get("path") if storage_result.get("success") else None,
                "content_hash": storage_result.get("hash"),
                "content_text": extracted_text,
                "url": url,
                "fetched_at": datetime.utcnow().isoformat() + "Z",
            }

            insert_exhibit(exhibit_record)
            processed += 1
            text_len = len(extracted_text) if extracted_text else 0
            log(f"    {name} ({len(content):,}B, {text_len:,} chars)")

        except Exception as e:
            log(f"    {name}: ERROR {e}")

    return processed


def run(all_forms: bool = False, dry_run: bool = False, limit: int = 0):
    log("=" * 60)
    log("SEC EXHIBIT BACKFILL")
    log("=" * 60)

    if not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    # Get filings needing exhibits
    forms = None if all_forms else HIGH_VALUE_FORMS
    filings = get_filings_needing_exhibits(forms)
    log(f"Filings needing exhibits: {len(filings)}")

    # Filter out already-processed
    already = get_already_processed()
    log(f"Already have exhibits: {len(already)}")
    filings = [f for f in filings if f["accession_number"] not in already]
    log(f"To process: {len(filings)}")

    if limit > 0:
        filings = filings[:limit]
        log(f"Limited to: {limit}")

    if not filings:
        log("Nothing to process.")
        return

    total_exhibits = 0
    success = 0
    no_exhibits = 0

    for i, f in enumerate(filings):
        accession = f["accession_number"]
        form = f["form"]
        log(f"[{i+1}/{len(filings)}] {form} ({f['filing_date']}): {accession}")

        count = process_exhibits(accession, form, dry_run)

        if count > 0:
            total_exhibits += count
            success += 1
            if not dry_run:
                mark_exhibit_count(accession, count)
        else:
            no_exhibits += 1
            if not dry_run:
                mark_exhibit_count(accession, 0)

        time.sleep(SEC_RATE_LIMIT_SECONDS)

        if (i + 1) % 10 == 0:
            log(f"Progress: {i+1}/{len(filings)} ({success} with exhibits, {total_exhibits} total)")

    log("=" * 60)
    log(f"DONE: {success} filings with exhibits, {total_exhibits} exhibits total")
    log(f"  {no_exhibits} filings had no exhibits")
    log("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SEC Exhibit Backfill")
    parser.add_argument("--all-forms", action="store_true", help="Process all form types")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    parser.add_argument("--limit", type=int, default=0, help="Max filings to process")
    args = parser.parse_args()

    run(all_forms=args.all_forms, dry_run=args.dry_run, limit=args.limit)
