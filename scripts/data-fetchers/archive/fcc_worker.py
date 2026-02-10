#!/usr/bin/env python3
"""
FCC ECFS Worker

Fetches FCC filings related to AST SpaceMobile from the Electronic Comment Filing System.
Stores in Supabase inbox table.

Key dockets:
- IB Docket 22-271: AST SpaceMobile Supplemental Coverage from Space
- Various spectrum coordination filings
"""

from __future__ import annotations
import json
import os
import sys
import time
import urllib.request
import urllib.error
import re
from datetime import datetime
from typing import Dict, List, Optional

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# FCC ECFS Public API (DEMO_KEY works, but rate limited)
# Register for proper key at: https://api.data.gov/signup/
FCC_API_BASE = "https://publicapi.fcc.gov/ecfs/filings"
FCC_API_KEY = os.environ.get("FCC_API_KEY", "DEMO_KEY")

# Key dockets for ASTS
KEY_DOCKETS = [
    # Primary SCS dockets
    "22-271",  # Supplemental Coverage from Space (SCS) Rules
    "23-65",   # Single Network Future: SCS
    # AST-specific proceedings
    "25-201",  # AST SpaceMobile modification application (Space Bureau)
    "25-306",  # AST recent filings
    "25-340",  # AST recent filings
    # Related spectrum dockets
    "22-411",  # Space Bureau spectrum
    "22-272",  # Related SCS docket
]

