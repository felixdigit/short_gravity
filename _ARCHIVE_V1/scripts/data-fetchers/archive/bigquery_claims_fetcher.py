#!/usr/bin/env python3
"""
BigQuery Patent Claims Fetcher

Fetches full claim text from Google BigQuery patents-public-data
for all US patents in the database.

Prerequisites:
1. gcloud CLI installed: brew install google-cloud-sdk
2. Authenticated: gcloud auth application-default login
3. Project set: gcloud config set project YOUR_PROJECT_ID

Run: python3 bigquery_claims_fetcher.py
"""

import json
import os
import re
import urllib.request
from datetime import datetime

# Supabase config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# BigQuery config
GCP_PROJECT = os.environ.get("GCP_PROJECT", "")


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


def normalize_patent_number(pn):
    """
    Convert patent number to BigQuery format.
    US10892818B1 -> US-10892818-B1
    US20210044349A1 -> US-20210044349-A1
    """
    # Already in correct format
    if "-" in pn:
        return pn

    # Match pattern: COUNTRY + NUMBER + KIND
    match = re.match(r'([A-Z]{2,3})(\d+)([A-Z]\d?)?$', pn)
    if match:
        country, num, kind = match.groups()
        if kind:
            return f"{country}-{num}-{kind}"
        return f"{country}-{num}"

    # Handle application format: US2021044349A1 -> US-2021044349-A1
    match = re.match(r'([A-Z]{2,3})(\d{4})(\d+)([A-Z]\d)$', pn)
    if match:
        country, year, num, kind = match.groups()
        return f"{country}-{year}{num}-{kind}"

    return pn


def get_us_patents():
    """Get all US patent numbers from database."""
    patents = supabase_request(
        "GET",
        "patents?select=patent_number&patent_number=like.US*&limit=500"
    )
    return [p["patent_number"] for p in patents]


def get_existing_claims():
    """Get patent numbers that already have claims."""
    claims = supabase_request(
        "GET",
        "patent_claims?select=patent_number"
    )
    return set(c["patent_number"] for c in claims)


