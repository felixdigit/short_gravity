#!/usr/bin/env python3
"""
EPO OPS Patent Fetcher

Fetches AST SpaceMobile patent data from EPO Open Patent Services API.
Covers global patents: US, EP, KR, AU, CA, JP, WO, etc.

Features:
- OAuth2 authentication with auto-refresh
- Applicant search across EPO/INPADOC database
- Family expansion to get all related publications
- Claim extraction for claim counting
- Rate limiting (20 req/min free tier)
- Supabase integration

Run: python3 epo_patent_fetcher.py [--dry-run|--report|--claims]
"""

from __future__ import annotations
import base64
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

# Supabase config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# EPO OPS config
EPO_CONSUMER_KEY = os.environ.get("EPO_CONSUMER_KEY", "")
EPO_CONSUMER_SECRET = os.environ.get("EPO_CONSUMER_SECRET", "")

# EPO API endpoints
EPO_AUTH_URL = "https://ops.epo.org/3.2/auth/accesstoken"
EPO_API_BASE = "https://ops.epo.org/3.2/rest-services"

# Search queries - EPO CQL syntax
# Note: Quoted phrases return 0 results; use unquoted terms + combinators
SEARCH_QUERIES = [
    "pa=AST and ta=satellite",       # AST applicant + satellite in title/abstract (72 results)
    "in=Avellan and ta=satellite",   # Abel Avellan inventor + satellite (67 results)
    "pa=AST and ta=cellular",        # AST + cellular
    "pa=AST and ta=mobile",          # AST + mobile
]

# Rate limiting
RATE_LIMIT_DELAY = 3.1  # seconds between requests (20/min = 3s, add buffer)
last_request_time = 0

# XML namespaces used by EPO OPS
NS = {
    "ops": "http://ops.epo.org",
    "epo": "http://www.epo.org/exchange",
    "exch": "http://www.epo.org/exchange",
}


def log(msg: str):
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def rate_limit():
    """Enforce rate limiting between EPO requests."""
    global last_request_time
    elapsed = time.time() - last_request_time
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)
    last_request_time = time.time()


class EPOAuth:
    """Handles EPO OPS OAuth2 authentication."""

    def __init__(self, consumer_key: str, consumer_secret: str):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None

    def get_token(self) -> str:
        """Get valid access token, refreshing if needed."""
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token

        return self._fetch_new_token()

    def _fetch_new_token(self) -> str:
        """Fetch new OAuth2 access token."""
        credentials = f"{self.consumer_key}:{self.consumer_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = "grant_type=client_credentials".encode()

        req = urllib.request.Request(EPO_AUTH_URL, data=data, headers=headers, method="POST")

        try:
            rate_limit()
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode())
                self.access_token = result["access_token"]
                expires_in = int(result.get("expires_in", 1200))
                self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)
                log(f"Got EPO access token (expires in {expires_in}s)")
                return self.access_token
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            log(f"EPO auth error: {e.code} - {error_body}")
            if e.code == 401:
                log("\n" + "=" * 60)
                log("AUTHENTICATION FAILED")
                log("=" * 60)
                log("Please verify in the EPO Developer Portal:")
                log("1. Go to https://developers.epo.org/user/apps")
                log("2. Click on 'Short Gravity Terminal' app")
                log("3. Go to 'Products' tab")
                log("4. Enable 'Open Patent Services' product")
                log("5. Wait a few minutes for activation")
                log("=" * 60)
            raise


