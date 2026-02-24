#!/usr/bin/env python3
"""
News Worker

Fetches ASTS news from Finnhub API and stores in Supabase inbox.
Includes press releases, analyst coverage, and company news.

Incremental: queries Supabase for the most recent article timestamp
and only fetches news since then. Falls back to 30 days on first run.
"""

from __future__ import annotations
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")

SOURCE_ID = "finnhub_news"


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


def get_latest_timestamp(source: str) -> Optional[str]:
    """Get the most recent published_at from inbox for this source."""
    try:
        result = supabase_request(
            "GET",
            f"inbox?source=eq.{source}&select=published_at&order=published_at.desc&limit=1",
        )
        if isinstance(result, list) and len(result) > 0 and result[0].get("published_at"):
            return result[0]["published_at"]
    except Exception as e:
        log(f"Error fetching latest timestamp: {e}")
    return None


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
    """Fetch news from Finnhub API with retry and exponential backoff."""
    url = f"https://finnhub.io/api/v1/company-news?symbol=ASTS&from={from_date}&to={to_date}&token={FINNHUB_API_KEY}"
    log(f"Fetching news from {from_date} to {to_date}")

    for attempt in range(3):
        try:
            data = fetch_json(url)
            if isinstance(data, list):
                log(f"  Finnhub returned {len(data)} articles")
                return data
            elif isinstance(data, dict) and "error" in data:
                log(f"  Finnhub API error: {data['error']}")
                return []
            return []
        except urllib.error.HTTPError as e:
            log(f"  Finnhub HTTP error (attempt {attempt + 1}/3): {e.code} {e.reason}")
            if attempt == 2:
                log(f"ERROR: Finnhub API failed after 3 attempts: HTTP {e.code}")
                return []
            time.sleep(2 ** (attempt + 1))
        except Exception as e:
            log(f"  Finnhub fetch error (attempt {attempt + 1}/3): {e}")
            if attempt == 2:
                log(f"ERROR: Finnhub API failed after 3 attempts: {e}")
                return []
            time.sleep(2 ** (attempt + 1))

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
            "source": SOURCE_ID,
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

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    if not FINNHUB_API_KEY:
        log("ERROR: FINNHUB_API_KEY not set")
        sys.exit(1)

    # Determine date range — incremental fetch
    latest_ts = get_latest_timestamp(SOURCE_ID)
    today = datetime.utcnow().strftime("%Y-%m-%d")

    if latest_ts:
        # Parse ISO timestamp and use that date as our start
        try:
            from_date = latest_ts[:10]  # "YYYY-MM-DD" from ISO string
            log(f"Incremental mode: fetching since {from_date}")
        except Exception:
            from_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
            log(f"Could not parse latest timestamp, falling back to last 30 days")
    else:
        from_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        log(f"No existing records — fetching last 30 days (since {from_date})")

    # Get existing news for dedup
    existing = get_existing_source_ids(SOURCE_ID)
    log(f"Found {len(existing)} existing news items in inbox")

    # Single fetch for the date range
    all_news = fetch_finnhub_news(from_date, today)
    log(f"Total news items fetched: {len(all_news)}")

    # Remove duplicates within the batch
    seen_ids = set()
    unique_news = []
    for item in all_news:
        item_id = str(item.get("id", "")) or item.get("url", "")
        if item_id and item_id not in seen_ids:
            seen_ids.add(item_id)
            unique_news.append(item)

    log(f"Unique news items (after dedup): {len(unique_news)}")

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
    log(f"Completed: {success} stored, {skipped} skipped (dupes/spam), {failed} failed")
    log(f"Finnhub returned {len(all_news)} articles, {len(unique_news)} unique, {success} new")
    log("=" * 60)


if __name__ == "__main__":
    run_worker()
