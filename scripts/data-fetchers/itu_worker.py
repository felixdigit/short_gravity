#!/usr/bin/env python3
"""
ITU "As Received" Satellite Filings Worker

Monitors the ITU Radiocommunication Bureau's "As Received" page for new
satellite network filings that may relate to AST SpaceMobile.

Source: https://www.itu.int/ITU-R/space/asreceived/Publication/AsReceived

This page shows filings received by ITU-R but not yet published in the
bi-weekly BR IFIC circular — the earliest public signal of new constellation
filings.

The worker also checks the ITU Space Network List for existing AST filings.

Usage:
    python3 itu_worker.py                  # Standard run
    python3 itu_worker.py --dry-run        # Preview only
    python3 itu_worker.py --all            # Fetch all, not just AST-related

Environment:
    SUPABASE_URL, SUPABASE_SERVICE_KEY — Database
    ANTHROPIC_API_KEY — For AI analysis (optional)

No Playwright needed — the ITU pages serve rendered HTML.
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
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Set

# =============================================================================
# Configuration
# =============================================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

ITU_AS_RECEIVED_URL = "https://www.itu.int/ITU-R/space/asreceived/Publication/AsReceived"
ITU_SNL_SEARCH_URL = "https://www.itu.int/net/ITU-R/space/snl/listofnetworks/index.asp"

# Keywords to match AST SpaceMobile filings
# ITU filings use network names, not company names
AST_KEYWORDS = [
    "spacemobile",
    "ast",
    "bluewalker",
    "bluebird",
    "usasat",
    "USASAT-NGSO",
    "PNGSO",      # Papua New Guinea NGSO (historical)
]

# Administrations that might file for AST
RELEVANT_ADMINS = [
    "USA",     # United States (primary)
    "D",       # Germany (Vodafone EU constellation)
    "PNG",     # Papua New Guinea (historical)
    "G",       # United Kingdom
]

RATE_LIMIT_SECONDS = 2.0

# Valid filing_system values per fcc_filings CHECK constraint
VALID_FILING_SYSTEMS = {"ICFS", "ECFS", "ELS"}


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# =============================================================================
# HTML Table Parser
# =============================================================================

class TableParser(HTMLParser):
    """Parse HTML tables into list of row dicts."""

    def __init__(self):
        super().__init__()
        self.tables: List[List[List[str]]] = []
        self.current_table: Optional[List[List[str]]] = None
        self.current_row: Optional[List[str]] = None
        self.current_cell: Optional[str] = None
        self.in_cell = False

    def handle_starttag(self, tag: str, attrs: list):
        if tag == "table":
            self.current_table = []
        elif tag == "tr" and self.current_table is not None:
            self.current_row = []
        elif tag in ("td", "th") and self.current_row is not None:
            self.current_cell = ""
            self.in_cell = True

    def handle_endtag(self, tag: str):
        if tag in ("td", "th") and self.in_cell:
            self.in_cell = False
            if self.current_row is not None and self.current_cell is not None:
                self.current_row.append(self.current_cell.strip())
            self.current_cell = None
        elif tag == "tr" and self.current_row is not None:
            if self.current_table is not None:
                self.current_table.append(self.current_row)
            self.current_row = None
        elif tag == "table" and self.current_table is not None:
            if self.current_table:
                self.tables.append(self.current_table)
            self.current_table = None

    def handle_data(self, data: str):
        if self.in_cell and self.current_cell is not None:
            self.current_cell += data


def parse_tables(html: str) -> List[List[List[str]]]:
    parser = TableParser()
    parser.feed(html)
    return parser.tables


def tables_to_dicts(tables: List[List[List[str]]]) -> List[List[Dict[str, str]]]:
    """Convert parsed tables to list of row dicts using first row as headers."""
    result = []
    for table in tables:
        if len(table) < 2:
            continue
        headers = [h.lower().strip() for h in table[0]]
        rows = []
        for row in table[1:]:
            if len(row) >= len(headers):
                rows.append({headers[i]: row[i] for i in range(len(headers))})
            elif row:
                # Pad with empty strings
                padded = row + [""] * (len(headers) - len(row))
                rows.append({headers[i]: padded[i] for i in range(len(headers))})
        if rows:
            result.append(rows)
    return result


# =============================================================================
# HTTP / Supabase
# =============================================================================

def fetch_url(url: str, retries: int = 3) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Short Gravity Research"
    }
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise last_error


def supabase_headers() -> Dict:
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def supabase_get(endpoint: str) -> List[Dict]:
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    try:
        req = urllib.request.Request(url, headers=supabase_headers())
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error = e.read().decode() if e.fp else ""
        log(f"  Supabase GET error {e.code}: {error[:200]}")
        return []


def supabase_upsert(table: str, rows: List[Dict], on_conflict: str) -> int:
    if not rows:
        return 0
    url = f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={on_conflict}"
    headers = supabase_headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"

    count = 0
    for i in range(0, len(rows), 50):
        batch = rows[i:i + 50]
        try:
            body = json.dumps(batch).encode()
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            urllib.request.urlopen(req, timeout=30)
            count += len(batch)
        except urllib.error.HTTPError as e:
            error = e.read().decode() if e.fp else ""
            log(f"  Upsert error {e.code}: {error[:300]}")
    return count


def get_existing_itu_ids() -> Set[str]:
    rows = supabase_get("fcc_filings?select=file_number&file_number=like.ITU-*")
    return {r["file_number"] for r in rows if r.get("file_number")}


def generate_ai_analysis(filing: Dict) -> Optional[str]:
    if not ANTHROPIC_API_KEY:
        return None
    try:
        content = json.dumps(filing, indent=2)
        body = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 400,
            "messages": [{
                "role": "user",
                "content": (
                    "Analyze this ITU satellite filing for an $ASTS investor. "
                    "Is this related to AST SpaceMobile? What does it tell us about "
                    "constellation plans, orbital parameters, or spectrum? "
                    "Be specific.\n\n" + content[:3000]
                ),
            }]
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return data.get("content", [{}])[0].get("text", "")
    except Exception as e:
        log(f"  AI analysis error: {e}")
        return None


# =============================================================================
# ITU "As Received" scraper
# =============================================================================

def is_ast_related(row: Dict[str, str]) -> tuple:
    """Check if a filing row might be related to AST SpaceMobile.

    Returns (is_related, matched_keyword) tuple.
    """
    values = " ".join(str(v).lower() for v in row.values())
    for kw in AST_KEYWORDS:
        if kw.lower() in values:
            return True, f"keyword:{kw}"
    # Check administration
    admin = row.get("adm", "") or row.get("administration", "") or row.get("adm.", "")
    if admin.upper() in RELEVANT_ADMINS:
        return True, f"admin:{admin.upper()}"
    return False, ""


def fetch_as_received(fetch_all: bool = False) -> List[Dict]:
    """Fetch ITU As Received filings page and parse the table."""
    log("Fetching ITU 'As Received' filings...")

    try:
        html = fetch_url(ITU_AS_RECEIVED_URL)
    except Exception as e:
        log(f"  Error fetching ITU page: {e}")
        return []

    tables = parse_tables(html)
    if not tables:
        log("  No tables found on ITU page")
        # Try to extract any useful content
        log(f"  Page length: {len(html)} chars")
        return []

    all_dicts = tables_to_dicts(tables)
    if not all_dicts:
        log("  Could not parse table headers")
        return []

    # Use the largest table (likely the main filings table)
    main_table = max(all_dicts, key=len)
    log(f"  Parsed {len(main_table)} rows from ITU table")

    # Filter for AST-related filings (or all if --all flag)
    filings = []
    for row in main_table:
        if fetch_all:
            filings.append(row)
        else:
            related, matched = is_ast_related(row)
            if related:
                log(f"  Match: {matched} — {list(row.values())[:3]}")
                filings.append(row)

    log(f"  {'All' if fetch_all else 'AST-related'} filings: {len(filings)}")
    return filings


def convert_to_fcc_filing(row: Dict[str, str], index: int) -> Dict:
    """Convert an ITU row to our fcc_filings table format."""
    # Extract fields — ITU table headers vary, try common patterns
    ntc_id = row.get("ntc_id", "") or row.get("ntc id", "") or row.get("ref", "")
    network_name = row.get("satellite network", "") or row.get("network", "") or row.get("sat_name", "")
    admin = row.get("adm", "") or row.get("adm.", "") or row.get("administration", "")
    date_received = row.get("date of receipt", "") or row.get("date received", "") or row.get("date", "")
    submission_type = row.get("type", "") or row.get("submission type", "") or row.get("nature", "")

    # Build a unique file number
    file_number = f"ITU-{ntc_id}" if ntc_id else f"ITU-AS-{index:04d}"

    # Parse date
    filed_date = None
    if date_received:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y"):
            try:
                filed_date = datetime.strptime(date_received.strip(), fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                continue

    title = f"ITU Filing: {network_name}" if network_name else f"ITU Filing: {admin} {submission_type}"
    description = " | ".join(f"{k}: {v}" for k, v in row.items() if v.strip())

    return {
        "file_number": file_number,
        "filing_system": "ICFS",
        "title": title,
        "description": description,
        "filer_name": admin,
        "call_sign": network_name,
        "filing_type": submission_type or "ITU-AsReceived",
        "filed_date": filed_date,
        "application_status": "Received by ITU",
        "content_text": f"{title}\n{description}\nAdministration: {admin}\nNetwork: {network_name}\nType: {submission_type}",
        "source_url": ITU_AS_RECEIVED_URL,
        "ai_summary": None,
    }


# =============================================================================
# Main
# =============================================================================

def run(fetch_all: bool = False, dry_run: bool = False):
    log("=" * 60)
    log("ITU AS RECEIVED WORKER")
    log(f"  Mode: {'ALL filings' if fetch_all else 'AST-related only'}")
    log(f"  Dry run: {dry_run}")
    log("=" * 60)

    existing = get_existing_itu_ids()
    log(f"  Existing ITU filings in DB: {len(existing)}")

    # Fetch and parse ITU page
    raw_filings = fetch_as_received(fetch_all)

    if not raw_filings:
        log("\n  No filings found. The ITU page may have changed structure.")
        log("  Check: " + ITU_AS_RECEIVED_URL)
        return

    # Convert to DB format
    converted = []
    for i, row in enumerate(raw_filings):
        filing = convert_to_fcc_filing(row, i)
        if filing["file_number"] not in existing:
            converted.append(filing)

    log(f"\n  New filings to process: {len(converted)}")

    if dry_run:
        for f in converted:
            log(f"  [DRY RUN] {f['file_number']} — {f['title']}")
        return

    # Generate AI analysis for AST-related filings
    if ANTHROPIC_API_KEY:
        for filing in converted:
            values = " ".join(str(v).lower() for v in filing.values())
            is_ast = any(kw.lower() in values for kw in AST_KEYWORDS)
            if is_ast:
                analysis = generate_ai_analysis(filing)
                if analysis:
                    filing["ai_summary"] = analysis
                    log(f"  AI: {filing['file_number']} — analyzed")
                time.sleep(RATE_LIMIT_SECONDS)

    # Validate filing_system before upsert
    valid = []
    for record in converted:
        if record.get("filing_system") not in VALID_FILING_SYSTEMS:
            log(f"  ERROR: Invalid filing_system '{record.get('filing_system')}' for {record.get('file_number')} — must be one of {VALID_FILING_SYSTEMS}")
            continue
        valid.append(record)
    converted = valid

    # Upsert to database
    if converted:
        count = supabase_upsert("fcc_filings", converted, "file_number,filing_system")
        log(f"\n  Upserted {count} ITU filings")
    else:
        log("\n  No new filings to upsert")

    log(f"\n{'=' * 60}")
    log(f"DONE: {len(converted)} filings processed")
    log(f"{'=' * 60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ITU As Received Satellite Filings Worker")
    parser.add_argument("--all", action="store_true", help="Fetch all filings, not just AST-related")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    run(fetch_all=args.all, dry_run=args.dry_run)
