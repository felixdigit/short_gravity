#!/usr/bin/env python3
"""
AST SpaceMobile Patent Fetcher

Fetches USPTO patent data via PatentsView API:
- Granted patents (AST & Science, LLC + AST&Defense, LLC)
- Pre-grant publications (by Abel Avellan inventor ID)
- Individual patent claims (for claim counting)

Run manually: python3 patent_fetcher.py
"""

from __future__ import annotations
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Optional, Any

# Configuration
API_BASE_URL = "https://search.patentsview.org"
PATENTSVIEW_API_KEY = os.environ.get("PATENTSVIEW_API_KEY", "")

# AST SpaceMobile assignee IDs
ASSIGNEE_IDS = {
    "AST & Science, LLC": "cacf699f-e783-4e35-840c-d1bcea17a2d4",
    "AST&Defense, LLC": "3e2e5dcb-b36d-4ed4-b211-292bf19edd97",
}

# Key inventor for pre-grant publications
ABEL_AVELLAN_ID = "fl:ab_ln:avellan-1"

# Rate limiting: 45 requests/minute
RATE_LIMIT_DELAY = 1.5  # seconds between requests

# Supabase config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


def log(msg: str):
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def api_request(endpoint: str, query: Dict, fields: Optional[List[str]] = None,
                size: int = 100) -> Dict:
    """Make PatentsView API request."""
    if not PATENTSVIEW_API_KEY:
        raise ValueError("PATENTSVIEW_API_KEY not set")

    url = f"{API_BASE_URL}/api/v1/{endpoint}/"
    headers = {
        "X-Api-Key": PATENTSVIEW_API_KEY,
        "Content-Type": "application/json",
    }

    body = {"q": query, "o": {"size": size}}
    if fields:
        body["f"] = fields

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        log(f"API error: {e.code} - {error_body}")
        raise


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


# ============================================================================
# PATENT FETCHING
# ============================================================================

def fetch_granted_patents() -> List[Dict]:
    """Fetch all granted US patents for AST SpaceMobile."""
    all_patents = []

    for assignee_name, assignee_id in ASSIGNEE_IDS.items():
        log(f"Fetching patents for: {assignee_name}")

        query = {"_eq": {"assignees.assignee_id": assignee_id}}
        fields = [
            "patent_id",
            "patent_title",
            "patent_date",
            "patent_type",
            "patent_abstract",
            "patent_processing_days",
            "assignees",
            "inventors",
            "cpc_current",
        ]

        result = api_request("patent", query, fields, size=100)

        if result.get("error"):
            log(f"  Error fetching patents")
            continue

        patents = result.get("patents", [])
        log(f"  Found {result.get('total_hits', 0)} patents")

        for patent in patents:
            patent["source_assignee"] = assignee_name
            all_patents.append(patent)

        time.sleep(RATE_LIMIT_DELAY)

    return all_patents


def fetch_pregrant_publications() -> List[Dict]:
    """Fetch pre-grant publications by Abel Avellan (CEO/inventor)."""
    log(f"Fetching pre-grant publications by Abel Avellan")

    query = {"_eq": {"inventors.inventor_id": ABEL_AVELLAN_ID}}
    fields = [
        "document_number",
        "publication_title",
        "publication_date",
        "publication_type",
        "publication_abstract",
        "assignees",
        "inventors",
        "cpc_current",
    ]

    result = api_request("publication", query, fields, size=100)

    if result.get("error"):
        log(f"  Error fetching publications")
        return []

    publications = result.get("publications", [])
    log(f"  Found {result.get('total_hits', 0)} pre-grant publications")

    return publications


def fetch_patent_claims(patent_id: str) -> List[Dict]:
    """Fetch individual claims for a patent."""
    query = {"patent_id": patent_id}
    fields = [
        "patent_id",
        "claim_sequence",
        "claim_text",
    ]

    result = api_request("g_claim", query, fields, size=200)

    if result.get("error"):
        return []

    return result.get("g_claims", [])


