#!/usr/bin/env python3
"""
FCC Attachment Downloader — Downloads actual technical documents from FCC systems.

Two download strategies:
  1. FCC ELS (apps.fcc.gov/els/GetAtt.html) — public, no auth needed
     - Uses Playwright same-origin fetch to bypass Akamai CDN
     - Requires known ELS attachment IDs
  2. FCC ICFS ServiceNow (fccprod.servicenowservices.com) — requires login
     - Uses Playwright with FCC_ICFS_USERNAME/FCC_ICFS_PASSWORD env vars
     - Discovers all attachments per filing via "Attachments" tab

Documents are stored in:
  - fcc_filing_attachments table (text extracted from PDFs)
  - Supabase Storage fcc-filings bucket (raw PDFs)

Usage:
    # Download known ELS attachments (no auth needed)
    python3 fcc_attachment_worker.py --els

    # Discover + download from ICFS ServiceNow (needs FCC login)
    python3 fcc_attachment_worker.py --icfs --filing SAT-AMD-20240311-00053

    # Scan ELS IDs in a range (finds new documents)
    python3 fcc_attachment_worker.py --els-scan --start 371000 --end 390000

    # Dry run
    python3 fcc_attachment_worker.py --els --dry-run

Environment:
    SUPABASE_URL, SUPABASE_SERVICE_KEY — Database
    ANTHROPIC_API_KEY — For AI summaries (optional)
    FCC_ICFS_USERNAME, FCC_ICFS_PASSWORD — For ServiceNow downloads (optional)

Requires: playwright (pip install playwright && playwright install chromium)
          pdfplumber (pip install pdfplumber)
"""

from __future__ import annotations
import argparse
import base64
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

# =============================================================================
# Configuration
# =============================================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
FCC_ICFS_USERNAME = os.environ.get("FCC_ICFS_USERNAME", "")
FCC_ICFS_PASSWORD = os.environ.get("FCC_ICFS_PASSWORD", "")

FCC_ELS_URL = "https://apps.fcc.gov/els/GetAtt.html?id="
FCC_APP_BASE = "https://apps.fcc.gov/"
ICFS_BASE = "https://fccprod.servicenowservices.com/icfs"
ICFS_DETAIL_URL = f"{ICFS_BASE}?id=ibfs_application_summary&number="

RATE_LIMIT_SECONDS = 2.0
MAX_ATTACHMENT_SIZE_MB = 50

# Known ELS attachment IDs for AST SpaceMobile filings
# These were discovered via audit of FCC filing records
KNOWN_ELS_IDS = {
    371448: {"label": "Experimental license application (0284-EX-CN-2025)", "filing": "SAT-LOA-20200413-00034"},
    371450: {"label": "FM1 ODAR Rev 1.0", "filing": "SAT-AMD-20240311-00053"},
    375091: {"label": "FM1-FM243 ODAR Rev 2.0 (DC-01936 B)", "filing": "SAT-AMD-20240311-00053"},
    376295: {"label": "SCS Interference Analysis (93 pages)", "filing": "SAT-MOD-20250612-00145"},
    377292: {"label": "Ex Parte - ODAR reference (June 2025)", "filing": "SAT-AMD-20240311-00053"},
    379516: {"label": "Ex Parte - ODAR reference (July 2025)", "filing": "SAT-AMD-20240311-00053"},
    380044: {"label": "FM1 ODAR Rev 6.0 (DC-01936)", "filing": "SAT-AMD-20240311-00053"},
    383613: {"label": "Experimental operations exhibit (0909-EX-CN-2025)", "filing": "SAT-STA-20251121-00333"},
    386452: {"label": "STA experimental operations request", "filing": "SAT-STA-20260116-00029"},
}


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# =============================================================================
# Supabase utilities
# =============================================================================

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


def supabase_insert(table: str, row: Dict) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = supabase_headers()
    headers["Prefer"] = "return=minimal"
    try:
        body = json.dumps(row).encode()
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        urllib.request.urlopen(req, timeout=60)
        return True
    except urllib.error.HTTPError as e:
        error = e.read().decode() if e.fp else ""
        log(f"  Insert error {e.code}: {error[:300]}")
        return False


