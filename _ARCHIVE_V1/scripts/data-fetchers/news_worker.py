#!/usr/bin/env python3
"""
News Worker

Fetches ASTS news from Finnhub API and stores in Supabase inbox.
Includes press releases, analyst coverage, and company news.
"""

from __future__ import annotations
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Optional

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dviagnysjftidxudeuyo.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "d5p3731r01qqu4br1230d5p3731r01qqu4br123g")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def fetch_json(url: str) -> Dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Short Gravity Research"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def supabase_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
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


def get_existing_source_ids(source: str) -> set:
    try:
        result = supabase_request("GET", f"inbox?source=eq.{source}&select=source_id")
        return {r["source_id"] for r in result}
    except Exception as e:
        log(f"Error fetching existing items: {e}")
        return set()


def categorize_news(headline: str, source: str) -> tuple:
    """Categorize news and determine importance."""
    headline_lower = headline.lower()
    source_lower = source.lower()

    category = "news"
    importance = "normal"
    tags = []

    # High importance sources
    if "businesswire" in source_lower or "prnewswire" in source_lower or "globenewswire" in source_lower:
        category = "press_release"
        importance = "high"

    # Earnings
    if any(w in headline_lower for w in ["earnings", "quarter", "q1", "q2", "q3", "q4", "results"]):
        category = "quarterly_results"
        importance = "high"
        tags.append("earnings")

    # Satellite/launch
    if any(w in headline_lower for w in ["launch", "satellite", "bluebird", "orbit", "spacex"]):
        category = "satellite_launch"
        importance = "high"
        tags.append("bluebird")

    # Partnerships
    if any(w in headline_lower for w in ["partner", "agreement", "at&t", "verizon", "vodafone", "deal"]):
        category = "partnership"
        importance = "high"

    # Financing
    if any(w in headline_lower for w in ["financing", "offering", "capital", "million", "billion", "raise"]):
        category = "financing"
        importance = "high"

    # Analyst coverage - lower priority
    if any(w in headline_lower for w in ["analyst", "rating", "price target", "upgrade", "downgrade"]):
        category = "analyst"
        importance = "normal"

    # Skip law firm spam
    if any(w in headline_lower for w in ["pomerantz", "investigation", "class action", "securities fraud"]):
        category = "legal_spam"
        importance = "low"

    return category, importance, tags


def fetch_finnhub_news(from_date: str, to_date: str) -> List[Dict]:
    """Fetch news from Finnhub API."""
    url = f"https://finnhub.io/api/v1/company-news?symbol=ASTS&from={from_date}&to={to_date}&token={FINNHUB_API_KEY}"
    log(f"Fetching news from {from_date} to {to_date}")

    data = fetch_json(url)
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "error" in data:
        log(f"Finnhub error: {data['error']}")
        return []
    return []


def process_news_item(item: Dict, existing: set) -> bool:
    """Process a single news item."""
    # Generate unique ID from URL or id
    source_id = str(item.get("id", "")) or item.get("url", "").split("/")[-1]

    if not source_id or source_id in existing:
        return False

    headline = item.get("headline", "")
    source = item.get("source", "")

    # Skip law firm spam
    category, importance, tags = categorize_news(headline, source)
    if category == "legal_spam":
        return False

    log(f"Processing: {headline[:50]}...")

    try:
        # Convert timestamp
        timestamp = item.get("datetime", 0)
        published_at = datetime.fromtimestamp(timestamp).isoformat() + "Z" if timestamp else None

        inbox_item = {
            "source": "press_release",  # Using press_release since news isn't in enum yet
            "source_id": source_id,
            "title": headline,
            "published_at": published_at,
            "url": item.get("url", ""),
            "category": category,
            "tags": tags,
            "importance": importance,
            "summary": item.get("summary", ""),
            "status": "completed",
            "metadata": json.dumps({
                "finnhub_source": source,
                "related": item.get("related", ""),
                "image": item.get("image", ""),
            }),
        }

        supabase_request("POST", "inbox", inbox_item)
        log(f"  ✓ Added ({category}, {importance})")
        return True

    except Exception as e:
        log(f"  ✗ Error: {e}")
        return False


def run_worker():
    """Main worker function."""
    log("=" * 60)
    log("News Worker Started (Finnhub)")
    log("=" * 60)

    if not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_SERVICE_KEY not set")
        sys.exit(1)

    if not FINNHUB_API_KEY:
        log("ERROR: FINNHUB_API_KEY not set")
        sys.exit(1)

    # Get existing news
    existing = get_existing_source_ids("press_release")
    log(f"Found {len(existing)} existing news items in inbox")

    # Fetch news from 2021 to now (ASTS went public April 2021)
    all_news = []

    # Fetch in chunks by year to get more data
    years = [
        ("2021-01-01", "2021-12-31"),
        ("2022-01-01", "2022-12-31"),
        ("2023-01-01", "2023-12-31"),
        ("2024-01-01", "2024-12-31"),
        ("2025-01-01", "2025-12-31"),
        ("2026-01-01", "2026-12-31"),
    ]

    for from_date, to_date in years:
        news = fetch_finnhub_news(from_date, to_date)
        all_news.extend(news)
        log(f"  {from_date[:4]}: {len(news)} items")
        time.sleep(0.5)  # Rate limit

    log(f"Total news items fetched: {len(all_news)}")

    # Remove duplicates
    seen_ids = set()
    unique_news = []
    for item in all_news:
        item_id = str(item.get("id", "")) or item.get("url", "")
        if item_id and item_id not in seen_ids:
            seen_ids.add(item_id)
            unique_news.append(item)

    log(f"Unique news items: {len(unique_news)}")

    # Process news
    success = 0
    skipped = 0
    failed = 0

    for item in unique_news:
        result = process_news_item(item, existing)
        if result:
            success += 1
        elif result is False:
            skipped += 1
        else:
            failed += 1

        # Small delay to avoid rate limits
        if success % 10 == 0 and success > 0:
            time.sleep(0.2)

    log("=" * 60)
    log(f"Completed: {success} added, {skipped} skipped, {failed} failed")
    log("=" * 60)


if __name__ == "__main__":
    run_worker()
