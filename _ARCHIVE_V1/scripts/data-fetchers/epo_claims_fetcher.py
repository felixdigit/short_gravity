#!/usr/bin/env python3
"""
EPO Claims Fetcher

Fetches full claim text from EPO OPS for EP and WO patents.
US patents are NOT available from EPO - use BigQuery for those.

Run: python3 epo_claims_fetcher.py
"""

import json
import os
import re
import time
import urllib.request
import urllib.error
import base64
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET

# Config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
EPO_CONSUMER_KEY = os.environ.get("EPO_CONSUMER_KEY", "")
EPO_CONSUMER_SECRET = os.environ.get("EPO_CONSUMER_SECRET", "")

EPO_AUTH_URL = "https://ops.epo.org/3.2/auth/accesstoken"
EPO_API_BASE = "https://ops.epo.org/3.2/rest-services"

RATE_LIMIT_DELAY = 3.2
last_request_time = 0


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def rate_limit():
    global last_request_time
    elapsed = time.time() - last_request_time
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)
    last_request_time = time.time()


class EPOAuth:
    def __init__(self):
        self.access_token = None
        self.token_expiry = None

    def get_token(self):
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token

        credentials = f"{EPO_CONSUMER_KEY}:{EPO_CONSUMER_SECRET}"
        encoded = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = "grant_type=client_credentials".encode()

        req = urllib.request.Request(EPO_AUTH_URL, data=data, headers=headers, method="POST")
        rate_limit()

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            self.access_token = result["access_token"]
            expires_in = int(result.get("expires_in", 1200))
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)
            log(f"Got EPO access token (expires in {expires_in}s)")
            return self.access_token


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


def parse_patent_number(pn):
    """Parse patent number into (country, number, kind)."""
    # EP3378176A1 -> ('EP', '3378176', 'A1')
    match = re.match(r'^([A-Z]{2})(\d+)([A-Z]\d?)?$', pn)
    if match:
        country, num, kind = match.groups()
        return country, num, kind or ""
    return None, None, None


def get_claims(auth, country, doc_number):
    """Get claims from EPO fulltext endpoint using epodoc format."""
    # For EP/WO patents, use epodoc format (no dots, no kind)
    epodoc_number = f"{country}{doc_number}"
    url = f"{EPO_API_BASE}/published-data/publication/epodoc/{epodoc_number}/claims"

    headers = {
        "Authorization": f"Bearer {auth.get_token()}",
        "Accept": "application/xml",
    }

    req = urllib.request.Request(url, headers=headers)

    try:
        rate_limit()
        with urllib.request.urlopen(req, timeout=30) as response:
            xml = response.read().decode()
            return parse_claims_xml(xml)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        log(f"EPO error for {epodoc_number}: {e.code}")
    except Exception as e:
        log(f"Error for {epodoc_number}: {e}")

    return []


def parse_claims_xml(xml_data):
    """Parse claims from EPO fulltext XML."""
    claims = []
    ftxt_ns = "{http://www.epo.org/fulltext}"

    try:
        root = ET.fromstring(xml_data)

        for claim in root.findall(f".//{ftxt_ns}claim"):
            claim_num_str = claim.get("num", "0")
            try:
                claim_num = int(claim_num_str)
            except ValueError:
                claim_num = 0

            # Get all claim-text elements and join them
            texts = []
            for ct in claim.findall(f"{ftxt_ns}claim-text"):
                # Get all text including nested elements
                text_parts = []
                if ct.text:
                    text_parts.append(ct.text)
                for child in ct:
                    if child.text:
                        text_parts.append(child.text)
                    if child.tail:
                        text_parts.append(child.tail)
                texts.append("".join(text_parts).strip())

            claim_text = " ".join(texts)

            if claim_text:
                # Detect independent vs dependent
                is_dependent = bool(re.search(r'\bclaims?\s+\d+', claim_text.lower()[:200]))
                claim_type = "dependent" if is_dependent else "independent"

                # Extract depends_on references
                depends_on = None
                if is_dependent:
                    matches = re.findall(r'claim[s]?\s+(\d+)', claim_text.lower())
                    if matches:
                        depends_on = [int(m) for m in matches]

                claims.append({
                    "claim_number": claim_num,
                    "claim_text": claim_text,
                    "claim_type": claim_type,
                    "depends_on": depends_on,
                })

    except ET.ParseError as e:
        log(f"XML parse error: {e}")

    return claims


def main():
    log("=" * 60)
    log("EPO CLAIMS FETCHER (EP/WO Patents)")
    log("=" * 60)

    # Get EP and WO patents from database
    ep_patents = supabase_request("GET", "patents?select=patent_number&patent_number=like.EP*&limit=200")
    wo_patents = supabase_request("GET", "patents?select=patent_number&patent_number=like.WO*&limit=200")

    all_patents = [p["patent_number"] for p in ep_patents + wo_patents]
    log(f"Found {len(all_patents)} EP/WO patents in database")

    # Check existing claims
    try:
        existing = supabase_request("GET", "patent_claims?select=patent_number")
        existing_patents = set(c["patent_number"] for c in existing)
        log(f"Already have claims for {len(existing_patents)} patents")
    except Exception:
        existing_patents = set()

    # Filter to patents needing claims
    to_fetch = [p for p in all_patents if p not in existing_patents]
    log(f"Need to fetch claims for {len(to_fetch)} patents")

    if not to_fetch:
        log("No patents to fetch!")
        return

    auth = EPOAuth()

    total_claims = 0
    patents_with_claims = 0
    errors = 0

    for i, patent_number in enumerate(to_fetch):
        country, doc_number, kind = parse_patent_number(patent_number)

        if not country:
            log(f"  [{i+1}/{len(to_fetch)}] Could not parse: {patent_number}")
            continue

        log(f"  [{i+1}/{len(to_fetch)}] {patent_number}")

        claims = get_claims(auth, country, doc_number)

        if claims:
            patents_with_claims += 1
            log(f"      -> {len(claims)} claims")

            # Insert claims
            for claim in claims:
                try:
                    data = {
                        "patent_number": patent_number,
                        "claim_number": claim["claim_number"],
                        "claim_text": claim["claim_text"],
                        "claim_type": claim["claim_type"],
                    }
                    if claim.get("depends_on"):
                        data["depends_on"] = claim["depends_on"]

                    supabase_request("POST", "patent_claims", data)
                    total_claims += 1
                except Exception as e:
                    if "duplicate key" not in str(e).lower():
                        errors += 1
                        if errors <= 3:
                            log(f"      Error: {e}")
        else:
            log(f"      -> No claims found")

    log("")
    log("=" * 60)
    log("SUMMARY")
    log("=" * 60)
    log(f"Patents with claims: {patents_with_claims}")
    log(f"Total claims inserted: {total_claims}")
    log(f"Errors: {errors}")

    # Verify
    try:
        final_count = supabase_request("GET", "patent_claims?select=id")
        log(f"Total claims in database: {len(final_count)}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
