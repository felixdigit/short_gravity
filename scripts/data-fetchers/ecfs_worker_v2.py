#!/usr/bin/env python3
"""
FCC ECFS (Electronic Comment Filing System) Worker v2

Enhanced ECFS worker that:
1. Fetches ALL comments/filings from relevant dockets
2. Stores full document content in Supabase Storage
3. Generates AI summaries
4. Uses the new fcc_filings table (not just inbox)

Key dockets for AST SpaceMobile:
- IB Docket 23-65: SCS Rulemaking
- WT Docket 22-271: Single Network Future - SCS Framework
- Various Space Bureau proceedings

Usage:
    # Standard run (incremental)
    python3 ecfs_worker_v2.py

    # Full backfill (all historical)
    python3 ecfs_worker_v2.py --backfill

    # Specific docket
    python3 ecfs_worker_v2.py --docket 23-65

    # Dry run
    python3 ecfs_worker_v2.py --dry-run
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
from datetime import datetime
from typing import Dict, List, Optional, Set
from html.parser import HTMLParser

# Import storage utilities
from storage_utils import (
    upload_fcc_filing,
    upload_fcc_attachment,
    compute_hash,
    FCC_BUCKET,
    log,
)
from pdf_extractor import extract_pdf_text


# ============================================================================
# Configuration
# ============================================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# FCC ECFS Public API
FCC_API_BASE = "https://publicapi.fcc.gov/ecfs/filings"
FCC_API_KEY = os.environ.get("FCC_API_KEY", "DEMO_KEY")

# Key dockets for AST SpaceMobile - comprehensive list
KEY_DOCKETS = [
    # Primary SCS dockets
    {"docket": "23-65", "name": "SCS Rulemaking", "importance": "critical"},
    {"docket": "22-271", "name": "Single Network Future: SCS Framework", "importance": "critical"},

    # Space Bureau proceedings
    {"docket": "25-201", "name": "AST SpaceMobile Modification Application", "importance": "high"},
    {"docket": "25-306", "name": "AST SpaceMobile Filings", "importance": "high"},
    {"docket": "25-340", "name": "AST SpaceMobile Filings", "importance": "high"},

    # Related spectrum/satellite dockets
    {"docket": "22-411", "name": "Space Bureau Spectrum", "importance": "normal"},
    {"docket": "22-272", "name": "Related SCS Docket", "importance": "normal"},
    {"docket": "20-117", "name": "NGSO Coordination", "importance": "normal"},

    # Mobile spectrum dockets that may affect D2D
    {"docket": "21-57", "name": "UWB Technical Rules", "importance": "low"},
    {"docket": "23-152", "name": "Spectrum Frontiers", "importance": "low"},
]

# Filers to highlight as high importance
HIGH_IMPORTANCE_FILERS = [
    "ast spacemobile",
    "ast & science",
    "at&t",
    "verizon",
    "t-mobile",
    "starlink",
    "spacex",
    "lynk",
    "federal communications commission",
]

# Rate limits
RATE_LIMIT_SECONDS = 0.5
RATE_LIMIT_RETRY_SECONDS = 10  # Wait time on 429 error


# ============================================================================
# HTTP Utilities
# ============================================================================

def fetch_url(url: str, headers: Optional[Dict] = None, retries: int = 3) -> str:
    """Fetch URL content with retry logic and 429 handling."""
    default_headers = {
        "User-Agent": "Short Gravity Research gabriel@shortgravity.com"
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
                # Rate limited - wait longer
                wait_time = RATE_LIMIT_RETRY_SECONDS * (attempt + 1)
                log(f"  Rate limited (429). Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            elif attempt < retries - 1:
                time.sleep(2 ** attempt)
        except urllib.error.URLError as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

    raise last_error


def fetch_json(url: str) -> Dict:
    """Fetch JSON from URL."""
    content = fetch_url(url, {"Accept": "application/json"})
    return json.loads(content)


def fetch_bytes(url: str, retries: int = 3) -> bytes:
    """Fetch binary content."""
    headers = {"User-Agent": "Short Gravity Research gabriel@shortgravity.com"}

    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as response:
                return response.read()
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

    raise last_error


# ============================================================================
# Supabase Operations
# ============================================================================

def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
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


def get_existing_ecfs_filings() -> Set[str]:
    """Get existing ECFS filing IDs from database."""
    try:
        # Check fcc_filings table for ECFS entries
        result = supabase_request("GET", "fcc_filings?filing_system=eq.ECFS&select=file_number")
        return {r["file_number"] for r in result if r.get("file_number")}
    except Exception as e:
        log(f"Error fetching existing ECFS filings: {e}")
        return set()


def upsert_fcc_filing(filing: Dict) -> Dict:
    """Insert or update FCC filing."""
    file_number = filing.get("file_number")
    filing_system = filing.get("filing_system", "ECFS")

    # Check if exists
    existing = supabase_request(
        "GET",
        f"fcc_filings?file_number=eq.{file_number}&filing_system=eq.{filing_system}&select=id"
    )

    if existing:
        return supabase_request(
            "PATCH",
            f"fcc_filings?file_number=eq.{file_number}&filing_system=eq.{filing_system}",
            filing
        )
    else:
        return supabase_request("POST", "fcc_filings", filing)


# ============================================================================
# FCC ECFS API
# ============================================================================

def fetch_docket_filings(docket: str, limit: int = 500, offset: int = 0) -> List[Dict]:
    """Fetch filings for a specific docket using FCC Public API."""
    url = f"{FCC_API_BASE}?api_key={FCC_API_KEY}&proceedings.name={docket}&limit={limit}&offset={offset}&sort=date_received,DESC"

    try:
        data = fetch_json(url)
        return data.get("filings", []) or data.get("filing", [])
    except Exception as e:
        log(f"Error fetching docket {docket}: {e}")
        return []


def fetch_all_docket_filings(docket: str) -> List[Dict]:
    """Fetch ALL filings for a docket, paginating through results."""
    all_filings = []
    offset = 0
    limit = 500

    while True:
        log(f"    Fetching offset {offset}...")
        filings = fetch_docket_filings(docket, limit=limit, offset=offset)

        if not filings:
            break

        all_filings.extend(filings)
        log(f"    Got {len(filings)} filings (total: {len(all_filings)})")

        if len(filings) < limit:
            break

        offset += limit
        time.sleep(RATE_LIMIT_SECONDS)

    return all_filings


def fetch_filer_filings(filer_name: str, limit: int = 100) -> List[Dict]:
    """Search for filings by filer name."""
    encoded = urllib.parse.quote(filer_name)
    url = f"{FCC_API_BASE}?api_key={FCC_API_KEY}&filers.name={encoded}&limit={limit}&sort=date_received,DESC"

    try:
        data = fetch_json(url)
        return data.get("filings", []) or data.get("filing", [])
    except Exception as e:
        log(f"Error searching filer {filer_name}: {e}")
        return []


def fetch_filing_document(filing_id: str) -> Optional[str]:
    """Fetch the actual document content for a filing."""
    # Try multiple document URLs
    urls = [
        f"https://www.fcc.gov/ecfs/document/{filing_id}/1",
        f"https://www.fcc.gov/ecfs/filing/{filing_id}",
    ]

    for url in urls:
        try:
            content = fetch_url(url)
            # Extract text from HTML
            text = extract_text_from_html(content)
            if len(text) > 100:  # Reasonable content
                return text
        except:
            continue

    return None


def extract_text_from_html(html: str) -> str:
    """Extract text from HTML content."""
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = re.sub(r"&#\d+;", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def process_ecfs_pdf_attachments(
    filing_id: str,
    documents: List[Dict],
    dry_run: bool = False
) -> tuple[str, List[str]]:
    """
    Process ECFS PDF document attachments - download and extract text.

    Phase 1 strategy: Only process direct download URLs (docs.fcc.gov).
    Skip slow fcc.gov/ecfs/document/ URLs - Playwright scraper handles those in Phase 2.

    Args:
        filing_id: The ECFS filing ID
        documents: List of document dicts from ECFS API (with 'src' or 'url' keys)
        dry_run: If True, don't actually download or store

    Returns:
        Tuple of (combined_extracted_text, list_of_storage_paths)
    """
    content_parts = []
    storage_paths = []

    for i, doc in enumerate(documents):  # Process ALL documents, no limit
        src = doc.get("src") or doc.get("url") or ""
        if not src:
            continue

        # Phase 1: Only process direct download URLs (fast)
        # Skip fcc.gov/ecfs/document/ URLs - they timeout, Playwright handles them in Phase 2
        is_direct_pdf = (
            'docs.fcc.gov' in src and src.lower().endswith('.pdf')
        )

        if not is_direct_pdf:
            # Log that we're skipping for Phase 2
            if 'fcc.gov/ecfs/document/' in src:
                log(f"    Skipping {src[:50]}... (Phase 2 - Playwright)")
            continue

        log(f"    Fetching PDF {i+1}: {src[:60]}...")

        if dry_run:
            log(f"    [DRY RUN] Would fetch and process PDF")
            continue

        try:
            pdf_bytes = fetch_bytes(src)

            if not pdf_bytes or len(pdf_bytes) < 1000:
                log(f"    PDF too small or empty, skipping")
                continue

            log(f"    Downloaded {len(pdf_bytes):,} bytes")

            # Extract text from PDF
            text = extract_pdf_text(pdf_bytes)

            if text and len(text) > 100:
                content_parts.append(f"--- PDF Document {i+1} ---\n{text}")
                log(f"    Extracted {len(text):,} chars from PDF")

                # Upload PDF to storage
                filename = f"doc_{i+1}.pdf"
                storage_result = upload_fcc_attachment(
                    file_number=filing_id,
                    attachment_number=i + 1,
                    content=pdf_bytes,
                    filename=filename,
                    content_type="application/pdf",
                )

                if storage_result.get("success"):
                    storage_paths.append(storage_result.get("path"))
                    log(f"    Uploaded to storage: {storage_result.get('path')}")
            else:
                log(f"    No text extracted from PDF (may be scanned/image)")

            time.sleep(RATE_LIMIT_SECONDS)

        except Exception as e:
            log(f"    Error processing PDF: {e}")
            continue

    return "\n\n".join(content_parts), storage_paths


# ============================================================================
# AI Summary
# ============================================================================

def generate_ecfs_summary(filing: Dict, content: Optional[str] = None) -> str:
    """Generate AI summary for an ECFS filing."""
    if not ANTHROPIC_API_KEY:
        return ""

    title = filing.get("title", "Unknown")
    filer = filing.get("filer_name", "Unknown")
    submission_type = filing.get("filing_type", "Filing")
    docket = filing.get("docket", "Unknown")

    content_section = ""
    if content:
        truncated = content[:30000] if len(content) > 30000 else content
        content_section = f"\n\nFiling content:\n{truncated}"

    prompt = f"""You are analyzing an FCC ECFS filing related to satellite-to-cellular communications.

