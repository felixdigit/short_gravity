#!/usr/bin/env python3
"""
Patent Worker v2 - Unified Patent Data Pipeline

Fetches, enriches, and maintains ASTS patent portfolio.
Designed for cron: run daily to catch new filings.

Stages:
1. DISCOVERY - Find new patents from PatentsView + EPO OPS
2. CLAIMS - Fetch claims for patents missing them
3. ENRICHMENT - Scrape Google Patents for missing titles/abstracts/figures
4. CLEANUP - Dedupe B1/B2, build RAG fields
5. REPORT - Log coverage stats

Usage:
    python3 patent_worker_v2.py              # Incremental update (default)
    python3 patent_worker_v2.py --full       # Full refresh of all data
    python3 patent_worker_v2.py --dry-run    # Preview changes only
    python3 patent_worker_v2.py --stage 2    # Run specific stage only

Environment:
    PATENTSVIEW_API_KEY - PatentsView API key
    EPO_CONSUMER_KEY, EPO_CONSUMER_SECRET - EPO OPS credentials
    SUPABASE_URL, SUPABASE_SERVICE_KEY - Database
"""

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from collections import defaultdict

# Optional: Playwright for Google Patents scraping
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# =============================================================================
# CONFIGURATION
# =============================================================================

# PatentsView
PATENTSVIEW_API_KEY = os.environ.get("PATENTSVIEW_API_KEY", "")
PATENTSVIEW_BASE = "https://search.patentsview.org/api/v1"
PATENTSVIEW_ASSIGNEE_IDS = {
    "AST & Science, LLC": "cacf699f-e783-4e35-840c-d1bcea17a2d4",
    "AST&Defense, LLC": "3e2e5dcb-b36d-4ed4-b211-292bf19edd97",
}

# EPO OPS
EPO_CONSUMER_KEY = os.environ.get("EPO_CONSUMER_KEY", "")
EPO_CONSUMER_SECRET = os.environ.get("EPO_CONSUMER_SECRET", "")
EPO_AUTH_URL = "https://ops.epo.org/3.2/auth/accesstoken"
EPO_API_BASE = "https://ops.epo.org/3.2/rest-services"

# Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Rate limits
PATENTSVIEW_DELAY = 1.5  # 45 req/min
EPO_DELAY = 3.0  # 20 req/min
GOOGLE_PATENTS_DELAY = 2.5


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# =============================================================================
# HTTP UTILITIES
# =============================================================================

def http_request(url: str, method: str = "GET", headers: Dict = None,
                 data: Any = None, timeout: int = 60) -> bytes:
    """Make HTTP request and return response bytes."""
    headers = headers or {}
    body = None
    if data:
        if isinstance(data, dict):
            body = json.dumps(data).encode()
            headers.setdefault("Content-Type", "application/json")
        elif isinstance(data, str):
            body = data.encode()
        else:
            body = data

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_json(url: str, method: str = "GET", headers: Dict = None,
              data: Any = None) -> Dict:
    """Make HTTP request and return JSON."""
    resp = http_request(url, method, headers, data)
    return json.loads(resp.decode())


# =============================================================================
# SUPABASE
# =============================================================================

def supabase_request(method: str, endpoint: str, data: Any = None) -> Any:
    """Make Supabase REST API request."""
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    try:
        resp = http_request(url, method, headers, data)
        return json.loads(resp.decode()) if resp else []
    except urllib.error.HTTPError as e:
        error = e.read().decode() if e.fp else ""
        raise Exception(f"Supabase {e.code}: {error[:200]}")


def get_existing_patents() -> Set[str]:
    """Get all patent numbers currently in database."""
    patents = supabase_request("GET", "patents?select=patent_number&limit=1000")
    return {p["patent_number"] for p in patents}


def get_patents_missing_claims() -> List[str]:
    """Get patents that don't have claims in patent_claims table."""
    # Get all patents
    patents = supabase_request("GET", "patents?select=patent_number&limit=1000")
    all_patents = {p["patent_number"] for p in patents}

    # Get patents with claims
    claims = supabase_request("GET", "patent_claims?select=patent_number&limit=5000")
    with_claims = {c["patent_number"] for c in claims}

    # Return difference
    return list(all_patents - with_claims)


