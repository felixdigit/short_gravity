#!/usr/bin/env python3
"""
Widget Data Worker — Unified live data updater for HUD widgets.

Updates: short interest, cash position, launch status.
Run: cd scripts/data-fetchers && export $(grep -v '^#' .env | xargs) && python3 widget_data_worker.py
Schedule: weekly via GitHub Actions
"""

import os
import sys
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
        print(f"    HTTP {e.code}: {e.read().decode()[:200]}")
        return None


def check_exists(table, filters):
    """Check if a row matching filters exists."""
    qs = '&'.join(f'{k}=eq.{v}' for k, v in filters.items())
    result = supabase_request(f'{table}?{qs}&select=id&limit=1')
    return result and len(result) > 0


# =========================================================================
# SHORT INTEREST (Yahoo Finance via yfinance)
# =========================================================================

def sync_short_interest():
    print("\n[1/3] SHORT INTEREST")
    try:
        import yfinance as yf
    except ImportError:
        print("  SKIP: yfinance not installed (pip install yfinance)")
        return False

    print("  Fetching from Yahoo Finance...")
    t = yf.Ticker('ASTS')
    info = t.info

    shares_short = info.get('sharesShort')
    if not shares_short:
        print("  ERROR: No short interest data returned")
        return False

    report_date = None
    if info.get('dateShortInterest'):
        report_date = datetime.fromtimestamp(
            info['dateShortInterest'], tz=timezone.utc
        ).strftime('%Y-%m-%d')

    if report_date and check_exists('short_interest', {'symbol': 'ASTS', 'report_date': report_date}):
        print(f"  Already have data for {report_date} — skipping")
        return True

    data = {
        'symbol': 'ASTS',
        'shares_short': shares_short,
        'short_ratio': info.get('shortRatio'),
        'short_pct_float': round(info.get('shortPercentOfFloat', 0) * 100, 2),
        'short_pct_outstanding': round(info.get('sharesPercentSharesOut', 0) * 100, 2),
        'shares_short_prior': info.get('sharesShortPriorMonth'),
        'shares_outstanding': info.get('sharesOutstanding'),
        'float_shares': info.get('floatShares'),
        'report_date': report_date,
        'fetched_at': datetime.now(timezone.utc).isoformat(),
    }

    result = supabase_request('short_interest', method='POST', data=data)
    if result:
        print(f"  {shares_short:,} shares short ({data['short_pct_float']}% float) · {data['short_ratio']}d to cover")
        print(f"  Report date: {report_date} · Stored OK")
        return True
    print("  ERROR: Failed to store")
    return False


# =========================================================================
# CASH POSITION (earnings transcript pro forma → 10-Q/10-K fallback)
# =========================================================================

def extract_proforma_from_transcript(transcript):
    """Extract pro forma cash/liquidity figure from earnings call transcript."""
    # Look for "$X.X billion" in context of pro forma / liquidity / cash
    patterns = [
        # "$3.2 billion in cash and liquidity ... pro forma"
        r'\$([\d.]+)\s*billion\s+(?:in\s+)?(?:cash(?:\s+and\s+(?:cash\s+equivalents|liquidity))?|pro\s*forma)',
        # "pro forma ... $3.2 billion"
        r'pro\s*forma.*?\$([\d.]+)\s*billion',
        # "cash, cash equivalents, and restricted cash and available liquidity ... $X.X billion"
        r'cash[,\s]+cash equivalents[,\s]+(?:and\s+)?restricted cash.*?\$([\d.]+)\s*billion',
        # "$X.X billion on a pro forma basis"
        r'\$([\d.]+)\s*billion\s+on\s+a\s+pro\s*forma\s+basis',
    ]
    for pattern in patterns:
        m = re.search(pattern, transcript, re.IGNORECASE)
        if m:
            return float(m.group(1))
    return None