class EPOClient:
    """EPO OPS API client."""

    def __init__(self, auth: EPOAuth):
        self.auth = auth

    def _request(self, endpoint: str, accept: str = "application/xml") -> str:
        """Make authenticated request to EPO OPS."""
        url = f"{EPO_API_BASE}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.auth.get_token()}",
            "Accept": accept,
        }

        req = urllib.request.Request(url, headers=headers, method="GET")

        try:
            rate_limit()
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read().decode()
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            if e.code == 404:
                return ""  # No results
            log(f"EPO API error ({endpoint}): {e.code} - {error_body[:200]}")
            if e.code == 403 and "quota" in error_body.lower():
                log("Rate limit exceeded - waiting 60s")
                time.sleep(60)
                return self._request(endpoint, accept)
            raise

    def search_applicant(self, name: str, start: int = 1, end: int = 100) -> List[Dict]:
        """Search for patents by applicant name (legacy - use search_query instead)."""
        return self.search_query(f'pa="{name}"', start, end)

    def search_query(self, query: str, start: int = 1, end: int = 100) -> List[Dict]:
        """Search for patents using EPO CQL query syntax."""
        encoded_query = urllib.parse.quote(query)
        endpoint = f"published-data/search?q={encoded_query}&Range={start}-{end}"

        log(f"Searching: {query}")
        xml_response = self._request(endpoint)

        if not xml_response:
            return []

        # Extract total count
        import re
        match = re.search(r'total-result-count="(\d+)"', xml_response)
        if match:
            log(f"  -> {match.group(1)} total results")

        return self._parse_search_results(xml_response)

    def _parse_search_results(self, xml_data: str) -> List[Dict]:
        """Parse EPO search results XML."""
        results = []
        try:
            root = ET.fromstring(xml_data)

            # Find all publication references (ops: namespace)
            # Note: document-id children are in default namespace (epo/exch)
            for pub_ref in root.findall(".//ops:publication-reference", NS):
                # Try both namespace variants for document-id
                doc_id = pub_ref.find(".//exch:document-id[@document-id-type='docdb']", NS)
                if doc_id is None:
                    doc_id = pub_ref.find(".//{http://www.epo.org/exchange}document-id[@document-id-type='docdb']")
                if doc_id is None:
                    # Try without namespace (default namespace)
                    doc_id = pub_ref.find(".//document-id[@document-id-type='docdb']")

                if doc_id is not None:
                    # Extract with fallback for namespace variants
                    country = (
                        doc_id.findtext("exch:country", "", NS) or
                        doc_id.findtext("{http://www.epo.org/exchange}country", "") or
                        doc_id.findtext("country", "")
                    )
                    doc_number = (
                        doc_id.findtext("exch:doc-number", "", NS) or
                        doc_id.findtext("{http://www.epo.org/exchange}doc-number", "") or
                        doc_id.findtext("doc-number", "")
                    )
                    kind = (
                        doc_id.findtext("exch:kind", "", NS) or
                        doc_id.findtext("{http://www.epo.org/exchange}kind", "") or
                        doc_id.findtext("kind", "")
                    )

                    if country and doc_number:
                        results.append({
                            "country": country,
                            "doc_number": doc_number,
                            "kind": kind or "",
                            "docdb": f"{country}.{doc_number}.{kind}",
                        })
        except ET.ParseError as e:
            log(f"XML parse error: {e}")

        return results

    def get_family(self, country: str, doc_number: str, kind: str = "") -> Dict:
        """Get patent family information."""
        doc_id = f"{country}.{doc_number}"
        if kind:
            doc_id += f".{kind}"

        endpoint = f"family/publication/docdb/{doc_id}"
        xml_response = self._request(endpoint)

        if not xml_response:
            return {"family_id": None, "members": []}

        return self._parse_family(xml_response)

    def _parse_family(self, xml_data: str) -> Dict:
        """Parse EPO family response XML."""
        family_data = {"family_id": None, "members": []}
        epo_ns = "{http://www.epo.org/exchange}"

        try:
            root = ET.fromstring(xml_data)

            # Get all family members (ops:family-member has family-id attribute)
            for member in root.findall(".//ops:family-member", NS):
                fam_id = member.get("family-id")
                if fam_id and not family_data["family_id"]:
                    family_data["family_id"] = fam_id

                # publication-reference is in default namespace (no prefix)
                pub_ref = member.find(f".//{epo_ns}publication-reference")
                if pub_ref is None:
                    pub_ref = member.find(".//publication-reference")

                if pub_ref is not None:
                    doc_id = pub_ref.find(f".//{epo_ns}document-id[@document-id-type='docdb']")
                    if doc_id is None:
                        doc_id = pub_ref.find(".//document-id[@document-id-type='docdb']")

                    if doc_id is not None:
                        country = (
                            doc_id.findtext(f"{epo_ns}country", "") or
                            doc_id.findtext("country", "")
                        )
                        doc_number = (
                            doc_id.findtext(f"{epo_ns}doc-number", "") or
                            doc_id.findtext("doc-number", "")
                        )
                        kind = (
                            doc_id.findtext(f"{epo_ns}kind", "") or
                            doc_id.findtext("kind", "")
                        )

                        if country and doc_number:
                            family_data["members"].append({
                                "country": country,
                                "doc_number": doc_number,
                                "kind": kind or "",
                                "title": "",  # Not in family response
                                "applicant": "",  # Not in family response
                                "docdb": f"{country}.{doc_number}.{kind}" if kind else f"{country}.{doc_number}",
                            })
        except ET.ParseError as e:
            log(f"Family XML parse error: {e}")

        return family_data

    def get_biblio(self, country: str, doc_number: str, kind: str = "") -> Dict:
        """Get bibliographic data for a patent."""
        doc_id = f"{country}.{doc_number}"
        if kind:
            doc_id += f".{kind}"

        endpoint = f"published-data/publication/docdb/{doc_id}/biblio"
        xml_response = self._request(endpoint)

        if not xml_response:
            return {}

        return self._parse_biblio(xml_response)

    def _parse_biblio(self, xml_data: str) -> Dict:
        """Parse bibliographic data XML."""
        biblio = {
            "title": "",
            "abstract": "",
            "inventors": [],
            "applicants": [],
            "ipc_codes": [],
            "cpc_codes": [],
            "priority_date": "",
            "publication_date": "",
            "application_date": "",
        }

        try:
            root = ET.fromstring(xml_data)

            # Title
            for title in root.findall(".//exch:invention-title", NS):
                if title.get("lang") == "en":
                    biblio["title"] = title.text or ""
                    break
                elif not biblio["title"]:
                    biblio["title"] = title.text or ""

            # Abstract
            for abstract in root.findall(".//exch:abstract", NS):
                if abstract.get("lang") == "en":
                    biblio["abstract"] = "".join(abstract.itertext())
                    break

            # Inventors
            for inv in root.findall(".//exch:inventor/exch:inventor-name/exch:name", NS):
                if inv.text:
                    biblio["inventors"].append(inv.text)

            # Applicants
            for app in root.findall(".//exch:applicant/exch:applicant-name/exch:name", NS):
                if app.text:
                    biblio["applicants"].append(app.text)

            # IPC codes
            for ipc in root.findall(".//exch:classification-ipc/exch:text", NS):
                if ipc.text:
                    biblio["ipc_codes"].append(ipc.text.strip())

            # Dates
            for date in root.findall(".//exch:publication-reference//exch:date", NS):
                if date.text:
                    biblio["publication_date"] = date.text
                    break

            for date in root.findall(".//exch:application-reference//exch:date", NS):
                if date.text:
                    biblio["application_date"] = date.text
                    break

            for priority in root.findall(".//exch:priority-claim//exch:date", NS):
                if priority.text:
                    biblio["priority_date"] = priority.text
                    break

        except ET.ParseError as e:
            log(f"Biblio XML parse error: {e}")

        return biblio

    def get_claims(self, country: str, doc_number: str, kind: str = "") -> Dict:
        """Get claims for a patent."""
        doc_id = f"{country}.{doc_number}"
        if kind:
            doc_id += f".{kind}"

        endpoint = f"published-data/publication/docdb/{doc_id}/claims"
        xml_response = self._request(endpoint)

        if not xml_response:
            return {"claims": [], "claim_count": 0}

        return self._parse_claims(xml_response)

    def _parse_claims(self, xml_data: str) -> Dict:
        """Parse claims XML."""
        claims_data = {"claims": [], "claim_count": 0}

        try:
            root = ET.fromstring(xml_data)

            # Find all claim elements
            for claim in root.findall(".//exch:claim", NS):
                claim_num = claim.get("num", "")
                claim_text = "".join(claim.itertext()).strip()
                if claim_text:
                    claims_data["claims"].append({
                        "number": claim_num,
                        "text": claim_text[:500],  # Truncate for storage
                    })

            claims_data["claim_count"] = len(claims_data["claims"])

        except ET.ParseError as e:
            log(f"Claims XML parse error: {e}")

        return claims_data


