#!/usr/bin/env python3
"""
CIPO Canadian Patent Claims Fetcher

Fetches patent claims from Canadian Intellectual Property Office.

Note: CIPO doesn't have a public REST API. This script uses:
1. IP Horizons bulk data download (requires registration)
2. Scraping from the Canadian Patents Database (fallback)

Prerequisites:
1. For bulk data: Register at https://ised-isde.canada.ca/site/canadian-intellectual-property-office/en
2. Download IP Horizons XML data

Run: python3 cipo_claims_fetcher.py
"""

import json
import os
import re
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from xml.etree import ElementTree as ET

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Canadian Patents Database (public, no API key needed)
CIPO_SEARCH_URL = "https://www.ic.gc.ca/opic-cipo/cpd/eng/patent"

RATE_LIMIT_DELAY = 2.0  # Be respectful to public website
last_request_time = 0


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def rate_limit():
    global last_request_time
    elapsed = time.time() - last_request_time
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)
    last_request_time = time.time()


def supabase_request(method, endpoint, data=None):
    """Make Supabase REST API request."""
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    with urllib.request.urlopen(req, timeout=60) as response:
        content = response.read().decode("utf-8")
        return json.loads(content) if content else {}


def parse_ca_patent_number(pn):
    """Parse CA patent number.
    CA3066691A1 -> ('3066691', 'A1')
    CA3134030C -> ('3134030', 'C')
    """
    match = re.match(r'^CA(\d+)([A-Z]\d?)?$', pn)
    if match:
        return match.group(1), match.group(2) or ""
    return None, None


def fetch_from_cipo_website(patent_number):
    """Fetch patent claims from CIPO public website.

    Note: This scrapes the public website. For production use,
    consider using IP Horizons bulk data instead.
    """
    doc_number, _ = parse_ca_patent_number(patent_number)
    if not doc_number:
        return []

    url = f"{CIPO_SEARCH_URL}/{doc_number}/claims.html"

    headers = {
        "User-Agent": "Mozilla/5.0 (research purposes)",
        "Accept": "text/html",
    }

    req = urllib.request.Request(url, headers=headers)

    try:
        rate_limit()
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode("utf-8", errors="ignore")
            return parse_claims_html(html)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        log(f"CIPO error: {e.code}")
        return []
    except Exception as e:
        log(f"CIPO error: {e}")
        return []


def parse_claims_html(html):
    """Parse claims from CIPO HTML page.

    Note: HTML structure may change. This is a basic implementation.
    """
    claims = []

    # Look for claim sections
    # CIPO typically uses <div class="claim"> or numbered paragraphs
    claim_pattern = r'<div[^>]*class="[^"]*claim[^"]*"[^>]*>(.*?)</div>'
    matches = re.findall(claim_pattern, html, re.DOTALL | re.IGNORECASE)

    if not matches:
        # Try alternative pattern: numbered paragraphs
        claim_pattern = r'(\d+)\.\s*([^<]+(?:<[^>]+>[^<]*</[^>]+>)*[^<]*)'
        matches = re.findall(claim_pattern, html)

        for num, text in matches:
            clean_text = re.sub(r'<[^>]+>', '', text).strip()
            if clean_text and len(clean_text) > 20:
                is_dependent = bool(re.search(r'\bclaim\s+\d+', clean_text.lower()[:200]))
                claims.append({
                    "number": int(num),
                    "text": clean_text,
                    "type": "dependent" if is_dependent else "independent",
                })
    else:
        for i, match in enumerate(matches, 1):
            clean_text = re.sub(r'<[^>]+>', '', match).strip()
            if clean_text:
                is_dependent = bool(re.search(r'\bclaim\s+\d+', clean_text.lower()[:200]))
                claims.append({
                    "number": i,
                    "text": clean_text,
                    "type": "dependent" if is_dependent else "independent",
                })

    return claims


def main():
    log("=" * 60)
    log("CIPO CANADIAN PATENT CLAIMS FETCHER")
    log("=" * 60)
    log("")
    log("Note: CIPO doesn't have a public REST API.")
    log("This script uses the public website (rate-limited).")
    log("For production, consider IP Horizons bulk data download.")
    log("")

    # Get CA patents from database
    ca_patents = supabase_request("GET", "patents?select=patent_number&patent_number=like.CA*&limit=100")
    log(f"Found {len(ca_patents)} CA patents in database")

    # Check existing claims
    try:
        existing = supabase_request("GET", "patent_claims?select=patent_number&patent_number=like.CA*")
        existing_patents = set(c["patent_number"] for c in existing)
        log(f"Already have claims for {len(existing_patents)} CA patents")
    except Exception:
        existing_patents = set()

    # Filter to patents needing claims
    to_fetch = [p["patent_number"] for p in ca_patents if p["patent_number"] not in existing_patents]
    log(f"Need to fetch claims for {len(to_fetch)} patents")

    if not to_fetch:
        log("No patents to fetch!")
        return

    total_claims = 0
    patents_with_claims = 0

    for i, patent_number in enumerate(to_fetch):
        log(f"  [{i+1}/{len(to_fetch)}] {patent_number}")

        claims = fetch_from_cipo_website(patent_number)

        if claims:
            patents_with_claims += 1
            log(f"      -> {len(claims)} claims")

            for claim in claims:
                try:
                    data = {
                        "patent_number": patent_number,
                        "claim_number": claim["number"],
                        "claim_text": claim["text"],
                        "claim_type": claim["type"],
                    }
                    supabase_request("POST", "patent_claims", data)
                    total_claims += 1
                except Exception as e:
                    if "duplicate key" not in str(e).lower():
                        log(f"      Error: {e}")
        else:
            log(f"      -> No claims found")

    log("")
    log("=" * 60)
    log("SUMMARY")
    log("=" * 60)
    log(f"Patents with claims: {patents_with_claims}")
    log(f"Total claims inserted: {total_claims}")


if __name__ == "__main__":
    main()
