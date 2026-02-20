#!/usr/bin/env python3
"""
Patent RAG Builder

Populates the RAG-optimized fields in the patents table:
1. claims_text - Aggregated claims from patent_claims table
2. content_text - Combined title + abstract + claims for full-text search
3. content_hash - SHA-256 hash for deduplication

Usage:
    python3 patent_rag_builder.py
    python3 patent_rag_builder.py --patent US12345678B2  # Single patent

Requirements: SUPABASE_URL, SUPABASE_SERVICE_KEY in .env
"""

import argparse
import hashlib
import json
import os
import urllib.request
import urllib.error
from datetime import datetime

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def supabase_request(method: str, endpoint: str, data=None):
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

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            content = response.read().decode("utf-8")
            return json.loads(content) if content else []
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        raise Exception(f"Supabase {e.code}: {error_body[:200]}")


def fetch_paginated(endpoint: str, fields: str, filter_str: str = ""):
    """Fetch all records with pagination."""
    all_records = []
    offset = 0
    batch_size = 1000

    while True:
        url = f"{endpoint}?select={fields}&limit={batch_size}&offset={offset}"
        if filter_str:
            url += f"&{filter_str}"

        records = supabase_request("GET", url)
        if not records:
            break
        all_records.extend(records)
        if len(records) < batch_size:
            break
        offset += batch_size

    return all_records


def get_claims_for_patent(patent_number: str) -> list:
    """Get all claims for a patent, ordered by claim number."""
    claims = supabase_request(
        "GET",
        f"patent_claims?patent_number=eq.{patent_number}&select=claim_number,claim_text&order=claim_number"
    )
    return claims


def build_claims_text(claims: list) -> str:
    """Build aggregated claims text."""
    if not claims:
        return ""

    lines = []
    for c in claims:
        num = c.get("claim_number", 0)
        text = c.get("claim_text", "").strip()
        if text:
            # Only add claim number prefix if not already present
            if not text.startswith(f"{num}.") and not text.startswith(f"{num} "):
                lines.append(f"{num}. {text}")
            else:
                lines.append(text)

    return "\n\n".join(lines)


def build_content_text(title: str, abstract: str, claims_text: str) -> str:
    """Build combined content for RAG search."""
    parts = []

    if title:
        parts.append(f"TITLE: {title}")

    if abstract:
        parts.append(f"ABSTRACT: {abstract}")

    if claims_text:
        parts.append(f"CLAIMS:\n{claims_text}")

    return "\n\n".join(parts)


def compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of content."""
    if not content:
        return ""
    return hashlib.sha256(content.encode()).hexdigest()


def update_patent(patent_number: str, claims_text: str, content_text: str, content_hash: str):
    """Update patent with RAG fields."""
    # URL encode the patent number for the query
    encoded_pn = patent_number.replace("/", "%2F")

    supabase_request(
        "PATCH",
        f"patents?patent_number=eq.{encoded_pn}",
        {
            "claims_text": claims_text if claims_text else None,
            "content_text": content_text if content_text else None,
            "content_hash": content_hash if content_hash else None,
        }
    )


def process_patent(patent: dict) -> dict:
    """Process a single patent and return stats."""
    pn = patent["patent_number"]
    title = patent.get("title") or ""
    abstract = patent.get("abstract") or ""

    # Get claims
    claims = get_claims_for_patent(pn)
    claims_text = build_claims_text(claims)

    # Build combined content
    content_text = build_content_text(title, abstract, claims_text)
    content_hash = compute_content_hash(content_text)

    # Update
    update_patent(pn, claims_text, content_text, content_hash)

    return {
        "patent_number": pn,
        "claims_count": len(claims),
        "content_length": len(content_text),
    }


def main():
    parser = argparse.ArgumentParser(description="Build RAG fields for patents")
    parser.add_argument("--patent", help="Process single patent")
    args = parser.parse_args()

    log("=" * 60)
    log("PATENT RAG BUILDER")
    log("=" * 60)

    # Get patents to process
    if args.patent:
        patents = supabase_request(
            "GET",
            f"patents?patent_number=eq.{args.patent}&select=patent_number,title,abstract"
        )
        log(f"Processing single patent: {args.patent}")
    else:
        patents = fetch_paginated("patents", "patent_number,title,abstract")
        log(f"Processing {len(patents)} patents")

    if not patents:
        log("No patents found!")
        return

    # Process each patent
    total_claims = 0
    total_content = 0
    processed = 0
    errors = 0

    for i, patent in enumerate(patents):
        try:
            stats = process_patent(patent)
            total_claims += stats["claims_count"]
            total_content += stats["content_length"]
            processed += 1

            if (i + 1) % 50 == 0 or (i + 1) == len(patents):
                log(f"  Processed {i + 1}/{len(patents)} patents")

        except Exception as e:
            errors += 1
            if errors <= 5:
                log(f"  Error processing {patent['patent_number']}: {e}")

    # Summary
    log("")
    log("=" * 60)
    log("SUMMARY")
    log("=" * 60)
    log(f"Patents processed: {processed}")
    log(f"Total claims aggregated: {total_claims}")
    log(f"Average content length: {total_content // processed if processed else 0} chars")
    log(f"Errors: {errors}")

    # Verify
    log("")
    log("Verification:")
    with_content = supabase_request(
        "GET",
        "patents?content_text=not.is.null&select=patent_number&limit=1"
    )
    # Get count via header
    import urllib.request
    url = f"{SUPABASE_URL}/rest/v1/patents?content_text=not.is.null&select=patent_number"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Prefer": "count=exact",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        content_range = resp.headers.get("content-range", "")
        if "/" in content_range:
            count = content_range.split("/")[1]
            log(f"  Patents with content_text: {count}")

    log("=" * 60)


if __name__ == "__main__":
    main()