def run_bigquery(query):
    """Execute BigQuery query using gcloud CLI."""
    import subprocess

    cmd = [
        "bq", "query",
        "--use_legacy_sql=false",
        "--format=json",
        "--max_rows=50000",
        query
    ]

    if GCP_PROJECT:
        cmd.insert(2, f"--project_id={GCP_PROJECT}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        log(f"BigQuery error: {result.stderr}")
        return []

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        log(f"Failed to parse BigQuery output: {result.stdout[:500]}")
        return []


def fetch_claims_batch(patent_numbers):
    """Fetch claims for a batch of patents from BigQuery."""
    # Convert to BigQuery format
    bq_numbers = [normalize_patent_number(pn) for pn in patent_numbers]

    # Build IN clause
    in_clause = ", ".join(f"'{pn}'" for pn in bq_numbers)

    query = f"""
    SELECT
      publication_number,
      claims.text AS claim_text,
      claims.claim_number
    FROM `patents-public-data.patents.publications`,
    UNNEST(claims_localized) AS claims
    WHERE publication_number IN ({in_clause})
    AND claims.language = 'en'
    ORDER BY publication_number, claims.claim_number
    """

    return run_bigquery(query)


def parse_claim_type(claim_text):
    """Determine if claim is independent or dependent."""
    if not claim_text:
        return None

    text_lower = claim_text.lower().strip()

    # Dependent claims typically reference other claims
    dependent_patterns = [
        r'^the .* of claim \d+',
        r'^a .* according to claim \d+',
        r'^claim \d+',
        r'as claimed in claim \d+',
        r'as recited in claim \d+',
    ]

    for pattern in dependent_patterns:
        if re.search(pattern, text_lower):
            return "dependent"

    return "independent"


def parse_depends_on(claim_text):
    """Extract claim numbers this claim depends on."""
    if not claim_text:
        return None

    # Find references like "claim 1", "claims 1-5", "claim 1 or 2"
    matches = re.findall(r'claim[s]?\s+(\d+(?:\s*[-,]\s*\d+)*)', claim_text.lower())

    if not matches:
        return None

    depends = set()
    for match in matches:
        # Handle ranges like "1-5"
        if '-' in match:
            parts = match.split('-')
            try:
                start = int(parts[0].strip())
                end = int(parts[1].strip())
                depends.update(range(start, end + 1))
            except ValueError:
                pass
        else:
            # Handle individual numbers
            for num in re.findall(r'\d+', match):
                depends.add(int(num))

    return list(sorted(depends)) if depends else None


def denormalize_patent_number(bq_number, original_numbers):
    """Convert BigQuery format back to our format."""
    # bq_number: US-10892818-B1
    # We need to find the matching original: US10892818B1

    bq_clean = bq_number.replace("-", "")

    for orig in original_numbers:
        if orig.replace("-", "") == bq_clean:
            return orig

    # If no exact match, return the cleaned version
    return bq_clean


def insert_claims(claims_data, original_numbers):
    """Insert claims into database."""
    inserted = 0
    errors = 0

    for claim in claims_data:
        bq_pn = claim.get("publication_number", "")
        claim_num = claim.get("claim_number")
        claim_text = claim.get("claim_text", "")

        if not bq_pn or not claim_num or not claim_text:
            continue

        # Convert back to our format
        patent_number = denormalize_patent_number(bq_pn, original_numbers)
        claim_type = parse_claim_type(claim_text)
        depends_on = parse_depends_on(claim_text)

        try:
            data = {
                "patent_number": patent_number,
                "claim_number": int(claim_num),
                "claim_text": claim_text,
                "claim_type": claim_type,
            }
            if depends_on:
                data["depends_on"] = depends_on

            supabase_request(
                "POST",
                "patent_claims?on_conflict=patent_number,claim_number",
                data
            )
            inserted += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                log(f"  Error inserting claim {patent_number}#{claim_num}: {e}")

    return inserted, errors


def main():
    log("=" * 60)
    log("BIGQUERY PATENT CLAIMS FETCHER")
    log("=" * 60)

    # Get US patents from database
    us_patents = get_us_patents()
    log(f"Found {len(us_patents)} US patents in database")

    # Filter to granted patents only (B1, B2 - not applications)
    granted = [p for p in us_patents if re.search(r'B\d$', p)]
    applications = [p for p in us_patents if re.search(r'A\d$', p)]
    design = [p for p in us_patents if p.startswith("USD")]

    log(f"  Granted patents: {len(granted)}")
    log(f"  Applications: {len(applications)}")
    log(f"  Design patents: {len(design)}")

    # Check existing claims
    existing = get_existing_claims()
    log(f"Already have claims for {len(existing)} patents")

    # Filter out patents we already have
    to_fetch = [p for p in granted if p not in existing]
    log(f"Need to fetch claims for {len(to_fetch)} patents")

    if not to_fetch:
        log("No patents to fetch!")
        return

    # Process in batches of 50 (BigQuery query size limit)
    batch_size = 50
    total_claims = 0
    total_errors = 0

    for i in range(0, len(to_fetch), batch_size):
        batch = to_fetch[i:i + batch_size]
        log(f"\nBatch {i // batch_size + 1}: {len(batch)} patents")

        # Fetch from BigQuery
        claims_data = fetch_claims_batch(batch)
        log(f"  BigQuery returned {len(claims_data)} claims")

        if claims_data:
            inserted, errors = insert_claims(claims_data, to_fetch)
            total_claims += inserted
            total_errors += errors
            log(f"  Inserted: {inserted}, Errors: {errors}")

    # Summary
    log("\n" + "=" * 60)
    log("SUMMARY")
    log("=" * 60)
    log(f"Total claims inserted: {total_claims}")
    log(f"Total errors: {total_errors}")

    # Verify
    final_count = supabase_request("GET", "patent_claims?select=id")
    log(f"Total claims in database: {len(final_count)}")


if __name__ == "__main__":
    main()
