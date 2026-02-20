#!/usr/bin/env python3
"""
J-PlatPat Japanese Patent Claims Fetcher

Fetches patent claims from Japan Patent Office API.

Prerequisites:
1. Contact JPO for API access: contact@ip-data-support.jpo.go.jp
2. Register at https://ip-data.jpo.go.jp
3. Set JPO_API_KEY in .env (trial phase, limited availability)

Run: python3 jplatpat_claims_fetcher.py
"""

import json
import os
import re
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
JPO_API_KEY = os.environ.get("JPO_API_KEY", "")

# JPO Patent Information Retrieval API
JPO_BASE = "https://ip-data.jpo.go.jp/api"

RATE_LIMIT_DELAY = 1.5
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


def parse_jp_patent_number(pn):
    """Parse JP patent number.
    JP2019001446A -> ('2019001446', 'A')
    JP2022173202A -> ('2022173202', 'A')
    """
    match = re.match(r'^JP(\d+)([A-Z]\d?)$', pn)
    if match:
        return match.group(1), match.group(2)
    return None, None


def jpo_request(endpoint, params=None):
    """Make JPO API request."""
    if not JPO_API_KEY:
        log("ERROR: JPO_API_KEY not set")
        return None

    params = params or {}

    query = urllib.parse.urlencode(params)
    url = f"{JPO_BASE}/{endpoint}"
    if query:
        url += f"?{query}"

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {JPO_API_KEY}",
    }

    req = urllib.request.Request(url, headers=headers)

    try:
        rate_limit()
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        log(f"JPO error: {e.code}")
        return None
    except Exception as e:
        log(f"JPO error: {e}")
        return None


def get_patent_claims(application_number):
    """Get claims for a Japanese patent.

    Note: JPO API structure may vary. This is a template based on
    common patent API patterns. Adjust endpoints based on actual
    JPO API documentation.
    """
    result = jpo_request(f"patent/{application_number}/claims")

    if result and "claims" in result:
        claims = []
        for item in result["claims"]:
            claim_num = item.get("claimNumber", 0)
            claim_text = item.get("claimText", "")

            if claim_text:
                # Japanese dependent claims reference 請求項 (seikyu-ko)
                is_dependent = bool(re.search(r'請求項\s*\d+', claim_text[:200]))
                claims.append({
                    "number": claim_num,
                    "text": claim_text,
                    "type": "dependent" if is_dependent else "independent",
                })

        return claims

    return []


def main():
    log("=" * 60)
    log("J-PLATPAT JAPANESE PATENT CLAIMS FETCHER")
    log("=" * 60)

    if not JPO_API_KEY:
        log("")
        log("ERROR: JPO_API_KEY not set!")
        log("")
        log("To get API access:")
        log("1. Visit https://ip-data.jpo.go.jp/pages/top_e.html")
        log("2. Email contact@ip-data-support.jpo.go.jp to request access")
        log("3. Note: API is in trial phase with limited availability")
        log("4. Once approved, add JPO_API_KEY=your_key to .env")
        return

    # Get JP patents from database
    jp_patents = supabase_request("GET", "patents?select=patent_number&patent_number=like.JP*&limit=100")
    log(f"Found {len(jp_patents)} JP patents in database")

    # Check existing claims
    try:
        existing = supabase_request("GET", "patent_claims?select=patent_number&patent_number=like.JP*")
        existing_patents = set(c["patent_number"] for c in existing)
        log(f"Already have claims for {len(existing_patents)} JP patents")
    except Exception:
        existing_patents = set()

    # Filter to patents needing claims
    to_fetch = [p["patent_number"] for p in jp_patents if p["patent_number"] not in existing_patents]
    log(f"Need to fetch claims for {len(to_fetch)} patents")

    if not to_fetch:
        log("No patents to fetch!")
        return

    total_claims = 0
    patents_with_claims = 0

    for i, patent_number in enumerate(to_fetch):
        doc_number, kind = parse_jp_patent_number(patent_number)

        if not doc_number:
            log(f"  [{i+1}/{len(to_fetch)}] Could not parse: {patent_number}")
            continue

        log(f"  [{i+1}/{len(to_fetch)}] {patent_number}")

        claims = get_patent_claims(doc_number)

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