# Filers to track (for keyword search fallback)
KEY_FILERS = [
    "AST SpaceMobile",
    "AST & Science",
]


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def fetch_url(url: str, headers: Optional[Dict] = None) -> str:
    default_headers = {"User-Agent": "Short Gravity Research gabriel@shortgravity.com"}
    if headers:
        default_headers.update(headers)
    req = urllib.request.Request(url, headers=default_headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8")


def fetch_json(url: str) -> Dict:
    content = fetch_url(url, {"Accept": "application/json"})
    return json.loads(content)


def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
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


def get_existing_source_ids(source: str) -> set:
    """Get existing source IDs from inbox."""
    try:
        result = supabase_request("GET", f"inbox?source=eq.{source}&select=source_id")
        return {r["source_id"] for r in result}
    except Exception as e:
        log(f"Error fetching existing items: {e}")
        return set()


def fetch_docket_filings(docket: str, limit: int = 500, offset: int = 0) -> List[Dict]:
    """Fetch filings for a specific docket using FCC Public API."""
    url = f"{FCC_API_BASE}?api_key={FCC_API_KEY}&proceedings.name={docket}&limit={limit}&offset={offset}&sort=date_received,DESC"

    try:
        data = fetch_json(url)
        return data.get("filing", [])
    except Exception as e:
        log(f"Error fetching docket {docket}: {e}")
        return []


def fetch_all_docket_filings(docket: str) -> List[Dict]:
    """Fetch ALL filings for a docket, paginating through results."""
    all_filings = []
    offset = 0
    limit = 500  # Max per request

    while True:
        log(f"  Fetching offset {offset}...")
        filings = fetch_docket_filings(docket, limit=limit, offset=offset)
        if not filings:
            break
        all_filings.extend(filings)
        log(f"  Got {len(filings)} filings (total: {len(all_filings)})")

        if len(filings) < limit:
            break  # No more pages
        offset += limit
        time.sleep(1)  # Rate limit

    return all_filings


def generate_summary(content: str, title: str) -> str:
    """Generate AI summary using Claude API."""
    if not ANTHROPIC_API_KEY:
        return ""

    max_content = 30000
    truncated = content[:max_content] if len(content) > max_content else content

    prompt = f"""You are analyzing an FCC filing related to AST SpaceMobile's satellite-to-cellular network.

Title: {title}

Provide a concise summary (2-3 sentences) focusing on:
- What the filing is about (comments, reply, application, etc.)
- Key positions or arguments made
- Any spectrum or regulatory implications
- Impact on AST SpaceMobile's business

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
        log(f"Error generating summary: {e}")
        return ""


def process_fcc_filing(filing: Dict, existing: set) -> bool:
    """Process a single FCC filing."""
    filing_id = filing.get("id_submission") or filing.get("id_long") or filing.get("id")
    if not filing_id:
        return False

    if str(filing_id) in existing:
        return False  # Already have it

    try:
        # Extract metadata
        submission_type = filing.get("submissiontype", {}).get("description", "Filing")
        filers = filing.get("filers", [])
        filer = filers[0].get("name", "Unknown") if filers else "Unknown"
        date_received = filing.get("date_received", "")

        # Get proceedings/dockets
        proceedings = [p.get("name", "") for p in filing.get("proceedings", [])]

        # Get document info
        docs = filing.get("documents", [])
        doc_url = docs[0].get("src", "") if docs else ""
        if not doc_url:
            doc_url = f"https://www.fcc.gov/ecfs/document/{filing_id}/1"

        # Build title
        title = f"{filer}: {submission_type}"
        if len(proceedings) > 0:
            title += f" (Docket {proceedings[0]})"

        # Determine importance
        importance = "normal"
        filer_lower = filer.lower()
        if "ast spacemobile" in filer_lower or "ast & science" in filer_lower:
            importance = "high"  # Direct ASTS filings are high importance
        elif any(x in filer_lower for x in ["t-mobile", "at&t", "verizon", "fcc"]):
            importance = "high"  # Partner/regulator filings

        # Build metadata
        metadata = {
            "filer": filer,
            "all_filers": [f.get("name") for f in filers],
            "proceedings": proceedings,
            "submission_type": submission_type,
            "submission_type_short": filing.get("submissiontype", {}).get("short", ""),
            "bureaus": [b.get("name") for b in filing.get("bureaus", [])],
        }

        # Insert into inbox (no summary yet)
        inbox_item = {
            "source": "fcc_filing",
            "source_id": str(filing_id),
            "title": title,
            "published_at": date_received,
            "url": doc_url,
            "category": "regulatory",
            "tags": proceedings,
            "importance": importance,
            "metadata": json.dumps(metadata),
            "status": "completed",
        }

        supabase_request("POST", "inbox", inbox_item)
        return True

    except Exception as e:
        log(f"  ✗ Error processing {filing_id}: {e}")
        return False


def run_worker():
    """Main worker function."""
    log("=" * 60)
    log("FCC ECFS Worker Started")
    log("=" * 60)
    log(f"Using API key: {FCC_API_KEY[:10]}...")

    if not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    # Get existing FCC filings
    existing = get_existing_source_ids("fcc_filing")
    log(f"Found {len(existing)} existing FCC filings in inbox")

    all_filings = []

    # Fetch ALL filings from key dockets
    for docket in KEY_DOCKETS:
        log(f"Fetching ALL filings for docket {docket}...")
        filings = fetch_all_docket_filings(docket)
        log(f"  Total: {len(filings)} filings")
        all_filings.extend(filings)
        time.sleep(2)

    # Deduplicate by filing ID
    seen = set()
    unique_filings = []
    for f in all_filings:
        fid = f.get("id_submission") or f.get("id_long") or f.get("id")
        if fid and str(fid) not in seen:
            seen.add(str(fid))
            unique_filings.append(f)

    log(f"Total unique filings: {len(unique_filings)}")
    log(f"Already in database: {len(existing)}")

    # Filter to only new ones
    new_filings = [f for f in unique_filings
                   if str(f.get("id_submission") or f.get("id_long") or f.get("id")) not in existing]
    log(f"New filings to process: {len(new_filings)}")

    if not new_filings:
        log("No new FCC filings. Done.")
        return

    success = 0
    failed = 0

    for i, filing in enumerate(new_filings):
        if process_fcc_filing(filing, existing):
            success += 1
            if success % 50 == 0:
                log(f"  Progress: {success} added...")
        else:
            failed += 1
        # Small delay to avoid rate limits
        if (i + 1) % 100 == 0:
            time.sleep(1)

    log("=" * 60)
    log(f"Completed: {success} success, {failed} skipped/failed")
    log("=" * 60)


if __name__ == "__main__":
    import urllib.parse
    run_worker()
