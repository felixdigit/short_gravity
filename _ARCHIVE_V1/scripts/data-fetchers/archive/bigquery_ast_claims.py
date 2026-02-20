#!/usr/bin/env python3
"""
BigQuery AST Claims Fetcher

Fetches ALL AST & Science / AST SpaceMobile US patent claims from BigQuery.
Queries by assignee name rather than patent numbers for complete coverage.

Run: python3 bigquery_ast_claims.py
"""

import json
import os
import re
import urllib.request
from datetime import datetime

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
GCP_PROJECT = "short-gravity-data"


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

    with urllib.request.urlopen(req, timeout=60) as response:
        content = response.read().decode("utf-8")
        return json.loads(content) if content else {}


def split_claims(text):
    """Split claim text blob into individual claims."""
    # Handle both "1." and "1 ." formats
    pattern = r'(?:^|\n)\s*(\d+)\s*\.\s*'
    matches = list(re.finditer(pattern, text))

    if not matches:
        return [{"number": 1, "text": text.strip()}]

    claims = []
    for i, match in enumerate(matches):
        claim_num = int(match.group(1))
        start = match.end()

        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)

        claim_text = text[start:end].strip()

        if claim_text:
            claims.append({
                "number": claim_num,
                "text": claim_text
            })

    return claims


def parse_claim_type(claim_text):
    """Determine if claim is independent or dependent."""
    if not claim_text:
        return "independent"

    text_lower = claim_text.lower()[:300]

    if re.search(r'\bof\s+claim\s+\d+', text_lower):
        return "dependent"
    if re.search(r'\baccording\s+to\s+claim\s+\d+', text_lower):
        return "dependent"
    if re.search(r'\bas\s+(?:claimed|recited)\s+in\s+claim\s+\d+', text_lower):
        return "dependent"
    if re.search(r'^the\s+\w+\s+of\s+claim\s+\d+', text_lower):
        return "dependent"

    return "independent"


def parse_depends_on(claim_text):
    """Extract claim numbers this claim depends on."""
    if not claim_text:
        return None

    matches = re.findall(r'claim[s]?\s+(\d+)', claim_text.lower()[:500])
    if matches:
        return [int(m) for m in matches[:5]]
    return None


def bq_to_our_format(bq_number):
    """Convert BigQuery format to our format.
    US-9973266-B1 -> US9973266B1
    """
    return bq_number.replace("-", "")


def main():
    log("=" * 60)
    log("BIGQUERY AST CLAIMS FETCHER")
    log("=" * 60)

    from google.cloud import bigquery
    client = bigquery.Client(project=GCP_PROJECT)

    # Query ALL AST patents with claims from BigQuery
    log("Querying BigQuery for all AST US patents...")

    query = '''
    SELECT
      publication_number,
      claims.text as claim_text
    FROM `patents-public-data.patents.publications`,
    UNNEST(claims_localized) as claims
    WHERE EXISTS (
      SELECT 1 FROM UNNEST(assignee_harmonized) a
      WHERE LOWER(a.name) LIKE "%ast & science%"
         OR LOWER(a.name) LIKE "%ast spacemobile%"
    )
    AND country_code = "US"
    AND claims.language = "en"
    ORDER BY publication_number
    '''

    results = list(client.query(query))
    log(f"BigQuery returned {len(results)} patents with claims")

    # Get existing claims
    try:
        existing = supabase_request("GET", "patent_claims?select=patent_number")
        existing_patents = set(c["patent_number"] for c in existing)
        log(f"Already have claims for {len(existing_patents)} patents")
    except Exception:
        existing_patents = set()

    # Process and insert
    total_inserted = 0
    total_errors = 0
    patents_processed = 0

    for record in results:
        bq_pn = record.publication_number
        our_pn = bq_to_our_format(bq_pn)

        # Skip if we already have claims for this patent
        if our_pn in existing_patents:
            continue

        patents_processed += 1
        claims = split_claims(record.claim_text)
        log(f"  {our_pn}: {len(claims)} claims")

        for claim in claims:
            claim_type = parse_claim_type(claim["text"])
            depends_on = parse_depends_on(claim["text"])

            try:
                data = {
                    "patent_number": our_pn,
                    "claim_number": claim["number"],
                    "claim_text": claim["text"],
                    "claim_type": claim_type,
                }
                if depends_on:
                    data["depends_on"] = depends_on

                supabase_request("POST", "patent_claims", data)
                total_inserted += 1
            except Exception as e:
                if "duplicate key" not in str(e).lower():
                    total_errors += 1
                    if total_errors <= 5:
                        log(f"    Error: {e}")

    log("")
    log("=" * 60)
    log("SUMMARY")
    log("=" * 60)
    log(f"Patents processed: {patents_processed}")
    log(f"Claims inserted: {total_inserted}")
    log(f"Errors: {total_errors}")

    # Final count
    try:
        final = supabase_request("GET", "patent_claims?select=id")
        log(f"Total claims in database: {len(final)}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
