#!/usr/bin/env python3
"""
SEC Filing Worker

Polls SEC EDGAR for new ASTS filings, fetches content,
generates AI summaries via Claude, and stores in Supabase.

v2: Full document storage (no truncation) + Supabase Storage integration

Run manually: python3 filing_worker.py
Run as cron: */15 * * * * cd /path/to/scripts && python3 filing_worker.py
"""

from __future__ import annotations
import json
import os
import sys
import time
import urllib.request
import urllib.error
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

# Import storage utilities (for full document storage)
try:
    from storage_utils import upload_sec_filing, compute_hash
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False

# Configuration
ASTS_CIK = "0001780312"
SEC_BASE_URL = "https://data.sec.gov"
SEC_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"
USER_AGENT = "Short Gravity Research gabriel@shortgravity.com"

# Supabase config (from environment)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Anthropic config
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Form types to process - None means ALL forms (complete historical record)
KEY_FORMS = None  # Set to list like ["10-K", "10-Q", "8-K"] to filter

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


def log(msg: str):
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def fetch_url(url: str, headers: Optional[Dict] = None) -> str:
    """Fetch URL content."""
    default_headers = {"User-Agent": USER_AGENT}
    if headers:
        default_headers.update(headers)

    req = urllib.request.Request(url, headers=default_headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        content = response.read()
        # Try UTF-8 first, fall back to latin-1 for SEC files with special chars
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1", errors="replace")


def fetch_json(url: str) -> Dict:
    """Fetch JSON from URL."""
    content = fetch_url(url, {"Accept": "application/json"})
    return json.loads(content)


def get_filing_url(accession_number: str, document: str) -> str:
    """Generate SEC filing URL."""
    accession_no_dashes = accession_number.replace("-", "")
    return f"{SEC_ARCHIVES_URL}/{ASTS_CIK}/{accession_no_dashes}/{document}"


def extract_text_from_html(html: str) -> str:
    """Extract text from HTML/iXBRL, removing tags and XBRL metadata."""
    # Remove display:none sections (contains XBRL hidden data in iXBRL filings)
    text = re.sub(r'<div[^>]*style="[^"]*display:\s*none[^"]*"[^>]*>[\s\S]*?</div>', '', html, flags=re.IGNORECASE)

    # Remove ix:header sections (XBRL metadata block)
    text = re.sub(r'<ix:header>[\s\S]*?</ix:header>', '', text, flags=re.IGNORECASE)

    # Remove script and style tags
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.IGNORECASE)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Decode common HTML entities
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = re.sub(r"&#\d+;", "", text)

    # Clean up whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def get_item_descriptions(items: str) -> List[str]:
    """Convert item codes to descriptions."""
    if not items:
        return []
    return [ITEM_CODES.get(item.strip(), f"Item {item.strip()}") for item in items.split(",")]


# ============================================================================
# SEC API
# ============================================================================

def fetch_recent_filings(limit: int = 1000) -> List[Dict]:
    """Fetch all ASTS filings from SEC EDGAR - complete historical record."""
    url = f"{SEC_BASE_URL}/submissions/CIK{ASTS_CIK}.json"
    log(f"Fetching SEC submissions: {url}")

    data = fetch_json(url)
    recent = data["filings"]["recent"]
    filings = []

    # Iterate through ALL filings
    total_filings = len(recent["accessionNumber"])
    for i in range(total_filings):
        form = recent["form"][i]

        # If KEY_FORMS is None, include all forms (complete record)
        if KEY_FORMS is not None and form not in KEY_FORMS:
            continue

        # Mark high-signal forms for frontend filtering
        is_high_signal = form in HIGH_SIGNAL_FORMS if HIGH_SIGNAL_FORMS else False

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

        if len(filings) >= limit:
            break

    return filings


def fetch_filing_content(url: str) -> str:
    """Fetch and extract text from filing HTML."""
    log(f"Fetching filing content: {url}")
    html = fetch_url(url)
    return extract_text_from_html(html)


