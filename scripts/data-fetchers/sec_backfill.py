#!/usr/bin/env python3
"""
SEC Historical Backfill Worker

Fetches ALL SEC filings for AST SpaceMobile (CIK 0001780312) since inception,
stores full documents in Supabase Storage (no truncation), and generates AI summaries.

This is a one-time backfill script. For ongoing monitoring, use filing_worker.py.

Usage:
    # Full backfill (all filings)
    python3 sec_backfill.py

    # Backfill specific form types
    python3 sec_backfill.py --forms 10-K,10-Q,8-K

    # Dry run (no database writes)
    python3 sec_backfill.py --dry-run

    # Resume from specific accession number
    python3 sec_backfill.py --resume 0001780312-24-000050

    # Skip AI summaries (faster, generate later)
    python3 sec_backfill.py --no-summaries
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
import re
from datetime import datetime
from typing import Dict, List, Optional, Set

# Import storage utilities
from storage_utils import (
    upload_sec_filing,
    upload_sec_exhibit,
    compute_hash,
    SEC_BUCKET,
    log,
)


# Configuration
ASTS_CIK = "0001780312"
SEC_BASE_URL = "https://data.sec.gov"
SEC_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"
USER_AGENT = "Short Gravity Research gabriel@shortgravity.com"

# Supabase config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Anthropic config
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Rate limits
SEC_RATE_LIMIT_SECONDS = 0.2  # SEC asks for 10 requests/second max
CLAUDE_RATE_LIMIT_SECONDS = 1.0  # Be nice to Claude API

# High-signal forms for frontend filtering
HIGH_SIGNAL_FORMS = ["10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A"]

# 8-K Item codes
ITEM_CODES = {
    "1.01": "Entry into Material Agreement",
    "1.02": "Termination of Material Agreement",
    "2.01": "Completion of Acquisition/Disposition",
    "2.02": "Results of Operations and Financial Condition",
    "2.03": "Creation of Direct Financial Obligation",
    "3.02": "Unregistered Sales of Equity Securities",
    "5.02": "Departure/Appointment of Directors or Officers",
    "5.07": "Submission of Matters to Vote",
    "7.01": "Regulation FD Disclosure",
    "8.01": "Other Events",
    "9.01": "Financial Statements and Exhibits",
}


# ============================================================================
# HTTP Utilities
# ============================================================================

def fetch_url(url: str, headers: Optional[Dict] = None, retries: int = 3) -> str:
    """Fetch URL content with retry logic."""
    default_headers = {"User-Agent": USER_AGENT}
    if headers:
        default_headers.update(headers)

    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=default_headers)
            with urllib.request.urlopen(req, timeout=60) as response:
                content = response.read()
                try:
                    return content.decode("utf-8")
                except UnicodeDecodeError:
                    return content.decode("latin-1", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            last_error = e
            if attempt < retries - 1:
                wait = 2 ** attempt
                log(f"  Retry {attempt + 1}/{retries} after {wait}s: {e}")
                time.sleep(wait)

    raise last_error


def fetch_json(url: str) -> Dict:
    """Fetch JSON from URL."""
    content = fetch_url(url, {"Accept": "application/json"})
    return json.loads(content)


def fetch_bytes(url: str, retries: int = 3) -> bytes:
    """Fetch binary content."""
    headers = {"User-Agent": USER_AGENT}

    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read()
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

    raise last_error


# ============================================================================
# SEC API
# ============================================================================

def get_filing_url(accession_number: str, document: str) -> str:
    """Generate SEC filing URL."""
    accession_no_dashes = accession_number.replace("-", "")
    return f"{SEC_ARCHIVES_URL}/{ASTS_CIK}/{accession_no_dashes}/{document}"


def get_filing_index_url(accession_number: str) -> str:
    """Get URL for filing index (lists all documents)."""
    accession_no_dashes = accession_number.replace("-", "")
    return f"{SEC_ARCHIVES_URL}/{ASTS_CIK}/{accession_no_dashes}/index.json"


def fetch_all_filings() -> List[Dict]:
    """Fetch ALL ASTS filings from SEC EDGAR."""
    url = f"{SEC_BASE_URL}/submissions/CIK{ASTS_CIK}.json"
    log(f"Fetching SEC submissions: {url}")

    data = fetch_json(url)
    recent = data["filings"]["recent"]
    filings = []

    total = len(recent["accessionNumber"])
    log(f"Total filings found: {total}")

    for i in range(total):
        form = recent["form"][i]
        is_high_signal = form in HIGH_SIGNAL_FORMS

        filings.append({
            "accession_number": recent["accessionNumber"][i],
            "form": form,
            "filing_date": recent["filingDate"][i],
            "report_date": recent["reportDate"][i] or None,
            "primary_document": recent["primaryDocument"][i],
            "primary_doc_description": recent["primaryDocDescription"][i] or None,
            "items": recent["items"][i] if "items" in recent else "",
            "file_size": recent["size"][i],
            "url": get_filing_url(recent["accessionNumber"][i], recent["primaryDocument"][i]),
            "is_high_signal": is_high_signal,
        })

    # Sort by filing date (oldest first for backfill)
    filings.sort(key=lambda x: x["filing_date"])
    return filings


def fetch_filing_index(accession_number: str) -> List[Dict]:
    """Fetch filing index to get list of all documents/exhibits."""
    url = get_filing_index_url(accession_number)

    try:
        data = fetch_json(url)
        return data.get("directory", {}).get("item", [])
    except Exception as e:
        log(f"  Warning: Could not fetch index: {e}")
        return []


def extract_text_from_html(html: str) -> str:
    """Extract text from HTML."""
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


def fetch_filing_content(url: str) -> str:
    """Fetch and extract text from filing HTML."""
    html = fetch_url(url)
    return extract_text_from_html(html)


# ============================================================================
# Supabase
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


def get_existing_accession_numbers() -> Set[str]:
    """Get accession numbers already in database."""
    try:
        result = supabase_request("GET", "filings?select=accession_number")
        return {r["accession_number"] for r in result}
    except Exception as e:
        log(f"Error fetching existing filings: {e}")
        return set()


def get_filings_with_storage() -> Set[str]:
    """Get accession numbers that already have storage_path set."""
    try:
        result = supabase_request(
            "GET",
            "filings?select=accession_number&storage_path=not.is.null"
        )
        return {r["accession_number"] for r in result}
    except Exception as e:
        log(f"Error fetching filings with storage: {e}")
        return set()


def upsert_filing(filing: Dict) -> Dict:
    """Insert or update filing in Supabase."""
    # Check if exists
    existing = supabase_request(
        "GET",
        f"filings?accession_number=eq.{filing['accession_number']}&select=id"
    )

    if existing:
        # Update
        return supabase_request(
            "PATCH",
            f"filings?accession_number=eq.{filing['accession_number']}",
            filing
        )
    else:
        # Insert
        return supabase_request("POST", "filings", filing)


def insert_exhibit(exhibit: Dict) -> Dict:
    """Insert exhibit record."""
    return supabase_request("POST", "sec_filing_exhibits", exhibit)


# ============================================================================
# Claude API
# ============================================================================

def generate_summary(content: str, form: str, items: str) -> str:
    """Generate AI summary using Claude."""
    if not ANTHROPIC_API_KEY:
        return "[Summary generation skipped - no API key]"

    # Get item descriptions for 8-K
    item_descriptions = []
    if items:
        item_descriptions = [
            ITEM_CODES.get(item.strip(), f"Item {item.strip()}")
            for item in items.split(",")
        ]
    items_context = f"\n\nItems reported: {', '.join(item_descriptions)}" if item_descriptions else ""

    # For very large documents, chunk and summarize key sections
    max_content = 100000  # Increased from 50K
    truncated = content[:max_content] if len(content) > max_content else content

    prompt = f"""You are analyzing an SEC {form} filing for AST SpaceMobile (ASTS), a company building a space-based cellular network.{items_context}