def get_patents_missing_data() -> List[Dict]:
    """Get patents missing title, abstract, or figures."""
    # Patents with NULL or empty title
    missing = supabase_request(
        "GET",
        "patents?select=patent_number,title,abstract,figure_urls&or=(title.is.null,abstract.is.null)&limit=500"
    )
    return missing


# =============================================================================
# PATENTSVIEW API
# =============================================================================

def patentsview_request(endpoint: str, query: Dict, fields: List[str],
                        size: int = 100) -> Dict:
    """Make PatentsView API request."""
    if not PATENTSVIEW_API_KEY:
        return {"error": "PATENTSVIEW_API_KEY not set"}

    url = f"{PATENTSVIEW_BASE}/{endpoint}/"
    headers = {
        "X-Api-Key": PATENTSVIEW_API_KEY,
        "Content-Type": "application/json",
    }
    body = {"q": query, "f": fields, "o": {"size": size}}

    try:
        return http_json(url, "POST", headers, body)
    except Exception as e:
        return {"error": str(e)}


def patentsview_fetch_patents() -> List[Dict]:
    """Fetch all AST patents from PatentsView."""
    all_patents = []

    for assignee_name, assignee_id in PATENTSVIEW_ASSIGNEE_IDS.items():
        query = {"_eq": {"assignees.assignee_id": assignee_id}}
        fields = [
            "patent_id", "patent_title", "patent_date", "patent_type",
            "patent_abstract", "assignees", "inventors", "cpc_current"
        ]

        result = patentsview_request("patent", query, fields, size=200)
        if result.get("error"):
            log(f"  PatentsView error for {assignee_name}: {result['error']}")
            continue

        patents = result.get("patents", [])
        for p in patents:
            # Convert to our format
            patent_id = p["patent_id"]
            all_patents.append({
                "patent_number": f"US{patent_id}B2",  # Assume B2 for modern patents
                "patent_id": patent_id,
                "title": p.get("patent_title"),
                "abstract": p.get("patent_abstract"),
                "grant_date": p.get("patent_date"),
                "assignee": assignee_name,
                "status": "granted",
                "source": "patentsview",
            })

        time.sleep(PATENTSVIEW_DELAY)

    return all_patents


def patentsview_fetch_claims(patent_id: str) -> List[Dict]:
    """Fetch claims for a single patent from PatentsView."""
    query = {"patent_id": patent_id}
    fields = ["patent_id", "claim_sequence", "claim_text"]

    result = patentsview_request("g_claim", query, fields, size=200)
    if result.get("error"):
        return []

    return result.get("g_claims", [])


# =============================================================================
# EPO OPS API
# =============================================================================

_epo_token = None
_epo_token_expires = 0