Filer: {filer}
Type: {submission_type}
Docket: {docket}
Title: {title}
{content_section}

Provide a concise summary (2-3 sentences) focusing on:
- The main argument or position taken
- Any specific technical or regulatory points
- Implications for AST SpaceMobile or the direct-to-device satellite industry

Summary:"""

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": prompt}],
    }

    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["content"][0]["text"].strip()
    except Exception as e:
        log(f"Summary generation error: {e}")
        return ""


# ============================================================================
# Filing Discovery & Processing
# ============================================================================

def discover_all_filings(specific_docket: Optional[str] = None) -> List[Dict]:
    """Discover all relevant ECFS filings."""
    all_filings = {}

    dockets_to_fetch = KEY_DOCKETS
    if specific_docket:
        dockets_to_fetch = [d for d in KEY_DOCKETS if d["docket"] == specific_docket]
        if not dockets_to_fetch:
            dockets_to_fetch = [{"docket": specific_docket, "name": "Custom", "importance": "normal"}]

    log("Discovering ECFS filings...")

    # Fetch from all dockets
    for docket_info in dockets_to_fetch:
        docket = docket_info["docket"]
        name = docket_info["name"]
        importance = docket_info["importance"]

        log(f"  Fetching docket {docket} ({name})...")
        filings = fetch_all_docket_filings(docket)

        for f in filings:
            filing_id = str(f.get("id_submission") or f.get("id_long") or f.get("id"))
            if filing_id and filing_id not in all_filings:
                f["_docket"] = docket
                f["_docket_name"] = name
                f["_docket_importance"] = importance
                all_filings[filing_id] = f

        time.sleep(RATE_LIMIT_SECONDS)

    log(f"Total unique filings discovered: {len(all_filings)}")

    # Also search for AST SpaceMobile filings directly
    log("  Searching for AST SpaceMobile filings...")
    for filer in ["AST SpaceMobile", "AST & Science"]:
        filings = fetch_filer_filings(filer)
        for f in filings:
            filing_id = str(f.get("id_submission") or f.get("id_long") or f.get("id"))
            if filing_id and filing_id not in all_filings:
                f["_docket"] = "direct_search"
                f["_docket_name"] = "Direct Filer Search"
                f["_docket_importance"] = "high"
                all_filings[filing_id] = f
        time.sleep(RATE_LIMIT_SECONDS)

    log(f"Total with filer search: {len(all_filings)}")

    return list(all_filings.values())


def process_filing(filing: Dict, dry_run: bool = False, fetch_content: bool = True) -> bool:
    """Process a single ECFS filing."""
    filing_id = str(filing.get("id_submission") or filing.get("id_long") or filing.get("id"))
    if not filing_id:
        return False

    log(f"Processing: {filing_id}")

    if dry_run:
        log("  [DRY RUN] Would process this filing")
        return True

    try:
        # Extract metadata
        submission_type = filing.get("submissiontype", {})
        type_desc = submission_type.get("description", "Filing")
        type_short = submission_type.get("short", "")

        filers = filing.get("filers", [])
        filer = filers[0].get("name", "Unknown") if filers else "Unknown"
        all_filers = [f.get("name") for f in filers]

        date_received = filing.get("date_received", "")
        if date_received and "T" not in date_received:
            date_received = f"{date_received}T00:00:00Z"

        proceedings = [p.get("name", "") for p in filing.get("proceedings", [])]
        docket = filing.get("_docket") or (proceedings[0] if proceedings else "Unknown")
        docket_name = filing.get("_docket_name", "")

        # Build title
        title = f"{filer}: {type_desc}"
        if docket and docket != "direct_search":
            title += f" (Docket {docket})"

        # Determine importance
        importance = filing.get("_docket_importance", "normal")
        filer_lower = filer.lower()
        for high_filer in HIGH_IMPORTANCE_FILERS:
            if high_filer in filer_lower:
                importance = "high"
                break
        if "ast spacemobile" in filer_lower or "ast & science" in filer_lower:
            importance = "critical"

        # Get document URL
        docs = filing.get("documents", [])
        doc_url = docs[0].get("src", "") if docs else ""
        if not doc_url:
            doc_url = f"https://www.fcc.gov/ecfs/document/{filing_id}/1"

        # Get documents array for attachment processing
        documents = filing.get("documents", [])

        # Fetch document content
        content_text = None
        storage_path = None
        pdf_storage_paths = []
        content_parts = []

        if fetch_content:
            # Process document attachments from the API response
            # The documents array contains direct URLs to PDFs/files - no need for HTML fetch
            if documents:
                log(f"  Processing {len(documents)} document attachment(s)...")
                pdf_content, pdf_storage_paths = process_ecfs_pdf_attachments(
                    filing_id, documents, dry_run=False
                )
                if pdf_content:
                    content_parts.append(pdf_content)

            # Combine all content
            if content_parts:
                content_text = "\n\n".join(content_parts)
                log(f"  Total content: {len(content_text):,} chars")

                # Upload combined content to storage
                storage_result = upload_fcc_filing(
                    filing_system="ecfs",
                    file_number=filing_id,
                    content=content_text,
                    filename="filing.txt",
                )

                if storage_result.get("success"):
                    storage_path = storage_result.get("path")
                    log(f"  Uploaded to: {storage_path}")

        # Skip summary generation for now - can batch generate later
        summary = None

        # Prepare database record
        db_record = {
            "filing_system": "ECFS",
            "file_number": filing_id,
            "docket": docket,
            "proceeding_name": docket_name,
            "filing_type": type_desc,
            "title": title,
            "filer_name": filer,
            "filed_date": date_received[:10] if date_received else None,
            "content_text": content_text[:500000] if content_text else None,  # Limit for DB
            "storage_path": storage_path,
            "source_url": doc_url,
            "metadata": json.dumps({
                "all_filers": all_filers,
                "proceedings": proceedings,
                "submission_type_short": type_short,
                "bureaus": [b.get("name") for b in filing.get("bureaus", [])],
                "importance": importance,
                "pdf_attachments": pdf_storage_paths,
                "document_count": len(documents) if fetch_content else 0,
            }),
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "status": "completed",
        }

        if summary:
            db_record.update({
                "ai_summary": summary,
                "ai_model": "claude-sonnet-4-20250514",
                "ai_generated_at": datetime.utcnow().isoformat() + "Z",
            })

        # Upsert to database
        upsert_fcc_filing(db_record)
        log(f"  ✓ Database updated")

        return True

    except Exception as e:
        log(f"  ✗ Error: {e}")
        return False


# ============================================================================
# Main
# ============================================================================

def run_worker(args):
    """Main worker function."""
    log("=" * 60)
    log("FCC ECFS Worker v2")
    log("=" * 60)
    log(f"API Key: {FCC_API_KEY[:10]}...")

    if not args.dry_run and not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    # Discover all filings
    all_filings = discover_all_filings(args.docket)
    log(f"Total filings discovered: {len(all_filings)}")

    # Get existing filings
    existing = get_existing_ecfs_filings()
    log(f"Already in database: {len(existing)}")

    # Determine what to process
    if args.backfill:
        to_process = all_filings
        log(f"Backfill mode: processing all {len(to_process)} filings")
    else:
        to_process = []
        for f in all_filings:
            fid = str(f.get("id_submission") or f.get("id_long") or f.get("id"))
            if fid not in existing:
                to_process.append(f)
        log(f"New filings to process: {len(to_process)}")

    if not to_process:
        log("Nothing to process. Done.")
        return

    # Sort by date (newest first for regular runs, oldest first for backfill)
    to_process.sort(
        key=lambda x: x.get("date_received", ""),
        reverse=not args.backfill
    )

    # Limit for dry runs
    if args.limit:
        to_process = to_process[:args.limit]
        log(f"Limited to {args.limit} filings")

    log("-" * 60)
    success = 0
    failed = 0

    for i, filing in enumerate(to_process):
        log(f"[{i+1}/{len(to_process)}]")

        if process_filing(filing, dry_run=args.dry_run, fetch_content=not args.no_content):
            success += 1
        else:
            failed += 1

        # Progress report
        if (i + 1) % 25 == 0:
            log(f"Progress: {i+1}/{len(to_process)} ({success} success, {failed} failed)")

    log("=" * 60)
    log(f"Completed: {success} success, {failed} failed")
    log("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FCC ECFS Worker v2")
    parser.add_argument("--backfill", action="store_true", help="Process all filings (not just new)")
    parser.add_argument("--docket", help="Process specific docket only")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to database")
    parser.add_argument("--no-content", action="store_true", help="Skip fetching document content")
    parser.add_argument("--limit", type=int, help="Limit number of filings to process")

    args = parser.parse_args()
    run_worker(args)
