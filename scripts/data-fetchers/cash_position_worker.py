#!/usr/bin/env python3
"""
Cash Position Worker
Extracts cash/liquidity data from latest SEC 10-Q/10-K filings in Supabase.

Run: cd scripts/data-fetchers && export $(grep -v '^#' .env | xargs) && python3 cash_position_worker.py
Schedule: after filing_worker runs (monthly or on new 10-Q/10-K)
"""

# DISABLED: Functionality fully covered by widget_data_worker.py sync_cash_position(),
# which is a superset — it extracts pro forma liquidity from earnings transcripts
# AND falls back to the same 10-Q/10-K regex parsing. Both write to cash_position table.
import sys
sys.exit(0)

import os
import json
import re
import urllib.request
import urllib.parse
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
        print(f"  HTTP {e.code}: {e.read().decode()[:200]}")
        return None


def get_latest_quarterly():
    """Get latest 10-Q or 10-K with content."""
    params = urllib.parse.urlencode({
        'select': 'accession_number,form,filing_date,content_text',
        'form': 'in.(10-Q,10-K,10-Q/A,10-K/A)',
        'status': 'eq.completed',
        'order': 'filing_date.desc',
        'limit': '3',
    })
    result = supabase_request(f'filings?{params}')
    if not result:
        print("ERROR: No filings found")
        return None
    # Return first with content
    for f in result:
        if f.get('content_text'):
            return f
    print("ERROR: No filings with content")
    return None


def extract_cash_data(content, form, filing_date, accession):
    """Extract cash figures from 10-Q/10-K content text."""
    data = {
        'symbol': 'ASTS',
        'filing_form': form,
        'filing_date': filing_date,
        'accession_number': accession,
        'unit': 'thousands',
    }

    # 1. Balance sheet: "Cash and cash equivalents $ X"
    m = re.search(
        r'Cash and cash equivalents\s+\$\s*([\d,]+)',
        content
    )
    if m:
        data['cash_and_equivalents'] = int(m.group(1).replace(',', ''))
        print(f"  Cash & equivalents: ${data['cash_and_equivalents']:,}K")

    # 2. Restricted cash from balance sheet
    m = re.search(
        r'Restricted cash\s+(\d[\d,]*)',
        content
    )
    if m:
        data['restricted_cash'] = int(m.group(1).replace(',', ''))
        print(f"  Restricted cash: ${data['restricted_cash']:,}K")

    # 3. Cash flow statement: "Cash, cash equivalents and restricted cash $ X"
    m = re.search(
        r'Cash, cash equivalents and restricted cash\s+\$\s*([\d,]+)',
        content
    )
    if m:
        data['total_cash_restricted'] = int(m.group(1).replace(',', ''))
        print(f"  Total cash+restricted: ${data['total_cash_restricted']:,}K")

    # 4. Liquidity disclosure: "$X million of cash ... on hand" + ATM remaining
    liquidity = 0
    label_parts = []

    m = re.search(
        r'\$([\d,.]+)\s*(?:million|billion)\s+(?:of\s+)?cash(?:\s+and\s+cash\s+equivalents)?\s+on\s+hand',
        content, re.IGNORECASE
    )
    if m:
        val = float(m.group(1).replace(',', ''))
        # Check if billion
        if 'billion' in content[m.start():m.end() + 20].lower():
            val *= 1000
        liquidity += val
        label_parts.append(f'${val:,.0f}M cash on hand')

    # ATM remaining
    m = re.search(
        r'\$([\d,.]+)\s*(?:million|billion)\s+remaining.*?(?:ATM|at.the.market)',
        content, re.IGNORECASE
    )
    if m:
        val = float(m.group(1).replace(',', ''))
        if 'billion' in content[m.start():m.end() + 20].lower():
            val *= 1000
        liquidity += val
        label_parts.append(f'${val:,.0f}M ATM')

    if liquidity > 0:
        data['available_liquidity'] = int(liquidity * 1000)  # convert M to K
        data['label'] = ' + '.join(label_parts)
        print(f"  Available liquidity: ${liquidity:,.1f}M ({data['label']})")

    # 5. Quarterly burn: "Cash used in operating activities (X)"
    m = re.search(
        r'Cash used in operating activities\s*\(?\s*([\d,]+)',
        content
    )
    if m:
        data['quarterly_burn'] = int(m.group(1).replace(',', ''))
        print(f"  Quarterly burn: ${data['quarterly_burn']:,}K")

    # 6. Also check for pro forma liquidity mentions in MD&A
    m = re.search(
        r'(?:pro\s*forma|including).*?(?:cash|liquidity).*?\$([\d,.]+)\s*(billion|million)',
        content, re.IGNORECASE
    )
    if m:
        val = float(m.group(1).replace(',', ''))
        unit = m.group(2).lower()
        if unit == 'billion':
            val_k = int(val * 1_000_000)
        else:
            val_k = int(val * 1_000)
        # Only use if larger than what we found
        if val_k > data.get('available_liquidity', 0):
            data['available_liquidity'] = val_k
            data['label'] = f'${val}{unit[0].upper()} pro forma liquidity'
            print(f"  Pro forma liquidity: ${val}{unit[0].upper()}")

    return data


def check_existing(filing_date):
    """Check if we already have data for this filing."""
    path = f"cash_position?symbol=eq.ASTS&filing_date=eq.{filing_date}&select=id&limit=1"
    result = supabase_request(path)
    return result and len(result) > 0


def store_cash_position(data):
    """Insert into Supabase cash_position table."""
    filing_date = data.get('filing_date')
    if filing_date and check_existing(filing_date):
        print(f"  Already have data for {filing_date} — skipping")
        return True

    result = supabase_request('cash_position', method='POST', data=data)
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

    print("Fetching latest quarterly filing...")
    filing = get_latest_quarterly()
    if not filing:
        sys.exit(1)

    print(f"  Found: {filing['form']} filed {filing['filing_date']}")
    print("Extracting cash data...")

    data = extract_cash_data(
        filing['content_text'],
        filing['form'],
        filing['filing_date'],
        filing['accession_number'],
    )

    if not data.get('cash_and_equivalents') and not data.get('available_liquidity'):
        print("WARNING: No cash data extracted")
    else:
        store_cash_position(data)

    print("Done.")


if __name__ == '__main__':
    main()
