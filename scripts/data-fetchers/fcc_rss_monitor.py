#!/usr/bin/env python3
"""
FCC RSS Feed Monitor

Monitors FCC RSS feeds for new filings in relevant dockets.
Designed for frequent runs (every 15 min) with low overhead.

Usage:
    python3 fcc_rss_monitor.py              # Check for new filings
    python3 fcc_rss_monitor.py --trigger    # Also trigger ingestion for new filings
    python3 fcc_rss_monitor.py --quiet      # Suppress output unless new filings found
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional, Set

from storage_utils import log

try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from discord.notify import notify_fcc_filing
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False


# ============================================================================
# Configuration
# ============================================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# FCC RSS Feeds to monitor
RSS_FEEDS = [
    {
        "url": "https://www.fcc.gov/ecfs/rss/filings?proceedings.name=23-65",
        "name": "SCS Rulemaking",
        "docket": "23-65",
        "importance": "critical",
    },
    {
        "url": "https://www.fcc.gov/ecfs/rss/filings?proceedings.name=22-271",
        "name": "SCS Framework",
        "docket": "22-271",
        "importance": "critical",
    },
    {
        "url": "https://www.fcc.gov/ecfs/rss/filings?proceedings.name=25-201",
        "name": "AST Modification",
        "docket": "25-201",
        "importance": "high",
    },
    {
        "url": "https://www.fcc.gov/ecfs/rss/filings?proceedings.name=25-306",
        "name": "AST Filings",
        "docket": "25-306",
        "importance": "high",
    },
]

# Alternative RSS format using ECFS API
ECFS_RSS_BASE = "https://ecfsapi.fcc.gov/filings"


# ============================================================================
# HTTP Utilities
# ============================================================================

def fetch_url(url: str, timeout: int = 30) -> str:
    """Fetch URL content."""
    headers = {
        "User-Agent": "Short Gravity Research FCC Monitor",
        "Accept": "application/rss+xml, application/xml, text/xml",
    }
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except Exception as e:
        log(f"Error fetching {url}: {e}")
        return ""


# ============================================================================
# Supabase Operations
# ============================================================================

def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None) -> any:
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
        log(f"Supabase error: {e.code}")
        return {}


def get_existing_ecfs_ids() -> Set[str]:
    """Get existing ECFS filing IDs from database."""
    try:
        result = supabase_request("GET", "fcc_filings?filing_system=eq.ECFS&select=file_number")
        return {r["file_number"] for r in result if r.get("file_number")}
    except Exception as e:
        log(f"Error fetching existing filings: {e}")
        return set()


# ============================================================================
# RSS Parsing
# ============================================================================

def parse_rss_feed(content: str) -> List[Dict]:
    """Parse RSS feed content and return filing items."""
    if not content:
        return []

    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        log(f"RSS parse error: {e}")
        return []

    items = []

    # Try standard RSS format
    for item in root.findall('.//item'):
        try:
            entry = {
                'title': item.findtext('title', ''),
                'link': item.findtext('link', ''),
                'pubDate': item.findtext('pubDate', ''),
                'description': item.findtext('description', ''),
            }

            # Extract filing ID from link
            filing_id = extract_filing_id(entry['link'])
            if filing_id:
                entry['filing_id'] = filing_id
                items.append(entry)

        except Exception as e:
            continue

    # Try Atom format
    for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry'):
        try:
            link_elem = entry.find('{http://www.w3.org/2005/Atom}link')
            item = {
                'title': entry.findtext('{http://www.w3.org/2005/Atom}title', ''),
                'link': link_elem.get('href', '') if link_elem is not None else '',
                'pubDate': entry.findtext('{http://www.w3.org/2005/Atom}published', ''),
                'description': entry.findtext('{http://www.w3.org/2005/Atom}summary', ''),
            }

            filing_id = extract_filing_id(item['link'])
            if filing_id:
                item['filing_id'] = filing_id
                items.append(item)

        except Exception as e:
            continue

    return items


def extract_filing_id(link: str) -> Optional[str]:
    """Extract ECFS filing ID from URL."""
    if not link:
        return None

    # Pattern: /ecfs/document/12345678901234/
    match = re.search(r'/(?:document|filing)/(\d{14,})', link)
    if match:
        return match.group(1)

    # Pattern: /ecfs/filing/12345678901234
    match = re.search(r'filing[=/](\d{14,})', link)
    if match:
        return match.group(1)

    # Pattern: id_submission=12345678901234
    match = re.search(r'id_submission=(\d+)', link)
    if match:
        return match.group(1)

    return None


def parse_ecfs_api_rss(docket: str) -> List[Dict]:
    """Fetch recent filings using ECFS API as RSS alternative."""
    url = f"{ECFS_RSS_BASE}?proceedings.name={docket}&sort=date_received,DESC&limit=25"

    try:
        content = fetch_url(url)
        if not content:
            return []

        # Check if we got JSON (API) or XML (RSS)
        if content.strip().startswith('{') or content.strip().startswith('['):
            data = json.loads(content)
            filings = data.get("filings", []) if isinstance(data, dict) else data

            items = []
            for f in filings:
                filing_id = str(f.get("id_submission") or f.get("id_long") or f.get("id"))
                if filing_id:
                    filers = f.get("filers", [])
                    filer_name = filers[0].get("name") if filers else "Unknown"

                    items.append({
                        'filing_id': filing_id,
                        'title': f"{filer_name} - {f.get('submissiontype', {}).get('description', 'Filing')}",
                        'link': f"https://www.fcc.gov/ecfs/document/{filing_id}/1",
                        'pubDate': f.get("date_received", ""),
                        'description': f.get("description", ""),
                    })

            return items
        else:
            # Try parsing as RSS/XML
            return parse_rss_feed(content)

    except Exception as e:
        log(f"ECFS API error for {docket}: {e}")
        return []


# ============================================================================
# Monitoring
# ============================================================================

def check_feed(feed: Dict, existing_ids: Set[str]) -> List[Dict]:
    """Check a single RSS feed for new filings."""
    url = feed["url"]
    docket = feed["docket"]

    # Try RSS feed first
    content = fetch_url(url)
    items = parse_rss_feed(content) if content else []

    # If RSS didn't work, try ECFS API
    if not items:
        items = parse_ecfs_api_rss(docket)

    # Filter to new filings only
    new_items = []
    for item in items:
        filing_id = item.get('filing_id')
        if filing_id and filing_id not in existing_ids:
            item['docket'] = docket
            item['docket_name'] = feed["name"]
            item['importance'] = feed["importance"]
            new_items.append(item)

    return new_items


def check_all_feeds(quiet: bool = False) -> List[Dict]:
    """Check all RSS feeds for new filings."""
    existing_ids = get_existing_ecfs_ids()

    if not quiet:
        log(f"Checking {len(RSS_FEEDS)} RSS feeds...")
        log(f"Known filing IDs: {len(existing_ids)}")

    all_new = []

    for feed in RSS_FEEDS:
        new_items = check_feed(feed, existing_ids)

        if new_items:
            all_new.extend(new_items)
            if not quiet:
                log(f"  {feed['name']}: {len(new_items)} new filing(s)")
        elif not quiet:
            log(f"  {feed['name']}: No new filings")

        time.sleep(0.5)  # Rate limit

    return all_new


def queue_for_ingestion(filings: List[Dict]) -> int:
    """Insert new filings as pending for worker to process."""
    inserted = 0

    for filing in filings:
        try:
            record = {
                "filing_system": "ECFS",
                "file_number": filing['filing_id'],
                "docket": filing.get('docket'),
                "proceeding_name": filing.get('docket_name'),
                "title": filing.get('title', 'New Filing'),
                "source_url": filing.get('link'),
                "metadata": json.dumps({
                    "rss_discovered": True,
                    "importance": filing.get('importance', 'normal'),
                    "pub_date": filing.get('pubDate'),
                }),
                "fetched_at": datetime.utcnow().isoformat() + "Z",
                "status": "pending",  # Will be processed by ecfs_worker
            }

            supabase_request("POST", "fcc_filings", record)
            inserted += 1
            log(f"  Queued: {filing['filing_id']} ({filing.get('docket')})")

            # Discord notification
            if DISCORD_AVAILABLE:
                notify_fcc_filing(
                    title=filing.get('title', 'New Filing'),
                    file_number=filing['filing_id'],
                    status="New",
                    filed_date=filing.get('pubDate', '')[:10],
                )

        except Exception as e:
            log(f"  Error queueing {filing['filing_id']}: {e}")

    return inserted


# ============================================================================
# Main
# ============================================================================

def run_monitor(args):
    """Main monitor function."""
    if not args.quiet:
        log("=" * 60)
        log("FCC RSS Feed Monitor")
        log("=" * 60)

    if not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    # Check all feeds
    new_filings = check_all_feeds(quiet=args.quiet)

    if not new_filings:
        if not args.quiet:
            log("No new filings found.")
        return

    # Report new filings
    log(f"Found {len(new_filings)} new filing(s)!")
    log("-" * 40)

    for filing in new_filings:
        importance = filing.get('importance', 'normal')
        marker = "🔴" if importance == 'critical' else "🟡" if importance == 'high' else "⚪"
        log(f"  {marker} [{filing.get('docket')}] {filing.get('title', 'Unknown')[:50]}")

    # Trigger ingestion if requested
    if args.trigger:
        log("-" * 40)
        log("Queuing filings for ingestion...")
        inserted = queue_for_ingestion(new_filings)
        log(f"Queued {inserted} filing(s)")
        log("Run 'python3 ecfs_worker_v2.py' to process pending filings.")

    # Output JSON if requested
    if args.json:
        print(json.dumps({
            "new_filings_count": len(new_filings),
            "filings": new_filings,
        }, indent=2))

    if not args.quiet:
        log("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FCC RSS Feed Monitor")
    parser.add_argument("--trigger", action="store_true", help="Queue new filings for ingestion")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress output unless new filings")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    run_monitor(args)
