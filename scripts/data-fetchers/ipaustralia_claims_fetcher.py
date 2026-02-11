#!/usr/bin/env python3
"""
IP Australia Patent Claims Fetcher

Fetches patent claims from IP Australia API.

Prerequisites:
1. Register at https://portal.api.ipaustralia.gov.au
2. Create an account and apply for API access
3. Set IPA_CLIENT_ID and IPA_CLIENT_SECRET in .env

Run: python3 ipaustralia_claims_fetcher.py
"""

import json
import os
import re
import time
import urllib.request
import urllib.error
import urllib.parse
import base64
from datetime import datetime, timedelta

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
IPA_CLIENT_ID = os.environ.get("IPA_CLIENT_ID", "")
IPA_CLIENT_SECRET = os.environ.get("IPA_CLIENT_SECRET", "")

# IP Australia API
IPA_BASE = "https://api.ipaustralia.gov.au"
IPA_AUTH_URL = "https://auth.ipaustralia.gov.au/oauth2/token"

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


class IPAAuth:
    """IP Australia OAuth2 authentication."""

    def __init__(self):
        self.access_token = None
        self.token_expiry = None

    def get_token(self):
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token
        return self._fetch_new_token()

    def _fetch_new_token(self):
        credentials = f"{IPA_CLIENT_ID}:{IPA_CLIENT_SECRET}"
        encoded = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = "grant_type=client_credentials".encode()

        req = urllib.request.Request(IPA_AUTH_URL, data=data, headers=headers, method="POST")

        try:
            rate_limit()
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode())
                self.access_token = result["access_token"]
                expires_in = int(result.get("expires_in", 3600))
                self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)
                log(f"Got IP Australia access token (expires in {expires_in}s)")
                return self.access_token
        except urllib.error.HTTPError as e:
            log(f"IP Australia auth error: {e.code}")
            raise


def parse_au_patent_number(pn):
    """Parse AU patent number.
    AU2018283981B2 -> ('2018283981', 'B2')
    AU2020241308A1 -> ('2020241308', 'A1')
    """
    match = re.match(r'^AU(\d+)([A-Z]\d?)$', pn)
    if match:
        return match.group(1), match.group(2)
    return None, None


def ipa_request(auth, endpoint):
    """Make IP Australia API request."""
    url = f"{IPA_BASE}/{endpoint}"

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {auth.get_token()}",
    }

    req = urllib.request.Request(url, headers=headers)

    try:
        rate_limit()
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        log(f"IP Australia error: {e.code}")
        return None
    except Exception as e:
        log(f"IP Australia error: {e}")
        return None


def get_patent_claims(auth, application_number):
    """Get claims for an Australian patent.

    Note: IP Australia API structure may vary. This is a template.
    Adjust endpoints based on actual API documentation.
    """
    result = ipa_request(auth, f"patents/{application_number}/claims")

    if result and "claims" in result:
        claims = []
        for item in result["claims"]:
            claim_num = item.get("claimNumber", 0)
            claim_text = item.get("claimText", "")

            if claim_text:
                is_dependent = bool(re.search(r'\bclaim\s+\d+', claim_text.lower()[:200]))
                claims.append({
                    "number": claim_num,
                    "text": claim_text,
                    "type": "dependent" if is_dependent else "independent",
                })

        return claims

    return []


def main():
    log("=" * 60)
    log("IP AUSTRALIA PATENT CLAIMS FETCHER")
    log("=" * 60)

    if not IPA_CLIENT_ID or not IPA_CLIENT_SECRET:
        log("")
        log("ERROR: IP Australia credentials not set!")
        log("")
        log("To get API access:")
        log("1. Go to https://portal.api.ipaustralia.gov.au")
        log("2. Create an account")
        log("3. Apply for API access")
        log("4. Add IPA_CLIENT_ID and IPA_CLIENT_SECRET to .env")
        return

    auth = IPAAuth()

    # Get AU patents from database
    au_patents = supabase_request("GET", "patents?select=patent_number&patent_number=like.AU*&limit=100")
    log(f"Found {len(au_patents)} AU patents in database")

    # Check existing claims
    try:
        existing = supabase_request("GET", "patent_claims?select=patent_number&patent_number=like.AU*")
        existing_patents = set(c["patent_number"] for c in existing)
        log(f"Already have claims for {len(existing_patents)} AU patents")
    except Exception:
        existing_patents = set()

    # Filter to patents needing claims
    to_fetch = [p["patent_number"] for p in au_patents if p["patent_number"] not in existing_patents]
    log(f"Need to fetch claims for {len(to_fetch)} patents")

    if not to_fetch:
        log("No patents to fetch!")
        return

    total_claims = 0
    patents_with_claims = 0

    for i, patent_number in enumerate(to_fetch):
        doc_number, kind = parse_au_patent_number(patent_number)

        if not doc_number:
            log(f"  [{i+1}/{len(to_fetch)}] Could not parse: {patent_number}")
            continue

        log(f"  [{i+1}/{len(to_fetch)}] {patent_number}")

        claims = get_patent_claims(auth, doc_number)

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