# ============================================================================
# SUPABASE
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


def get_existing_accession_numbers() -> set:
    """Get accession numbers already in database."""
    try:
        result = supabase_request("GET", "filings?select=accession_number")
        return {r["accession_number"] for r in result}
    except Exception as e:
        log(f"Error fetching existing filings: {e}")
        return set()


def insert_filing(filing: Dict) -> Dict:
    """Insert new filing into Supabase."""
    return supabase_request("POST", "filings", filing)


def update_filing(accession_number: str, updates: Dict) -> Dict:
    """Update filing in Supabase."""
    endpoint = f"filings?accession_number=eq.{accession_number}"
    return supabase_request("PATCH", endpoint, updates)


# ============================================================================
# CLAUDE API
# ============================================================================

def generate_summary(content: str, form: str, items: str) -> str:
    """Generate AI summary using Claude API."""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set")

    # Build context
    item_descriptions = get_item_descriptions(items)
    items_context = ""
    if item_descriptions:
        items_context = f"\n\nItems reported: {', '.join(item_descriptions)}"

    # Use more content for better summaries (up to 100K chars)
    max_content = 100000
    truncated = content[:max_content] if len(content) > max_content else content

    prompt = f"""You are analyzing an SEC {form} filing for AST SpaceMobile (ASTS), a company building a space-based cellular network.{items_context}

Provide a concise summary (2-4 sentences) of the key information in this filing that would be most relevant to investors. Focus on:
- Material business developments
- Financial metrics or guidance
- Partnership/contract updates
- Satellite launch or operational milestones
- Executive changes
- Any risks or concerns

Filing content:
{truncated}

Summary:"""

    # Call Claude API
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    }

    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    log("Calling Claude API for summary...")

    with urllib.request.urlopen(req, timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))
        return result["content"][0]["text"].strip()


# ============================================================================
# MAIN WORKER
# ============================================================================

def process_filing(filing: Dict) -> bool:
    """Process a single filing: fetch content, generate summary, store in DB and Storage."""
    accession = filing["accession_number"]
    form = filing["form"]
    log(f"Processing {form} filed {filing['filing_date']}: {accession}")

    try:
        # Insert with pending status
        filing["status"] = "processing"
        insert_filing(filing)

        # Fetch content (FULL content, no truncation)
        content = fetch_filing_content(filing["url"])
        content_length = len(content)
        content_bytes = content.encode("utf-8")
        content_hash = None
        storage_path = None
        log(f"  Content length: {content_length:,} chars")

        # Upload full document to Supabase Storage (if available)
        if STORAGE_AVAILABLE:
            try:
                content_hash = compute_hash(content_bytes)
                storage_result = upload_sec_filing(
                    accession_number=accession,
                    form_type=form,
                    content=content,
                    document_name="primary.txt",
                )
                if storage_result.get("success"):
                    storage_path = storage_result.get("path")
                    log(f"  Uploaded to Storage: {storage_path}")
                else:
                    log(f"  Warning: Storage upload failed: {storage_result.get('error')}")
            except Exception as e:
                log(f"  Warning: Storage upload error: {e}")

        # Generate summary
        summary = generate_summary(content, form, filing.get("items", ""))
        log(f"  Summary: {summary[:100]}...")

        # Update with FULL content, storage path, and summary
        updates = {
            "content_text": content,  # FULL content - no truncation!
            "content_length": content_length,
            "summary": summary,
            "summary_model": "claude-haiku-4-5-20251001",
            "summary_generated_at": datetime.utcnow().isoformat() + "Z",
            "status": "completed",
        }

        # Add storage fields if available
        if storage_path:
            updates["storage_path"] = storage_path
        if content_hash:
            updates["full_content_hash"] = content_hash
        updates["filing_size_bytes"] = len(content_bytes)

        update_filing(accession, updates)

        log(f"  ✓ Completed")
        return True

    except Exception as e:
        log(f"  ✗ Error: {e}")
        try:
            update_filing(accession, {
                "status": "failed",
                "error_message": str(e)[:500],
            })
        except:
            pass
        return False


