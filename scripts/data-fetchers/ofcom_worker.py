#!/usr/bin/env python3
"""
Ofcom (UK) Regulatory Scraper

Tracks UK spectrum/satellite filings and consultations related to AST SpaceMobile
and its UK partner Vodafone from Ofcom, the UK communications regulator.

Sources:
  1. Ofcom space-and-satellites section pages
  2. Ofcom consultations-and-statements with keyword search
  3. Individual consultation/statement detail pages

Storage:
  fcc_filings table with filing_system='ICFS' and file_number prefix 'OFCOM-*'
  (CHECK constraint only allows ICFS/ECFS/ELS — do NOT use filing_system='OFCOM')

NOTE: Ofcom's website is behind Cloudflare WAF which blocks basic HTTP requests.
This worker uses the Wayback Machine as a fallback to access cached page content.
If direct access becomes available, the worker will prefer live pages.

Usage:
    python3 ofcom_worker.py                 # Full run
    python3 ofcom_worker.py --dry-run       # Preview without writing to DB
    python3 ofcom_worker.py --limit 10      # Process max N items
    python3 ofcom_worker.py --live-only     # Skip Wayback, only try live site
    python3 ofcom_worker.py --wayback-only  # Only use Wayback Machine
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

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

OFCOM_BASE = "https://www.ofcom.org.uk"

# Rate limiting
RATE_LIMIT_DELAY = 2.0
MAX_RETRIES = 3

# Valid filing_system values per fcc_filings CHECK constraint
VALID_FILING_SYSTEMS = {"ICFS", "ECFS", "ELS"}

# Search keywords for finding ASTS-relevant Ofcom documents
SEARCH_KEYWORDS = [
    "AST SpaceMobile",
    "AST & Science",
    "supplemental coverage from space",
    "direct to device",
    "D2D",
    "non-terrestrial network",
    "NTN",
    "satellite to cell",
    "satellite direct",
]

# Vodafone keywords (searched separately since Vodafone is a huge filer)
VODAFONE_SATELLITE_KEYWORDS = [
    "Vodafone satellite",
    "Vodafone direct to device",
    "Vodafone D2D",
]

# Known Ofcom pages related to ASTS/satellite D2D
# These are the high-value target pages discovered through research
KNOWN_PAGES = [
    {
        "url": "/spectrum/space-and-satellites/consultation-enabling-satellite-direct-to-device-services-in-mobile-spectrum-bands/",
        "title": "Consultation: Enabling satellite direct to device services in Mobile spectrum bands",
        "filing_type": "consultation",
    },
    {
        "url": "/spectrum/space-and-satellites/improving-mobile-connectivity-from-the-sky-and-space/",
        "title": "Statement: Improving mobile connectivity from the sky and space",
        "filing_type": "statement",
    },
    {
        "url": "/spectrum/space-and-satellites/standard-smartphones-to-receive-signal-from-space/",
        "title": "Standard smartphones to receive signal from space",
        "filing_type": "statement",
    },
    {
        "url": "/spectrum/space-and-satellites/satellite-filings/",
        "title": "Satellite filings",
        "filing_type": "reference",
    },
    {
        "url": "/spectrum/space-and-satellites/call-for-input-expanding-spectrum-access-for-satellite-gateways/",
        "title": "Consultation: Expanding spectrum access for satellite gateways",
        "filing_type": "consultation",
    },
    {
        "url": "/spectrum/space-and-satellites/kuiper-application-for-an-ngso-earth-station-network-licence/",
        "title": "Statement: Amazon Kuiper NGSO earth station network licence",
        "filing_type": "statement",
    },
    {
        "url": "/spectrum/space-and-satellites/kepler-communications-inc-application/",
        "title": "Statement: Kepler Communications Inc application",
        "filing_type": "statement",
    },
    {
        "url": "/spectrum/space-and-satellites/increasing-use-of-the-27-5-to-30-ghz-band/",
        "title": "Statement: Increasing use of the 27.5-30 GHz band",
        "filing_type": "statement",
    },
    {
        "url": "/spectrum/space-and-satellites/non-geo-fss/",
        "title": "Non-geostationary satellite earth station licensing",
        "filing_type": "reference",
    },
    {
        "url": "/spectrum/space-and-satellites/updates-to-procedures-for-the-management-of-satellite-filings/",
        "title": "Updates to procedures for management of satellite filings",
        "filing_type": "consultation",
    },
]

# Section pages to scrape for additional listings
SECTION_PAGES = [
    "/spectrum/space-and-satellites/",
]


# ============================================================================
# Logging
# ============================================================================

def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ============================================================================
# HTML Parser
# ============================================================================

class OfcomCardParser(HTMLParser):
    """Parse Ofcom listing pages to extract info-card items.

    Ofcom consultation/statement listing pages use this structure:
        <a href="/spectrum/.../">
            <div class="info-card">
                <h3 class="info-card-header">Title</h3>
                <div class="serach-date">  (note: typo is in Ofcom's HTML)
                    <p>Published: 25 March 2025</p>
                    <p>Last updated: 4 April 2025</p>
                </div>
                <p>Description text...</p>
            </div>
        </a>
    """

    def __init__(self):
        super().__init__()
        self.items: List[Dict] = []
        self._current_item: Optional[Dict] = None
        self._in_card = False
        self._in_header = False
        self._in_date_div = False
        self._in_date_p = False
        self._in_description_p = False
        self._current_link = ""
        self._depth = 0
        self._card_depth = 0
        self._text_buf = ""

    def handle_starttag(self, tag: str, attrs: list):
        attr_dict = dict(attrs)
        cls = attr_dict.get("class", "")

        if tag == "a" and not self._in_card:
            href = attr_dict.get("href", "")
            # Strip wayback prefix if present
            href = re.sub(r'.*/https://www\.ofcom\.org\.uk', '', href)
            if href.startswith("/"):
                self._current_link = href

        if tag == "div" and "info-card" in cls and "info-card-header" not in cls:
            self._in_card = True
            self._depth = 0
            self._current_item = {
                "url": self._current_link,
                "title": "",
                "published_date": "",
                "last_updated": "",
                "description": "",
            }

        if self._in_card:
            self._depth += 1

            if tag in ("h2", "h3") and "info-card-header" in cls:
                self._in_header = True
                self._text_buf = ""

            if tag == "div" and "serach-date" in cls:
                self._in_date_div = True

            if self._in_date_div and tag == "p":
                self._in_date_p = True
                self._text_buf = ""

            # Description paragraph (inside card but not in header or date div)
            if tag == "p" and not self._in_date_div and not self._in_header and self._in_card:
                if self._current_item and not self._current_item["description"]:
                    self._in_description_p = True
                    self._text_buf = ""

    def handle_endtag(self, tag: str):
        if self._in_card:
            if tag in ("h2", "h3") and self._in_header:
                self._in_header = False
                if self._current_item:
                    self._current_item["title"] = self._text_buf.strip()

            if tag == "p" and self._in_date_p:
                self._in_date_p = False
                text = self._text_buf.strip()
                if self._current_item:
                    if text.lower().startswith("published"):
                        date_str = re.sub(r'^published:?\s*', '', text, flags=re.I).strip()
                        self._current_item["published_date"] = date_str
                    elif text.lower().startswith("last updated"):
                        date_str = re.sub(r'^last\s+updated:?\s*', '', text, flags=re.I).strip()
                        self._current_item["last_updated"] = date_str
                    elif text.lower().startswith("consultation closes"):
                        date_str = re.sub(r'^consultation\s+closes:?\s*', '', text, flags=re.I).strip()
                        if self._current_item.get("metadata") is None:
                            self._current_item["metadata"] = {}
                    elif text.lower().startswith("status"):
                        status = re.sub(r'^status:?\s*', '', text, flags=re.I).strip()
                        self._current_item["consultation_status"] = status

            if tag == "div" and self._in_date_div:
                self._in_date_div = False

            if tag == "p" and self._in_description_p:
                self._in_description_p = False
                if self._current_item:
                    self._current_item["description"] = self._text_buf.strip()

            self._depth -= 1
            if tag == "div" and self._depth <= 0:
                self._in_card = False
                if self._current_item and self._current_item.get("title"):
                    self.items.append(self._current_item)
                self._current_item = None

    def handle_data(self, data: str):
        if self._in_header or self._in_date_p or self._in_description_p:
            self._text_buf += data


class OfcomDetailParser(HTMLParser):
    """Parse an individual Ofcom consultation/statement detail page.

    Structure:
        <h1 id="skipToContent">Title</h1>
        <div class="row row-cols-auto">
            Published: 25 March 2025
            Consultation closes: 20 May 2025
            Status: Open
        </div>
        <div class="rich-text-block">
            <p>Main content...</p>
        </div>
    """

    def __init__(self):
        super().__init__()
        self.title = ""
        self.published_date = ""
        self.close_date = ""
        self.status = ""
        self.content_paragraphs: List[str] = []
        self.pdf_links: List[str] = []
        self.tags: List[str] = []

        self._in_title = False
        self._in_richtext = False
        self._in_p = False
        self._in_tag_btn = False
        self._in_meta_row = False
        self._text_buf = ""
        self._richtext_depth = 0

    def handle_starttag(self, tag: str, attrs: list):
        attr_dict = dict(attrs)
        cls = attr_dict.get("class", "")
        href = attr_dict.get("href", "")

        if tag == "h1" and (attr_dict.get("id") == "skipToContent"
                             or attr_dict.get("data-epi-type") == "title"):
            self._in_title = True
            self._text_buf = ""

        if tag == "div" and "row-cols-auto" in cls:
            self._in_meta_row = True

        if tag == "div" and "rich-text-block" in cls:
            self._in_richtext = True
            self._richtext_depth = 0

        if self._in_richtext:
            self._richtext_depth += 1
            if tag == "p":
                self._in_p = True
                self._text_buf = ""

        if tag == "a" and "btn-tag" in cls:
            self._in_tag_btn = True
            self._text_buf = ""

        # Collect PDF links (handle .pdf and .pdf?v=... patterns)
        # Only collect PDFs from within the rich-text-block (actual document PDFs)
        if tag == "a" and ".pdf" in href and self._in_richtext:
            # Strip wayback prefix
            clean_href = re.sub(r'.*?/https://www\.ofcom\.org\.uk', '', href)
            if clean_href.startswith("/"):
                pdf_url = OFCOM_BASE + clean_href.split("?")[0]
                if pdf_url not in self.pdf_links:
                    self.pdf_links.append(pdf_url)
            elif "ofcom.org.uk" in href:
                pdf_url = re.sub(r'\?.*$', '', href)
                if pdf_url not in self.pdf_links:
                    self.pdf_links.append(pdf_url)

        if self._in_meta_row and tag == "div" and "col-12" in cls:
            self._text_buf = ""
            self._in_p = True  # Reuse _in_p for meta collection

    def handle_endtag(self, tag: str):
        if tag == "h1" and self._in_title:
            self._in_title = False
            self.title = re.sub(r'<[^>]+>', '', self._text_buf).strip()

        if self._in_meta_row:
            if tag == "div":
                text = self._text_buf.strip()
                if text.lower().startswith("published"):
                    self.published_date = re.sub(r'^published:?\s*', '', text, flags=re.I).strip()
                elif "closes" in text.lower():
                    self.close_date = re.sub(r'^consultation\s+closes:?\s*', '', text, flags=re.I).strip()
                elif text.lower().startswith("status"):
                    self.status = re.sub(r'^status:?\s*', '', text, flags=re.I).strip()
                self._in_p = False

        if self._in_richtext:
            if tag == "p" and self._in_p:
                self._in_p = False
                text = self._text_buf.strip()
                if text and len(text) > 10:
                    self.content_paragraphs.append(text)
            if tag == "div":
                self._richtext_depth -= 1
                if self._richtext_depth <= 0:
                    self._in_richtext = False

        if tag == "a" and self._in_tag_btn:
            self._in_tag_btn = False
            tag_text = self._text_buf.strip()
            if tag_text:
                self.tags.append(tag_text)

        if tag == "div" and self._in_meta_row:
            # Check if this is the closing of the meta row
            pass  # Let the col-12 handler deal with it

        if tag == "section" and self._in_meta_row:
            self._in_meta_row = False

    def handle_data(self, data: str):
        if self._in_title or self._in_p or self._in_tag_btn:
            self._text_buf += data
        if self._in_meta_row and not self._in_p:
            self._text_buf += data


# ============================================================================
# HTTP / Retry
# ============================================================================

def fetch_url(url: str, headers: Optional[Dict] = None, retries: int = MAX_RETRIES,
              timeout: int = 30) -> Optional[str]:
    """Fetch URL with retry + exponential backoff."""
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "identity",
    }
    if headers:
        default_headers.update(headers)

    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=default_headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code == 403:
                # Cloudflare block - don't retry
                log(f"  Blocked (403) on {url[:80]}...")
                return None
            elif e.code == 429:
                wait = 10 * (attempt + 1)
                log(f"  Rate limited (429). Waiting {wait}s...")
                time.sleep(wait)
            elif e.code >= 500:
                wait = 2 ** attempt
                log(f"  Server error ({e.code}). Retrying in {wait}s...")
                time.sleep(wait)
            else:
                log(f"  HTTP {e.code} on {url[:80]}")
                return None
        except (urllib.error.URLError, OSError) as e:
            last_error = e
            wait = 2 ** attempt
            log(f"  Network error: {e}. Retrying in {wait}s...")
            time.sleep(wait)

    if last_error:
        log(f"  Failed after {retries} retries: {last_error}")
    return None


def fetch_wayback(ofcom_path: str, retries: int = 2) -> Optional[str]:
    """Fetch a page from the Wayback Machine.

    Uses the CDX API to find the most recent snapshot, then fetches it.

    Args:
        ofcom_path: Path relative to ofcom.org.uk (e.g., "/spectrum/space-and-satellites/")

    Returns:
        HTML content or None
    """
    # Skip parameterized search URLs - Wayback rarely caches these
    if "?" in ofcom_path:
        log(f"  Skipping Wayback for parameterized URL: {ofcom_path[:60]}")
        return None

    full_url = f"www.ofcom.org.uk{ofcom_path}"

    # Step 1: Find most recent snapshot via CDX API
    cdx_url = (
        f"https://web.archive.org/cdx/search/cdx?"
        f"url={urllib.parse.quote(full_url, safe='')}"
        f"&output=json&limit=1&fl=timestamp,original,statuscode"
        f"&filter=statuscode:200&sort=reverse"
    )

    cdx_content = fetch_url(cdx_url, retries=retries, timeout=20)
    if not cdx_content:
        return None

    try:
        rows = json.loads(cdx_content)
        if len(rows) < 2:  # First row is header
            log(f"  No Wayback snapshot for {ofcom_path}")
            return None
        timestamp = rows[1][0]
        original = rows[1][1]
    except (json.JSONDecodeError, IndexError, KeyError):
        return None

    # Step 2: Fetch the cached page
    wayback_url = f"https://web.archive.org/web/{timestamp}/{original}"
    log(f"  Wayback: {timestamp[:8]} snapshot")
    content = fetch_url(wayback_url, retries=retries, timeout=30)
    return content


def fetch_ofcom_page(path: str, use_live: bool = True, use_wayback: bool = True) -> Optional[str]:
    """Fetch an Ofcom page, trying live site first, then Wayback Machine fallback.

    Args:
        path: URL path relative to ofcom.org.uk
        use_live: Whether to attempt direct fetch
        use_wayback: Whether to fall back to Wayback Machine

    Returns:
        HTML content or None
    """
    # Ensure path starts with /
    if not path.startswith("/"):
        path = "/" + path

    # Try live site first
    if use_live:
        live_url = f"{OFCOM_BASE}{path}"
        content = fetch_url(live_url, retries=1)
        if content and len(content) > 1000:
            log(f"  Live fetch OK: {path[:60]}")
            return content

    # Fallback to Wayback Machine
    if use_wayback:
        content = fetch_wayback(path)
        if content and len(content) > 1000:
            return content

    log(f"  Could not fetch: {path[:60]}")
    return None


def discover_wayback_pages(prefix: str) -> List[str]:
    """Use Wayback CDX API to discover all unique Ofcom pages under a prefix.

    Returns list of URL paths (e.g., ["/spectrum/space-and-satellites/foo/"]).
    """
    cdx_url = (
        f"https://web.archive.org/cdx/search/cdx?"
        f"url=www.ofcom.org.uk{urllib.parse.quote(prefix, safe='/')}*"
        f"&output=json&fl=original&filter=statuscode:200"
        f"&collapse=urlkey&limit=100"
    )
    content = fetch_url(cdx_url, retries=2, timeout=20)
    if not content:
        return []

    try:
        rows = json.loads(content)
        paths = set()
        for row in rows[1:]:  # Skip header
            original = row[0]
            # Extract path from full URL
            path = re.sub(r'https?://www\.ofcom\.org\.uk', '', original)
            if path and not path.endswith(('.css', '.js', '.png', '.jpg', '.svg', '.gif', '.ico')):
                paths.add(path)
        return sorted(paths)
    except (json.JSONDecodeError, IndexError):
        return []


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
    """Get all existing OFCOM file_numbers from fcc_filings table."""
    try:
        result = supabase_request(
            "GET",
            "fcc_filings?file_number=like.OFCOM-*&select=file_number"
        )
        return {r["file_number"] for r in result if r.get("file_number")}
    except Exception as e:
        log(f"Error fetching existing file_numbers: {e}")
        return set()


def upsert_filing(record: Dict) -> bool:
    """Upsert filing into fcc_filings table."""
    if record.get("filing_system") not in VALID_FILING_SYSTEMS:
        log(f"  ERROR: Invalid filing_system '{record.get('filing_system')}' for {record.get('file_number')} — must be one of {VALID_FILING_SYSTEMS}")
        return False
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
        log(f"  Upsert error: {e.code}")
        return False
    except Exception as e:
        log(f"  Upsert error: {e}")
        return False


# ============================================================================
# Parsing and Processing
# ============================================================================

def normalize_path(url_path: str) -> str:
    """Normalize an Ofcom URL path for consistent comparison and hashing."""
    # Strip trailing slash, lowercase
    normalized = url_path.rstrip("/").lower()
    # Remove common prefixes for shorter hashes
    normalized = re.sub(r'^/spectrum/space-and-satellites/', '', normalized)
    normalized = re.sub(r'^/consultations-and-statements/', '', normalized)
    normalized = re.sub(r'^/', '', normalized)
    return normalized


def generate_file_number(url_path: str) -> str:
    """Generate a deterministic file_number from an Ofcom URL path.

    Uses OFCOM-{short_hash} format for uniqueness.
    """
    normalized = normalize_path(url_path)
    hash_val = hashlib.sha256(normalized.encode()).hexdigest()[:12]
    return f"OFCOM-{hash_val}"


def parse_date(date_str: str) -> Optional[str]:
    """Parse Ofcom date strings like '25 March 2025' to ISO format."""
    if not date_str:
        return None

    date_str = date_str.strip()

    # Try common formats
    formats = [
        "%d %B %Y",      # 25 March 2025
        "%d %b %Y",      # 25 Mar 2025
        "%B %d, %Y",     # March 25, 2025
        "%Y-%m-%d",      # 2025-03-25
        "%d/%m/%Y",      # 25/03/2025
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


def determine_filing_type(title: str) -> str:
    """Determine filing type from title prefix."""
    title_lower = title.lower().strip()
    if title_lower.startswith("consultation"):
        return "consultation"
    elif title_lower.startswith("statement"):
        return "statement"
    elif title_lower.startswith("decision"):
        return "decision"
    elif title_lower.startswith("call for input"):
        return "consultation"
    elif title_lower.startswith("discussion"):
        return "consultation"
    else:
        return "reference"


def is_asts_relevant(text: str) -> bool:
    """Check if text contains ASTS-relevant keywords."""
    text_lower = text.lower()
    keywords = [
        "ast spacemobile", "ast & science",
        "direct to device", "direct-to-device", "d2d",
        "supplemental coverage from space",
        "non-terrestrial network", "non terrestrial network", "ntn",
        "satellite to cell", "satellite-to-cell",
        "satellite direct",
        "mobile spectrum bands",
        "satellite earth station",
        "ngso", "non-geostationary",
        "vodafone",
    ]
    return any(kw in text_lower for kw in keywords)


def parse_listing_page(html: str) -> List[Dict]:
    """Parse an Ofcom listing page for consultation/statement cards."""
    parser = OfcomCardParser()
    try:
        parser.feed(html)
    except Exception as e:
        log(f"  Parse error: {e}")
    return parser.items


def parse_detail_page(html: str) -> Dict:
    """Parse an individual Ofcom detail page."""
    parser = OfcomDetailParser()
    try:
        parser.feed(html)
    except Exception as e:
        log(f"  Detail parse error: {e}")

    return {
        "title": parser.title,
        "published_date": parser.published_date,
        "close_date": parser.close_date,
        "status": parser.status,
        "content_text": "\n\n".join(parser.content_paragraphs),
        "pdf_links": parser.pdf_links,
        "tags": parser.tags,
    }


def build_filing_record(item: Dict, detail: Optional[Dict] = None) -> Dict:
    """Build a fcc_filings record from parsed Ofcom data."""
    url_path = item.get("url", "")
    title = item.get("title", "")

    # Use detail page data if available, but prefer the listing title
    # (because detail page titles on Wayback may reflect updated status,
    # e.g., a consultation page might now show "Statement:" after closure)
    if not title and detail and detail.get("title"):
        title = detail["title"]

    published_date = item.get("published_date", "")
    if detail and detail.get("published_date"):
        published_date = detail["published_date"]

    content_text = item.get("description", "")
    if detail and detail.get("content_text"):
        content_text = detail["content_text"]

    filed_date = parse_date(published_date)

    # Use hint from known pages if available, otherwise derive from title
    filing_type = item.get("filing_type_hint", "") or determine_filing_type(title)
    file_number = generate_file_number(url_path)

    source_url = f"{OFCOM_BASE}{url_path}" if url_path.startswith("/") else url_path

    metadata = {
        "source": "ofcom",
        "section": "space-and-satellites",
    }
    if item.get("last_updated"):
        metadata["last_updated"] = item["last_updated"]
    if item.get("consultation_status"):
        metadata["consultation_status"] = item["consultation_status"]
    if detail:
        if detail.get("close_date"):
            metadata["close_date"] = detail["close_date"]
        if detail.get("status"):
            metadata["consultation_status"] = detail["status"]
        if detail.get("pdf_links"):
            metadata["pdf_links"] = detail["pdf_links"]
        if detail.get("tags"):
            metadata["tags"] = detail["tags"]

    # Determine filer based on content
    filer_name = "Ofcom"
    combined_text = (title + " " + content_text).lower()
    if "ast spacemobile" in combined_text or "ast & science" in combined_text:
        filer_name = "Ofcom (re: AST SpaceMobile)"
    elif "vodafone" in combined_text:
        filer_name = "Ofcom (re: Vodafone)"

    # Build attachment URLs from PDFs
    attachment_urls = []
    if detail and detail.get("pdf_links"):
        attachment_urls = detail["pdf_links"][:20]  # Cap at 20

    record = {
        "filing_system": "ICFS",
        "file_number": file_number,
        "filing_type": filing_type,
        "title": title[:500] if title else "Untitled Ofcom Document",
        "description": item.get("description", "")[:2000],
        "filer_name": filer_name,
        "filed_date": filed_date,
        "application_status": metadata.get("consultation_status", "published"),
        "content_text": content_text[:50000] if content_text else None,
        "source_url": source_url,
        "attachment_urls": json.dumps(attachment_urls) if attachment_urls else None,
        "metadata": json.dumps(metadata),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
    }

    return record


# ============================================================================
# Discovery: Find relevant Ofcom pages
# ============================================================================

def discover_from_section_pages(use_live: bool, use_wayback: bool) -> List[Dict]:
    """Scrape Ofcom section listing pages for satellite/spectrum items."""
    all_items = []

    for section_path in SECTION_PAGES:
        log(f"Scraping section: {section_path}")
        html = fetch_ofcom_page(section_path, use_live=use_live, use_wayback=use_wayback)
        if not html:
            log(f"  Could not fetch section page")
            continue

        items = parse_listing_page(html)
        log(f"  Found {len(items)} items on section page")

        # Filter to satellite/D2D relevant items
        relevant = [
            item for item in items
            if is_asts_relevant(item.get("title", "") + " " + item.get("description", ""))
        ]
        log(f"  {len(relevant)} relevant to ASTS/D2D")
        all_items.extend(relevant)
        time.sleep(RATE_LIMIT_DELAY)

    return all_items


def discover_from_consultations_search(use_live: bool, use_wayback: bool) -> List[Dict]:
    """Search the consultations-and-statements page with keyword filters.

    Ofcom's consultations page accepts URL params:
      ?query=<search term>&SelectedTopic=67891&SortBy=Newest
    Topic 67891 = Spectrum
    """
    all_items = []
    seen_urls = set()

    search_terms = [
        "satellite direct to device",
        "supplemental coverage",
        "non-terrestrial network",
        "satellite earth station",
    ]

    for term in search_terms:
        encoded_term = urllib.parse.quote(term)
        search_path = f"/consultations-and-statements/?query={encoded_term}&SelectedTopic=67891&SortBy=Newest"

        log(f"Searching consultations: '{term}'")
        html = fetch_ofcom_page(search_path, use_live=use_live, use_wayback=use_wayback)
        if not html:
            continue

        items = parse_listing_page(html)
        log(f"  Found {len(items)} results")

        for item in items:
            url = item.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_items.append(item)

        time.sleep(RATE_LIMIT_DELAY)

    return all_items


def discover_from_known_pages() -> List[Dict]:
    """Generate items from the hardcoded known pages list."""
    items = []
    for page in KNOWN_PAGES:
        items.append({
            "url": page["url"],
            "title": page["title"],
            "published_date": "",
            "last_updated": "",
            "description": "",
            "filing_type_hint": page["filing_type"],
        })
    return items


def discover_from_wayback_cdx() -> List[Dict]:
    """Use Wayback Machine CDX API to discover Ofcom space/satellite pages.

    This finds all unique URLs under the space-and-satellites section
    that Wayback has indexed, giving us pages we might not find through
    the section listing alone.
    """
    log("Discovering pages via Wayback CDX wildcard search...")
    paths = discover_wayback_pages("/spectrum/space-and-satellites/")
    log(f"  Found {len(paths)} unique URLs in Wayback")

    items = []
    for path in paths:
        # Skip non-page URLs (PDFs, assets, etc.)
        if any(path.endswith(ext) for ext in ['.pdf', '.css', '.js', '.png', '.jpg', '.svg']):
            continue
        # Skip the section index itself (we scrape it separately)
        if path.rstrip("/") == "/spectrum/space-and-satellites":
            continue
        # Must end with / (Ofcom page pattern) or be a clean path
        if not path.endswith("/") and "." in path.split("/")[-1]:
            continue

        # Derive a title from the URL path
        slug = path.rstrip("/").split("/")[-1]
        title = slug.replace("-", " ").title() if slug else ""

        items.append({
            "url": path,
            "title": title,
            "published_date": "",
            "last_updated": "",
            "description": "",
        })

    return items


# ============================================================================
# Main Worker
# ============================================================================

def run_worker(dry_run: bool = False, limit: int = 0,
               use_live: bool = True, use_wayback: bool = True):
    """Main worker function."""
    log("=" * 60)
    log("Ofcom Worker Started")
    log("=" * 60)
    log(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    log(f"Sources: live={'yes' if use_live else 'no'} wayback={'yes' if use_wayback else 'no'}")

    if not dry_run and (not SUPABASE_URL or not SUPABASE_SERVICE_KEY):
        log("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    # Get existing OFCOM records
    existing = set()
    if not dry_run:
        existing = get_existing_file_numbers()
        log(f"Found {len(existing)} existing OFCOM records")

    # ---- Phase 1: Discover pages ----
    log("")
    log("Phase 1: Discovering Ofcom pages")
    log("-" * 40)

    all_items: List[Dict] = []
    seen_normalized: Set[str] = set()  # Normalized paths for dedup

    def add_item(item: Dict) -> bool:
        """Add item if its normalized path hasn't been seen."""
        url = item.get("url", "")
        if not url:
            return False
        norm = normalize_path(url)
        if norm in seen_normalized:
            return False
        seen_normalized.add(norm)
        all_items.append(item)
        return True

    # 1a. Known pages (always included)
    known = discover_from_known_pages()
    for item in known:
        add_item(item)
    log(f"Known pages: {len(known)}")

    # 1b. Section page scraping
    section_items = discover_from_section_pages(use_live, use_wayback)
    new_from_section = sum(1 for item in section_items if add_item(item))
    log(f"Section pages: {new_from_section} new items")

    # 1c. Wayback CDX wildcard discovery
    if use_wayback:
        cdx_items = discover_from_wayback_cdx()
        new_from_cdx = sum(1 for item in cdx_items if add_item(item))
        log(f"Wayback CDX discovery: {new_from_cdx} new items")

    # 1d. Consultations search (live only - Wayback doesn't cache search results)
    if use_live:
        search_items = discover_from_consultations_search(use_live, use_wayback=False)
        new_from_search = sum(1 for item in search_items if add_item(item))
        log(f"Search results: {new_from_search} new items")

    log(f"Total unique pages discovered: {len(all_items)}")

    # Apply limit
    if limit > 0 and len(all_items) > limit:
        all_items = all_items[:limit]
        log(f"Limited to {limit} items")

    # ---- Phase 2: Fetch detail pages and build records ----
    log("")
    log("Phase 2: Fetching detail pages and building records")
    log("-" * 40)

    records: List[Dict] = []
    skipped_existing = 0
    skipped_irrelevant = 0

    for i, item in enumerate(all_items):
        url_path = item.get("url", "")
        if not url_path:
            continue

        file_number = generate_file_number(url_path)

        # Skip if already in DB
        if file_number in existing:
            skipped_existing += 1
            continue

        log(f"[{i+1}/{len(all_items)}] {item.get('title', url_path)[:70]}")

        # Fetch detail page for richer content
        detail = None
        if url_path.startswith("/"):
            detail_html = fetch_ofcom_page(url_path, use_live=use_live, use_wayback=use_wayback)
            if detail_html:
                detail = parse_detail_page(detail_html)
                log(f"  Detail: {len(detail.get('content_text', ''))} chars, "
                    f"{len(detail.get('pdf_links', []))} PDFs")
            time.sleep(RATE_LIMIT_DELAY)

        record = build_filing_record(item, detail)

        # Final relevance check on full content
        full_text = (record.get("title", "") + " " +
                     record.get("description", "") + " " +
                     (record.get("content_text", "") or ""))
        if not is_asts_relevant(full_text):
            # Still include items from known pages
            if item.get("filing_type_hint") or item.get("url", "") in [p["url"] for p in KNOWN_PAGES]:
                pass  # Keep known pages regardless
            else:
                skipped_irrelevant += 1
                log(f"  Skipped: not ASTS-relevant")
                continue

        records.append(record)

    log(f"Records to upsert: {len(records)}")
    log(f"Skipped (existing): {skipped_existing}")
    log(f"Skipped (irrelevant): {skipped_irrelevant}")

    # ---- Phase 3: Upsert to Supabase ----
    log("")
    log("Phase 3: Upserting to Supabase")
    log("-" * 40)

    if dry_run:
        log("DRY RUN - printing records instead of upserting")
        for record in records:
            log(f"  [{record['file_number']}] {record['title'][:70]}")
            log(f"    type={record['filing_type']} date={record['filed_date']} "
                f"filer={record['filer_name']}")
            log(f"    url={record['source_url']}")
            if record.get("content_text"):
                log(f"    content={len(record['content_text'])} chars")
            log("")
        log(f"Would upsert {len(records)} records")
        return

    success = 0
    failed = 0
    for record in records:
        if upsert_filing(record):
            success += 1
            log(f"  Upserted: {record['file_number']} - {record['title'][:60]}")
        else:
            failed += 1
            log(f"  Failed: {record['file_number']}")

    log("")
    log("=" * 60)
    log(f"Completed: {success} upserted, {failed} failed, "
        f"{skipped_existing} skipped (existing)")
    log("=" * 60)


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Ofcom UK regulatory scraper for ASTS-related satellite filings"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview results without writing to database"
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Maximum number of items to process (0 = unlimited)"
    )
    parser.add_argument(
        "--live-only", action="store_true",
        help="Only attempt direct site fetch, skip Wayback Machine"
    )
    parser.add_argument(
        "--wayback-only", action="store_true",
        help="Only use Wayback Machine, skip direct site fetch"
    )

    args = parser.parse_args()

    use_live = not args.wayback_only
    use_wayback = not args.live_only

    if args.live_only and args.wayback_only:
        log("ERROR: Cannot use both --live-only and --wayback-only")
        sys.exit(1)

    run_worker(
        dry_run=args.dry_run,
        limit=args.limit,
        use_live=use_live,
        use_wayback=use_wayback,
    )


if __name__ == "__main__":
    main()
