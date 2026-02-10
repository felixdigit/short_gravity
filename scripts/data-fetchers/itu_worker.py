#!/usr/bin/env python3
"""
ITU Satellite Filings Worker

Monitors the ITU Radiocommunication Bureau's "As Received" page and the
Space Network List (SNL) for AST SpaceMobile satellite network filings.

AST SpaceMobile's known ITU network names:
  - MICRONSAT / MICRONSAT-2  (filed via Papua New Guinea "PNG" admin)
  - USASAT-NGSO-20           (filed via USA admin)

Sources:
  As Received: https://www.itu.int/ITU-R/space/asreceived/Publication/AsReceived
  SNL Hub:     https://www.itu.int/en/ITU-R/space/snl/Pages/default.aspx
  Explorer:    https://www.itu.int/itu-r/space/apps/public/spaceexplorer/

Usage:
    python3 itu_worker.py                  # Standard run
    python3 itu_worker.py --dry-run        # Preview only
    python3 itu_worker.py --all            # Fetch all, not just AST-related
    python3 itu_worker.py --audit          # Audit existing ITU records for garbage

Environment:
    SUPABASE_URL, SUPABASE_SERVICE_KEY -- Database
    ANTHROPIC_API_KEY -- For AI analysis (optional)

No Playwright needed -- the ITU pages serve rendered HTML.
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Set, Tuple

# =============================================================================
# Configuration
# =============================================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

ITU_AS_RECEIVED_URL = "https://www.itu.int/ITU-R/space/asreceived/Publication/AsReceived"
ITU_SNL_HUB_URL = "https://www.itu.int/en/ITU-R/space/snl/Pages/default.aspx"
ITU_SPACE_EXPLORER_BASE = "https://www.itu.int/itu-r/space/apps/public/spaceexplorer"

# ---------------------------------------------------------------------------
# AST SpaceMobile's actual ITU network names.
# These are the ONLY networks we care about. "ast" alone matches too broadly
# (e.g. ASTRA, CASTLEROCK, ASTRASAT ...). The keyword list is checked as
# case-insensitive substrings against all row values joined together.
# ---------------------------------------------------------------------------
AST_NETWORK_NAMES = [
    "MICRONSAT",        # PNG filing -- BlueWalker / Bluebird constellation
    "MICRONSAT-2",      # PNG filing -- 368-sat expansion
    "USASAT-NGSO-20",   # USA filing -- FCC coordination
]

AST_KEYWORDS = [
    "spacemobile",
    "ast spacemobile",
    "bluewalker",
    "bluebird",
    "micronsat",
    "usasat-ngso-20",
]

RATE_LIMIT_SECONDS = 2.0


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
                padded = row + [""] * (len(headers) - len(row))
                rows.append({headers[i]: padded[i] for i in range(len(headers))})
        if rows:
            result.append(rows)
    return result


# =============================================================================
# HTTP / Supabase
# =============================================================================

def fetch_url(url: str, retries: int = 3, data: Optional[bytes] = None,
              extra_headers: Optional[Dict[str, str]] = None) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Short Gravity Research"
    }
    if extra_headers:
        headers.update(extra_headers)
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers, data=data)
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
# Filtering
# =============================================================================

def is_ast_related(row: Dict[str, str]) -> bool:
    """Check if a filing row is related to AST SpaceMobile.

    Matches on:
      1. Exact network names (MICRONSAT, USASAT-NGSO-20) -- primary signal
      2. Keyword substrings (spacemobile, bluewalker, etc.) -- secondary signal

    Does NOT match on administration alone. Matching admin=USA/PNG would pull
    in every O3B, Starlink, Kuiper, and HYPERION filing on the page.
    """
    # Gather all row values into one string for substring search
    values = " ".join(str(v) for v in row.values())
    values_upper = values.upper()

    # Check exact network names (case-insensitive)
    for name in AST_NETWORK_NAMES:
        if name.upper() in values_upper:
            return True

    # Check broader keywords (case-insensitive)
    values_lower = values.lower()
    for kw in AST_KEYWORDS:
        if kw.lower() in values_lower:
            return True

    return False


# =============================================================================
# ITU "As Received" scraper
# =============================================================================

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
        if fetch_all or is_ast_related(row):
            filings.append(row)

    log(f"  {'All' if fetch_all else 'AST-related'} filings: {len(filings)}")
    return filings


# =============================================================================
# ITU Space Network List (SNL) search
# =============================================================================

def fetch_snl_for_network(network_name: str) -> List[Dict]:
    """Search the ITU SNL Hub and Space Explorer for a specific network name.

    The ITU Space Explorer is a JavaScript SPA and its backend API requires
    authentication.  We try multiple approaches:

      1. The SNL Hub WordPress tables API (public, limited)
      2. The SNL "bringing into use" / "list in use" ASP pages (parse HTML)
      3. The Space Explorer deep-link pages (limited without JS but may
         contain metadata in the initial HTML payload)

    Returns a list of dicts with whatever filing metadata we can extract.
    """
    results: List[Dict] = []

    # --- Approach 1: SNL "list in use" page (ASP, serves HTML tables) ---
    list_in_use_url = (
        "https://www.itu.int/net/ITU-R/space/snl/listinuse/index.asp"
        f"?sel_satname={urllib.parse.quote(network_name)}"
        "&sel_adm=&sel_long_from=&sel_long_to="
        "&sel_gso=N"  # Non-GSO
        "&order=d_reg_limit&mod=desc"
    )
    log(f"  SNL search: {network_name} via list-in-use...")
    try:
        html = fetch_url(list_in_use_url)
        tables = parse_tables(html)
        all_dicts = tables_to_dicts(tables)
        for table_rows in all_dicts:
            for row in table_rows:
                row_text = " ".join(str(v).upper() for v in row.values())
                if network_name.upper() in row_text:
                    row["_source"] = "snl-list-in-use"
                    row["_network_name"] = network_name
                    results.append(row)
        if results:
            log(f"    Found {len(results)} rows in list-in-use")
    except Exception as e:
        log(f"    list-in-use fetch failed: {e}")

    time.sleep(RATE_LIMIT_SECONDS)

    # --- Approach 2: SNL "list of networks" page ---
    list_of_networks_url = (
        "https://www.itu.int/net/ITU-R/space/snl/listofnetworks/index.asp"
        f"?sel_satname={urllib.parse.quote(network_name)}"
        "&sel_adm=&sel_long_from=&sel_long_to="
        "&sel_gso=N"
        "&order=d_reg_limit&mod=desc"
    )
    log(f"  SNL search: {network_name} via list-of-networks...")
    try:
        html = fetch_url(list_of_networks_url)
        tables = parse_tables(html)
        all_dicts = tables_to_dicts(tables)
        for table_rows in all_dicts:
            for row in table_rows:
                row_text = " ".join(str(v).upper() for v in row.values())
                if network_name.upper() in row_text:
                    row["_source"] = "snl-list-of-networks"
                    row["_network_name"] = network_name
                    results.append(row)
        if not any(r["_source"] == "snl-list-of-networks" for r in results):
            log(f"    No rows matched in list-of-networks")
    except Exception as e:
        log(f"    list-of-networks fetch failed: {e}")

    time.sleep(RATE_LIMIT_SECONDS)

    # --- Approach 3: Space Explorer deep-link (metadata in HTML if any) ---
    explorer_url = (
        f"{ITU_SPACE_EXPLORER_BASE}/networks-explorer/"
        f"space-stations/dashboard/non-plans/{urllib.parse.quote(network_name)}/"
    )
    log(f"  SNL search: {network_name} via Space Explorer deep-link...")
    try:
        html = fetch_url(explorer_url)
        # Space Explorer is a React SPA, but sometimes embeds JSON in the HTML
        # or has <meta> tags with useful info. Extract what we can.
        json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', html, re.DOTALL)
        if json_match:
            try:
                state = json.loads(json_match.group(1))
                log(f"    Found embedded state data")
                results.append({
                    "_source": "space-explorer",
                    "_network_name": network_name,
                    "_state_data": state,
                })
            except json.JSONDecodeError:
                pass

        # Check for any title or meta content
        title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        if title_match and network_name.upper() in title_match.group(1).upper():
            log(f"    Page title mentions {network_name}")
        else:
            log(f"    Space Explorer page is JS-rendered (no server-side data)")
    except Exception as e:
        log(f"    Space Explorer fetch failed: {e}")

    return results


def fetch_snl_filings() -> List[Dict]:
    """Search the SNL for all known AST SpaceMobile network names."""
    log("\nSearching ITU Space Network List (SNL)...")
    all_results: List[Dict] = []

    for network_name in AST_NETWORK_NAMES:
        results = fetch_snl_for_network(network_name)
        all_results.extend(results)
        time.sleep(RATE_LIMIT_SECONDS)

    log(f"  Total SNL results: {len(all_results)}")
    return all_results


def convert_snl_to_fcc_filing(row: Dict, index: int) -> Dict:
    """Convert an SNL result row to our fcc_filings table format."""
    network_name = row.get("_network_name", "")
    source = row.get("_source", "snl")

    # Try to extract fields from whatever columns the SNL page returned
    sat_name = (
        row.get("satellite network", "")
        or row.get("network", "")
        or row.get("sat_name", "")
        or row.get("name", "")
        or network_name
    )
    admin = row.get("adm", "") or row.get("adm.", "") or row.get("administration", "")
    status = row.get("status", "") or row.get("reg. status", "")
    date_str = (
        row.get("date of receipt", "")
        or row.get("date received", "")
        or row.get("date", "")
        or row.get("reg. date", "")
    )
    orbit_info = row.get("long.", "") or row.get("orbit", "") or row.get("longitude", "")
    provision = row.get("provision", "") or row.get("rr provision", "")

    file_number = f"ITU-SNL-{network_name}-{index:03d}"

    filed_date = None
    if date_str:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y"):
            try:
                filed_date = datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                continue

    # Strip internal keys from description
    desc_items = {k: v for k, v in row.items() if not k.startswith("_") and str(v).strip()}
    description = " | ".join(f"{k}: {v}" for k, v in desc_items.items())

    title = f"ITU SNL: {sat_name}" if sat_name else f"ITU SNL: {network_name}"

    return {
        "file_number": file_number,
        "filing_system": "ICFS",
        "title": title,
        "description": description,
        "filer_name": admin or ("PNG" if "MICRONSAT" in network_name.upper() else "USA"),
        "call_sign": sat_name,
        "filing_type": provision or f"ITU-SNL-{source}",
        "filed_date": filed_date,
        "application_status": status or "SNL Record",
        "content_text": (
            f"{title}\n{description}\n"
            f"Administration: {admin}\nNetwork: {sat_name}\n"
            f"Orbit: {orbit_info}\nProvision: {provision}"
        ),
        "source_url": ITU_SNL_HUB_URL,
        "ai_summary": None,
    }


# =============================================================================
# Garbage audit
# =============================================================================

def audit_existing_itu_records():
    """Check all ITU-* records in the DB and flag non-AST garbage.

    Queries every record with file_number LIKE 'ITU-%' and checks whether
    it actually matches AST SpaceMobile network names or keywords. Logs
    which records are legit and which are garbage. Does NOT delete anything.
    """
    log("=" * 60)
    log("ITU RECORD AUDIT")
    log("=" * 60)

    rows = supabase_get(
        "fcc_filings?select=file_number,title,call_sign,filer_name,description,content_text"
        "&file_number=like.ITU-*"
        "&order=file_number.asc"
    )

    if not rows:
        log("  No ITU records found in DB")
        return

    log(f"  Found {len(rows)} ITU records\n")

    legit = []
    garbage = []

    for row in rows:
        text = " ".join(str(v) for v in row.values() if v)
        text_upper = text.upper()
        text_lower = text.lower()

        is_match = False
        matched_by = ""

        # Check exact network names
        for name in AST_NETWORK_NAMES:
            if name.upper() in text_upper:
                is_match = True
                matched_by = f"network:{name}"
                break

        # Check keywords
        if not is_match:
            for kw in AST_KEYWORDS:
                if kw.lower() in text_lower:
                    is_match = True
                    matched_by = f"keyword:{kw}"
                    break

        file_num = row.get("file_number", "?")
        title = row.get("title", "?")
        call_sign = row.get("call_sign", "")
        admin = row.get("filer_name", "")

        if is_match:
            legit.append(row)
            log(f"  OK   {file_num}  [{matched_by}]")
            log(f"        {title}  admin={admin}  network={call_sign}")
        else:
            garbage.append(row)
            log(f"  GARBAGE  {file_num}")
            log(f"           {title}  admin={admin}  network={call_sign}")

    log(f"\n  Summary: {len(legit)} legit, {len(garbage)} garbage out of {len(rows)} total")

    if garbage:
        log("\n  Garbage file_numbers (safe to delete):")
        for g in garbage:
            log(f"    - {g['file_number']}")
        log("\n  To delete, run SQL:")
        file_nums = ", ".join(f"'{g['file_number']}'" for g in garbage)
        log(f"    DELETE FROM fcc_filings WHERE file_number IN ({file_nums});")


# =============================================================================
# Convert As Received row to DB format
# =============================================================================

def convert_to_fcc_filing(row: Dict[str, str], index: int) -> Dict:
    """Convert an ITU row to our fcc_filings table format."""
    ntc_id = row.get("ntc_id", "") or row.get("ntc id", "") or row.get("ref", "")
    network_name = row.get("satellite network", "") or row.get("network", "") or row.get("sat_name", "")
    admin = row.get("adm", "") or row.get("adm.", "") or row.get("administration", "")
    date_received = row.get("date of receipt", "") or row.get("date received", "") or row.get("date", "")
    submission_type = row.get("type", "") or row.get("submission type", "") or row.get("nature", "")

    file_number = f"ITU-{ntc_id}" if ntc_id else f"ITU-AS-{index:04d}"

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
    log("ITU SATELLITE FILINGS WORKER")
    log(f"  Mode: {'ALL filings' if fetch_all else 'AST-related only'}")
    log(f"  Dry run: {dry_run}")
    log(f"  Target networks: {', '.join(AST_NETWORK_NAMES)}")
    log("=" * 60)

    existing = get_existing_itu_ids()
    log(f"  Existing ITU filings in DB: {len(existing)}")

    # ----- Phase 1: As Received page -----
    raw_filings = fetch_as_received(fetch_all)
    converted = []

    if raw_filings:
        for i, row in enumerate(raw_filings):
            filing = convert_to_fcc_filing(row, i)
            if filing["file_number"] not in existing:
                converted.append(filing)
        log(f"\n  New As Received filings: {len(converted)}")
    else:
        log("\n  No As Received filings found (page may have changed structure)")
        log(f"  Check: {ITU_AS_RECEIVED_URL}")

    # ----- Phase 2: SNL search for known network names -----
    snl_results = fetch_snl_filings()
    snl_converted = []

    if snl_results:
        for i, row in enumerate(snl_results):
            filing = convert_snl_to_fcc_filing(row, i)
            if filing["file_number"] not in existing:
                snl_converted.append(filing)
        log(f"  New SNL filings: {len(snl_converted)}")
        converted.extend(snl_converted)

    # ----- Output -----
    log(f"\n  Total new filings to process: {len(converted)}")

    if dry_run:
        for f in converted:
            log(f"  [DRY RUN] {f['file_number']} -- {f['title']}")
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
                    log(f"  AI: {filing['file_number']} -- analyzed")
                time.sleep(RATE_LIMIT_SECONDS)

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
    parser = argparse.ArgumentParser(description="ITU Satellite Filings Worker")
    parser.add_argument("--all", action="store_true", help="Fetch all filings, not just AST-related")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--audit", action="store_true", help="Audit existing ITU records for garbage")
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    if args.audit:
        audit_existing_itu_records()
    else:
        run(fetch_all=args.all, dry_run=args.dry_run)
