#!/usr/bin/env python3
"""
Google Patents Scraper

Scrapes claims, abstract, images, and PDF URLs from Google Patents
for JP/KR/AU/CA patents. Also updates existing patent records with
enriched data.

Uses Playwright for browser automation.

Run: python3 google_patents_scraper.py

Requirements: pip install playwright && playwright install chromium
"""

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

# Rate limiting - be respectful
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

    with urllib.request.urlopen(req, timeout=30) as response:
        content = response.read().decode("utf-8")
        return json.loads(content) if content else {}


def detect_claim_type(claim_text, claim_number):
    """Detect if claim is independent or dependent."""
    if claim_number == 1:
        return "independent", None

    text_lower = claim_text.lower()[:300]

    # Look for dependency references
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
        data.abstract = text.slice(0, 2000);
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


def main():
    log("=" * 60)
    log("GOOGLE PATENTS SCRAPER (JP/KR/AU/CA)")
    log("=" * 60)

    # Check Playwright installation
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("ERROR: Playwright not installed")
        log("Run: pip install playwright && playwright install chromium")
        return

    # Get international patents from database
    jurisdictions = ["JP", "KR", "AU", "CA"]
    all_patents = []

    for jur in jurisdictions:
        patents = supabase_request("GET", f"patents?select=patent_number&patent_number=like.{jur}*&limit=200")
        all_patents.extend([p["patent_number"] for p in patents])
        log(f"Found {len(patents)} {jur} patents")

    log(f"Total international patents: {len(all_patents)}")

    # Check existing claims
    try:
        existing = supabase_request("GET", "patent_claims?select=patent_number")
        existing_patents = set(c["patent_number"] for c in existing)
        log(f"Already have claims for {len(existing_patents)} patents")
    except Exception:
        existing_patents = set()

    # Filter to patents needing claims
    to_fetch = [p for p in all_patents if p not in existing_patents]
    log(f"Need to fetch data for {len(to_fetch)} patents")

    if not to_fetch:
        log("No patents to fetch!")
        return

    # Start browser
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()

        total_claims = 0
        patents_with_claims = 0
        patents_updated = 0
        errors = 0

        for i, patent_number in enumerate(to_fetch):
            log(f"  [{i+1}/{len(to_fetch)}] {patent_number}")

            data, error = scrape_patent(page, patent_number)

            if error:
                log(f"      -> Error: {error}")
                errors += 1
                time.sleep(REQUEST_DELAY)
                continue

            # Update patent record with enriched data
            if data.get("title") or data.get("abstract") or data.get("images") or data.get("pdf_url"):
                try:
                    update_data = {}
                    if data.get("title"):
                        update_data["title"] = data["title"]
                    if data.get("abstract"):
                        update_data["abstract"] = data["abstract"]
                    if data.get("images"):
                        update_data["figure_urls"] = data["images"]
                    if data.get("pdf_url"):
                        update_data["source_url"] = data["pdf_url"]
                    if data.get("claims_count"):
                        update_data["claims_count"] = data["claims_count"]

                    if update_data:
                        supabase_request(
                            "PATCH",
                            f"patents?patent_number=eq.{patent_number}",
                            update_data
                        )
                        patents_updated += 1
                        log(f"      -> Updated: title, abstract, {len(data.get('images', []))} images")
                except Exception as e:
                    log(f"      -> Update error: {e}")

            # Insert claims
            if data.get("claims"):
                patents_with_claims += 1
                log(f"      -> {len(data['claims'])} claims")

                for claim in data["claims"]:
                    claim_num = claim["num"]
                    claim_text = claim["text"]

                    if not claim_text or len(claim_text) < 10:
                        continue

                    # Detect type
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
                        total_claims += 1
                    except Exception as e:
                        if "duplicate key" not in str(e).lower():
                            log(f"      Claim error: {e}")

            time.sleep(REQUEST_DELAY)

        browser.close()

    log("")
    log("=" * 60)
    log("SUMMARY")
    log("=" * 60)
    log(f"Patents processed: {len(to_fetch)}")
    log(f"Patents updated with metadata: {patents_updated}")
    log(f"Patents with claims: {patents_with_claims}")
    log(f"Total claims inserted: {total_claims}")
    log(f"Errors: {errors}")

    # Verify final count
    try:
        final_count = supabase_request("GET", "patent_claims?select=id")
        log(f"Total claims in database: {len(final_count)}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