def supabase_patch(table: str, filters: str, data: Dict):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{filters}"
    headers = supabase_headers()
    headers["Prefer"] = "return=minimal"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="PATCH")
    try:
        urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e:
        error = e.read().decode() if e.fp else ""
        log(f"  Patch error {e.code}: {error[:200]}")


# =============================================================================
# PDF extraction
# =============================================================================

def extract_text_from_pdf(pdf_bytes: bytes) -> Tuple[str, int]:
    """Extract text from PDF. Returns (text, page_count)."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                pt = page.extract_text()
                if pt:
                    text_parts.append(pt)
            text = "\n\n".join(text_parts)
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = re.sub(r"[ \t]+", " ", text)
            return text.strip(), len(pdf.pages)
    except ImportError:
        pass
    except Exception as e:
        log(f"    pdfplumber error: {e}")

    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text_parts = []
        for page in reader.pages:
            pt = page.extract_text()
            if pt:
                text_parts.append(pt)
        text = "\n\n".join(text_parts)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip(), len(reader.pages)
    except ImportError:
        pass
    except Exception as e:
        log(f"    PyPDF2 error: {e}")

    log("    No PDF library available (install pdfplumber or PyPDF2)")
    return "", 0


def identify_doc_type(text: str) -> str:
    """Identify FCC document type from content."""
    first_2k = text[:2000]
    if "Orbital Debris Assessment Report" in first_2k or "ODAR" in first_2k:
        return "Orbital Debris Assessment Report (ODAR)"
    if "Schedule S" in first_2k:
        return "Schedule S - Technical Data"
    if "interference" in first_2k.lower() and "analysis" in first_2k.lower():
        return "Interference Analysis"
    if "Ex Parte" in first_2k or "ex parte" in first_2k.lower():
        return "Ex Parte Filing"
    if "narrative" in first_2k.lower():
        return "Application Narrative"
    if "certification" in first_2k.lower():
        return "Certification"
    if "experimental" in first_2k.lower():
        return "Experimental Operations"
    if "letter" in first_2k[:500].lower():
        return "Letter/Correspondence"
    return "Technical Document"


# =============================================================================
# AI summary
# =============================================================================

def generate_summary(els_id: str, doc_type: str, content: str) -> Optional[str]:
    if not ANTHROPIC_API_KEY or not content or len(content) < 200:
        return None
    try:
        body = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 400,
            "messages": [{
                "role": "user",
                "content": (
                    f"Summarize this FCC filing attachment for an $ASTS investor. "
                    f"Focus on key technical parameters, spectrum, satellite specs, "
                    f"or regulatory requests.\n\n"
                    f"Document: {doc_type} (ELS {els_id})\n\n"
                    f"Content (first 4000 chars):\n{content[:4000]}"
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
        log(f"    AI summary error: {e}")
        return None


# =============================================================================
# Storage upload
# =============================================================================

def upload_to_storage(els_id: str, content: bytes) -> Optional[str]:
    """Upload PDF to Supabase Storage. Returns path or None."""
    path = f"els/{els_id}.pdf"
    url = f"{SUPABASE_URL}/storage/v1/object/fcc-filings/{path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/pdf",
        "x-upsert": "true",
    }
    req = urllib.request.Request(url, data=content, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return path
    except urllib.error.HTTPError as e:
        error = e.read().decode() if e.fp else ""
        log(f"    Storage error {e.code}: {error[:200]}")
        return None


# =============================================================================
# ELS Download Strategy — Playwright same-origin fetch
# =============================================================================

def download_els_documents(page: Any, els_ids: List[int], dry_run: bool = False) -> List[Dict]:
    """Download documents from FCC ELS using Playwright same-origin fetch."""
    results = []

    for els_id in els_ids:
        url = f"{FCC_ELS_URL}{els_id}"
        log(f"\n  ELS {els_id}")

        if dry_run:
            log(f"    [DRY RUN] {url}")
            results.append({"els_id": str(els_id), "source_url": url})
            continue

        try:
            # Use browser's fetch API from same-origin context
            result = page.evaluate("""async (url) => {
                try {
                    const resp = await fetch(url);
                    if (!resp.ok) return { error: resp.status + ' ' + resp.statusText };
                    const buffer = await resp.arrayBuffer();
                    const bytes = new Uint8Array(buffer);
                    let binary = '';
                    for (let i = 0; i < bytes.length; i += 32768) {
                        const chunk = bytes.subarray(i, i + 32768);
                        binary += String.fromCharCode.apply(null, chunk);
                    }
                    return { size: bytes.length, b64: btoa(binary) };
                } catch(e) { return { error: e.message }; }
            }""", url)

            if result.get("error"):
                log(f"    Error: {result['error']}")
                continue

            data = base64.b64decode(result["b64"])

            if data[:4] != b"%PDF":
                log(f"    Not PDF ({len(data)} bytes)")
                continue

            log(f"    Downloaded: {len(data):,} bytes")

            # Extract text
            text, page_count = extract_text_from_pdf(data)
            doc_type = identify_doc_type(text) if text else "Unknown"
            log(f"    Pages: {page_count}, Text: {len(text):,} chars, Type: {doc_type}")

            content_hash = hashlib.sha256(data).hexdigest()

            # Upload to storage
            storage_path = upload_to_storage(str(els_id), data)
            if storage_path:
                log(f"    Stored: {storage_path}")

            results.append({
                "els_id": str(els_id),
                "doc_type": doc_type,
                "page_count": page_count,
                "file_size_bytes": len(data),
                "content_text": text,
                "content_hash": content_hash,
                "storage_path": storage_path,
                "source_url": url,
            })

            time.sleep(RATE_LIMIT_SECONDS)

        except Exception as e:
            log(f"    ERROR: {e}")

    return results


# =============================================================================
# ICFS ServiceNow Strategy — Playwright with login
# =============================================================================

def icfs_login(page: Any) -> bool:
    """Login to FCC ICFS ServiceNow portal via Okta SSO."""
    if not FCC_ICFS_USERNAME or not FCC_ICFS_PASSWORD:
        log("  No FCC ICFS credentials configured")
        return False

    try:
        # Step 1: SSO locator page
        page.goto("https://fccprod.servicenowservices.com/login_locate_sso.do",
                   wait_until="networkidle", timeout=30000)
        time.sleep(2)

        # Step 2: Enter email to find SSO provider
        page.fill("#sso_selector_id", FCC_ICFS_USERNAME)
        page.evaluate("() => { if (typeof locateSSO === 'function') locateSSO(); }")
        time.sleep(8)

        # Step 3: Fill Okta login form
        page.fill('input[name="identifier"]', FCC_ICFS_USERNAME)
        page.fill('input[name="credentials.passcode"]', FCC_ICFS_PASSWORD)
        page.click('input[type="submit"]')
        time.sleep(8)
        page.wait_for_load_state("networkidle", timeout=15000)

        # Verify login succeeded (URL should leave login page)
        if "login" not in page.url.lower() or "servicenow" in page.url.lower():
            log("  Logged in to FCC ICFS via Okta SSO")
            return True

        log("  Login may have failed — checking session...")
        page.goto(f"{ICFS_DETAIL_URL}SAT-LOA-20200413-00034",
                   wait_until="networkidle", timeout=15000)
        has_content = page.evaluate("() => document.body.innerText.length > 500")
        if has_content:
            log("  Session active (verified via filing page)")
            return True

        log("  Login failed")
        return False

    except Exception as e:
        log(f"  Login error: {e}")
        return False


def discover_icfs_attachments(page: Any, file_number: str) -> List[Dict]:
    """Discover attachments from ICFS filing detail page (requires login for download)."""
    url = f"{ICFS_DETAIL_URL}{file_number}"
    attachments: List[Dict] = []

    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(3)

        # Click Attachments tab
        page.evaluate("""() => {
            const links = document.querySelectorAll('a, li, span, button');
            for (const el of links) {
                if (el.textContent.trim() === 'Attachments') { el.click(); return true; }
            }
            return false;
        }""")
        time.sleep(3)

        # Extract sys_attachment.do links
        att_data = page.evaluate("""() => {
            const results = [];
            const links = document.querySelectorAll('a[href*="sys_attachment.do"]');
            for (const a of links) {
                const href = a.href || '';
                const match = href.match(/sys_id=([a-f0-9]{32})/);
                if (match) {
                    results.push({
                        sys_id: match[1],
                        name: a.textContent.trim() || 'Download',
                        url: href,
                    });
                }
            }
            return results;
        }""")

        seen: Set[str] = set()
        for att in att_data:
            sid = att.get("sys_id")
            if sid and sid not in seen:
                seen.add(sid)
                attachments.append(att)

    except Exception as e:
        log(f"    Discovery error: {e}")

    return attachments


def download_icfs_attachment(page: Any, att: Dict) -> Optional[bytes]:
    """Download attachment from ICFS ServiceNow (requires active login session)."""
    url = att["url"]
    try:
        result = page.evaluate("""async (url) => {
            try {
                const resp = await fetch(url);
                if (!resp.ok) return { error: resp.status + ' ' + resp.statusText };
                const buffer = await resp.arrayBuffer();
                const bytes = new Uint8Array(buffer);
                let binary = '';
                for (let i = 0; i < bytes.length; i += 32768) {
                    const chunk = bytes.subarray(i, i + 32768);
                    binary += String.fromCharCode.apply(null, chunk);
                }
                return { size: bytes.length, b64: btoa(binary) };
            } catch(e) { return { error: e.message }; }
        }""", url)

        if result.get("error"):
            log(f"    Download error: {result['error']}")
            return None

        return base64.b64decode(result["b64"])

    except Exception as e:
        log(f"    Download error: {e}")
        return None


# =============================================================================
# Database operations
# =============================================================================

def get_stored_icfs_file_numbers() -> Set[str]:
    """Get file numbers that already have ICFS attachments stored."""
    rows = supabase_get(
        "fcc_filing_attachments?select=file_number&source_url=like.*servicenow*"
    )
    return {r["file_number"] for r in rows}


def get_stored_els_ids() -> Set[str]:
    """Get ELS IDs already stored in the database."""
    rows = supabase_get("fcc_filing_attachments?select=source_url&source_url=like.*els*")
    ids = set()
    for r in rows:
        url = r.get("source_url", "")
        m = re.search(r"id=(\d+)", url)
        if m:
            ids.add(m.group(1))
    return ids


def store_attachment(els_id: str, filing: str, doc_type: str, result: Dict) -> bool:
    """Store attachment in fcc_filing_attachments table."""
    row = {
        "file_number": filing,
        "attachment_number": int(els_id) if els_id.isdigit() else 1,
        "filename": f"{doc_type}.pdf",
        "description": f"FCC ELS {els_id} - {doc_type}",
        "content_type": "application/pdf",
        "file_size_bytes": result.get("file_size_bytes"),
        "content_text": result.get("content_text"),
        "content_hash": result.get("content_hash"),
        "storage_path": result.get("storage_path"),
        "source_url": result.get("source_url"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    return supabase_insert("fcc_filing_attachments", row)


# =============================================================================
# ELS ID Scanner — finds new AST-related documents
# =============================================================================

def scan_els_range(page: Any, start: int, end: int, step: int = 1) -> List[Dict]:
    """Scan a range of ELS IDs and download AST-related documents."""
    results = []
    ast_keywords = [
        "ast spacemobile", "ast & science", "ast science",
        "bluewalker", "bluebird", "spacemobile",
        "direct-to-device", "direct to device",
    ]

    for els_id in range(start, end + 1, step):
        if (els_id - start) % 100 == 0:
            log(f"  Scanning ELS {els_id}...")

        url = f"{FCC_ELS_URL}{els_id}"

        try:
            result = page.evaluate("""async (url) => {
                try {
                    const resp = await fetch(url, { method: 'HEAD' });
                    if (!resp.ok) return { error: resp.status };
                    const type = resp.headers.get('content-type') || '';
                    const length = parseInt(resp.headers.get('content-length') || '0');
                    return { type, length };
                } catch(e) { return { error: e.message }; }
            }""", url)

            if result.get("error"):
                continue

            # Only process PDFs
            if "pdf" not in result.get("type", "").lower():
                continue

            # Download and check if AST-related
            dl_result = page.evaluate("""async (url) => {
                try {
                    const resp = await fetch(url);
                    if (!resp.ok) return { error: resp.status };
                    const buffer = await resp.arrayBuffer();
                    const bytes = new Uint8Array(buffer);
                    let binary = '';
                    for (let i = 0; i < bytes.length; i += 32768) {
                        const chunk = bytes.subarray(i, i + 32768);
                        binary += String.fromCharCode.apply(null, chunk);
                    }
                    return { size: bytes.length, b64: btoa(binary) };
                } catch(e) { return { error: e.message }; }
            }""", url)

            if dl_result.get("error"):
                continue

            data = base64.b64decode(dl_result["b64"])
            if data[:4] != b"%PDF":
                continue

            text, page_count = extract_text_from_pdf(data)
            if not text:
                continue

            # Check if AST-related
            text_lower = text[:5000].lower()
            is_ast = any(kw in text_lower for kw in ast_keywords)

            if is_ast:
                doc_type = identify_doc_type(text)
                log(f"  FOUND AST document at ELS {els_id}: {doc_type} ({page_count} pages)")
                results.append({
                    "els_id": str(els_id),
                    "doc_type": doc_type,
                    "page_count": page_count,
                    "file_size_bytes": len(data),
                    "content_text": text,
                    "content_hash": hashlib.sha256(data).hexdigest(),
                    "source_url": url,
                })

            time.sleep(0.5)

        except Exception:
            continue

    return results


# =============================================================================
# Main
# =============================================================================

def run(args):
    log("=" * 60)
    log("FCC ATTACHMENT DOWNLOADER")
    log("=" * 60)

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("ERROR: playwright not installed")
        sys.exit(1)

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)

    try:
        if args.els or args.els_scan:
            # ELS strategy — download from apps.fcc.gov
            page = browser.new_page()
            page.goto(FCC_APP_BASE, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)

            if args.els_scan:
                log(f"  Scanning ELS IDs {args.start} to {args.end}")
                results = scan_els_range(page, args.start, args.end, args.step)
            else:
                # Download known ELS documents
                already = get_stored_els_ids() if not args.backfill else set()
                els_ids = [eid for eid in KNOWN_ELS_IDS if str(eid) not in already]

                if not els_ids:
                    log("All known ELS documents already stored.")
                    return

                log(f"  Downloading {len(els_ids)} ELS documents")
                results = download_els_documents(page, els_ids, args.dry_run)

            # Store results
            if not args.dry_run:
                stored = 0
                for r in results:
                    els_id = r["els_id"]
                    filing = KNOWN_ELS_IDS.get(int(els_id), {}).get("filing", f"ELS-{els_id}")
                    doc_type = r.get("doc_type", "Technical Document")
                    if store_attachment(els_id, filing, doc_type, r):
                        stored += 1
                        log(f"  Stored: ELS-{els_id} ({doc_type})")
                log(f"\n  Stored {stored}/{len(results)} documents")

            total_chars = sum(len(r.get("content_text", "")) for r in results)
            log(f"\n  Total: {len(results)} documents, {total_chars:,} chars")

        elif args.icfs or args.icfs_incremental:
            # ICFS ServiceNow strategy
            if not FCC_ICFS_USERNAME:
                log("ERROR: FCC_ICFS_USERNAME and FCC_ICFS_PASSWORD required for ICFS mode")
                log("  Sign up at: https://fccprod.servicenowservices.com/icfs")
                sys.exit(1)

            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            if not icfs_login(page):
                log("ICFS login failed. Check credentials.")
                sys.exit(1)

            if args.filing:
                filings = [args.filing]
            elif args.icfs_incremental:
                # Incremental: only filings NOT yet in fcc_filing_attachments
                already_stored = get_stored_icfs_file_numbers()
                rows = supabase_get(
                    "fcc_filings?select=file_number&filing_system=eq.ICFS"
                    "&file_number=like.SAT*&order=filed_date.desc"
                )
                all_filings = [r["file_number"] for r in rows]
                filings = [fn for fn in all_filings if fn not in already_stored]
                log(f"  Incremental: {len(filings)} new filings ({len(all_filings)} total, {len(already_stored)} already stored)")
            else:
                rows = supabase_get(
                    "fcc_filings?select=file_number&filing_system=eq.ICFS"
                    "&file_number=like.SAT*&order=file_number.asc"
                )
                filings = [r["file_number"] for r in rows]

            log(f"  Processing {len(filings)} filings")

            for i, fn in enumerate(filings):
                log(f"\n[{i + 1}/{len(filings)}] {fn}")
                attachments = discover_icfs_attachments(page, fn)
                log(f"  Found {len(attachments)} attachments")

                if args.dry_run:
                    for att in attachments:
                        log(f"    {att['name']}: {att['sys_id']}")
                    continue

                for idx, att in enumerate(attachments):
                    data = download_icfs_attachment(page, att)
                    if not data:
                        continue

                    if data[:4] == b"%PDF":
                        text, page_count = extract_text_from_pdf(data)
                        content_type = "application/pdf"
                    elif data[:1] in (b"[", b"{", b"<", b" ") or data[:4] in (b"Form", b"Befo", b"UNIT"):
                        text = data.decode("utf-8", errors="replace")
                        page_count = 0
                        content_type = "text/plain"
                    else:
                        text, page_count = "", 0
                        content_type = "application/octet-stream"

                    # Skip if content looks like an HTML error page
                    if text and "<html" in text[:200].lower() and len(data) < 30000:
                        log(f"    SKIP (HTML error page): {att['name']}")
                        continue

                    doc_type = identify_doc_type(text) if text else "Unknown"
                    log(f"    {att['name']}: {len(data):,} bytes, {doc_type}")

                    row = {
                        "file_number": fn,
                        "attachment_number": idx + 1,
                        "filename": att["name"],
                        "description": f"ServiceNow sys_id: {att['sys_id']}",
                        "content_type": content_type,
                        "file_size_bytes": len(data),
                        "content_text": text,
                        "content_hash": hashlib.sha256(data).hexdigest(),
                        "source_url": att["url"],
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                    }
                    supabase_insert("fcc_filing_attachments", row)
                    time.sleep(RATE_LIMIT_SECONDS)

        else:
            log("Specify --els, --els-scan, or --icfs mode")
            sys.exit(1)

    finally:
        browser.close()
        pw.stop()

    log(f"\n{'=' * 60}")
    log("DONE")
    log(f"{'=' * 60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FCC Attachment Downloader")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--els", action="store_true", help="Download known ELS attachments")
    mode.add_argument("--els-scan", action="store_true", help="Scan ELS ID range for AST documents")
    mode.add_argument("--icfs", action="store_true", help="Download from ICFS ServiceNow (full crawl)")
    mode.add_argument("--icfs-incremental", action="store_true", help="ICFS: only new filings not yet stored")

    parser.add_argument("--filing", type=str, help="Process single filing (ICFS mode)")
    parser.add_argument("--start", type=int, default=370000, help="ELS scan start ID")
    parser.add_argument("--end", type=int, default=390000, help="ELS scan end ID")
    parser.add_argument("--step", type=int, default=1, help="ELS scan step")
    parser.add_argument("--backfill", action="store_true", help="Re-process already downloaded")
    parser.add_argument("--dry-run", action="store_true", help="Preview without downloading")

    args = parser.parse_args()
    run(args)
