#!/usr/bin/env python3
"""
FCC Filing Content Audit

Analyzes content completeness across the fcc_filings table.
Identifies filings needing content extraction and generates coverage reports.

Usage:
    python3 fcc_content_audit.py              # Full report
    python3 fcc_content_audit.py --fix        # Re-queue filings without content
    python3 fcc_content_audit.py --short      # Only filings with short content
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Optional


# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


def log(msg: str):
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None) -> any:
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
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        log(f"Supabase error: {e.code} - {error_body}")
        raise


def get_filing_stats() -> Dict:
    """Get overall filing statistics by filing_system."""
    log("Fetching filing statistics...")

    # Total count by filing system
    all_filings = supabase_request(
        "GET",
        "fcc_filings?select=filing_system"
    )

    stats = {
        "ICFS": {"total": 0, "with_content": 0, "without_content": 0, "short_content": 0},
        "ECFS": {"total": 0, "with_content": 0, "without_content": 0, "short_content": 0},
        "ELS": {"total": 0, "with_content": 0, "without_content": 0, "short_content": 0},
    }

    for f in all_filings:
        fs = f.get("filing_system", "Unknown")
        if fs in stats:
            stats[fs]["total"] += 1

    # Filings with content_text
    with_content = supabase_request(
        "GET",
        "fcc_filings?content_text=not.is.null&select=filing_system"
    )
    for f in with_content:
        fs = f.get("filing_system", "Unknown")
        if fs in stats:
            stats[fs]["with_content"] += 1

    # Calculate without content
    for fs in stats:
        stats[fs]["without_content"] = stats[fs]["total"] - stats[fs]["with_content"]

    return stats


def get_filings_without_content(limit: int = 100) -> List[Dict]:
    """Get filings that don't have content_text."""
    return supabase_request(
        "GET",
        f"fcc_filings?content_text=is.null&select=id,file_number,filing_system,title,filed_date,source_url&order=filed_date.desc&limit={limit}"
    )


def get_filings_with_short_content(min_length: int = 500, limit: int = 50) -> List[Dict]:
    """Get filings with very short content (likely extraction failures)."""
    # Supabase doesn't have LENGTH() in REST API, so fetch all with content and filter
    filings = supabase_request(
        "GET",
        f"fcc_filings?content_text=not.is.null&select=id,file_number,filing_system,title,filed_date,content_text&order=filed_date.desc&limit=500"
    )

    short_filings = []
    for f in filings:
        content = f.get("content_text", "")
        if content and len(content) < min_length:
            short_filings.append({
                "id": f["id"],
                "file_number": f["file_number"],
                "filing_system": f["filing_system"],
                "title": f["title"],
                "filed_date": f["filed_date"],
                "content_length": len(content),
            })

    # Sort by content length (shortest first)
    short_filings.sort(key=lambda x: x.get("content_length", 0))
    return short_filings[:limit]


def get_content_length_distribution() -> Dict:
    """Analyze content length distribution."""
    filings = supabase_request(
        "GET",
        "fcc_filings?content_text=not.is.null&select=filing_system,content_text&limit=1000"
    )

    distribution = {
        "< 500 chars": 0,
        "500-5K chars": 0,
        "5K-50K chars": 0,
        "50K-500K chars": 0,
        "> 500K chars": 0,
    }

    for f in filings:
        content = f.get("content_text", "")
        length = len(content) if content else 0

        if length < 500:
            distribution["< 500 chars"] += 1
        elif length < 5000:
            distribution["500-5K chars"] += 1
        elif length < 50000:
            distribution["5K-50K chars"] += 1
        elif length < 500000:
            distribution["50K-500K chars"] += 1
        else:
            distribution["> 500K chars"] += 1

    return distribution


def reset_filing_for_reprocessing(file_number: str) -> bool:
    """Reset a filing's content so it can be reprocessed."""
    try:
        supabase_request(
            "PATCH",
            f"fcc_filings?file_number=eq.{file_number}",
            {"content_text": None, "storage_path": None, "status": "pending"}
        )
        return True
    except:
        return False


