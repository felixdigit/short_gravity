#!/usr/bin/env python3
"""
Short Interest Worker
Fetches ASTS short interest data from Yahoo Finance via yfinance
and stores it in Supabase for the HUD widget.

Run: cd scripts/data-fetchers && export $(grep -v '^#' .env | xargs) && python3 short_interest_worker.py
Schedule: weekly (FINRA updates biweekly, mid-month and end-of-month)
"""

import os
import sys
import json
import urllib.request
from datetime import datetime, timezone

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')

def supabase_request(path, method='GET', data=None):
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
        print(f"  HTTP {e.code}: {e.read().decode()}")
        return None

def fetch_short_interest():
    """Fetch short interest data using yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance not installed. Run: pip3 install yfinance")
        sys.exit(1)

    print("Fetching ASTS short interest from Yahoo Finance...")
    t = yf.Ticker('ASTS')
    info = t.info

    shares_short = info.get('sharesShort')
    if shares_short is None:
        print("ERROR: No short interest data returned")
        return None

    data = {
        'symbol': 'ASTS',
        'shares_short': shares_short,
        'short_ratio': info.get('shortRatio'),
        'short_pct_float': round(info.get('shortPercentOfFloat', 0) * 100, 2),
        'short_pct_outstanding': round(info.get('sharesPercentSharesOut', 0) * 100, 2),
        'shares_short_prior': info.get('sharesShortPriorMonth'),
        'shares_outstanding': info.get('sharesOutstanding'),
        'float_shares': info.get('floatShares'),
        'report_date': datetime.fromtimestamp(
            info.get('dateShortInterest', 0), tz=timezone.utc
        ).strftime('%Y-%m-%d') if info.get('dateShortInterest') else None,
        'fetched_at': datetime.now(timezone.utc).isoformat(),
    }

    print(f"  Shares short: {shares_short:,}")
    print(f"  Float shorted: {data['short_pct_float']}%")
    print(f"  Days to cover: {data['short_ratio']}")
    print(f"  Prior month: {data['shares_short_prior']:,}" if data['shares_short_prior'] else "  Prior month: N/A")
    print(f"  Report date: {data['report_date']}")

    return data

def check_existing(report_date):
    """Check if we already have data for this report_date."""
    path = f"short_interest?symbol=eq.ASTS&report_date=eq.{report_date}&select=id&limit=1"
    result = supabase_request(path)
    return result and len(result) > 0

def store_short_interest(data):
    """Insert into Supabase short_interest table (skip if duplicate)."""
    report_date = data.get('report_date')
    if report_date and check_existing(report_date):
        print(f"  Already have data for {report_date} — skipping")
        return True

    result = supabase_request('short_interest', method='POST', data=data)
    if result:
        print(f"  Stored in Supabase (id: {result[0].get('id', 'ok')})")
        return True
    else:
        print("  Failed to store in Supabase")
        return False

def main():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY")
        sys.exit(1)

    data = fetch_short_interest()
    if data:
        store_short_interest(data)
    print("Done.")

if __name__ == '__main__':
    main()