def run_worker():
    """Main worker loop."""
    log("=" * 60)
    log("SEC Filing Worker v2 (Full Storage)")
    log("=" * 60)
    log(f"Storage integration: {'enabled' if STORAGE_AVAILABLE else 'disabled'}")

    # Check required env vars
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    if not ANTHROPIC_API_KEY:
        log("ERROR: ANTHROPIC_API_KEY not set")
        log("Set it in your environment or .env file")
        sys.exit(1)

    # Get existing filings
    existing = get_existing_accession_numbers()
    log(f"Found {len(existing)} existing filings in database")

    # Fetch all filings from SEC (528 total as of Jan 2025)
    recent = fetch_recent_filings(limit=600)
    log(f"Fetched {len(recent)} recent key filings from SEC")

    # Find new filings
    new_filings = [f for f in recent if f["accession_number"] not in existing]
    log(f"New filings to process: {len(new_filings)}")

    if not new_filings:
        log("No new filings. Done.")
        return

    # Process each new filing
    success = 0
    failed = 0

    for filing in new_filings:
        if process_filing(filing):
            success += 1
        else:
            failed += 1

        # Rate limit: wait between filings
        time.sleep(2)

    log("=" * 60)
    log(f"Completed: {success} success, {failed} failed")
    log("=" * 60)


def reprocess_failed():
    """Reprocess filings that previously failed."""
    log("=" * 60)
    log("Reprocessing Failed Filings")
    log("=" * 60)

    if not SUPABASE_SERVICE_KEY or not ANTHROPIC_API_KEY:
        log("ERROR: Missing SUPABASE_SERVICE_KEY or ANTHROPIC_API_KEY")
        sys.exit(1)

    # Get failed filings
    result = supabase_request("GET", "filings?status=eq.failed&select=*")
    log(f"Found {len(result)} failed filings")

    if not result:
        log("No failed filings to reprocess.")
        return

    success = 0
    for filing in result:
        accession = filing["accession_number"]
        log(f"Reprocessing {filing['form']} filed {filing['filing_date']}: {accession}")

        try:
            # Fetch content
            content = fetch_filing_content(filing["url"])
            log(f"  Content length: {len(content):,} chars")

            # Generate summary
            summary = generate_summary(content, filing["form"], filing.get("items", ""))
            log(f"  Summary: {summary[:100]}...")

            # Upload to storage if available
            storage_path = None
            content_hash = None
            if STORAGE_AVAILABLE:
                try:
                    content_hash = compute_hash(content.encode("utf-8"))
                    storage_result = upload_sec_filing(
                        accession_number=accession,
                        form_type=filing["form"],
                        content=content,
                    )
                    if storage_result.get("success"):
                        storage_path = storage_result.get("path")
                        log(f"  Uploaded to Storage: {storage_path}")
                except Exception as e:
                    log(f"  Storage upload error: {e}")

            # Update with FULL content
            updates = {
                "content_text": content,  # Full content, no truncation
                "content_length": len(content),
                "summary": summary,
                "summary_model": "claude-haiku-4-5-20251001",
                "summary_generated_at": datetime.utcnow().isoformat() + "Z",
                "status": "completed",
                "error_message": None,
            }
            if storage_path:
                updates["storage_path"] = storage_path
            if content_hash:
                updates["full_content_hash"] = content_hash
            updates["filing_size_bytes"] = len(content.encode("utf-8"))

            update_filing(accession, updates)
            log(f"  ✓ Completed")
            success += 1
        except Exception as e:
            log(f"  ✗ Error: {e}")

        time.sleep(2)

    log(f"Reprocessed {success}/{len(result)} filings")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--reprocess":
        reprocess_failed()
    else:
        run_worker()