Provide a concise summary (2-4 sentences) of the key information that would be most relevant to investors. Focus on:
- Material business developments
- Financial metrics or guidance
- Partnership/contract updates
- Satellite launch or operational milestones
- Executive changes
- Any risks or concerns

Filing content:
{truncated}

Summary:"""

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    }

    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["content"][0]["text"].strip()
    except Exception as e:
        log(f"  Warning: Summary generation failed: {e}")
        return f"[Summary generation failed: {e}]"


# ============================================================================
# Main Backfill Logic
# ============================================================================

def process_filing(
    filing: Dict,
    dry_run: bool = False,
    generate_summaries: bool = True,
    process_exhibits: bool = True,
) -> bool:
    """
    Process a single filing:
    1. Fetch full content
    2. Upload to Supabase Storage (no truncation)
    3. Generate AI summary
    4. Update database
    5. Optionally process exhibits
    """
    accession = filing["accession_number"]
    form = filing["form"]
    log(f"Processing {form} ({filing['filing_date']}): {accession}")

    if dry_run:
        log("  [DRY RUN] Would process this filing")
        return True

    try:
        # Fetch full content
        content = fetch_filing_content(filing["url"])
        content_bytes = content.encode("utf-8")
        content_length = len(content)
        content_hash = compute_hash(content_bytes)
        log(f"  Content: {content_length:,} chars")

        time.sleep(SEC_RATE_LIMIT_SECONDS)

        # Upload full document to storage
        storage_result = upload_sec_filing(
            accession_number=accession,
            form_type=form,
            content=content,
            document_name="primary.txt",
        )

        if not storage_result["success"]:
            log(f"  Warning: Storage upload failed: {storage_result.get('error')}")
            storage_path = None
        else:
            storage_path = storage_result["path"]
            log(f"  Uploaded to: {storage_path}")

        # Generate summary
        summary = None
        if generate_summaries:
            log("  Generating summary...")
            summary = generate_summary(content, form, filing.get("items", ""))
            log(f"  Summary: {summary[:80]}...")
            time.sleep(CLAUDE_RATE_LIMIT_SECONDS)

        # Update database
        db_record = {
            "accession_number": accession,
            "cik": ASTS_CIK,
            "form": form,
            "filing_date": filing["filing_date"],
            "report_date": filing.get("report_date"),
            "primary_document": filing["primary_document"],
            "primary_doc_description": filing.get("primary_doc_description"),
            "items": filing.get("items", ""),
            "file_size": filing.get("file_size"),
            "url": filing["url"],
            "content_text": content,  # Full content, no truncation
            "content_length": content_length,
            "storage_path": storage_path,
            "full_content_hash": content_hash,
            "filing_size_bytes": len(content_bytes),
            "status": "completed",
        }

        if summary:
            db_record.update({
                "summary": summary,
                "summary_model": "claude-3-5-sonnet-20241022",
                "summary_generated_at": datetime.utcnow().isoformat() + "Z",
            })

        upsert_filing(db_record)
        log(f"  ✓ Database updated")

        # Process exhibits (optional)
        if process_exhibits:
            exhibit_count = process_filing_exhibits(accession, form, dry_run)
            if exhibit_count > 0:
                supabase_request(
                    "PATCH",
                    f"filings?accession_number=eq.{accession}",
                    {"exhibit_count": exhibit_count}
                )

        return True

    except Exception as e:
        log(f"  ✗ Error: {e}")
        if not dry_run:
            try:
                supabase_request(
                    "PATCH",
                    f"filings?accession_number=eq.{accession}",
                    {"status": "failed", "error_message": str(e)[:500]}
                )
            except:
                pass
        return False


def process_filing_exhibits(accession: str, form: str, dry_run: bool = False) -> int:
    """Process exhibits for a filing."""
    # Get filing index
    index_items = fetch_filing_index(accession)
    if not index_items:
        return 0

    # Filter for exhibits
    exhibit_items = [
        item for item in index_items
        if item.get("name", "").lower().startswith("ex") or
           "exhibit" in item.get("description", "").lower()
    ]

    if not exhibit_items:
        return 0

    log(f"  Processing {len(exhibit_items)} exhibits...")
    processed = 0

    for item in exhibit_items[:10]:  # Limit to 10 exhibits per filing
        try:
            name = item.get("name", "")
            desc = item.get("description", "")

            # Construct URL
            url = get_filing_url(accession, name)

            if dry_run:
                log(f"    [DRY RUN] Would process exhibit: {name}")
                processed += 1
                continue

            # Fetch exhibit content
            content = fetch_bytes(url)
            time.sleep(SEC_RATE_LIMIT_SECONDS)

            # Determine content type
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

            # Extract text if HTML
            extracted_text = None
            if content_type == "text/html":
                try:
                    html_content = content.decode("utf-8", errors="replace")
                    extracted_text = extract_text_from_html(html_content)[:50000]
                except:
                    pass

            # Insert exhibit record
            exhibit_record = {
                "accession_number": accession,
                "exhibit_number": name,
                "exhibit_type": desc or None,
                "description": desc or None,
                "filename": name,
                "file_size_bytes": len(content),
                "content_type": content_type,
                "storage_path": storage_result.get("path"),
                "content_hash": storage_result.get("hash"),
                "content_text": extracted_text,
                "url": url,
                "fetched_at": datetime.utcnow().isoformat() + "Z",
            }

            insert_exhibit(exhibit_record)
            processed += 1
            log(f"    ✓ {name}")

        except Exception as e:
            log(f"    ✗ {item.get('name', 'unknown')}: {e}")

    return processed


def run_backfill(args):
    """Run the backfill process."""
    log("=" * 60)
    log("SEC Historical Backfill")
    log("=" * 60)

    # Validate environment
    if not args.dry_run and not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    # Fetch all filings
    all_filings = fetch_all_filings()
    log(f"Total SEC filings: {len(all_filings)}")

    # Filter by form type if specified
    if args.forms:
        form_filter = set(f.strip() for f in args.forms.split(","))
        all_filings = [f for f in all_filings if f["form"] in form_filter]
        log(f"Filtered to forms {form_filter}: {len(all_filings)} filings")

    # Get existing filings
    existing = get_existing_accession_numbers()
    with_storage = get_filings_with_storage()
    log(f"Already in database: {len(existing)}")
    log(f"Already have storage: {len(with_storage)}")

    # Determine what to process
    if args.update_all:
        # Re-process all filings (update storage)
        to_process = all_filings
        log(f"Updating all {len(to_process)} filings")
    elif args.missing_storage:
        # Only process filings without storage
        to_process = [f for f in all_filings if f["accession_number"] not in with_storage]
        log(f"Filings missing storage: {len(to_process)}")
    else:
        # Only new filings
        to_process = [f for f in all_filings if f["accession_number"] not in existing]
        log(f"New filings to process: {len(to_process)}")

    # Resume from specific accession if specified
    if args.resume:
        found = False
        for i, f in enumerate(to_process):
            if f["accession_number"] == args.resume:
                to_process = to_process[i:]
                found = True
                break
        if not found:
            log(f"WARNING: Resume point {args.resume} not found")

    if not to_process:
        log("Nothing to process. Done.")
        return

    log(f"Processing {len(to_process)} filings...")
    log("-" * 60)

    # Process filings
    success = 0
    failed = 0

    for i, filing in enumerate(to_process):
        log(f"[{i+1}/{len(to_process)}]")

        if process_filing(
            filing,
            dry_run=args.dry_run,
            generate_summaries=not args.no_summaries,
            process_exhibits=args.exhibits,
        ):
            success += 1
        else:
            failed += 1

        # Progress report every 25 filings
        if (i + 1) % 25 == 0:
            log(f"Progress: {i+1}/{len(to_process)} ({success} success, {failed} failed)")

    log("=" * 60)
    log(f"Backfill complete: {success} success, {failed} failed")
    log("=" * 60)


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SEC Historical Backfill")
    parser.add_argument("--forms", help="Comma-separated list of form types to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to database")
    parser.add_argument("--resume", help="Resume from specific accession number")
    parser.add_argument("--no-summaries", action="store_true", help="Skip AI summary generation")
    parser.add_argument("--exhibits", action="store_true", help="Process exhibits for each filing")
    parser.add_argument("--update-all", action="store_true", help="Update all filings (not just new)")
    parser.add_argument("--missing-storage", action="store_true", help="Only process filings without storage")

    args = parser.parse_args()
    run_backfill(args)
