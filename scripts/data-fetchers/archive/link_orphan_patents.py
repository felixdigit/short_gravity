#!/usr/bin/env python3
"""
Link Orphan Patents to Families

Queries EPO family endpoint for patents without family_id,
updates them with their DOCDB family identifier.

Run: python3 link_orphan_patents.py
"""

import json
import os
import re
import time
import urllib.request
import urllib.error
import base64
from datetime import datetime, timedelta

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


def get_family_id(auth, country, doc_number, kind=""):
    """Get family_id from EPO for a patent."""
    doc_id = f"{country}.{doc_number}"
    if kind:
        doc_id += f".{kind}"

    url = f"{EPO_API_BASE}/family/publication/docdb/{doc_id}"
    headers = {
        "Authorization": f"Bearer {auth.get_token()}",
        "Accept": "application/xml",
    }

    req = urllib.request.Request(url, headers=headers)

    try:
        rate_limit()
        with urllib.request.urlopen(req, timeout=30) as response:
            xml = response.read().decode()

            # Extract family-id from XML
            match = re.search(r'family-id="(\d+)"', xml)
            if match:
                return match.group(1)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        log(f"EPO error for {doc_id}: {e.code}")
    except Exception as e:
        log(f"Error for {doc_id}: {e}")

    return None


def parse_patent_number(pn):
    """Parse patent number into (country, number, kind)."""
    # US9973266B1 -> ('US', '9973266', 'B1')
    # US20210044349A1 -> ('US', '20210044349', 'A1')
    match = re.match(r'([A-Z]{2})(\d+)([A-Z]\d?)?', pn)
    if match:
        country, num, kind = match.groups()
        return country, num, kind or ""
    return None, None, None


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


def main():
    log("=" * 60)
    log("LINK ORPHAN PATENTS TO FAMILIES")
    log("=" * 60)

    # Get orphan patents
    orphans = supabase_request("GET", "patents?select=patent_number&family_id=is.null")
    log(f"Found {len(orphans)} orphan patents")

    if not orphans:
        log("No orphans to process")
        return

    auth = EPOAuth()

    linked = 0
    not_found = 0
    families_found = set()

    for i, patent in enumerate(orphans):
        pn = patent["patent_number"]
        country, num, kind = parse_patent_number(pn)

        if not country:
            log(f"  [{i+1}/{len(orphans)}] Could not parse: {pn}")
            continue

        log(f"  [{i+1}/{len(orphans)}] {pn}")

        family_id = get_family_id(auth, country, num, kind)

        if family_id:
            # Update patent with family_id
            try:
                supabase_request(
                    "PATCH",
                    f"patents?patent_number=eq.{pn}",
                    {"family_id": family_id}
                )
                linked += 1
                families_found.add(family_id)
                log(f"      -> family {family_id}")
            except Exception as e:
                log(f"      -> Error updating: {e}")
        else:
            not_found += 1
            log(f"      -> Not found in EPO")

    log("")
    log("=" * 60)
    log("SUMMARY")
    log("=" * 60)
    log(f"Patents linked: {linked}")
    log(f"Not found in EPO: {not_found}")
    log(f"Unique families discovered: {len(families_found)}")

    if families_found:
        log(f"\nNew family IDs: {sorted(families_found)[:10]}...")


if __name__ == "__main__":
    main()
