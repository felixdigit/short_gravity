#!/usr/bin/env python3
"""
ISED (Innovation, Science and Economic Development Canada) Regulatory Worker

Tracks Canadian spectrum/satellite filings related to AST SpaceMobile.
ISED is the Canadian spectrum regulator. Rogers Communications is AST's
Canadian MNO partner.

Data sources:
1. ISED Drupal JSON API — Full content pages (consultations, decisions, notices)
2. Canada Gazette Part I — Weekly regulatory notices referencing ISED spectrum
3. ISED Satellite Licence Lists — Authorized satellite operators in Canada

Stores in Supabase fcc_filings table with filing_system='ICFS' and
file_number prefix 'ISED-*' (CHECK constraint only allows ICFS/ECFS/ELS).

Usage:
    # Standard run (incremental)
    python3 ised_worker.py

    # Full backfill
    python3 ised_worker.py --backfill

    # Dry run (no database writes)
    python3 ised_worker.py --dry-run

    # Limit number processed
    python3 ised_worker.py --limit 10

    # Gazette only
    python3 ised_worker.py --gazette-only

    # ISED API only
    python3 ised_worker.py --api-only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Dict, List, Optional, Set, Tuple


# ============================================================================
# Configuration
# ============================================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

ISED_BASE = "https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en"
ISED_JSON_API = f"{ISED_BASE}/jsonapi/node/page"
GAZETTE_BASE = "https://gazette.gc.ca"

USER_AGENT = "Short Gravity Research gabriel@shortgravity.com"

# Rate limits
RATE_LIMIT_SECONDS = 0.5
MAX_RETRIES = 3

# Valid filing_system values per fcc_filings CHECK constraint
VALID_FILING_SYSTEMS = {"ICFS", "ECFS", "ELS"}

# Keywords that indicate relevance to AST SpaceMobile / satellite D2D
SATELLITE_KEYWORDS = [
    "ast spacemobile",
    "supplemental mobile coverage",
    "supplemental coverage",
    "direct to device",
    "direct-to-device",
    "d2d",
    "non-terrestrial network",
    "non-terrestrial",
    "ntn ",
    "satellite direct",
    "mobile satellite service",
    "mobile satellite",
    "satellite spectrum",
    "satellite licence",
    "satellite license",
    "space station licence",
    "earth station",
    "smcs",
]

# Broader keywords — match these in ISED content for general relevance
BROAD_KEYWORDS = [
    "rogers",
    "spectrum allocation",
    "spectrum auction",
    "spectrum consultation",
    "spectrum policy",
    "radiocommunication",
    "satellite",
]

# Known high-value ISED node IDs (hand-picked from API exploration)
# These are pages directly about supplemental mobile coverage by satellite
HIGH_VALUE_NIDS = {
    2154,  # SMSE-006-24: Consultation on SMCS Framework
    2264,  # Decision on SMCS Framework
    2430,  # S2: Space Station Licences for SMCS
    2316,  # S3: Generic Earth Stations for SMCS
    2313,  # SRSP-103: Technical Requirements for SMCS Space Stations
    2332,  # SMSE-007-25: Consultation on frequency bands for SMCS
    2405,  # Comments on SMSE-007-25
    2417,  # Reply Comments on SMSE-007-25
    2245,  # Consultation on Space Debris licensing changes
    2278,  # Comments on Space Debris consultation
    2443,  # Notice re Telesat continued operation
    2453,  # Notice re SpaceX E-band frequencies
    1135,  # Applications Received for Satellite Licences
    315,   # Foreign satellites approved for FSS in Canada
    345,   # Authorized and Approved Canadian Satellites
    272,   # Authorized MSS Providers
    164,   # CPC-2-6-02: Application procedure for space station spectrum licences
    1372,  # N2: Space Station Licences
    2028,  # CPC-2-6-04: Foreign-Licensed Satellite Approval procedure
    2030,  # CPC-2-6-03: Generic Earth Station Spectrum Licences procedure
    2010,  # Spectrum Outlook 2023 to 2027
}


# ============================================================================
# Logging
# ============================================================================

def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ============================================================================
# HTML Text Extraction
# ============================================================================

class TextExtractor(HTMLParser):
    """Extract text from HTML, stripping tags."""

    def __init__(self) -> None:
        super().__init__()
        self._pieces: List[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in ("script", "style", "noscript"):
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript"):
            self._skip = False
        if tag in ("p", "br", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr"):
            self._pieces.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._pieces.append(data)

    def get_text(self) -> str:
        raw = "".join(self._pieces)
        # Normalize whitespace within lines, preserve line breaks
        lines = raw.split("\n")
        cleaned = []
        for line in lines:
            line = re.sub(r"[ \t]+", " ", line).strip()
            if line:
                cleaned.append(line)
        return "\n".join(cleaned)


def extract_text_from_html(html: str) -> str:
    """Extract clean text from HTML content."""
    parser = TextExtractor()
    try:
        parser.feed(html)
        return parser.get_text()
    except Exception:
        # Fallback regex approach
        text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
        text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = text.replace("&nbsp;", " ").replace("&amp;", "&")
        text = text.replace("&lt;", "<").replace("&gt;", ">")
        text = text.replace("&quot;", '"').replace("&#8212;", " -- ")
        text = text.replace("&mdash;", " -- ").replace("&ndash;", " - ")
        text = re.sub(r"&#\d+;", "", text)
        text = re.sub(r"&\w+;", "", text)
        return re.sub(r"\s+", " ", text).strip()


# ============================================================================
# HTTP Utilities
# ============================================================================

def fetch_url(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 60) -> str:
    """Fetch URL content with retry and exponential backoff."""
    default_headers = {"User-Agent": USER_AGENT}
    if headers:
        default_headers.update(headers)

    last_error: Optional[Exception] = None
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers=default_headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code == 429:
                wait = 10 * (attempt + 1)
                log(f"  Rate limited (429). Waiting {wait}s...")
                time.sleep(wait)
            elif e.code == 404:
                log(f"  404 Not Found: {url[:80]}")
                raise
            elif attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
        except (urllib.error.URLError, OSError) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                log(f"  Network error, retrying in {wait}s: {e}")
                time.sleep(wait)

    raise last_error  # type: ignore[misc]


def fetch_json(url: str) -> Dict:
    """Fetch and parse JSON from URL."""
    content = fetch_url(url, {"Accept": "application/vnd.api+json"})
    return json.loads(content)


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
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode("utf-8")
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        log(f"  Supabase error: {e.code} - {error_body[:200]}")
        raise


def get_existing_ised_ids() -> Set[str]:
    """Get existing ISED filing IDs from database."""
    try:
        result = supabase_request(
            "GET",
            "fcc_filings?file_number=like.ISED-*&select=file_number"
        )
        return {r["file_number"] for r in result if r.get("file_number")}
    except Exception as e:
        log(f"  Error fetching existing ISED filings: {e}")
        return set()


def upsert_ised_filing(filing: Dict) -> bool:
    """Insert or update an ISED filing in fcc_filings."""
    file_number = filing.get("file_number", "")
    filing_system = filing.get("filing_system", "ICFS")

    if filing_system not in VALID_FILING_SYSTEMS:
        log(f"  ERROR: Invalid filing_system '{filing_system}' for {file_number} — must be one of {VALID_FILING_SYSTEMS}")
        return False

    try:
        existing = supabase_request(
            "GET",
            f"fcc_filings?file_number=eq.{urllib.parse.quote(file_number)}"
            f"&filing_system=eq.{filing_system}&select=id"
        )

        if existing:
            supabase_request(
                "PATCH",
                f"fcc_filings?file_number=eq.{urllib.parse.quote(file_number)}"
                f"&filing_system=eq.{filing_system}",
                filing
            )
        else:
            supabase_request("POST", "fcc_filings", filing)

        return True
    except Exception as e:
        log(f"  Database error for {file_number}: {e}")
        return False


# ============================================================================
# ISED Drupal JSON API
# ============================================================================

def generate_ised_file_number(nid: int, title: str) -> str:
    """Generate a stable file_number from ISED node ID.

    Uses the ISED document reference code if one is found in the title
    (e.g. SMSE-006-24, SRSP-103, CPC-2-6-02). Otherwise falls back to
    ISED-NID-{nid}.
    """
    # Try to extract ISED document codes from title
    # Patterns: SMSE-006-24, SRSP-103, CPC-2-6-02, SPB-001-25, DBS-01-20, RSS-102, GL-10
    code_match = re.search(
        r'((?:SMSE|SRSP|CPC|SPB|DBS|RSS|SAB|GL|BS|RP)-[\w.-]+)',
        title,
        re.IGNORECASE
    )
    if code_match:
        return f"ISED-{code_match.group(1).upper()}"

    return f"ISED-NID-{nid}"


def classify_ised_page(title: str, body_text: str) -> str:
    """Classify an ISED page into a filing_type."""
    t = title.lower()
    b = body_text.lower()[:2000]

    if "consultation" in t or "consultation" in b[:500]:
        return "consultation"
    if "decision" in t:
        return "decision"
    if "notice" in t or "notice" in b[:200]:
        return "notice"
    if "comments received" in t or "reply comments" in t:
        return "comments"
    if "results" in t and "auction" in t:
        return "auction_results"
    if any(x in t for x in ["srsp-", "rss-", "ices-", "gl-", "bs-"]):
        return "technical_standard"
    if "licence" in t or "license" in t:
        return "licence"
    if any(x in t for x in ["cpc-", "procedure"]):
        return "procedure"
    if "subordination" in t:
        return "subordination"
    if "spectrum outlook" in t:
        return "policy"
    return "notice"


def is_satellite_relevant(title: str, body_text: str) -> Tuple[bool, str]:
    """Check if an ISED page is relevant to satellite/D2D topics.

    Returns (is_relevant, matched_keyword).
    """
    combined = (title + " " + body_text[:10000]).lower()

    for kw in SATELLITE_KEYWORDS:
        if kw in combined:
            return True, kw

    for kw in BROAD_KEYWORDS:
        if kw in combined:
            return True, kw

    return False, ""


def fetch_ised_pages(limit: Optional[int] = None) -> List[Dict]:
    """Fetch all pages from ISED Drupal JSON API.

    Paginates through the API and filters for satellite-relevant content.
    """
    all_relevant: List[Dict] = []
    url: Optional[str] = (
        f"{ISED_JSON_API}?page[limit]=50&sort=-changed"
        f"&fields[node--page]=title,drupal_internal__nid,created,changed,body"
    )
    page_num = 0
    max_pages = 30  # Safety limit

    log("Fetching ISED pages via Drupal JSON API...")

    while url and page_num < max_pages:
        log(f"  API page {page_num}...")
        try:
            data = fetch_json(url)
        except Exception as e:
            log(f"  Error fetching API page {page_num}: {e}")
            break

        pages = data.get("data", [])
        if not pages:
            break

        for page in pages:
            attrs = page.get("attributes", {})
            title = attrs.get("title", "")
            nid = attrs.get("drupal_internal__nid", 0)
            body = attrs.get("body", {})
            body_html = body.get("value", "") if body else ""
            created = attrs.get("created", "")
            changed = attrs.get("changed", "")

            # Always include high-value nodes
            if nid in HIGH_VALUE_NIDS:
                body_text = extract_text_from_html(body_html) if body_html else ""
                all_relevant.append({
                    "nid": nid,
                    "title": title,
                    "body_html": body_html,
                    "body_text": body_text,
                    "created": created,
                    "changed": changed,
                    "matched_keyword": "high_value_node",
                })
                continue

            # Check keyword relevance
            body_preview = extract_text_from_html(body_html[:10000]) if body_html else ""
            relevant, keyword = is_satellite_relevant(title, body_preview)

            if relevant:
                body_text = extract_text_from_html(body_html) if body_html else ""
                all_relevant.append({
                    "nid": nid,
                    "title": title,
                    "body_html": body_html,
                    "body_text": body_text,
                    "created": created,
                    "changed": changed,
                    "matched_keyword": keyword,
                })

        log(f"    Scanned {len(pages)} pages, relevant so far: {len(all_relevant)}")

        if limit and len(all_relevant) >= limit:
            break

        # Next page
        next_link = data.get("links", {}).get("next", {})
        url = next_link.get("href") if isinstance(next_link, dict) else None
        page_num += 1
        time.sleep(RATE_LIMIT_SECONDS)

    log(f"  Total relevant ISED pages: {len(all_relevant)}")
    return all_relevant


def process_ised_page(page: Dict, dry_run: bool = False) -> Optional[Dict]:
    """Process a single ISED page into a fcc_filings record."""
    nid = page["nid"]
    title = page["title"]
    body_text = page.get("body_text", "")
    created = page.get("created", "")
    changed = page.get("changed", "")

    # Clean up HTML entities in title
    title = title.replace("&#8212;", " -- ").replace("&mdash;", " -- ")
    title = title.replace("&#8211;", " - ").replace("&ndash;", " - ")
    title = title.replace("&amp;", "&").replace("&nbsp;", " ")

    file_number = generate_ised_file_number(nid, title)
    filing_type = classify_ised_page(title, body_text)
    source_url = f"{ISED_BASE}/node/{nid}"

    # Determine filer based on content
    filer_name = "ISED"
    text_lower = (title + " " + body_text[:3000]).lower()
    if "rogers" in text_lower:
        filer_name = "ISED (Rogers)"
    if "telesat" in text_lower:
        filer_name = "ISED (Telesat)"
    if "spacex" in text_lower:
        filer_name = "ISED (SpaceX)"
    if "ast spacemobile" in text_lower:
        filer_name = "ISED (AST SpaceMobile)"

    # Extract filing date from content or use created date
    filed_date = None
    # Look for date patterns like "June 2024" or "February 2025"
    date_match = re.search(
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})',
        body_text[:500]
    )
    if date_match:
        month_str = date_match.group(1)
        year_str = date_match.group(2)
        months = {
            "January": "01", "February": "02", "March": "03", "April": "04",
            "May": "05", "June": "06", "July": "07", "August": "08",
            "September": "09", "October": "10", "November": "11", "December": "12",
        }
        filed_date = f"{year_str}-{months[month_str]}-01"
    elif created:
        filed_date = created[:10]

    # Build description
    description = ""
    if body_text:
        # First ~300 chars as description
        desc_text = body_text[:500].replace("\n", " ").strip()
        description = desc_text[:300]
        if len(desc_text) > 300:
            description += "..."

    record = {
        "filing_system": "ICFS",
        "file_number": file_number,
        "title": title[:500],
        "description": description,
        "filer_name": filer_name,
        "filing_type": filing_type,
        "filed_date": filed_date,
        "content_text": body_text[:500000] if body_text else None,
        "source_url": source_url,
        "metadata": json.dumps({
            "nid": nid,
            "created": created,
            "changed": changed,
            "matched_keyword": page.get("matched_keyword", ""),
            "source": "ised_drupal_api",
            "jurisdiction": "ISED",
            "high_value": nid in HIGH_VALUE_NIDS,
        }),
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "completed",
    }

    if dry_run:
        log(f"  [DRY RUN] {file_number}: {title[:60]}")
        return record

    return record


# ============================================================================
# Canada Gazette Scraper
# ============================================================================

def fetch_gazette_years() -> List[int]:
    """Get available Canada Gazette Part I years."""
    # Gazette Part I contains ISED spectrum notices
    # Check recent years
    current_year = datetime.now().year
    return list(range(current_year, current_year - 3, -1))


def fetch_gazette_index(year: int) -> List[Dict]:
    """Fetch the Canada Gazette Part I index for a given year.

    Returns list of {url, title, date} for each edition.
    """
    url = f"{GAZETTE_BASE}/rp-pr/p1/{year}/index-eng.html"
    editions = []

    try:
        html = fetch_url(url)
    except Exception as e:
        log(f"  Error fetching Gazette {year} index: {e}")
        return []

    # Parse edition links: /rp-pr/p1/YYYY/YYYY-MM-DD/html/index-eng.html
    pattern = r'href="(/rp-pr/p1/\d{4}/(\d{4}-\d{2}-\d{2})/html/index-eng\.html)"'
    for match in re.finditer(pattern, html):
        path = match.group(1)
        date = match.group(2)
        editions.append({
            "url": f"{GAZETTE_BASE}{path}",
            "date": date,
        })

    # Also catch extra editions
    extra_pattern = r'href="(/rp-pr/p1/\d{4}/(\d{4}-\d{2}-\d{2})-x\d+/html/extra\d+-eng\.html)"'
    for match in re.finditer(extra_pattern, html):
        path = match.group(1)
        date = match.group(2)
        editions.append({
            "url": f"{GAZETTE_BASE}{path}",
            "date": date,
        })

    return editions


def scrape_gazette_edition(edition_url: str, edition_date: str) -> List[Dict]:
    """Scrape a single Gazette edition for ISED spectrum/satellite notices.

    Returns list of notice dicts with title, url, content.
    """
    notices = []

    try:
        html = fetch_url(edition_url, timeout=30)
    except Exception as e:
        log(f"    Error fetching {edition_url}: {e}")
        return []

    # Find links to notice pages that reference ISED, spectrum, satellite, etc.
    # Notice links look like: ./notice-avis-eng.html#ne8
    # or: ./notice-avis-eng.html
    links = re.findall(
        r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        html,
        re.DOTALL
    )

    base_url = edition_url.rsplit("/", 1)[0]
    relevant_links: List[Tuple[str, str]] = []

    for href, text in links:
        text_clean = re.sub(r"<[^>]+>", "", text).strip()
        text_clean = text_clean.replace("&nbsp;", " ").replace("&mdash;", " -- ")
        text_lower = text_clean.lower()

        # Check if the link text references spectrum/satellite/ISED topics
        is_relevant = any(
            kw in text_lower for kw in [
                "spectrum", "satellite", "radiocommunication",
                "ised", "innovation, science",
                "smse", "srsp", "spb", "dgso", "dbs",
                "mobile", "telecommunication",
                "supplemental", "direct to device",
            ]
        )

        if is_relevant and text_clean and len(text_clean) > 10:
            # Resolve relative URL
            if href.startswith("./"):
                full_url = f"{base_url}/{href[2:]}"
            elif href.startswith("/"):
                full_url = f"{GAZETTE_BASE}{href}"
            elif href.startswith("http"):
                full_url = href
            else:
                full_url = f"{base_url}/{href}"

            relevant_links.append((full_url, text_clean))

    if not relevant_links:
        return []

    # For each relevant link, try to fetch the notice content
    seen_urls = set()
    for notice_url, notice_title in relevant_links:
        # Deduplicate by base URL (ignore anchors)
        base_notice_url = notice_url.split("#")[0]
        if base_notice_url in seen_urls:
            continue
        seen_urls.add(base_notice_url)

        content_text = ""
        try:
            notice_html = fetch_url(base_notice_url, timeout=30)
            content_text = extract_text_from_html(notice_html)
            time.sleep(RATE_LIMIT_SECONDS)
        except Exception as e:
            log(f"    Could not fetch notice content: {e}")

        # Further filter: check if actual content is satellite-relevant
        if content_text:
            _, kw = is_satellite_relevant(notice_title, content_text)
            if not kw:
                continue

        notices.append({
            "title": notice_title,
            "url": notice_url,
            "date": edition_date,
            "content_text": content_text,
            "source": "canada_gazette",
        })

    return notices


def fetch_gazette_notices(years: Optional[List[int]] = None, limit: Optional[int] = None) -> List[Dict]:
    """Fetch all satellite-relevant notices from Canada Gazette."""
    if years is None:
        years = fetch_gazette_years()

    all_notices: List[Dict] = []

    log("Fetching Canada Gazette notices...")

    for year in years:
        log(f"  Gazette {year}...")
        editions = fetch_gazette_index(year)
        log(f"    Found {len(editions)} editions")

        for edition in editions:
            notices = scrape_gazette_edition(edition["url"], edition["date"])
            if notices:
                log(f"    {edition['date']}: {len(notices)} relevant notice(s)")
                all_notices.extend(notices)

            if limit and len(all_notices) >= limit:
                break

            time.sleep(RATE_LIMIT_SECONDS)

        if limit and len(all_notices) >= limit:
            break

    log(f"  Total Gazette notices: {len(all_notices)}")
    return all_notices


def process_gazette_notice(notice: Dict, dry_run: bool = False) -> Optional[Dict]:
    """Process a Canada Gazette notice into a fcc_filings record."""
    title = notice["title"]
    url = notice["url"]
    date = notice["date"]
    content = notice.get("content_text", "")

    # Generate stable file number from URL hash
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:12]
    file_number = f"ISED-GAZ-{url_hash}"

    # Try to extract ISED document code from title
    code_match = re.search(
        r'((?:SMSE|SRSP|CPC|SPB|DBS|RSS|SAB|GL)-[\w.-]+)',
        title,
        re.IGNORECASE
    )
    if code_match:
        file_number = f"ISED-GAZ-{code_match.group(1).upper()}"

    filing_type = "notice"
    if "consultation" in title.lower():
        filing_type = "consultation"
    elif "decision" in title.lower():
        filing_type = "decision"

    description = ""
    if content:
        desc = content[:500].replace("\n", " ").strip()
        description = desc[:300]
        if len(desc) > 300:
            description += "..."

    record = {
        "filing_system": "ICFS",
        "file_number": file_number,
        "title": f"[Canada Gazette] {title}"[:500],
        "description": description,
        "filer_name": "ISED (Canada Gazette)",
        "filing_type": filing_type,
        "filed_date": date,
        "content_text": content[:500000] if content else None,
        "source_url": url,
        "metadata": json.dumps({
            "source": "canada_gazette",
            "jurisdiction": "ISED",
            "gazette_date": date,
        }),
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "completed",
    }

    if dry_run:
        log(f"  [DRY RUN] {file_number}: {title[:60]}")
        return record

    return record


# ============================================================================
# Main Worker
# ============================================================================

def run_worker(args: argparse.Namespace) -> None:
    """Main worker function."""
    log("=" * 60)
    log("ISED Regulatory Worker")
    log("=" * 60)

    if not args.dry_run and not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    if not args.dry_run and not SUPABASE_URL:
        log("ERROR: SUPABASE_URL not set")
        sys.exit(1)

    # Get existing ISED filings
    existing_ids: Set[str] = set()
    if not args.dry_run:
        existing_ids = get_existing_ised_ids()
        log(f"Existing ISED filings in database: {len(existing_ids)}")

    all_records: List[Dict] = []

    # ── Source 1: ISED Drupal JSON API ──
    if not args.gazette_only:
        ised_pages = fetch_ised_pages(limit=args.limit)

        for page in ised_pages:
            record = process_ised_page(page, dry_run=args.dry_run)
            if record:
                all_records.append(record)

    # ── Source 2: Canada Gazette ──
    if not args.api_only:
        gazette_notices = fetch_gazette_notices(limit=args.limit)

        for notice in gazette_notices:
            record = process_gazette_notice(notice, dry_run=args.dry_run)
            if record:
                all_records.append(record)

    log(f"\nTotal records collected: {len(all_records)}")

    # Deduplicate by file_number
    seen: Dict[str, Dict] = {}
    for record in all_records:
        fn = record["file_number"]
        if fn not in seen:
            seen[fn] = record
        else:
            # Keep the one with more content
            existing_len = len(seen[fn].get("content_text", "") or "")
            new_len = len(record.get("content_text", "") or "")
            if new_len > existing_len:
                seen[fn] = record

    unique_records = list(seen.values())
    log(f"Unique records after dedup: {len(unique_records)}")

    # Filter to new/updated only (unless backfill)
    if not args.backfill:
        new_records = [r for r in unique_records if r["file_number"] not in existing_ids]
        log(f"New records to insert: {len(new_records)}")
    else:
        new_records = unique_records
        log(f"Backfill mode: processing all {len(new_records)} records")

    if args.limit:
        new_records = new_records[:args.limit]
        log(f"Limited to {args.limit} records")

    if not new_records:
        log("Nothing to process. Done.")
        return

    # Write to database
    success = 0
    failed = 0

    for i, record in enumerate(new_records):
        fn = record["file_number"]
        title = record.get("title", "")[:60]

        if args.dry_run:
            log(f"  [{i+1}/{len(new_records)}] [DRY RUN] {fn}: {title}")
            success += 1
            continue

        log(f"  [{i+1}/{len(new_records)}] {fn}: {title}")
        if upsert_ised_filing(record):
            success += 1
        else:
            failed += 1

        if (i + 1) % 10 == 0:
            time.sleep(RATE_LIMIT_SECONDS)

    log("=" * 60)
    log(f"Completed: {success} success, {failed} failed")
    log("=" * 60)


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ISED Regulatory Worker")
    parser.add_argument(
        "--backfill", action="store_true",
        help="Process all filings (not just new)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Don't write to database"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limit number of filings to process"
    )
    parser.add_argument(
        "--gazette-only", action="store_true",
        help="Only scrape Canada Gazette"
    )
    parser.add_argument(
        "--api-only", action="store_true",
        help="Only use ISED Drupal JSON API"
    )

    args = parser.parse_args()
    run_worker(args)