def count_claims_for_patents(patents: List[Dict]) -> Dict[str, int]:
    """Fetch claim counts for all patents."""
    log("Fetching claim counts for each patent...")
    claim_counts = {}

    for i, patent in enumerate(patents):
        patent_id = patent["patent_id"]
        claims = fetch_patent_claims(patent_id)
        claim_count = len(claims)
        claim_counts[patent_id] = claim_count

        if (i + 1) % 10 == 0:
            log(f"  Processed {i + 1}/{len(patents)} patents")

        time.sleep(RATE_LIMIT_DELAY)

    return claim_counts


# ============================================================================
# SUPABASE STORAGE
# ============================================================================

def get_existing_patent_numbers() -> set:
    """Get patent numbers already in database."""
    try:
        result = supabase_request("GET", "patents?select=patent_number")
        return {r["patent_number"] for r in result}
    except Exception as e:
        log(f"Error fetching existing patents: {e}")
        return set()


def get_existing_application_numbers() -> set:
    """Get application document numbers already in database."""
    try:
        result = supabase_request("GET", "patent_applications?select=document_number")
        return {r["document_number"] for r in result}
    except Exception as e:
        log(f"Error fetching existing applications: {e}")
        return set()


def insert_patent(patent: Dict) -> bool:
    """Insert patent into Supabase."""
    try:
        supabase_request("POST", "patents", patent)
        return True
    except Exception as e:
        log(f"Error inserting patent {patent.get('patent_number')}: {e}")
        return False


def insert_application(application: Dict) -> bool:
    """Insert patent application into Supabase."""
    try:
        supabase_request("POST", "patent_applications", application)
        return True
    except Exception as e:
        log(f"Error inserting application {application.get('document_number')}: {e}")
        return False


def transform_patent_for_db(patent: Dict, claim_count: int = 0) -> Dict:
    """Transform PatentsView patent data for existing Supabase schema."""
    assignees = patent.get("assignees", [])
    inventors = patent.get("inventors", [])
    cpc = patent.get("cpc_current", [])

    # Convert patent_id to patent_number format (e.g., "9973266" -> "US9973266B1")
    patent_id = patent["patent_id"]
    patent_number = f"US{patent_id}B1"  # Most AST patents are utility patents (B1)

    return {
        "patent_number": patent_number,
        "patent_id": patent_id,  # Store raw ID too
        "title": patent.get("patent_title"),
        "abstract": patent.get("patent_abstract"),
        "grant_date": patent.get("patent_date"),
        "assignee": assignees[0].get("assignee_organization") if assignees else None,
        "claims_count": claim_count if claim_count > 0 else None,
        "cpc_codes": [c.get("cpc_group_id") for c in cpc] if cpc else [],
        "inventors": [
            {"first": i.get("inventor_name_first"), "last": i.get("inventor_name_last")}
            for i in inventors
        ] if inventors else [],
        "status": "granted",
        "source": "patentsview",
    }


def transform_application_for_db(pub: Dict) -> Dict:
    """Transform PatentsView publication data for Supabase."""
    assignees = pub.get("assignees", [])
    inventors = pub.get("inventors", [])
    cpc = pub.get("cpc_current", [])

    return {
        "document_number": str(pub["document_number"]),
        "publication_title": pub.get("publication_title"),
        "publication_date": pub.get("publication_date"),
        "assignee_organization": assignees[0].get("assignee_organization") if assignees else None,
        "cpc_codes": json.dumps([c.get("cpc_group_id") for c in cpc]) if cpc else None,
        "inventors": json.dumps([
            {"first": i.get("inventor_name_first"), "last": i.get("inventor_name_last")}
            for i in inventors
        ]) if inventors else None,
        "status": "pending",
        "source": "patentsview",
    }


# ============================================================================
# MAIN
# ============================================================================