def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Any:
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


def run_fetch(dry_run: bool = False, fetch_claims: bool = False):
    """Main fetch function."""
    log("=" * 60)
    log("EPO OPS Patent Fetcher")
    log("=" * 60)

    if not EPO_CONSUMER_KEY or not EPO_CONSUMER_SECRET:
        log("ERROR: EPO credentials not set")
        log("Set EPO_CONSUMER_KEY and EPO_CONSUMER_SECRET in .env")
        sys.exit(1)

    # Initialize
    auth = EPOAuth(EPO_CONSUMER_KEY, EPO_CONSUMER_SECRET)
    client = EPOClient(auth)

    # Search for all AST patents using multiple queries
    all_results = []
    seen_docdb = set()

    for query in SEARCH_QUERIES:
        results = client.search_query(query)
        log(f"  Found {len(results)} results for '{query}'")

        for r in results:
            if r["docdb"] not in seen_docdb:
                seen_docdb.add(r["docdb"])
                all_results.append(r)

    log(f"\nTotal unique publications found: {len(all_results)}")

    if not all_results:
        log("No results found")
        return

    # Get family information for each result
    families = {}
    family_members_all = []

    log("\nFetching family information...")
    for i, pub in enumerate(all_results[:10]):  # Limit to first 10 for now (rate limits)
        log(f"  [{i+1}/{min(len(all_results), 10)}] {pub['docdb']}")

        family_data = client.get_family(pub["country"], pub["doc_number"], pub["kind"])

        if family_data["family_id"]:
            fam_id = family_data["family_id"]
            if fam_id not in families:
                families[fam_id] = {
                    "family_id": fam_id,
                    "members": [],
                    "countries": set(),
                }

            for member in family_data["members"]:
                if member["docdb"] not in [m["docdb"] for m in families[fam_id]["members"]]:
                    families[fam_id]["members"].append(member)
                    families[fam_id]["countries"].add(member["country"])
                    family_members_all.append(member)

    # Summary
    log("\n" + "=" * 60)
    log("SUMMARY")
    log("=" * 60)
    log(f"Patent families: {len(families)}")
    log(f"Total family members: {len(family_members_all)}")

    # Country breakdown
    country_counts = {}
    for member in family_members_all:
        country = member["country"]
        country_counts[country] = country_counts.get(country, 0) + 1

    log("\nCountry breakdown:")
    for country, count in sorted(country_counts.items(), key=lambda x: -x[1]):
        log(f"  {country}: {count}")

    # Sample family
    if families:
        sample_fam = list(families.values())[0]
        log(f"\nSample family ({sample_fam['family_id']}):")
        log(f"  Members: {len(sample_fam['members'])}")
        log(f"  Countries: {', '.join(sample_fam['countries'])}")
        if sample_fam["members"]:
            log(f"  First title: {sample_fam['members'][0].get('title', 'N/A')[:60]}...")

    if dry_run:
        log("\n[DRY RUN] Would save to Supabase")
        return families

    # Save to Supabase
    if not SUPABASE_SERVICE_KEY:
        log("\nSUPABASE_SERVICE_KEY not set - skipping DB save")
        return families

    log("\nSaving to Supabase...")
    inserted = 0

    for member in family_members_all:
        # Create patent number format: CC{number}{kind}
        patent_number = f"{member['country']}{member['doc_number']}{member['kind']}"

        record = {
            "patent_number": patent_number,
            "title": member.get("title", ""),
            "assignee": member.get("applicant", "AST & Science LLC"),
            "status": "granted" if member["kind"].startswith("B") else "pending",
            "source": "epo_ops",
        }

        try:
            # Check if exists
            existing = supabase_request(
                "GET",
                f"patents?patent_number=eq.{patent_number}&select=id"
            )

            if not existing:
                supabase_request("POST", "patents", record)
                inserted += 1
        except Exception as e:
            log(f"Error saving {patent_number}: {e}")

    log(f"Inserted {inserted} new patents")

    return families


