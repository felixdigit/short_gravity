#!/usr/bin/env python3
"""
Split Combined Claims

Splits claim text blobs into individual claims.
EPO returns all claims as one text block - this splits them properly.

Run: python3 split_claims.py
"""

import json
import os
import re
import urllib.request
from datetime import datetime

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


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

    with urllib.request.urlopen(req, timeout=30) as response:
        content = response.read().decode("utf-8")
        return json.loads(content) if content else {}


def split_claims(text):
    """Split claim text into individual claims."""
    # Pattern: Number followed by period and space
    # "1. A method..." or "1.A method..."
    pattern = r'(?:^|\n)(\d+)\.\s*'

    # Find all claim starts
    matches = list(re.finditer(pattern, text))

    if not matches:
        # If no numbered claims found, return as single claim
        return [{"number": 1, "text": text.strip()}]

    claims = []
    for i, match in enumerate(matches):
        claim_num = int(match.group(1))
        start = match.end()

        # End is either next claim start or end of text
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

    # Dependent claims reference other claims
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
        return [int(m) for m in matches[:5]]  # Limit to first 5
    return None


def main():
    log("=" * 60)
    log("SPLIT COMBINED CLAIMS")
    log("=" * 60)

    # Get all claims with claim_number = 0 (combined blobs)
    combined = supabase_request("GET", "patent_claims?select=id,patent_number,claim_text&claim_number=eq.0")
    log(f"Found {len(combined)} combined claim blobs")

    if not combined:
        log("No combined claims to split!")
        return

    total_new = 0
    total_deleted = 0

    for blob in combined:
        patent_number = blob["patent_number"]
        claim_text = blob["claim_text"]
        blob_id = blob["id"]

        claims = split_claims(claim_text)
        log(f"  {patent_number}: {len(claims)} individual claims")

        if len(claims) <= 1:
            # Already a single claim, just update the claim_number
            try:
                supabase_request(
                    "PATCH",
                    f"patent_claims?id=eq.{blob_id}",
                    {"claim_number": 1}
                )
            except Exception as e:
                log(f"    Error updating: {e}")
            continue

        # Multiple claims - delete the blob and insert individuals
        for claim in claims:
            claim_type = parse_claim_type(claim["text"])
            depends_on = parse_depends_on(claim["text"])

            try:
                data = {
                    "patent_number": patent_number,
                    "claim_number": claim["number"],
                    "claim_text": claim["text"],
                    "claim_type": claim_type,
                }
                if depends_on:
                    data["depends_on"] = depends_on

                supabase_request("POST", "patent_claims", data)
                total_new += 1
            except Exception as e:
                if "duplicate key" not in str(e).lower():
                    log(f"    Error inserting claim {claim['number']}: {e}")

        # Delete the original blob
        try:
            supabase_request("DELETE", f"patent_claims?id=eq.{blob_id}")
            total_deleted += 1
        except Exception as e:
            log(f"    Error deleting blob: {e}")

    log("")
    log("=" * 60)
    log("SUMMARY")
    log("=" * 60)
    log(f"Claims deleted (blobs): {total_deleted}")
    log(f"Claims inserted: {total_new}")

    # Verify
    final = supabase_request("GET", "patent_claims?select=id")
    log(f"Total claims in database: {len(final)}")


if __name__ == "__main__":
    main()
