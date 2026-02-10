#!/usr/bin/env python3
"""
USPTO Patent Worker

Fetches AST SpaceMobile patents from multiple sources:
1. PatentsView API (primary, requires free API key)
2. USPTO Open Data Portal (bulk XML)
3. USPTO.report scraper (fallback)

Stores in Supabase patents table with full text for RAG.

Usage:
    python3 patent_worker.py                    # Incremental update
    python3 patent_worker.py --backfill         # Full historical fetch
    python3 patent_worker.py --dry-run          # Preview without writing
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
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Set
from html.parser import HTMLParser

# Storage utilities
try:
    from storage_utils import compute_hash, log
except ImportError:
    def log(msg: str):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    def compute_hash(content: str) -> str:
        import hashlib
        return hashlib.sha256(content.encode()).hexdigest()[:16]


# ============================================================================
# Configuration
# ============================================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# PatentsView API (requires free API key)
PATENTSVIEW_API_KEY = os.environ.get("PATENTSVIEW_API_KEY", "")
PATENTSVIEW_BASE = "https://search.patentsview.org/api/v1"

# AST SpaceMobile assignee variations
AST_ASSIGNEES = [
    "AST & Science, LLC",
    "AST & Science",
    "AST Science",
    "AST SpaceMobile",
]

# Key inventors to also search
KEY_INVENTORS = [
    "Avellan; Abel",
    "Abel Avellan",
]

# Rate limiting
RATE_LIMIT_SECONDS = 1.0
USER_AGENT = "Short Gravity Research gabriel@shortgravity.com"


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
                return response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

    raise last_error


def fetch_json(url: str, headers: Optional[Dict] = None) -> Dict:
    """Fetch JSON from URL."""
    default_headers = {"Accept": "application/json"}
    if headers:
        default_headers.update(headers)
    content = fetch_url(url, default_headers)
    return json.loads(content)


def post_json(url: str, data: Dict, headers: Optional[Dict] = None) -> Dict:
    """POST JSON to URL."""
    default_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    if headers:
        default_headers.update(headers)

    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=default_headers, method="POST")

    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


# ============================================================================
# Supabase Operations
# ============================================================================

def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None) -> any:
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
        with urllib.request.urlopen(req, timeout=60) as response:
            content = response.read().decode("utf-8")
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        log(f"Supabase error: {e.code} - {error_body}")
        raise


def get_existing_patents() -> Set[str]:
    """Get existing patent numbers from database."""
    try:
        result = supabase_request("GET", "patents?select=patent_number")
        return {r["patent_number"] for r in result if r.get("patent_number")}
    except Exception as e:
        log(f"Error fetching existing patents: {e}")
        return set()


def upsert_patent(patent: Dict) -> Dict:
    """Insert or update patent."""
    patent_number = patent.get("patent_number")
    if not patent_number:
        return {}

    # Check if exists
    encoded = urllib.parse.quote(patent_number)
    existing = supabase_request("GET", f"patents?patent_number=eq.{encoded}&select=id")

    if existing:
        return supabase_request("PATCH", f"patents?patent_number=eq.{encoded}", patent)
    else:
        return supabase_request("POST", "patents", patent)


# ============================================================================
# PatentsView API (Primary Source)
# ============================================================================

def fetch_patents_patentsview(assignee: str) -> List[Dict]:
    """Fetch patents from PatentsView API."""
    if not PATENTSVIEW_API_KEY:
        log("  PatentsView API key not set, skipping")
        return []

    patents = []
    page = 1
    per_page = 100

    while True:
        # Build query
        query = {
            "q": {"assignee_organization": assignee},
            "f": [
                "patent_number",
                "patent_title",
                "patent_date",
                "patent_abstract",
                "patent_num_claims",
                "patent_type",
                "inventors",
                "assignees",
                "cpcs",
                "application",
            ],
            "o": {
                "page": page,
                "per_page": per_page,
            },
        }

        url = f"{PATENTSVIEW_BASE}/patent/"
        headers = {"X-Api-Key": PATENTSVIEW_API_KEY}

        try:
            # PatentsView uses query params, not POST body for simple queries
            params = urllib.parse.urlencode({
                "q": json.dumps(query["q"]),
                "f": json.dumps(query["f"]),
                "o": json.dumps(query["o"]),
            })
            full_url = f"{url}?{params}"

            data = fetch_json(full_url, headers)
            results = data.get("patents", [])

            if not results:
                break

            patents.extend(results)
            log(f"    Page {page}: {len(results)} patents (total: {len(patents)})")

            if len(results) < per_page:
                break

            page += 1
            time.sleep(RATE_LIMIT_SECONDS)

        except Exception as e:
            log(f"  PatentsView API error: {e}")
            break

    return patents


def parse_patentsview_patent(raw: Dict) -> Dict:
    """Parse PatentsView response into our schema."""
    # Extract inventors
    inventors = []
    for inv in raw.get("inventors", []):
        inventors.append({
            "name": f"{inv.get('inventor_first_name', '')} {inv.get('inventor_last_name', '')}".strip(),
            "city": inv.get("inventor_city"),
            "state": inv.get("inventor_state"),
            "country": inv.get("inventor_country"),
            "sequence": inv.get("inventor_sequence"),
        })

    # Extract assignee
    assignees = raw.get("assignees", [])
    assignee = assignees[0].get("assignee_organization") if assignees else None
    assignee_type = assignees[0].get("assignee_type") if assignees else None

    # Extract CPC codes
    cpc_codes = [c.get("cpc_group_id") for c in raw.get("cpcs", []) if c.get("cpc_group_id")]

    # Get application info
    app = raw.get("application", {})

    # Build content text for RAG
    content_parts = [
        raw.get("patent_title", ""),
        raw.get("patent_abstract", ""),
    ]
    content_text = "\n\n".join(filter(None, content_parts))

    return {
        "patent_number": raw.get("patent_number"),
        "patent_id": raw.get("patent_id"),
        "title": raw.get("patent_title"),
        "abstract": raw.get("patent_abstract"),
        "filing_date": app.get("app_date"),
        "grant_date": raw.get("patent_date"),
        "inventors": json.dumps(inventors) if inventors else None,
        "assignee": assignee,
        "assignee_organization": assignee,
        "assignee_type": assignee_type,
        "cpc_codes": cpc_codes if cpc_codes else None,
        "claims_count": raw.get("patent_num_claims"),
        "status": "granted",
        "content_text": content_text if content_text else None,
        "source": "patentsview",
        "source_url": f"https://patents.google.com/patent/{raw.get('patent_number')}",
        "raw_data": json.dumps(raw),
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }


# ============================================================================
# USPTO.report Scraper (Fallback)
# ============================================================================

class PatentListParser(HTMLParser):
    """Parse patent list from USPTO.report."""

    def __init__(self):
        super().__init__()
        self.patents = []
        self.current_patent = {}
        self.in_row = False
        self.in_cell = False
        self.cell_index = 0
        self.current_data = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "tr":
            self.in_row = True
            self.current_patent = {}
            self.cell_index = 0
        elif tag == "td" and self.in_row:
            self.in_cell = True
            self.current_data = ""
        elif tag == "a" and self.in_cell:
            href = attrs_dict.get("href", "")
            if "/patent/" in href:
                # Extract patent number from link
                match = re.search(r'/patent/([A-Z0-9]+)', href)
                if match:
                    self.current_patent["patent_number"] = match.group(1)

    def handle_endtag(self, tag):
        if tag == "td" and self.in_cell:
            self.in_cell = False
            data = self.current_data.strip()
            if self.cell_index == 1:  # Title column
                self.current_patent["title"] = data
            elif self.cell_index == 2:  # Date column
                self.current_patent["date"] = data
            self.cell_index += 1
        elif tag == "tr" and self.in_row:
            self.in_row = False
            if self.current_patent.get("patent_number"):
                self.patents.append(self.current_patent)

    def handle_data(self, data):
        if self.in_cell:
            self.current_data += data


def scrape_uspto_report(company_slug: str = "Ast-Science-L-L-C") -> List[Dict]:
    """Scrape patents from uspto.report."""
    url = f"https://uspto.report/company/{company_slug}/patents"

    try:
        html = fetch_url(url)

        # Find all patent links and titles
        patents = []

        # Pattern: <a href="/patent/app/XXXXXXX">Title</a>
        app_pattern = r'<a href="/patent/app/(\d+)"[^>]*>([^<]+)</a>'
        for match in re.finditer(app_pattern, html):
            patents.append({
                "patent_number": match.group(1),
                "title": match.group(2).strip(),
                "status": "pending",
                "source": "uspto_report",
            })

        # Pattern: <a href="/patent/US........">Title</a>
        grant_pattern = r'<a href="/patent/(US\d+[A-Z]?\d*)"[^>]*>([^<]+)</a>'
        for match in re.finditer(grant_pattern, html):
            patents.append({
                "patent_number": match.group(1),
                "title": match.group(2).strip(),
                "status": "granted",
                "source": "uspto_report",
            })

        return patents

    except Exception as e:
        log(f"  uspto.report scrape error: {e}")
        return []


def fetch_patent_details_uspto_report(patent_number: str) -> Dict:
    """Fetch detailed patent info from uspto.report."""
    # Determine URL based on patent number format
    if patent_number.startswith("US"):
        url = f"https://uspto.report/patent/{patent_number}"
    else:
        url = f"https://uspto.report/patent/app/{patent_number}"

    try:
        html = fetch_url(url)

        details = {
            "patent_number": patent_number,
            "source_url": url,
        }

        # Extract title
        title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        if title_match:
            details["title"] = title_match.group(1).strip()

        # Extract abstract
        abstract_match = re.search(r'Abstract[:\s]*</[^>]+>\s*<[^>]+>([^<]+)', html, re.IGNORECASE)
        if abstract_match:
            details["abstract"] = abstract_match.group(1).strip()

        # Extract filing date
        filing_match = re.search(r'Filed[:\s]*(\d{4}-\d{2}-\d{2})', html)
        if filing_match:
            details["filing_date"] = filing_match.group(1)

        # Extract grant date
        grant_match = re.search(r'(?:Granted|Published)[:\s]*(\d{4}-\d{2}-\d{2})', html)
        if grant_match:
            details["grant_date"] = grant_match.group(1)

        # Extract inventors
        inv_matches = re.findall(r'Inventor[s]?[:\s]*([^<]+)', html, re.IGNORECASE)
        if inv_matches:
            inventors = []
            for inv_text in inv_matches:
                names = [n.strip() for n in inv_text.split(",") if n.strip()]
                for name in names[:10]:  # Limit
                    inventors.append({"name": name})
            if inventors:
                details["inventors"] = json.dumps(inventors)

        # Extract claims count
        claims_match = re.search(r'(\d+)\s*[Cc]laim', html)
        if claims_match:
            details["claims_count"] = int(claims_match.group(1))

        # Build content text
        content_parts = [
            details.get("title", ""),
            details.get("abstract", ""),
        ]
        details["content_text"] = "\n\n".join(filter(None, content_parts))

        return details

    except Exception as e:
        log(f"    uspto.report error for {patent_number}: {e}")
        return {"patent_number": patent_number}


# ============================================================================
# USPTO PEDS API (Patent Examination Data System)
# ============================================================================

def fetch_patents_peds(assignee_search: str) -> List[Dict]:
    """Fetch patents from USPTO PEDS API (no key required)."""
    url = "https://ped.uspto.gov/api/queries"

    payload = {
        "searchText": f"firstNamedApplicant:({assignee_search})",
        "fq": [],
        "fl": "*",
        "mm": "100%",
        "df": "patentTitle",
        "facet": "false",
        "sort": "applId desc",
        "start": "0",
    }

    try:
        result = post_json(url, payload)
        docs = result.get("queryResults", {}).get("searchResponse", {}).get("response", {}).get("docs", [])
        return docs
    except Exception as e:
        log(f"  PEDS API error: {e}")
        return []


def parse_peds_patent(raw: Dict) -> Dict:
    """Parse PEDS response into our schema."""
    # PEDS uses application number format
    app_id = raw.get("applId", "")
    patent_number = raw.get("patentNumber")

    # Use patent number if granted, otherwise app number
    identifier = f"US{patent_number}" if patent_number else app_id

    # Extract inventors
    inventors = []
    inv_name = raw.get("inventorName", "")
    if inv_name:
        for name in inv_name.split(";"):
            name = name.strip()
            if name:
                inventors.append({"name": name})

    # Determine status
    app_status = raw.get("appStatus", "").lower()
    if patent_number:
        status = "granted"
    elif "pending" in app_status or "docketed" in app_status:
        status = "pending"
    elif "abandoned" in app_status:
        status = "abandoned"
    else:
        status = "unknown"

    return {
        "patent_number": identifier,
        "application_number": app_id,
        "title": raw.get("inventionTitle"),
        "filing_date": raw.get("appFilingDate"),
        "grant_date": raw.get("patentIssueDate"),
        "inventors": json.dumps(inventors) if inventors else None,
        "assignee": raw.get("firstNamedApplicant"),
        "assignee_organization": raw.get("firstNamedApplicant"),
        "status": status,
        "source": "peds",
        "source_url": f"https://ped.uspto.gov/api/queries/{app_id}",
        "raw_data": json.dumps(raw),
    }


# ============================================================================
# AI Summary Generation
# ============================================================================

def generate_patent_summary(patent: Dict) -> str:
    """Generate AI summary for a patent."""
    if not ANTHROPIC_API_KEY:
        return ""

    title = patent.get("title", "Unknown")
    abstract = patent.get("abstract", "No abstract available")
    claims_count = patent.get("claims_count", "Unknown")

    prompt = f"""Analyze this AST SpaceMobile patent and provide a 2-3 sentence summary explaining:
1. What technology or method it protects
2. Why it matters for direct-to-device satellite communications

Patent Title: {title}
Abstract: {abstract}
Claims: {claims_count}

Summary:"""

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
    }
    body = {
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        result = post_json(url, body, headers)
        return result["content"][0]["text"].strip()
    except Exception as e:
        log(f"    Summary generation error: {e}")
        return ""


# ============================================================================
# Discovery & Processing
# ============================================================================

def discover_all_patents() -> List[Dict]:
    """Discover all AST SpaceMobile patents from multiple sources."""
    all_patents = {}  # patent_number -> patent dict

    log("Discovering patents...")

    # Source 1: PatentsView API (most comprehensive if API key available)
    if PATENTSVIEW_API_KEY:
        log("  [1/4] Querying PatentsView API...")
        for assignee in AST_ASSIGNEES:
            patents = fetch_patents_patentsview(assignee)
            for p in patents:
                parsed = parse_patentsview_patent(p)
                pn = parsed.get("patent_number")
                if pn and pn not in all_patents:
                    all_patents[pn] = parsed
            time.sleep(RATE_LIMIT_SECONDS)
        log(f"       Found {len(all_patents)} patents from PatentsView")
    else:
        log("  [1/4] PatentsView API key not set, skipping")

    # Source 2: USPTO PEDS API (no key required)
    log("  [2/4] Querying USPTO PEDS API...")
    for search_term in ["AST Science", "AST Spacemobile"]:
        patents = fetch_patents_peds(search_term)
        for p in patents:
            parsed = parse_peds_patent(p)
            pn = parsed.get("patent_number")
            if pn and pn not in all_patents:
                all_patents[pn] = parsed
        time.sleep(RATE_LIMIT_SECONDS)
    log(f"       Total: {len(all_patents)} patents from PEDS")

    # Source 3: USPTO.report scraper (may be blocked)
    log("  [3/4] Scraping uspto.report...")
    for slug in ["Ast-Science-L-L-C", "Ast-Spacemobile-Inc"]:
        patents = scrape_uspto_report(slug)
        for p in patents:
            pn = p.get("patent_number")
            if pn and pn not in all_patents:
                all_patents[pn] = p
        time.sleep(RATE_LIMIT_SECONDS)
    log(f"       Total: {len(all_patents)} patents")

    # Source 4: Known core patents (seed data) - US, International, Korean
    log("  [4/4] Adding known core patents...")
    known_patents = [
        # === US GRANTED PATENTS ===
        {"patent_number": "US9973266B1", "title": "System and method for high throughput fractionated satellites (HTFS)", "status": "granted", "grant_date": "2018-05-15", "abstract": "A high throughput fractionated satellite (HTFS) system where the functional capabilities of a conventional monolithic spacecraft are distributed across many small or very small satellites and a central command and relay satellite.", "assignee": "AST & Science, LLC"},
        {"patent_number": "US10892818B1", "title": "Satellite communication system", "status": "granted", "assignee": "AST & Science, LLC"},
        {"patent_number": "US11063661B1", "title": "Broadband satellite communication system", "status": "granted", "assignee": "AST & Science, LLC"},
        {"patent_number": "US11431417B1", "title": "Space-based network communication", "status": "granted", "assignee": "AST & Science, LLC"},
        {"patent_number": "US11082131B1", "title": "Modular space platform architecture", "status": "granted", "assignee": "AST & Science, LLC"},
        {"patent_number": "US11153819B1", "title": "Direct communication with mobile devices", "status": "granted", "assignee": "AST & Science, LLC"},
        {"patent_number": "US11239904B1", "title": "Beam forming for satellite communications", "status": "granted", "assignee": "AST & Science, LLC"},
        {"patent_number": "US12483327", "title": "Ground station processing of downlink signals", "status": "granted", "abstract": "Ground station that processes downlink signals received from respective satellites with Doppler and delay compensation.", "assignee": "AST & Science, LLC"},

        # === US PENDING APPLICATIONS ===
        {"patent_number": "US20210044349A1", "title": "Satellite MIMO system", "status": "pending", "abstract": "Multiple-input multiple-output satellite communication system.", "assignee": "AST & Science, LLC"},
        {"patent_number": "US20190238216A1", "title": "High throughput fractionated satellites for direct connectivity", "status": "pending", "abstract": "System and method for high throughput fractionated satellites for direct connectivity to end user devices.", "assignee": "AST & Science, LLC"},
        {"patent_number": "US20220103258A1", "title": "Satellite power amplifier calibration", "status": "pending", "assignee": "AST & Science, LLC"},
        {"patent_number": "US20220200686A1", "title": "Mutual coupling based calibration with OFDM signals", "status": "pending", "assignee": "AST & Science, LLC"},
        {"patent_number": "US20210135714A1", "title": "Network architecture for mobile device connectivity", "status": "pending", "assignee": "AST & Science, LLC"},
        {"patent_number": "US20210376911A1", "title": "Spectrum sharing for satellite-terrestrial systems", "status": "pending", "assignee": "AST & Science, LLC"},

        # === PCT/WIPO INTERNATIONAL APPLICATIONS ===
        {"patent_number": "WO2021163729A1", "title": "AI power management system for effective duty cycle for space constellations", "status": "pending", "filing_date": "2021-02-11", "assignee": "AST & Science, LLC", "source": "wipo"},
        {"patent_number": "WO2016060954A3", "title": "Satellite operating system, architecture, testing and radio communication", "status": "granted", "assignee": "AST & Science, LLC", "source": "wipo"},
        {"patent_number": "WO2020172580A1", "title": "Space-based network for cellular communication", "status": "pending", "assignee": "AST & Science, LLC", "source": "wipo"},

        # === EUROPEAN PATENT OFFICE (EPO) - derived from PCT national phase ===
        # EP patents typically enter from WO applications - need to verify these exist
        # {"patent_number": "EP3378176A1", "title": "Satellite operating system and architecture", "status": "pending", "assignee": "AST & Science, LLC", "source": "epo"},

        # NOTE: Korean patents claimed by GreyB report but NOT independently verified
        # The "Korea (South)" jurisdiction in patent databases often refers to:
        # 1. PCT national phase entries (automatic from WO filings)
        # 2. Patent family members (not separate filings)
        # Removing unverified Korean patents until we can confirm with KIPRIS database
    ]
    for p in known_patents:
        pn = p.get("patent_number")
        if pn and pn not in all_patents:
            all_patents[pn] = p
    log(f"       Total: {len(all_patents)} patents")

    return list(all_patents.values())


def process_patent(patent: Dict, dry_run: bool = False, no_summary: bool = False) -> bool:
    """Process a single patent."""
    patent_number = patent.get("patent_number")
    if not patent_number:
        return False

    log(f"Processing: {patent_number}")

    if dry_run:
        log("  [DRY RUN] Would process this patent")
        return True

    try:
        # Fetch detailed info if we only have basic data
        if not patent.get("abstract") and not patent.get("title"):
            log("  Fetching details...")
            details = fetch_patent_details_uspto_report(patent_number)
            patent.update(details)
            time.sleep(RATE_LIMIT_SECONDS)

        # Generate AI summary
        if not no_summary and patent.get("abstract"):
            log("  Generating summary...")
            summary = generate_patent_summary(patent)
            if summary:
                patent["ai_summary"] = summary
                patent["ai_model"] = "claude-3-5-haiku-20241022"
                patent["ai_generated_at"] = datetime.utcnow().isoformat() + "Z"
                log(f"    Summary: {summary[:60]}...")
            time.sleep(RATE_LIMIT_SECONDS)

        # Compute content hash
        content = patent.get("content_text", "")
        if content:
            patent["content_hash"] = compute_hash(content)

        # Set defaults
        patent["source"] = patent.get("source", "uspto_report")
        patent["fetched_at"] = datetime.utcnow().isoformat() + "Z"

        # Upsert to database
        upsert_patent(patent)
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
    log("USPTO Patent Worker")
    log("=" * 60)

    if PATENTSVIEW_API_KEY:
        log(f"PatentsView API Key: {PATENTSVIEW_API_KEY[:10]}...")
    else:
        log("PatentsView API Key: NOT SET (will use scrapers)")

    if not args.dry_run and not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    # Discover all patents
    all_patents = discover_all_patents()
    log(f"Total patents discovered: {len(all_patents)}")

    # Get existing patents
    existing = get_existing_patents()
    log(f"Already in database: {len(existing)}")

    # Determine what to process
    if args.backfill:
        to_process = all_patents
        log(f"Backfill mode: processing all {len(to_process)} patents")
    else:
        to_process = [p for p in all_patents if p.get("patent_number") not in existing]
        log(f"New patents to process: {len(to_process)}")

    if not to_process:
        log("Nothing to process. Done.")
        return

    # Limit if specified
    if args.limit:
        to_process = to_process[:args.limit]
        log(f"Limited to {args.limit} patents")

    log("-" * 60)
    success = 0
    failed = 0

    for i, patent in enumerate(to_process):
        log(f"[{i+1}/{len(to_process)}]")

        if process_patent(patent, dry_run=args.dry_run, no_summary=args.no_summary):
            success += 1
        else:
            failed += 1

        if (i + 1) % 10 == 0:
            log(f"Progress: {i+1}/{len(to_process)} ({success} success, {failed} failed)")

    log("=" * 60)
    log(f"Completed: {success} success, {failed} failed")
    log("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="USPTO Patent Worker")
    parser.add_argument("--backfill", action="store_true", help="Process all patents")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to database")
    parser.add_argument("--no-summary", action="store_true", help="Skip AI summary generation")
    parser.add_argument("--limit", type=int, help="Limit number of patents to process")

    args = parser.parse_args()
    run_worker(args)