def print_report(stats: Dict, short_filings: List[Dict], without_content: List[Dict]):
    """Print formatted audit report."""
    print()
    print("=" * 70)
    print("FCC FILING CONTENT AUDIT REPORT")
    print("=" * 70)
    print()

    # Overall stats
    total_all = sum(s["total"] for s in stats.values())
    with_content_all = sum(s["with_content"] for s in stats.values())
    coverage = (with_content_all / total_all * 100) if total_all > 0 else 0

    print(f"OVERALL COVERAGE: {with_content_all}/{total_all} ({coverage:.1f}%)")
    print()

    # By filing system
    print("BY FILING SYSTEM:")
    print("-" * 50)
    for fs, s in stats.items():
        if s["total"] > 0:
            pct = (s["with_content"] / s["total"] * 100)
            print(f"  {fs:6} | Total: {s['total']:4} | With content: {s['with_content']:4} ({pct:5.1f}%) | Missing: {s['without_content']:4}")
    print()

    # Content length distribution
    distribution = get_content_length_distribution()
    print("CONTENT LENGTH DISTRIBUTION:")
    print("-" * 50)
    for bucket, count in distribution.items():
        bar = "█" * min(count, 40)
        print(f"  {bucket:15} | {count:4} | {bar}")
    print()

    # Filings without content
    if without_content:
        print(f"FILINGS WITHOUT CONTENT (showing {len(without_content)}):")
        print("-" * 50)
        for f in without_content[:20]:
            print(f"  {f['filing_system']:5} | {f['file_number'][:35]:35} | {f.get('filed_date', 'N/A')}")
        if len(without_content) > 20:
            print(f"  ... and {len(without_content) - 20} more")
    print()

    # Filings with short content
    if short_filings:
        print(f"FILINGS WITH SHORT CONTENT (<500 chars, showing {len(short_filings)}):")
        print("-" * 50)
        for f in short_filings[:15]:
            print(f"  {f['filing_system']:5} | {f['file_number'][:30]:30} | {f['content_length']:6} chars")
        if len(short_filings) > 15:
            print(f"  ... and {len(short_filings) - 15} more")
    print()

    print("=" * 70)


def run_audit(args):
    """Run the content audit."""
    log("=" * 60)
    log("FCC Filing Content Audit")
    log("=" * 60)

    if not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    # Get statistics
    stats = get_filing_stats()

    # Get filings without content
    without_content = get_filings_without_content(limit=100)
    log(f"Filings without content: {len(without_content)}")

    # Get filings with short content
    short_filings = get_filings_with_short_content()
    log(f"Filings with short content (<500 chars): {len(short_filings)}")

    # Print report
    if not args.quiet:
        print_report(stats, short_filings, without_content)

    # Fix mode: reset filings for reprocessing
    if args.fix:
        log("FIX MODE: Resetting filings for reprocessing...")

        to_fix = without_content if not args.short else short_filings
        if args.limit:
            to_fix = to_fix[:args.limit]

        fixed = 0
        for f in to_fix:
            fn = f.get("file_number")
            if fn and reset_filing_for_reprocessing(fn):
                fixed += 1
                log(f"  Reset: {fn}")

        log(f"Reset {fixed} filings for reprocessing")
        log("Run the appropriate worker to re-fetch content:")
        log("  python3 ecfs_worker_v2.py --backfill")
        log("  python3 icfs_worker_v2.py --backfill")

    # Output JSON for scripting
    if args.json:
        output = {
            "stats": stats,
            "without_content_count": len(without_content),
            "short_content_count": len(short_filings),
            "without_content": without_content[:20],
            "short_content": short_filings[:20],
        }
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FCC Filing Content Audit")
    parser.add_argument("--fix", action="store_true", help="Reset filings without content for reprocessing")
    parser.add_argument("--short", action="store_true", help="Include filings with short content in --fix")
    parser.add_argument("--limit", type=int, help="Limit number of filings to fix")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress detailed report")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    run_audit(args)
