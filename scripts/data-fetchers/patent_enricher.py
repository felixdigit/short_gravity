#!/usr/bin/env python3
"""
Patent Data Enricher

Enriches patent records with data from Google Patents:
- Title, abstract, claims count
- Figure/drawing images
- PDF download URLs
- Individual claims (stored in patent_claims table)

Runs on ALL patents (US, EP, WO, JP, KR, AU, CA) - not just international.

Usage:
    python3 patent_enricher.py --missing-only    # Only patents with gaps
    python3 patent_enricher.py --jurisdiction US # Only US patents
    python3 patent_enricher.py --patent US123    # Single patent
    python3 patent_enricher.py --all --force     # Re-enrich everything

Requirements: pip install playwright && playwright install chromium
"""

import argparse
import json
import os
import re
import time
import urllib.request
import urllib.error
from datetime import datetime

# Config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

GOOGLE_PATENTS_BASE = "https://patents.google.com/patent"

# Rate limiting - be respectful to Google
REQUEST_DELAY = 2.5  # seconds between requests


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


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

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode("utf-8")
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        raise Exception(f"HTTP {e.code}: {error_body[:200]}")


def detect_claim_type(claim_text, claim_number):
    """Detect if claim is independent or dependent."""
    if claim_number == 1:
        return "independent", None

    text_lower = claim_text.lower()[:300]

    dep_patterns = [
        r'in claim[s]?\s+(\d+)',
        r'claim[s]?\s+(\d+)',
        r'according to claim[s]?\s+(\d+)',
        r'as claimed in claim[s]?\s+(\d+)',
        r'the .+ of claim[s]?\s+(\d+)',
    ]

    depends_on = []
    for pattern in dep_patterns:
        matches = re.findall(pattern, text_lower)
        depends_on.extend([int(m) for m in matches])

    if depends_on:
        return "dependent", list(set(depends_on))

    return "independent", None


# JavaScript to extract all patent data from Google Patents page
JS_EXTRACT_PATENT_DATA = """
() => {
    const data = {
        claims: [],
        title: null,
        abstract: null,
        images: [],
        pdf_url: null,
        claims_count: null
    };

    // Title from page title
    const pageTitle = document.title;
    const titleMatch = pageTitle.match(/^([^-]+)\\s+-\\s+(.+?)\\s+-\\s+Google Patents/);
    if (titleMatch) {
        data.title = titleMatch[2].trim();
    }

    // Extract English text helper - removes original language spans
    const extractEnglish = (element) => {
        if (!element) return '';
        const clone = element.cloneNode(true);
        clone.querySelectorAll('.google-src-text').forEach(el => el.remove());
        return clone.textContent.trim().replace(/\\s+/g, ' ');
    };

    // Abstract
    const abstractSection = document.querySelector('section#abstract');
    if (abstractSection) {
        let text = extractEnglish(abstractSection);
        text = text.replace(/^Abstract\\s*/i, '').replace(/translated from.*/i, '').trim();
        if (text.length > 20) {
            data.abstract = text.slice(0, 2000);
        }
    }

    // Claims
    const claims = document.querySelectorAll('claims > claim');
    data.claims = Array.from(claims).map(c => {
        const num = parseInt(c.getAttribute('num')) || 0;
        const text = extractEnglish(c.querySelector('claim-text'));
        return { num, text };
    });
    data.claims_count = claims.length;

    // Images - get unique URLs from patentimages storage
    const imgElements = document.querySelectorAll('img[src*="patentimages.storage.googleapis"]');
    const imgUrls = Array.from(imgElements).map(img => img.src);
    data.images = [...new Set(imgUrls)].slice(0, 30);

    // PDF URL
    const pdfLink = Array.from(document.querySelectorAll('a')).find(a =>
        a.href && a.href.includes('.pdf') && a.href.includes('patentimages')
    );
    data.pdf_url = pdfLink ? pdfLink.href : null;

    return data;
}
"""


def scrape_patent(page, patent_number):
    """Scrape all data from a Google Patents page."""
    url = f"{GOOGLE_PATENTS_BASE}/{patent_number}/en"

    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(1.5)  # Let dynamic content load

        # Check if patent exists
        if "404" in page.title() or "not found" in page.title().lower():
            return None, "Patent not found"

        # Extract all data
        data = page.evaluate(JS_EXTRACT_PATENT_DATA)
        return data, None

    except Exception as e:
        return None, str(e)


def get_patents_to_enrich(args):
    """Get list of patents based on CLI arguments."""

    # Single patent mode
    if args.patent:
        return [args.patent]

    # Build query based on flags
    select_fields = "patent_number,title,abstract,figure_urls"

    if args.jurisdiction:
        query = f"patents?select={select_fields}&patent_number=like.{args.jurisdiction}*&limit=500"
    else:
        query = f"patents?select={select_fields}&limit=500"

    patents = supabase_request("GET", query)

    if args.missing_only:
        # Filter to patents with missing data
        filtered = []
        for p in patents:
            has_title = p.get("title") and p["title"] != "[no title]"
            has_abstract = p.get("abstract") and len(p["abstract"]) > 20
            has_figures = p.get("figure_urls") and len(p["figure_urls"]) > 0

            if not (has_title and has_abstract and has_figures):
                filtered.append(p["patent_number"])
        return filtered

    if args.force or args.all:
        return [p["patent_number"] for p in patents]

    # Default: missing only
    filtered = []
    for p in patents:
        has_title = p.get("title") and p["title"] != "[no title]"
        has_abstract = p.get("abstract") and len(p["abstract"]) > 20
        has_figures = p.get("figure_urls") and len(p["figure_urls"]) > 0

        if not (has_title and has_abstract and has_figures):
            filtered.append(p["patent_number"])
    return filtered