def epo_get_token() -> str:
    """Get EPO OAuth token (cached)."""
    global _epo_token, _epo_token_expires

    if _epo_token and time.time() < _epo_token_expires:
        return _epo_token

    if not EPO_CONSUMER_KEY or not EPO_CONSUMER_SECRET:
        raise ValueError("EPO credentials not set")

    auth = base64.b64encode(f"{EPO_CONSUMER_KEY}:{EPO_CONSUMER_SECRET}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    resp = http_request(EPO_AUTH_URL, "POST", headers, "grant_type=client_credentials")
    data = json.loads(resp.decode())

    _epo_token = data["access_token"]
    _epo_token_expires = time.time() + int(data.get("expires_in", 1200)) - 60

    return _epo_token


def epo_search(query: str) -> List[Dict]:
    """Search EPO OPS for patents."""
    token = epo_get_token()
    url = f"{EPO_API_BASE}/published-data/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    params = urllib.parse.urlencode({"q": query, "Range": "1-100"})

    try:
        resp = http_request(f"{url}?{params}", "GET", headers)
        return json.loads(resp.decode())
    except Exception as e:
        log(f"  EPO search error: {e}")
        return {}


def epo_fetch_family_patents() -> List[Dict]:
    """Fetch ASTS patent families from EPO OPS."""
    patents = []

    # Search for AST SpaceMobile patents
    queries = [
        'pa="AST & Science"',
        'pa="AST SpaceMobile"',
    ]

    for query in queries:
        result = epo_search(query)
        # Parse EPO response format
        # (EPO returns complex XML/JSON - simplified here)
        # In practice, need to parse exchange-documents
        time.sleep(EPO_DELAY)

    return patents


# =============================================================================
# GOOGLE PATENTS SCRAPER
# =============================================================================

def scrape_google_patent(page, patent_number: str) -> Dict:
    """Scrape patent data from Google Patents."""
    url = f"https://patents.google.com/patent/{patent_number}/en"

    try:
        page.goto(url, wait_until="networkidle", timeout=30000)

        if "404" in page.title().lower() or "not found" in page.title().lower():
            return {"error": "Not found"}

        # Extract data via JavaScript
        data = page.evaluate("""
        () => {
            const result = {title: null, abstract: null, images: []};

            // Title
            const titleEl = document.querySelector('h1[itemprop="title"]');
            if (titleEl) result.title = titleEl.textContent.trim();

            // Abstract
            const abstractEl = document.querySelector('section[itemprop="abstract"] div.abstract');
            if (abstractEl) {
                const clone = abstractEl.cloneNode(true);
                clone.querySelectorAll('.google-src-text').forEach(el => el.remove());
                result.abstract = clone.textContent.trim().replace(/\\s+/g, ' ');
            }

            // Images
            const imgs = document.querySelectorAll('img[src*="patentimages.storage.googleapis"]');
            result.images = [...new Set(Array.from(imgs).map(i => i.src))].slice(0, 30);

            return result;
        }
        """)

        return data

    except Exception as e:
        return {"error": str(e)}


def enrich_patents_google(patents: List[Dict], dry_run: bool = False) -> int:
    """Enrich patents with data from Google Patents."""
    if not PLAYWRIGHT_AVAILABLE:
        log("  Playwright not available, skipping Google Patents enrichment")
        return 0

    if not patents:
        return 0

    updated = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for i, patent in enumerate(patents):
            pn = patent["patent_number"]
            log(f"  [{i+1}/{len(patents)}] Enriching {pn}")

            data = scrape_google_patent(page, pn)

            if data.get("error"):
                log(f"    -> Error: {data['error']}")
                time.sleep(GOOGLE_PATENTS_DELAY)
                continue

            # Build update
            updates = {}
            if data.get("title") and not patent.get("title"):
                updates["title"] = data["title"]
            if data.get("abstract") and not patent.get("abstract"):
                updates["abstract"] = data["abstract"]
            if data.get("images"):
                updates["figure_urls"] = data["images"]

            if updates and not dry_run:
                supabase_request("PATCH", f"patents?patent_number=eq.{pn}", updates)
                updated += 1
                log(f"    -> Updated: {list(updates.keys())}")
            elif updates:
                log(f"    -> Would update: {list(updates.keys())}")

            time.sleep(GOOGLE_PATENTS_DELAY)

        browser.close()

    return updated


# =============================================================================
# CLAIMS PROCESSING
# =============================================================================

def parse_claim_type(text: str) -> str:
    """Determine if claim is independent or dependent."""
    if not text:
        return "independent"

    text_lower = text.lower().strip()
    patterns = [
        r'^the .* of claim \d+',
        r'^a .* according to claim \d+',
        r'as claimed in claim \d+',
        r'as recited in claim \d+',
    ]
    for pattern in patterns:
        if re.search(pattern, text_lower):
            return "dependent"
    return "independent"


def parse_depends_on(text: str) -> Optional[List[int]]:
    """Extract claim numbers this claim depends on."""
    if not text:
        return None

    matches = re.findall(r'claim[s]?\s+(\d+)', text.lower())
    if matches:
        return [int(m) for m in matches[:5]]
    return None


def insert_claims(patent_number: str, claims: List[Dict], dry_run: bool = False) -> int:
    """Insert claims into patent_claims table."""
    inserted = 0

    for claim in claims:
        claim_num = claim.get("claim_sequence") or claim.get("claim_number")
        claim_text = claim.get("claim_text", "")

        if not claim_num or not claim_text:
            continue

        data = {
            "patent_number": patent_number,
            "claim_number": int(claim_num),
            "claim_text": claim_text,
            "claim_type": parse_claim_type(claim_text),
        }

        depends = parse_depends_on(claim_text)
        if depends:
            data["depends_on"] = depends

        if not dry_run:
            try:
                supabase_request("POST", "patent_claims", data)
                inserted += 1
            except Exception as e:
                if "duplicate" not in str(e).lower():
                    log(f"    Error inserting claim: {e}")

    return inserted


# =============================================================================
# DEDUPLICATION & RAG
# =============================================================================

def dedupe_b1_b2(dry_run: bool = False) -> int:
    """Remove B1 patents when B2 exists."""
    patents = supabase_request("GET", "patents?select=patent_number&limit=1000")

    # Group by base number
    by_base = defaultdict(list)
    for p in patents:
        pn = p["patent_number"]
        match = re.match(r'^(US\d+)(B\d)$', pn)
        if match:
            by_base[match.group(1)].append(pn)

    # Find B1/B2 pairs
    deleted = 0
    for base, versions in by_base.items():
        b1 = f"{base}B1"
        b2 = f"{base}B2"
        if b1 in versions and b2 in versions:
            if not dry_run:
                # Delete B1 claims first
                supabase_request("DELETE", f"patent_claims?patent_number=eq.{b1}")
                # Delete B1 patent
                supabase_request("DELETE", f"patents?patent_number=eq.{b1}")
            deleted += 1
            log(f"  {'Would delete' if dry_run else 'Deleted'} {b1} (keeping {b2})")

    return deleted


def build_rag_fields(dry_run: bool = False) -> int:
    """Build content_text and claims_text for RAG."""
    patents = supabase_request(
        "GET",
        "patents?select=patent_number,title,abstract&limit=1000"
    )

    updated = 0
    for patent in patents:
        pn = patent["patent_number"]

        # Get claims for this patent
        claims = supabase_request(
            "GET",
            f"patent_claims?patent_number=eq.{pn}&select=claim_number,claim_text&order=claim_number"
        )

        # Build claims_text
        claims_text = "\n\n".join(
            f"{c['claim_number']}. {c['claim_text']}" for c in claims
        ) if claims else ""

        # Build content_text
        parts = []
        if patent.get("title"):
            parts.append(f"TITLE: {patent['title']}")
        if patent.get("abstract"):
            parts.append(f"ABSTRACT: {patent['abstract']}")
        if claims_text:
            parts.append(f"CLAIMS:\n{claims_text}")

        content_text = "\n\n".join(parts)
        content_hash = hashlib.sha256(content_text.encode()).hexdigest() if content_text else None

        if content_text and not dry_run:
            supabase_request("PATCH", f"patents?patent_number=eq.{pn}", {
                "claims_text": claims_text if claims_text else None,
                "content_text": content_text,
                "content_hash": content_hash,
            })
            updated += 1

    return updated


# =============================================================================
# MAIN WORKER
# =============================================================================

class PatentWorker:
    def __init__(self, dry_run: bool = False, full_refresh: bool = False):
        self.dry_run = dry_run
        self.full_refresh = full_refresh
        self.stats = {
            "new_patents": 0,
            "new_claims": 0,
            "enriched": 0,
            "deduped": 0,
            "rag_built": 0,
        }

    def run(self, stage: int = None):
        """Run all stages or a specific stage."""
        log("=" * 60)
        log("PATENT WORKER V2")
        log("=" * 60)
        log(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        log(f"Refresh: {'FULL' if self.full_refresh else 'INCREMENTAL'}")
        log("")

        stages = [
            (1, "DISCOVERY", self.stage_discovery),
            (2, "CLAIMS", self.stage_claims),
            (3, "ENRICHMENT", self.stage_enrichment),
            (4, "CLEANUP", self.stage_cleanup),
            (5, "REPORT", self.stage_report),
        ]

        for num, name, func in stages:
            if stage and num != stage:
                continue
            log(f"STAGE {num}: {name}")
            log("-" * 40)
            func()
            log("")

    def stage_discovery(self):
        """Find and insert new patents."""
        existing = get_existing_patents()
        log(f"Existing patents in DB: {len(existing)}")

        # Fetch from PatentsView
        log("Fetching from PatentsView...")
        pv_patents = patentsview_fetch_patents()
        log(f"  Found {len(pv_patents)} patents from PatentsView")

        # Filter to new only (unless full refresh)
        if not self.full_refresh:
            pv_patents = [p for p in pv_patents if p["patent_number"] not in existing]

        log(f"  New patents to add: {len(pv_patents)}")

        # Insert new patents
        for patent in pv_patents:
            if not self.dry_run:
                try:
                    supabase_request("POST", "patents", patent)
                    self.stats["new_patents"] += 1
                except Exception as e:
                    if "duplicate" not in str(e).lower():
                        log(f"  Error inserting {patent['patent_number']}: {e}")

        log(f"Inserted {self.stats['new_patents']} new patents")

    def stage_claims(self):
        """Fetch claims for patents missing them."""
        missing = get_patents_missing_claims()
        log(f"Patents missing claims: {len(missing)}")

        # Filter to US patents (PatentsView only has US)
        us_missing = [pn for pn in missing if pn.startswith("US")]
        log(f"US patents to fetch claims for: {len(us_missing)}")

        for i, pn in enumerate(us_missing):
            # Extract patent_id from patent_number
            match = re.match(r'^US(\d+)', pn)
            if not match:
                continue

            patent_id = match.group(1)
            log(f"  [{i+1}/{len(us_missing)}] Fetching claims for {pn}")

            claims = patentsview_fetch_claims(patent_id)
            if claims:
                inserted = insert_claims(pn, claims, self.dry_run)
                self.stats["new_claims"] += inserted
                log(f"    -> {inserted} claims")
            else:
                log(f"    -> No claims found")

            time.sleep(PATENTSVIEW_DELAY)

        log(f"Total claims added: {self.stats['new_claims']}")

    def stage_enrichment(self):
        """Enrich patents with missing data from Google Patents."""
        missing = get_patents_missing_data()
        log(f"Patents missing title/abstract: {len(missing)}")

        if not missing:
            log("No patents need enrichment")
            return

        enriched = enrich_patents_google(missing, self.dry_run)
        self.stats["enriched"] = enriched
        log(f"Enriched {enriched} patents")

    def stage_cleanup(self):
        """Deduplicate and build RAG fields."""
        # Dedupe B1/B2
        log("Deduplicating B1/B2 pairs...")
        deduped = dedupe_b1_b2(self.dry_run)
        self.stats["deduped"] = deduped
        log(f"  Removed {deduped} B1 patents")

        # Build RAG fields
        log("Building RAG fields...")
        built = build_rag_fields(self.dry_run)
        self.stats["rag_built"] = built
        log(f"  Updated {built} patents with content_text")

    def stage_report(self):
        """Report final stats."""
        # Get current counts
        patents = supabase_request("GET", "patents?select=patent_number&limit=1000")
        claims = supabase_request("GET", "patent_claims?select=patent_number&limit=5000")

        unique_with_claims = len(set(c["patent_number"] for c in claims))

        log("=" * 60)
        log("SUMMARY")
        log("=" * 60)
        log(f"Total patents: {len(patents)}")
        log(f"Total claims: {len(claims)}")
        log(f"Patents with claims: {unique_with_claims}")
        log("")
        log("This run:")
        log(f"  New patents added: {self.stats['new_patents']}")
        log(f"  New claims added: {self.stats['new_claims']}")
        log(f"  Patents enriched: {self.stats['enriched']}")
        log(f"  B1 patents deduped: {self.stats['deduped']}")
        log(f"  RAG fields built: {self.stats['rag_built']}")
        log("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Patent Worker v2 - Unified pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes only")
    parser.add_argument("--full", action="store_true", help="Full refresh (not incremental)")
    parser.add_argument("--stage", type=int, choices=[1, 2, 3, 4, 5],
                        help="Run specific stage only")
    args = parser.parse_args()

    if not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    worker = PatentWorker(dry_run=args.dry_run, full_refresh=args.full)
    worker.run(stage=args.stage)


if __name__ == "__main__":
    main()
