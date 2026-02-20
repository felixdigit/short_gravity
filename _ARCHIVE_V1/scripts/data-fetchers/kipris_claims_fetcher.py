#!/usr/bin/env python3
"""
KIPRIS Korean Patent Claims Fetcher

Fetches patent claims from KIPRIS Plus API (Korea).
Free tier: 1,000 calls/month

Prerequisites:
1. Register at https://plus.kipris.or.kr
2. Apply for API key
3. Set KIPRIS_API_KEY in .env

Run: python3 kipris_claims_fetcher.py
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
KIPRIS_API_KEY = os.environ.get("KIPRIS_API_KEY", "")

# KIPRIS Plus API endpoints
KIPRIS_BASE = "http://plus.kipris.or.kr/openapi/rest"

RATE_LIMIT_DELAY = 1.0
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


def parse_kr_patent_number(pn):
    """Parse KR patent number.
    KR102454426B1 -> ('102454426', 'B1')
    """
    match = re.match(r'^KR(\d+)([A-Z]\d?)$', pn)
    if match:
        return match.group(1), match.group(2)
    return None, None


def kipris_request(endpoint, params=None):
    """Make KIPRIS Plus API request."""
    if not KIPRIS_API_KEY:
        log("ERROR: KIPRIS_API_KEY not set")
        return None

    params = params or {}
    params["accessKey"] = KIPRIS_API_KEY

    query = urllib.parse.urlencode(params)
    url = f"{KIPRIS_BASE}/{endpoint}?{query}"

    headers = {
        "Accept": "application/json",
    }

    req = urllib.request.Request(url, headers=headers)

    try:
        rate_limit()
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        log(f"KIPRIS error: {e.code}")
        return None
    except Exception as e:
        log(f"KIPRIS error: {e}")
        return None


def get_patent_claims(application_number):
    """Get claims for a Korean patent.

    KIPRIS Plus offers several endpoints:
    - patentClaimInfo: Get claim information
    - patentDetailInfo: Get detailed patent info including claims

    Note: Actual endpoint names may vary. Check KIPRIS Plus documentation
    for current API specifications.
    """
    # Try the claims endpoint
    result = kipris_request("patentClaimInfo", {
        "applicationNumber": application_number,
    })

    if result and "response" in result:
        body = result.get("response", {}).get("body", {})
        items = body.get("items", {}).get("item", [])

        if isinstance(items, dict):
            items = [items]

        claims = []
        for item in items:
            claim_num = item.get("claimNumber", 0)
            claim_text = item.get("claimContent", "")

            if claim_text:
                is_dependent = bool(re.search(r'청구항\s*\d+', claim_text[:200]))
                claims.append({
                    "number": claim_num,
                    "text": claim_text,
                    "type": "dependent" if is_dependent else "independent",
                })

        return claims

    return []


def main():
    log("=" * 60)
    log("KIPRIS KOREAN PATENT CLAIMS FETCHER")
    log("=" * 60)

    if not KIPRIS_API_KEY:
        log("")
        log("ERROR: KIPRIS_API_KEY not set!")
        log("")
        log("To get an API key:")
        log("1. Go to https://plus.kipris.or.kr")
        log("2. Register for an account")
        log("3. Apply for API access (free tier: 1,000 calls/month)")
        log("4. Add KIPRIS_API_KEY=your_key to .env")
        return

    # Get KR patents from database
    kr_patents = supabase_request("GET", "patents?select=patent_number&patent_number=like.KR*&limit=100")
    log(f"Found {len(kr_patents)} KR patents in database")

    # Check existing claims
    try:
        existing = supabase_request("GET", "patent_claims?select=patent_number&patent_number=like.KR*")
        existing_patents = set(c["patent_number"] for c in existing)
        log(f"Already have claims for {len(existing_patents)} KR patents")
    except Exception:
        existing_patents = set()

    # Filter to patents needing claims
    to_fetch = [p["patent_number"] for p in kr_patents if p["patent_number"] not in existing_patents]
    log(f"Need to fetch claims for {len(to_fetch)} patents")

    if not to_fetch:
        log("No patents to fetch!")
        return

    total_claims = 0
    patents_with_claims = 0

    for i, patent_number in enumerate(to_fetch):
        doc_number, kind = parse_kr_patent_number(patent_number)

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