def sync_cash_position():
    print("\n[2/3] CASH POSITION")

    # --- Step 1: Check latest earnings transcript for pro forma liquidity ---
    transcript_params = urllib.parse.urlencode({
        'select': 'source_id,title,published_at,content_text,metadata',
        'source': 'eq.earnings_call',
        'content_text': 'not.is.null',
        'order': 'published_at.desc',
        'limit': '1',
    })
    transcripts = supabase_request(f'inbox?{transcript_params}')

    proforma_billions = None
    transcript_date = None
    transcript_quarter = None

    if transcripts and len(transcripts) > 0:
        t = transcripts[0]
        transcript_date = t.get('published_at', '')[:10]  # YYYY-MM-DD
        meta = t.get('metadata') or {}
        if isinstance(meta, str):
            meta = json.loads(meta)
        transcript_quarter = f"{meta.get('fiscal_quarter', '??')} {meta.get('fiscal_year', '????')}"
        content = t.get('content_text', '')
        if content:
            proforma_billions = extract_proforma_from_transcript(content)
            if proforma_billions:
                print(f"  Found ${proforma_billions}B pro forma in {transcript_quarter} call")

    # --- Step 2: Also get latest 10-Q/10-K for burn rate + balance sheet ---
    params = urllib.parse.urlencode({
        'select': 'accession_number,form,filing_date,content_text',
        'form': 'in.(10-Q,10-K,10-Q/A,10-K/A)',
        'status': 'eq.completed',
        'order': 'filing_date.desc',
        'limit': '1',
    })
    filings = supabase_request(f'filings?{params}')

    filing_date = None
    filing_form = None
    accession = None
    quarterly_burn = None
    balance_sheet_cash = None

    if filings and len(filings) > 0:
        filing = filings[0]
        content = filing.get('content_text', '')
        filing_date = filing.get('filing_date')
        filing_form = filing.get('form')
        accession = filing.get('accession_number')

        if content:
            print(f"  Parsing {filing_form} filed {filing_date}...")

            # Balance sheet cash
            m = re.search(r'Cash and cash equivalents\s+\$\s*([\d,]+)', content)
            if m:
                balance_sheet_cash = int(m.group(1).replace(',', ''))

            # Quarterly burn
            m = re.search(r'Cash used in operating activities\s*\(?\s*([\d,]+)', content, re.IGNORECASE)
            if m:
                quarterly_burn = int(m.group(1).replace(',', ''))

    # --- Step 3: Determine best date for dedup ---
    best_date = transcript_date or filing_date
    if not best_date:
        print("  ERROR: No filings or transcripts found")
        return False

    if check_exists('cash_position', {'symbol': 'ASTS', 'filing_date': best_date}):
        print(f"  Already have data for {best_date} — skipping")
        return True

    # --- Step 4: Build record, preferring pro forma from transcript ---
    data = {
        'symbol': 'ASTS',
        'filing_form': filing_form or 'CALL',
        'filing_date': best_date,
        'accession_number': accession,
        'unit': 'thousands',
    }

    if balance_sheet_cash:
        data['cash_and_equivalents'] = balance_sheet_cash

    if quarterly_burn:
        data['quarterly_burn'] = quarterly_burn

    if proforma_billions:
        # Pro forma from earnings call — this is the headline number
        data['available_liquidity'] = int(proforma_billions * 1_000_000)  # billions → thousands
        data['label'] = f'PRO FORMA LIQUIDITY ({transcript_quarter} CALL)'
    else:
        # Fall back to 10-Q balance sheet
        if balance_sheet_cash:
            data['available_liquidity'] = balance_sheet_cash
            data['label'] = 'ON HAND'
        else:
            print("  WARNING: No cash data extracted")
            return False

    result = supabase_request('cash_position', method='POST', data=data)
    if result:
        liq = data.get('available_liquidity', 0)
        burn = data.get('quarterly_burn', 0)
        print(f"  Liquidity: ${liq / 1_000_000:,.1f}B · Burn: ${burn / 1_000:,.0f}M/qtr · Stored OK")
        return True
    print("  ERROR: Failed to store")
    return False


# =========================================================================
# LAUNCH STATUS (mark past launches as LAUNCHED)
# =========================================================================

def sync_launch_status():
    print("\n[3/3] LAUNCH STATUS")

    launches = supabase_request(
        'next_launches?status=eq.SCHEDULED&order=target_date.asc&select=id,mission,target_date'
    )
    if not launches:
        print("  No scheduled launches found")
        return True

    now = datetime.now(timezone.utc)
    updated = 0

    for launch in launches:
        target = launch.get('target_date')
        if not target:
            continue
        target_dt = datetime.fromisoformat(target.replace('Z', '+00:00'))
        # If target date is more than 7 days in the past, mark as launched
        if (now - target_dt).days > 7:
            result = supabase_request(
                f"next_launches?id=eq.{launch['id']}",
                method='PATCH',
                data={'status': 'LAUNCHED', 'updated_at': now.isoformat()}
            )
            if result:
                print(f"  Marked {launch['mission']} as LAUNCHED (target was {target[:10]})")
                updated += 1

    print(f"  {len(launches)} scheduled, {updated} auto-marked as launched")
    return True


# =========================================================================
# MAIN
# =========================================================================

def main():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY")
        sys.exit(1)

    print("=" * 50)
    print("WIDGET DATA WORKER")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 50)

    results = {}
    results['short_interest'] = sync_short_interest()
    results['cash_position'] = sync_cash_position()
    results['launch_status'] = sync_launch_status()

    print("\n" + "=" * 50)
    for k, v in results.items():
        status = "OK" if v else "FAILED"
        print(f"  {k}: {status}")
    print("=" * 50)

    if not all(results.values()):
        sys.exit(1)


if __name__ == '__main__':
    main()