def run_report():
    """Generate report without saving."""
    log("=" * 60)
    log("EPO OPS Patent Report (Read-Only)")
    log("=" * 60)

    if not EPO_CONSUMER_KEY or not EPO_CONSUMER_SECRET:
        log("ERROR: EPO credentials not set")
        sys.exit(1)

    auth = EPOAuth(EPO_CONSUMER_KEY, EPO_CONSUMER_SECRET)
    client = EPOClient(auth)

    # Quick search using working queries
    all_patents = []
    seen = set()

    for query in SEARCH_QUERIES:
        results = client.search_query(query, start=1, end=25)

        for r in results:
            if r["docdb"] not in seen:
                seen.add(r["docdb"])
                all_patents.append(r)

    log(f"\nTotal unique patents found: {len(all_patents)}")
    log("\nSample patents:")
    for p in all_patents[:10]:
        log(f"  {p['country']}{p['doc_number']}{p['kind']}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--report":
            run_report()
        elif sys.argv[1] == "--dry-run":
            run_fetch(dry_run=True)
        elif sys.argv[1] == "--claims":
            run_fetch(dry_run=True, fetch_claims=True)
        else:
            log("Usage: python3 epo_patent_fetcher.py [--report|--dry-run|--claims]")
    else:
        run_fetch()
