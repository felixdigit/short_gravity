#!/usr/bin/env python3
"""
SEC EDGAR Data Fetcher for ASTS
Fetches filings from SEC's free API

CIK: 0001780312 (AST SpaceMobile)
API Docs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
"""

from __future__ import annotations
import json
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Union, Any

ASTS_CIK = "0001780312"
SEC_BASE_URL = "https://data.sec.gov"
USER_AGENT = "Short Gravity gabriel@shortgravity.com"  # SEC requires identification

# Key form types for ASTS analysis
FORM_TYPES = {
    "ANNUAL": ["10-K", "10-K/A"],
    "QUARTERLY": ["10-Q", "10-Q/A"],
    "CURRENT": ["8-K", "8-K/A"],
    "PROXY": ["DEF 14A", "DEFA14A"],
    "REGISTRATION": ["S-1", "S-1/A", "S-3", "S-3/A"],
    "INSIDER": ["4", "3", "5"],
    "PROSPECTUS": ["424B3", "424B4", "424B5"],
}


def fetch_with_retry(url: str, retries: int = 3) -> Union[Dict, str]:
    """Fetch URL with retry logic and rate limit handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }

    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read().decode("utf-8")
                if url.endswith(".json"):
                    return json.loads(content)
                return content
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait_time = 2 ** i
                print(f"Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            raise
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(1)

    raise Exception("Max retries exceeded")


def fetch_asts_submissions() -> Dict:
    """Fetch all ASTS submissions from SEC EDGAR."""
    url = f"{SEC_BASE_URL}/submissions/CIK{ASTS_CIK}.json"
    print(f"Fetching: {url}")
    return fetch_with_retry(url)


def parse_filings(submissions: Dict) -> List[Dict]:
    """Parse filings from submissions response."""
    recent = submissions["filings"]["recent"]
    filings = []

    for i in range(len(recent["accessionNumber"])):
        filings.append({
            "accessionNumber": recent["accessionNumber"][i],
            "filingDate": recent["filingDate"][i],
            "reportDate": recent["reportDate"][i] if recent["reportDate"][i] else None,
            "form": recent["form"][i],
            "primaryDocument": recent["primaryDocument"][i],
            "primaryDocDescription": recent["primaryDocDescription"][i],
            "items": recent.get("items", [""] * len(recent["accessionNumber"]))[i],
            "size": recent["size"][i],
            "isXBRL": recent["isXBRL"][i] == 1,
            "isInlineXBRL": recent["isInlineXBRL"][i] == 1,
        })

    return filings


def filter_by_form_type(filings: List[Dict], form_types: List[str]) -> List[Dict]:
    """Filter filings by form type."""
    return [f for f in filings if f["form"] in form_types]


def get_filing_url(cik: str, accession_number: str, document: str) -> str:
    """Generate URL for a specific filing document."""
    accession_no_dashes = accession_number.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dashes}/{document}"


def main():
    print("=== SEC EDGAR Fetcher for ASTS ===\n")

    # Fetch all submissions
    submissions = fetch_asts_submissions()

    print(f"Company: {submissions['name']}")
    print(f"CIK: {submissions['cik']}")
    print(f"Tickers: {', '.join(submissions.get('tickers', []))}")
    print(f"Exchanges: {', '.join(submissions.get('exchanges', []))}")
    print(f"Industry: {submissions.get('sicDescription', 'N/A')}\n")

    # Parse filings
    all_filings = parse_filings(submissions)
    print(f"Total filings: {len(all_filings)}\n")

    # Filter key filings (10-K, 10-Q, 8-K)
    key_forms = FORM_TYPES["ANNUAL"] + FORM_TYPES["QUARTERLY"] + FORM_TYPES["CURRENT"]
    key_filings = filter_by_form_type(all_filings, key_forms)

    print("=== Key Filings (10-K, 10-Q, 8-K) ===\n")

    # Group by year
    by_year = {}
    for filing in key_filings:
        year = filing["filingDate"][:4]
        if year not in by_year:
            by_year[year] = []
        by_year[year].append(filing)

    # Print summary
    for year in sorted(by_year.keys(), reverse=True):
        filings = by_year[year]
        print(f"\n{year}:")
        for f in filings[:10]:
            desc = f["primaryDocDescription"][:50] if f["primaryDocDescription"] else "N/A"
            print(f"  {f['filingDate']} | {f['form']:<8} | {desc}")
        if len(filings) > 10:
            print(f"  ... and {len(filings) - 10} more")

    # Prepare output
    output = {
        "fetchedAt": datetime.utcnow().isoformat() + "Z",
        "company": {
            "name": submissions["name"],
            "cik": submissions["cik"],
            "tickers": submissions.get("tickers", []),
            "exchanges": submissions.get("exchanges", []),
            "industry": submissions.get("sicDescription", ""),
        },
        "summary": {
            "totalFilings": len(all_filings),
            "keyFilings": len(key_filings),
            "byFormType": {},
        },
        "filings": [],
    }

    # Count by form type
    for filing in key_filings:
        form = filing["form"]
        output["summary"]["byFormType"][form] = output["summary"]["byFormType"].get(form, 0) + 1

    # Add filings with URLs
    for filing in key_filings:
        filing_with_url = {
            **filing,
            "url": get_filing_url(ASTS_CIK, filing["accessionNumber"], filing["primaryDocument"]),
        }
        output["filings"].append(filing_with_url)

    # Write to research folder
    script_dir = Path(__file__).parent
    output_path = script_dir / "../../research/asts/filings/sec-filings.json"
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n\nSaved to: {output_path}")
    print(f"Key filings count: {len(key_filings)}")

    # Also save all filings for comprehensive analysis
    all_output = {
        "fetchedAt": datetime.utcnow().isoformat() + "Z",
        "company": output["company"],
        "filings": [
            {**f, "url": get_filing_url(ASTS_CIK, f["accessionNumber"], f["primaryDocument"])}
            for f in all_filings
        ],
    }

    all_output_path = script_dir / "../../research/asts/filings/sec-filings-all.json"
    all_output_path = all_output_path.resolve()

    with open(all_output_path, "w") as f:
        json.dump(all_output, f, indent=2)

    print(f"All filings saved to: {all_output_path}")


if __name__ == "__main__":
    main()