def enrich_patent(page, patent_number, existing_data, force=False):
    """Enrich a single patent record."""
    data, error = scrape_patent(page, patent_number)

    if error:
        return None, error

    # Build update dict - only update empty fields unless force
    update_data = {}
    enriched_fields = []

    has_title = existing_data.get("title") and existing_data["title"] != "[no title]"
    has_abstract = existing_data.get("abstract") and len(existing_data.get("abstract", "")) > 20
    has_figures = existing_data.get("figure_urls") and len(existing_data.get("figure_urls", [])) > 0

    if data.get("title") and (force or not has_title):
        update_data["title"] = data["title"]
        enriched_fields.append("title")

    if data.get("abstract") and len(data["abstract"]) > 20 and (force or not has_abstract):
        update_data["abstract"] = data["abstract"]
        enriched_fields.append("abstract")

    if data.get("images") and (force or not has_figures):
        update_data["figure_urls"] = data["images"]
        enriched_fields.append(f"{len(data['images'])} images")

    if data.get("pdf_url"):
        update_data["source_url"] = data["pdf_url"]

    if data.get("claims_count"):
        update_data["claims_count"] = data["claims_count"]

    return {
        "update_data": update_data,
        "enriched_fields": enriched_fields,
        "claims": data.get("claims", []),
        "claims_count": data.get("claims_count", 0)
    }, None


def main():
    parser = argparse.ArgumentParser(description="Enrich patent data from Google Patents")
    parser.add_argument("--all", action="store_true", help="Process all patents")
    parser.add_argument("--missing-only", action="store_true", help="Only patents with missing data (default)")
    parser.add_argument("--jurisdiction", "-j", help="Filter by jurisdiction (US, EP, JP, etc)")
    parser.add_argument("--patent", "-p", help="Process single patent number")
    parser.add_argument("--force", "-f", action="store_true", help="Overwrite existing data")
    parser.add_argument("--skip-claims", action="store_true", help="Skip inserting claims")
    args = parser.parse_args()

    log("=" * 60)
    log("PATENT DATA ENRICHER")
    log("=" * 60)

    # Check Playwright
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("ERROR: Playwright not installed")
        log("Run: pip install playwright && playwright install chromium")
        return

    # Get patents to process
    to_fetch = get_patents_to_enrich(args)
    log(f"Patents to enrich: {len(to_fetch)}")

    if not to_fetch:
        log("No patents need enrichment!")
        return

    # Get existing data for all patents
    existing_map = {}
    for pn in to_fetch:
        try:
            result = supabase_request("GET", f"patents?select=title,abstract,figure_urls&patent_number=eq.{pn}")
            if result:
                existing_map[pn] = result[0]
        except:
            existing_map[pn] = {}

    # Check existing claims
    existing_claims = set()
    if not args.skip_claims:
        try:
            claims = supabase_request("GET", "patent_claims?select=patent_number")
            existing_claims = set(c["patent_number"] for c in claims)
            log(f"Patents with existing claims: {len(existing_claims)}")
        except:
            pass

    # Start browser
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()

        stats = {
            "processed": 0,
            "updated": 0,
            "claims_added": 0,
            "errors": 0,
            "skipped": 0
        }

        for i, patent_number in enumerate(to_fetch):
            log(f"  [{i+1}/{len(to_fetch)}] {patent_number}")

            existing = existing_map.get(patent_number, {})
            result, error = enrich_patent(page, patent_number, existing, args.force)

            if error:
                log(f"      -> Error: {error}")
                stats["errors"] += 1
                time.sleep(REQUEST_DELAY)
                continue

            stats["processed"] += 1

            # Update patent record
            if result["update_data"]:
                try:
                    supabase_request(
                        "PATCH",
                        f"patents?patent_number=eq.{patent_number}",
                        result["update_data"]
                    )
                    stats["updated"] += 1
                    if result["enriched_fields"]:
                        log(f"      -> Enriched: {', '.join(result['enriched_fields'])}")
                except Exception as e:
                    log(f"      -> Update error: {e}")
            else:
                stats["skipped"] += 1
                log(f"      -> Already complete")

            # Insert claims if not already present
            if not args.skip_claims and result["claims"] and patent_number not in existing_claims:
                claims_added = 0
                for claim in result["claims"]:
                    claim_num = claim["num"]
                    claim_text = claim["text"]

                    if not claim_text or len(claim_text) < 10:
                        continue

                    claim_type, depends_on = detect_claim_type(claim_text, claim_num)

                    try:
                        claim_data = {
                            "patent_number": patent_number,
                            "claim_number": claim_num,
                            "claim_text": claim_text,
                            "claim_type": claim_type,
                        }
                        if depends_on:
                            claim_data["depends_on"] = depends_on

                        supabase_request("POST", "patent_claims", claim_data)
                        claims_added += 1
                    except Exception as e:
                        if "duplicate key" not in str(e).lower():
                            pass  # Silently skip duplicates

                if claims_added:
                    stats["claims_added"] += claims_added
                    log(f"      -> Added {claims_added} claims")

            time.sleep(REQUEST_DELAY)

        browser.close()

    log("")
    log("=" * 60)
    log("SUMMARY")
    log("=" * 60)
    log(f"Processed: {stats['processed']}")
    log(f"Updated: {stats['updated']}")
    log(f"Already complete: {stats['skipped']}")
    log(f"Claims added: {stats['claims_added']}")
    log(f"Errors: {stats['errors']}")


if __name__ == "__main__":
    main()