def run_fetcher(fetch_claims: bool = False, store_to_db: bool = True):
    """Main fetcher."""
    log("=" * 60)
    log("AST SpaceMobile Patent Fetcher")
    log("=" * 60)

    if not PATENTSVIEW_API_KEY:
        log("ERROR: PATENTSVIEW_API_KEY not set")
        sys.exit(1)

    # Fetch granted patents
    patents = fetch_granted_patents()
    log(f"\nTotal granted patents: {len(patents)}")

    # Fetch pre-grant publications
    time.sleep(RATE_LIMIT_DELAY)
    publications = fetch_pregrant_publications()
    log(f"Total pre-grant publications: {len(publications)}")

    # Fetch claim counts (optional, takes longer)
    claim_counts = {}
    if fetch_claims and patents:
        claim_counts = count_claims_for_patents(patents)
        total_claims = sum(claim_counts.values())
        log(f"\nTotal claims across granted patents: {total_claims}")

    # Store to Supabase
    if store_to_db and SUPABASE_SERVICE_KEY:
        log("\nStoring to Supabase...")

        # Patents - match against existing patent_number format
        existing_patents = get_existing_patent_numbers()
        new_patents = [p for p in patents if f"US{p['patent_id']}B1" not in existing_patents]
        log(f"Existing patents in DB: {len(existing_patents)}")
        log(f"New patents to insert: {len(new_patents)}")

        success = 0
        for patent in new_patents:
            claim_count = claim_counts.get(patent["patent_id"], 0)
            db_patent = transform_patent_for_db(patent, claim_count)
            if insert_patent(db_patent):
                success += 1
        log(f"  Inserted {success}/{len(new_patents)} patents")

        # Applications
        existing_apps = get_existing_application_numbers()
        new_apps = [p for p in publications if str(p["document_number"]) not in existing_apps]
        log(f"New applications to insert: {len(new_apps)}")

        success = 0
        for pub in new_apps:
            db_app = transform_application_for_db(pub)
            if insert_application(db_app):
                success += 1
        log(f"  Inserted {success}/{len(new_apps)} applications")

    # Summary
    log("\n" + "=" * 60)
    log("SUMMARY")
    log("=" * 60)
    log(f"Granted US patents: {len(patents)}")
    log(f"Pre-grant publications: {len(publications)}")
    if claim_counts:
        log(f"Total claims (granted): {sum(claim_counts.values())}")
    log("=" * 60)

    return {
        "patents": patents,
        "publications": publications,
        "claim_counts": claim_counts,
    }


def print_report():
    """Print a detailed report without storing to DB."""
    log("=" * 60)
    log("AST SpaceMobile Patent Report (Read-only)")
    log("=" * 60)

    if not PATENTSVIEW_API_KEY:
        log("ERROR: PATENTSVIEW_API_KEY not set")
        sys.exit(1)

    # Fetch data
    patents = fetch_granted_patents()
    time.sleep(RATE_LIMIT_DELAY)
    publications = fetch_pregrant_publications()

    # Print patents
    log("\n" + "-" * 40)
    log("GRANTED US PATENTS")
    log("-" * 40)
    for p in sorted(patents, key=lambda x: x.get("patent_date", ""), reverse=True):
        date = p.get("patent_date", "?")
        title = p.get("patent_title", "?")[:60]
        log(f"  {p['patent_id']} | {date} | {title}...")

    # Print applications
    log("\n" + "-" * 40)
    log("PRE-GRANT PUBLICATIONS")
    log("-" * 40)
    for p in sorted(publications, key=lambda x: x.get("publication_date", ""), reverse=True):
        date = p.get("publication_date", "?")
        title = p.get("publication_title", "?")[:60]
        log(f"  {p['document_number']} | {date} | {title}...")

    # Summary
    log("\n" + "=" * 60)
    log(f"Total granted: {len(patents)} | Total pending: {len(publications)}")
    log("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--report":
            print_report()
        elif sys.argv[1] == "--with-claims":
            run_fetcher(fetch_claims=True)
        elif sys.argv[1] == "--dry-run":
            run_fetcher(store_to_db=False)
        else:
            log("Usage: python3 patent_fetcher.py [--report|--with-claims|--dry-run]")
    else:
        run_fetcher()
