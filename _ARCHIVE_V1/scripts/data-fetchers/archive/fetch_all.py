#!/usr/bin/env python3
"""
Master Data Fetcher for AST SpaceMobile
Runs all fetchers and creates a unified index

Usage: python3 fetch_all.py
"""

from __future__ import annotations
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

SCRIPT_DIR = Path(__file__).parent
RESEARCH_DIR = SCRIPT_DIR / "../../research/asts"


def run_fetcher(name: str, script: str) -> bool:
    """Run a fetcher script and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {name}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            [sys.executable, script],
            cwd=SCRIPT_DIR,
            capture_output=False,
            timeout=120,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error running {name}: {e}")
        return False


def create_unified_index() -> Dict:
    """Create a unified index of all data sources."""
    index = {
        "createdAt": datetime.utcnow().isoformat() + "Z",
        "company": {
            "name": "AST SpaceMobile, Inc.",
            "ticker": "ASTS",
            "cik": "0001780312",
            "fccCallSign": "S3065",
        },
        "dataSources": {},
        "quickLinks": {
            "sec": {
                "edgarSearch": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001780312",
                "recentFilings": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001780312&type=&dateb=&owner=include&count=40",
            },
            "fcc": {
                "fccReport": "https://fcc.report/company/Ast-Spacemobile",
                "ecfsSearch": "https://www.fcc.gov/ecfs/search/search-filings?q=AST%20SpaceMobile",
                "experimentalLicenses": "https://fcc.report/ELS/AST-Spacemobile",
            },
            "company": {
                "investorRelations": "https://investors.ast-science.com/",
                "pressReleases": "https://investors.ast-science.com/press-releases",
                "secFilings": "https://investors.ast-science.com/sec-filings",
                "quarterlyResults": "https://investors.ast-science.com/quarterly-results",
            },
            "tracking": {
                "spaceTrack": "https://www.space-track.org/",
                "celestrak": "https://celestrak.org/NORAD/elements/",
                "n2yo": "https://www.n2yo.com/?s=54361",  # BlueWalker 3
            },
            "market": {
                "nasdaq": "https://www.nasdaq.com/market-activity/stocks/asts",
                "yahooFinance": "https://finance.yahoo.com/quote/ASTS",
                "seekingAlpha": "https://seekingalpha.com/symbol/ASTS",
            },
        },
        "localFiles": [],
    }

    # Scan for local data files
    research_path = RESEARCH_DIR.resolve()
    if research_path.exists():
        for json_file in research_path.rglob("*.json"):
            rel_path = json_file.relative_to(research_path.parent.parent)
            file_stat = json_file.stat()

            # Load file to get summary
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    record_count = None
                    if "filings" in data:
                        record_count = len(data["filings"])
                    elif "pressReleases" in data:
                        record_count = len(data["pressReleases"])
            except:
                data = {}
                record_count = None

            index["localFiles"].append({
                "path": str(rel_path),
                "size": file_stat.st_size,
                "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat() + "Z",
                "records": record_count,
            })

            # Add to dataSources
            source_name = json_file.stem.replace("-", "_")
            index["dataSources"][source_name] = {
                "path": str(rel_path),
                "fetchedAt": data.get("fetchedAt", "unknown"),
            }

    return index


def main():
    print("="*60)
    print("AST SpaceMobile Data Aggregator")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")

    # Run all fetchers
    fetchers = [
        ("SEC EDGAR Filings", "sec_edgar.py"),
        ("FCC Filings", "fcc_filings.py"),
        ("Investor Relations", "investor_relations.py"),
    ]

    results = {}
    for name, script in fetchers:
        success = run_fetcher(name, script)
        results[name] = "SUCCESS" if success else "FAILED"

    # Create unified index
    print(f"\n{'='*60}")
    print("Creating Unified Index")
    print(f"{'='*60}")

    index = create_unified_index()

    # Save index
    index_path = RESEARCH_DIR / "INDEX.json"
    index_path = index_path.resolve()
    index_path.parent.mkdir(parents=True, exist_ok=True)

    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)

    print(f"Index saved to: {index_path}")

    # Print summary
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")

    for name, status in results.items():
        icon = "✓" if status == "SUCCESS" else "✗"
        print(f"  {icon} {name}: {status}")

    print(f"\nData files created:")
    for file_info in index["localFiles"]:
        size_kb = file_info["size"] / 1024
        records = f" ({file_info['records']} records)" if file_info["records"] else ""
        print(f"  - {file_info['path']}: {size_kb:.1f} KB{records}")

    print(f"\nCompleted at: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
