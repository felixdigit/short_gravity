#!/usr/bin/env python3
"""
FCC ECFS Docket Crawler Worker

Systematically ingests ALL filings from key ASTS-related FCC ECFS proceedings.
Targets the fcc_filings table with filing_system=ECFS.

Fills the gap: AT&T missing 14 filings, SpaceX 20+ adversary filings missing,
and dockets 23-135, 25-201, 25-340, 25-306 not tracked systematically.

Usage:
    # Crawl all target dockets (incremental by default)
    python3 ecfs_worker.py

    # Single docket
    python3 ecfs_worker.py --docket 23-65

    # Full backfill (re-process everything)
    python3 ecfs_worker.py --backfill

    # Incremental only (skip existing file_numbers)
    python3 ecfs_worker.py --incremental

    # Dry run
    python3 ecfs_worker.py --dry-run

    # Limit filings processed
    python3 ecfs_worker.py --limit 50

    # Skip PDF download/extraction
    python3 ecfs_worker.py --no-pdf
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple


# ============================================================================
# Configuration
# ============================================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

FCC_API_BASE = "https://publicapi.fcc.gov/ecfs/filings"
FCC_API_KEY = os.environ.get("FCC_API_KEY", "DEMO_KEY")

# Rate limiting
RATE_LIMIT_DELAY = 1.0        # seconds between ECFS API requests
RATE_LIMIT_429_WAIT = 15.0    # seconds to wait on 429 response
MAX_RETRIES = 3

# Target dockets - hardcoded for ASTS coverage
TARGET_DOCKETS = [
    {
        "docket": "23-65",
        "name": "SCS NPRM - Supplemental Coverage from Space Rulemaking",
        "expected": 269,
        "importance": "critical",
    },
    {
        "docket": "23-135",
        "name": "SpaceX/T-Mobile SCS Authorization",
        "expected": 50,
        "importance": "high",
    },
    {
        "docket": "25-201",
        "name": "AST SpaceMobile SCS Modification Application",
        "expected": 100,
        "importance": "critical",
    },
    {
        "docket": "25-306",
        "name": "Space Modernization NPRM",
        "expected": 50,
        "importance": "high",
    },
    {
        "docket": "25-340",
        "name": "SpaceX NextGen MSS Application",
        "expected": 30,
        "importance": "high",
    },
    {
        "docket": "22-271",
        "name": "Space Innovation / Single Network Future SCS Framework",
        "expected": 200,
        "importance": "critical",
    },
]

# Filers flagged as high importance for ASTS research
HIGH_IMPORTANCE_FILERS = {
    "ast spacemobile",
    "ast & science",
    "at&t",
    "at&t services",
    "t-mobile",
    "t-mobile usa",
    "verizon",
    "verizon communications",
    "spacex",
    "space exploration holdings",
    "space exploration technologies",
    "starlink",
    "lynk global",
    "federal communications commission",
    "dish network",
    "echostar",
    "ligado networks",
}


# ============================================================================
# Logging
# ============================================================================

def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ============================================================================
# HTTP / Retry
# ============================================================================

def fetch_url(url: str, headers: Optional[Dict] = None, retries: int = MAX_RETRIES) -> str:
    """Fetch URL with retry + exponential backoff + 429 handling."""
    default_headers = {
        "User-Agent": "Short Gravity Research gabriel@shortgravity.com",
        "Accept": "application/json",
    }
    if headers:
        default_headers.update(headers)

    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=default_headers)
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code == 429:
                wait = RATE_LIMIT_429_WAIT * (attempt + 1)
                log(f"  Rate limited (429). Waiting {wait:.0f}s...")
                time.sleep(wait)
            elif e.code >= 500:
                wait = 2 ** attempt
                log(f"  Server error ({e.code}). Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
        except (urllib.error.URLError, OSError) as e:
            last_error = e
            wait = 2 ** attempt
            log(f"  Network error: {e}. Retrying in {wait}s...")
            time.sleep(wait)

    raise last_error


def fetch_json(url: str) -> Dict:
    """Fetch and parse JSON."""
    content = fetch_url(url)
    return json.loads(content)


def fetch_bytes(url: str, retries: int = MAX_RETRIES) -> bytes:
    """Fetch binary content (for PDFs)."""
    headers = {"User-Agent": "Short Gravity Research gabriel@shortgravity.com"}
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as response:
                return response.read()
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise last_error


# ============================================================================
# Supabase Operations
# ============================================================================

def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None,
                     extra_headers: Optional[Dict] = None) -> list | dict:
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
    if extra_headers:
        headers.update(extra_headers)

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


def get_existing_file_numbers() -> Set[str]:
    """Get all existing ECFS file_numbers from fcc_filings table."""
    try:
        result = supabase_request(
            "GET",
            "fcc_filings?filing_system=eq.ECFS&select=file_number"
        )
        return {r["file_number"] for r in result if r.get("file_number")}
    except Exception as e:
        log(f"Error fetching existing file_numbers: {e}")
        return set()


def get_latest_filing_date(docket: str) -> Optional[str]:
    """Get the most recent filed_date for a docket (for incremental mode)."""
    try:
        encoded = urllib.parse.quote(docket)
        result = supabase_request(
            "GET",
            f"fcc_filings?filing_system=eq.ECFS&docket=eq.{encoded}"
            f"&select=filed_date&order=filed_date.desc&limit=1"
        )
        if result and result[0].get("filed_date"):
            return result[0]["filed_date"]
    except Exception as e:
        log(f"Error fetching latest date for docket {docket}: {e}")
    return None


def upsert_filing(record: Dict) -> bool:
    """Upsert filing — insert or skip if file_number already exists."""
    try:
        supabase_request(
            "POST",
            "fcc_filings?on_conflict=filing_system,file_number",
            record,
            extra_headers={"Prefer": "return=minimal,resolution=merge-duplicates"},
        )
        return True
    except urllib.error.HTTPError as e:
        if e.code == 409:
            return False
        return False
    except Exception:
        return False


# ============================================================================
# ECFS API
# ============================================================================

def fetch_docket_page(docket: str, limit: int = 25, offset: int = 0) -> Tuple[List[Dict], int]:
    """
    Fetch one page of filings for a docket.
    Returns (filings_list, total_count).
    """
    url = (
        f"{FCC_API_BASE}?api_key={FCC_API_KEY}"
        f"&proceedings.name={urllib.parse.quote(docket)}"
        f"&sort=date_received,DESC"
        f"&limit={limit}&offset={offset}"
    )

    data = fetch_json(url)

    # The ECFS API returns filings under "filings" or "filing" key
    filings = data.get("filings", []) or data.get("filing", [])

    # Total count from aggregations
    total = 0
    agg = data.get("aggregations", {})
    if isinstance(agg, dict):
        total = agg.get("total", 0)
    elif isinstance(data.get("matches"), int):
        total = data["matches"]

    return filings, total


def fetch_all_docket_filings(docket: str, since_date: Optional[str] = None) -> List[Dict]:
    """
    Paginate through ALL filings for a docket.
    If since_date is provided, stop when we reach filings older than that date.
    """
    all_filings = []
    offset = 0
    limit = 25  # ECFS API default page size
    total = None

    while True:
        log(f"    Fetching offset {offset}...")
        filings, reported_total = fetch_docket_page(docket, limit=limit, offset=offset)

        if total is None and reported_total > 0:
            total = reported_total
            log(f"    Total filings in docket: {total}")

        if not filings:
            break

        # Check if we've passed the since_date cutoff
        if since_date:
            cutoff_reached = False
            for f in filings:
                date_recv = (f.get("date_received") or "")[:10]
                if date_recv and date_recv <= since_date:
                    cutoff_reached = True
                    break
            if cutoff_reached:
                # Add only filings newer than since_date
                for f in filings:
                    date_recv = (f.get("date_received") or "")[:10]
                    if date_recv and date_recv > since_date:
                        all_filings.append(f)
                log(f"    Reached cutoff date {since_date}, stopping pagination")
                break

        all_filings.extend(filings)
        log(f"    Got {len(filings)} (total collected: {len(all_filings)})")

        if len(filings) < limit:
            break  # Last page

        offset += limit
        time.sleep(RATE_LIMIT_DELAY)

    return all_filings


# ============================================================================
# PDF Processing
# ============================================================================

def try_import_pdf_extractor():
    """Try to import pdf_extractor, return None if unavailable."""
    try:
        from pdf_extractor import extract_pdf_text
        return extract_pdf_text
    except ImportError:
        return None


def try_import_storage_utils():
    """Try to import storage_utils, return None if unavailable."""
    try:
        from storage_utils import upload_fcc_filing, upload_fcc_attachment
        return upload_fcc_filing, upload_fcc_attachment
    except ImportError:
        return None, None


def process_documents(filing_id: str, documents: List[Dict],
                      extract_fn, upload_filing_fn, upload_attach_fn,
                      dry_run: bool = False) -> Tuple[str, List[str]]:
    """
    Download PDFs from a filing's document list, extract text, upload to storage.
    Returns (combined_text, list_of_storage_paths).
    """
    content_parts = []
    storage_paths = []

    for i, doc in enumerate(documents):
        src = doc.get("src") or doc.get("url") or ""
        if not src:
            continue

        # Only process direct PDF URLs (docs.fcc.gov) -- skip ecfs/document/ URLs
        # that require Playwright (handled by fcc_playwright_scraper.py)
        is_direct_pdf = "docs.fcc.gov" in src and src.lower().endswith(".pdf")

        if not is_direct_pdf:
            if "fcc.gov/ecfs/document/" in src:
                log(f"      Skipping {src[:60]}... (needs Playwright)")
            continue

        log(f"      Downloading PDF {i+1}: {src[:70]}...")

        if dry_run:
            log(f"      [DRY RUN] Would fetch PDF")
            continue

        try:
            pdf_bytes = fetch_bytes(src)
            if not pdf_bytes or len(pdf_bytes) < 500:
                log(f"      PDF too small ({len(pdf_bytes)} bytes), skipping")
                continue

            log(f"      Downloaded {len(pdf_bytes):,} bytes")

            # Extract text
            text = ""
            if extract_fn:
                text = extract_fn(pdf_bytes)

            if text and len(text) > 100:
                content_parts.append(f"--- Document {i+1} ---\n{text}")
                log(f"      Extracted {len(text):,} chars")

                # Upload to storage
                if upload_attach_fn:
                    filename = doc.get("name", f"doc_{i+1}.pdf")
                    result = upload_attach_fn(
                        file_number=filing_id,
                        attachment_number=i + 1,
                        content=pdf_bytes,
                        filename=filename,
                        content_type="application/pdf",
                    )
                    if result.get("success"):
                        storage_paths.append(result.get("path"))
                        log(f"      Uploaded: {result.get('path')}")
            else:
                log(f"      No text extracted (may be scanned/image PDF)")

            time.sleep(RATE_LIMIT_DELAY)

        except Exception as e:
            log(f"      Error processing PDF: {e}")
            continue

    combined_text = "\n\n".join(content_parts)

    # Upload combined text to storage
    if combined_text and upload_filing_fn and not dry_run:
        result = upload_filing_fn(
            filing_system="ecfs",
            file_number=filing_id,
            content=combined_text,
            filename="filing.txt",
        )
        if result.get("success"):
            storage_paths.insert(0, result.get("path"))

    return combined_text, storage_paths


# ============================================================================
# HTML text extraction (for inline text_data from API)
# ============================================================================

def strip_html(html: str) -> str:
    """Strip HTML tags and decode entities."""
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    text = re.sub(r"&#\d+;", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ============================================================================
# Filing Processing
# ============================================================================

def determine_importance(filer_name: str, docket_importance: str) -> str:
    """Determine filing importance based on filer and docket."""
    filer_lower = filer_name.lower()

    if "ast spacemobile" in filer_lower or "ast & science" in filer_lower:
        return "critical"

    for known in HIGH_IMPORTANCE_FILERS:
        if known in filer_lower:
            return "high"

    return docket_importance


def process_single_filing(
    filing: Dict,
    docket_info: Dict,
    existing_ids: Set[str],
    extract_fn,
    upload_filing_fn,
    upload_attach_fn,
    dry_run: bool = False,
    skip_pdf: bool = False,
) -> Optional[str]:
    """
    Process one ECFS filing into a fcc_filings record.
    Returns the file_number on success, None on skip/failure.
    """
    # Extract filing ID
    filing_id = str(
        filing.get("id_submission")
        or filing.get("id_long")
        or filing.get("id")
        or ""
    )
    if not filing_id:
        return None

    # Skip if already in DB
    if filing_id in existing_ids:
        return None

    # Extract core fields
    filers = filing.get("filers", [])
    filer_name = filers[0].get("name", "Unknown") if filers else "Unknown"
    all_filers = [f.get("name", "") for f in filers]

    submission_type = filing.get("submissiontype", {})
    type_desc = submission_type.get("description", "Filing") if isinstance(submission_type, dict) else str(submission_type)
    type_short = submission_type.get("short", "") if isinstance(submission_type, dict) else ""

    date_received = filing.get("date_received", "")
    proceedings = [p.get("name", "") for p in filing.get("proceedings", [])]
    bureaus = [b.get("name", "") for b in filing.get("bureaus", [])]
    lawfirms = [lf.get("name", "") for lf in filing.get("lawfirms", [])]

    docket = docket_info["docket"]
    docket_name = docket_info["name"]

    # Build title: "FilerName: FILING_TYPE (Docket XX-XXX)"
    title = f"{filer_name}: {type_desc} (Docket {docket})"

    # Build description
    description = f"{filer_name} filed {type_desc} in docket {docket} ({docket_name})"
    if lawfirms:
        description += f". Represented by {', '.join(lawfirms)}"

    # Importance
    importance = determine_importance(filer_name, docket_info.get("importance", "normal"))

    # Inline text from API
    text_data = filing.get("text_data", "") or ""
    if text_data:
        text_data = strip_html(text_data)

    # Document URLs
    documents = filing.get("documents", [])
    doc_urls = []
    for doc in documents:
        src = doc.get("src") or doc.get("url") or ""
        if src:
            doc_urls.append(src)

    # Primary document URL
    source_url = doc_urls[0] if doc_urls else f"https://www.fcc.gov/ecfs/filing/{filing_id}"

    # Process PDFs
    pdf_text = ""
    storage_paths = []
    if not skip_pdf and documents:
        log(f"    Processing {len(documents)} document(s)...")
        pdf_text, storage_paths = process_documents(
            filing_id, documents,
            extract_fn, upload_filing_fn, upload_attach_fn,
            dry_run=dry_run,
        )

    # Combine content_text: inline text + PDF text
    content_parts = []
    if text_data:
        content_parts.append(text_data)
    if pdf_text:
        content_parts.append(pdf_text)
    content_text = "\n\n".join(content_parts) if content_parts else None

    # Cap content at 500KB for DB column
    if content_text and len(content_text) > 500000:
        content_text = content_text[:500000]

    # Filed date
    filed_date = None
    if date_received:
        filed_date = date_received[:10]  # YYYY-MM-DD

    # Build DB record
    record = {
        "filing_system": "ECFS",
        "file_number": filing_id,
        "docket": docket,
        "proceeding_name": docket_name,
        "filing_type": type_desc,
        "title": title,
        "filer_name": filer_name,
        "filed_date": filed_date,
        "content_text": content_text,
        "description": description,
        "application_status": None,
        "source_url": source_url,
        "storage_path": storage_paths[0] if storage_paths else None,
        "metadata": json.dumps({
            "all_filers": all_filers,
            "proceedings": proceedings,
            "bureaus": bureaus,
            "lawfirms": lawfirms,
            "submission_type_short": type_short,
            "importance": importance,
            "document_urls": doc_urls,
            "document_count": len(documents),
            "pdf_storage_paths": storage_paths,
            "ecfs_id": filing_id,
        }),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
    }

    if dry_run:
        log(f"    [DRY RUN] {filing_id} | {filer_name[:30]} | {type_desc} | {filed_date}")
        return filing_id

    # Insert
    if upsert_filing(record):
        log(f"    + {filing_id} | {filer_name[:30]} | {type_desc} | {filed_date}")
        return filing_id
    else:
        log(f"    ! Failed to insert {filing_id}")
        return None


# ============================================================================
# Main Worker
# ============================================================================

def run_worker(args):
    log("=" * 70)
    log("FCC ECFS Docket Crawler")
    log("=" * 70)
    log(f"API Key: {FCC_API_KEY[:10]}...")
    log(f"Mode: {'dry-run' if args.dry_run else 'backfill' if args.backfill else 'incremental'}")
    log(f"PDF processing: {'disabled' if args.no_pdf else 'enabled'}")

    if not args.dry_run and not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    # Optional imports for PDF processing
    extract_fn = try_import_pdf_extractor() if not args.no_pdf else None
    upload_filing_fn, upload_attach_fn = (None, None)
    if not args.no_pdf:
        upload_filing_fn, upload_attach_fn = try_import_storage_utils()

    if not args.no_pdf:
        if extract_fn:
            log("PDF extractor: available")
        else:
            log("PDF extractor: not available (install pdfplumber/PyPDF2)")
        if upload_filing_fn:
            log("Storage utils: available")
        else:
            log("Storage utils: not available")

    # Determine which dockets to crawl
    if args.docket:
        dockets = [d for d in TARGET_DOCKETS if d["docket"] == args.docket]
        if not dockets:
            dockets = [{
                "docket": args.docket,
                "name": f"Custom docket {args.docket}",
                "expected": 0,
                "importance": "normal",
            }]
    else:
        dockets = TARGET_DOCKETS

    log(f"Target dockets: {len(dockets)}")
    for d in dockets:
        log(f"  - {d['docket']}: {d['name']} (est. {d['expected']} filings)")

    # Get existing ECFS filing IDs
    if not args.dry_run:
        existing_ids = get_existing_file_numbers()
        log(f"Existing ECFS filings in DB: {len(existing_ids)}")
    else:
        existing_ids = set()

    # ---- Phase 1: Discover all filings ----
    log("-" * 70)
    log("Phase 1: Discovery")
    log("-" * 70)

    all_filings = []  # list of (filing_dict, docket_info)

    for docket_info in dockets:
        docket = docket_info["docket"]
        log(f"Crawling docket {docket} ({docket_info['name']})...")

        # For incremental mode, find the latest date we have
        since_date = None
        if args.incremental and not args.backfill and not args.dry_run:
            since_date = get_latest_filing_date(docket)
            if since_date:
                log(f"  Incremental: fetching filings after {since_date}")

        filings = fetch_all_docket_filings(docket, since_date=since_date)
        log(f"  Found {len(filings)} filings")

        for f in filings:
            all_filings.append((f, docket_info))

        time.sleep(RATE_LIMIT_DELAY)

    # Deduplicate by filing ID
    seen_ids = set()
    unique_filings = []
    for filing, docket_info in all_filings:
        fid = str(filing.get("id_submission") or filing.get("id_long") or filing.get("id") or "")
        if fid and fid not in seen_ids:
            seen_ids.add(fid)
            unique_filings.append((filing, docket_info))

    log(f"Total unique filings discovered: {len(unique_filings)}")

    # Filter out already-existing
    if not args.backfill:
        new_filings = [(f, d) for f, d in unique_filings
                       if str(f.get("id_submission") or f.get("id_long") or f.get("id") or "") not in existing_ids]
        log(f"New filings to process: {len(new_filings)}")
    else:
        new_filings = unique_filings
        log(f"Backfill mode: processing all {len(new_filings)} filings")

    if not new_filings:
        log("Nothing new to process. Done.")
        return

    # Sort: newest first for regular runs, oldest first for backfill
    new_filings.sort(
        key=lambda x: x[0].get("date_received", "") or "",
        reverse=not args.backfill,
    )

    # Apply limit
    if args.limit:
        new_filings = new_filings[:args.limit]
        log(f"Limited to {args.limit} filings")

    # ---- Phase 2: Process filings ----
    log("-" * 70)
    log("Phase 2: Processing")
    log("-" * 70)

    success = 0
    skipped = 0
    failed = 0

    for i, (filing, docket_info) in enumerate(new_filings):
        fid = str(filing.get("id_submission") or filing.get("id_long") or filing.get("id") or "")
        filers = filing.get("filers", [])
        filer_preview = filers[0].get("name", "?")[:25] if filers else "?"

        log(f"[{i+1}/{len(new_filings)}] {fid} - {filer_preview}")

        result = process_single_filing(
            filing=filing,
            docket_info=docket_info,
            existing_ids=existing_ids,
            extract_fn=extract_fn,
            upload_filing_fn=upload_filing_fn,
            upload_attach_fn=upload_attach_fn,
            dry_run=args.dry_run,
            skip_pdf=args.no_pdf,
        )

        if result:
            success += 1
            existing_ids.add(result)  # Track so we skip dupes within this run
        elif result is None:
            # Could be skip (already exists) or failure
            fid_check = str(filing.get("id_submission") or filing.get("id_long") or filing.get("id") or "")
            if fid_check in existing_ids:
                skipped += 1
            else:
                failed += 1

        # Progress report
        if (i + 1) % 25 == 0:
            log(f"  Progress: {i+1}/{len(new_filings)} "
                f"({success} added, {skipped} skipped, {failed} failed)")

        # Rate limit between filings
        if not args.dry_run:
            time.sleep(0.2)

    # ---- Summary ----
    log("=" * 70)
    log(f"ECFS Crawler Complete")
    log(f"  Added:   {success}")
    log(f"  Skipped: {skipped}")
    log(f"  Failed:  {failed}")
    log(f"  Total:   {success + skipped + failed}")
    log("=" * 70)


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="FCC ECFS Docket Crawler - ingests all filings from ASTS-related proceedings"
    )
    parser.add_argument(
        "--docket",
        help="Crawl a single docket (e.g. 23-65). Default: all target dockets.",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        default=True,
        help="Only fetch filings newer than the last run (default behavior).",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Re-process all filings, including existing ones.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without writing to DB.",
    )
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="Skip PDF download and text extraction.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of filings to process.",
    )

    args = parser.parse_args()
    run_worker(args)
