#!/usr/bin/env python3
"""
Price Worker
Backfills and updates ASTS daily OHLCV prices from yfinance into Supabase.

Modes:
  backfill  — Fetch all available history (2020-01-01 to present)
  update    — Fetch last 30 days (fills gaps, adds new days)

Run:
  cd scripts/data-fetchers && export $(grep -v '^#' .env | xargs)
  python3 price_worker.py --mode backfill
  python3 price_worker.py --mode update

Schedule: daily at 22:00 UTC (after market close)
"""

from __future__ import annotations

import os
import sys
import json
import urllib.request
import argparse
from datetime import datetime, timezone, timedelta

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY required")
    sys.exit(1)


def supabase_request(path: str, method: str = 'GET', data: object = None) -> object:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        'apikey': SUPABASE_SERVICE_KEY,
        'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation',
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  HTTP {e.code}: {error_body[:200]}")
        return None


def get_existing_dates(symbol: str = 'ASTS') -> set:
    """Get all dates we already have in the database."""
    dates = set()
    offset = 0
    batch = 1000
    while True:
        path = f"daily_prices?symbol=eq.{symbol}&select=date&order=date.asc&offset={offset}&limit={batch}"
        result = supabase_request(path)
        if not result:
            break
        for row in result:
            dates.add(row['date'])
        if len(result) < batch:
            break
        offset += batch
    return dates


def fetch_prices(start: str, end: str, symbol: str = 'ASTS') -> list:
    """Fetch daily OHLCV from yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance not installed. Run: pip3 install yfinance")
        sys.exit(1)

    print(f"Fetching {symbol} daily prices: {start} → {end}")
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end, interval='1d')

    if df.empty:
        print("  No data returned")
        return []

    rows = []
    for idx, row in df.iterrows():
        date_str = idx.strftime('%Y-%m-%d')
        rows.append({
            'symbol': symbol,
            'date': date_str,
            'open': round(float(row['Open']), 4),
            'high': round(float(row['High']), 4),
            'low': round(float(row['Low']), 4),
            'close': round(float(row['Close']), 4),
            'volume': int(row['Volume']),
        })

    print(f"  Got {len(rows)} trading days ({rows[0]['date']} → {rows[-1]['date']})")
    return rows


def upsert_prices(rows: list) -> int:
    """Upsert price rows into Supabase. Returns count inserted/updated."""
    if not rows:
        return 0

    # Batch upsert in chunks of 500
    inserted = 0
    chunk_size = 500
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]

        # Use upsert (on conflict update)
        path = "daily_prices?on_conflict=symbol,date"
        headers = {
            'apikey': SUPABASE_SERVICE_KEY,
            'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation,resolution=merge-duplicates',
        }
        url = f"{SUPABASE_URL}/rest/v1/{path}"
        body = json.dumps(chunk).encode()
        req = urllib.request.Request(url, data=body, headers=headers, method='POST')

        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode())
                inserted += len(result)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            print(f"  Upsert error (batch {i // chunk_size}): HTTP {e.code}: {error_body[:200]}")

    return inserted


def main():
    parser = argparse.ArgumentParser(description='ASTS price backfill worker')
    parser.add_argument('--mode', choices=['backfill', 'update'], default='update',
                        help='backfill = full history from 2020, update = last 30 days')
    parser.add_argument('--symbol', default='ASTS', help='Stock symbol')
    parser.add_argument('--dry-run', action='store_true', help='Fetch but do not store')
    args = parser.parse_args()

    print(f"=== Price Worker [{args.mode}] — {args.symbol} ===")
    print(f"    {datetime.now(timezone.utc).isoformat()}")

    if args.mode == 'backfill':
        start = '2020-01-01'
    else:
        start = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    end = datetime.now().strftime('%Y-%m-%d')

    # Fetch from yfinance
    rows = fetch_prices(start, end, args.symbol)
    if not rows:
        print("No price data to store")
        return

    if args.dry_run:
        print(f"\n[DRY RUN] Would upsert {len(rows)} rows")
        print(f"  First: {rows[0]['date']} close={rows[0]['close']}")
        print(f"  Last:  {rows[-1]['date']} close={rows[-1]['close']}")
        return

    # Check existing
    existing = get_existing_dates(args.symbol)
    new_rows = [r for r in rows if r['date'] not in existing]
    print(f"  Existing: {len(existing)} days | New: {len(new_rows)} days | Total fetched: {len(rows)}")

    # Upsert all (handles both new and updated)
    count = upsert_prices(rows)
    print(f"\n  Upserted {count} price records")
    print("Done.")


if __name__ == '__main__':
    main()
