#!/usr/bin/env python3
"""Audit SEC filings database for missing referenced documents."""

import os
import json
import urllib.request
import urllib.parse
import ssl

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

# Disable SSL verification for macOS
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def query_supabase(table, select="*", filters=None, order=None, limit=None):
    """Query Supabase REST API."""
    params = {"select": select}
    if filters:
        params.update(filters)
    if order:
        params["order"] = order
    if limit:
        params["limit"] = str(limit)

    url = f"{SUPABASE_URL}/rest/v1/{table}?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    })
    with urllib.request.urlopen(req, context=ctx) as resp:
        return json.loads(resp.read())

def query_rpc(function_name, body=None):
    """Call Supabase RPC function."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/{function_name}"
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(url, data=data, headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, context=ctx) as resp:
        return json.loads(resp.read())

def query_raw_sql(sql):
    """Run raw SQL via RPC - may not be available."""
    try:
        return query_rpc("exec_sql", {"query": sql})
    except Exception as e:
        return f"RPC not available: {e}"

# ============================================================
# 1. FORM TYPE DISTRIBUTION
# ============================================================
print("=" * 80)
print("1. FILING FORM TYPE DISTRIBUTION")
print("=" * 80)

all_filings = query_supabase("filings", select="form,filing_date,id")
from collections import Counter
form_counts = Counter(f["form"] for f in all_filings)
for form, count in form_counts.most_common():
    print(f"  {form}: {count}")
print(f"\n  TOTAL FILINGS: {len(all_filings)}")

# ============================================================
# 2. CHECK FOR EARNINGS CALL / TRANSCRIPT TABLES
# ============================================================
print("\n" + "=" * 80)
print("2. CHECK FOR EARNINGS CALLS / TRANSCRIPTS")
print("=" * 80)

for table in ["earnings_calls", "transcripts", "earnings_transcripts", "conference_calls"]:
    try:
        result = query_supabase(table, select="id", limit=1)
        print(f"  Table '{table}': EXISTS ({len(result)} sample rows)")
    except Exception as e:
        status = str(e)
        if "404" in status or "does not exist" in status.lower() or "42P01" in status:
            print(f"  Table '{table}': DOES NOT EXIST")
        else:
            print(f"  Table '{table}': Error - {status[:100]}")

# ============================================================
# 3. CHECK FOR INVESTOR PRESENTATION FORMS
# ============================================================
print("\n" + "=" * 80)
print("3. INVESTOR PRESENTATIONS / 8-K / DEF 14A CHECK")
print("=" * 80)

# 8-K often contains investor presentations as exhibits
eightk = query_supabase("filings", select="id,form,filing_date,content_text",
                         filters={"form": "eq.8-K"}, order="filing_date.desc", limit=5)
print(f"  8-K filings found: {form_counts.get('8-K', 0)}")
for f in eightk[:3]:
    ct = f.get("content_text", "") or ""
    has_pres = "presentation" in ct.lower() or "investor" in ct.lower()
    print(f"    {f['filing_date']}: {'HAS PRESENTATION REF' if has_pres else 'no presentation ref'} ({len(ct)} chars)")

# Check DEF 14A (proxy statements)
print(f"  DEF 14A (proxy statements): {form_counts.get('DEF 14A', 0)}")
print(f"  DEFA14A: {form_counts.get('DEFA14A', 0)}")
print(f"  S-1: {form_counts.get('S-1', 0)}")
print(f"  S-1/A: {form_counts.get('S-1/A', 0)}")
print(f"  424B: {form_counts.get('424B', 0)}")

# ============================================================
# 4. GET MOST RECENT 10-K
# ============================================================
print("\n" + "=" * 80)
print("4. MOST RECENT 10-K ANALYSIS")
print("=" * 80)

tenk = query_supabase("filings", select="id,form,filing_date,content_text",
                       filters={"form": "eq.10-K"}, order="filing_date.desc", limit=1)

if tenk:
    tk = tenk[0]
    content = tk.get("content_text", "") or ""
    print(f"  Most recent 10-K: {tk['filing_date']} ({len(content):,} chars)")

    # Save full content for separate analysis
    with open("/tmp/latest_10k.txt", "w") as f:
        f.write(content)
    print(f"  Saved to /tmp/latest_10k.txt")
else:
    print("  NO 10-K FOUND!")

# ============================================================
# 5. GET ALL 10-Qs
# ============================================================
print("\n" + "=" * 80)
print("5. 10-Q FILINGS")
print("=" * 80)

tenq = query_supabase("filings", select="id,form,filing_date",
                       filters={"form": "eq.10-Q"}, order="filing_date.desc")
print(f"  10-Q filings: {len(tenq)}")
for f in tenq:
    print(f"    {f['filing_date']}")

# ============================================================
# 6. SEARCH FOR EXHIBIT REFERENCES IN ALL FILINGS
# ============================================================
print("\n" + "=" * 80)
print("6. SEARCHING FOR KEY TERMS ACROSS ALL FILINGS")
print("=" * 80)

# We'll search a sample of filings for key terms
# Focus on 10-K and 10-Q
annual_quarterly = query_supabase("filings", select="id,form,filing_date,content_text",
                                   filters={"or": "(form.eq.10-K,form.eq.10-Q)"},
                                   order="filing_date.desc", limit=20)

search_terms = {
    "Exhibit": [],
    "incorporated by reference": [],
    "material contract": [],
    "agreement": [],
    "AT&T": [],
    "Vodafone": [],
    "Rakuten": [],
    "Verizon": [],
    "Ligado": [],
    "launch services": [],
    "SpaceX": [],
    "Blue Origin": [],
    "earnings call": [],
    "conference call": [],
    "transcript": [],
    "investor presentation": [],
    "investor day": [],
    "FCC": [],
    "ITU": [],
    "Ofcom": [],
    "patent": [],
    "credit facility": [],
    "credit agreement": [],
    "convertible": [],
    "indenture": [],
    "warrant": [],
    "employment agreement": [],
    "compensation": [],
    "spectrum": [],
    "ACMA": [],
    "MIC Japan": [],
}

for filing in annual_quarterly:
    ct = (filing.get("content_text", "") or "").lower()
    for term in search_terms:
        if term.lower() in ct:
            search_terms[term].append(f"{filing['form']} ({filing['filing_date']})")

print("\n  Term occurrence in 10-K/10-Q filings:")
for term, filings in sorted(search_terms.items()):
    if filings:
        print(f"  '{term}': found in {len(filings)} filings")
        for f in filings[:3]:
            print(f"      {f}")
    else:
        print(f"  '{term}': NOT FOUND")

# ============================================================
# 7. CHECK ALL TABLES IN THE DATABASE
# ============================================================
print("\n" + "=" * 80)
print("7. ALL DATABASE TABLES")
print("=" * 80)

known_tables = [
    "filings", "fcc_filings", "patents", "patent_claims", "patent_families",
    "earnings_calls", "transcripts", "press_releases", "news", "news_articles",
    "glossary_terms", "glossary", "tle_data", "tle_latest", "satellites",
    "short_interest", "cash_position", "worker_runs", "brain_conversations",
    "investor_presentations", "material_contracts", "exhibits",
    "launches", "next_launches", "itu_filings",
]

for table in known_tables:
    try:
        result = query_supabase(table, select="id", limit=1)
        # Get count
        all_rows = query_supabase(table, select="id")
        print(f"  {table}: EXISTS ({len(all_rows)} rows)")
    except Exception as e:
        status = str(e)
        if "404" in status or "42P01" in status:
            print(f"  {table}: DOES NOT EXIST")
        else:
            print(f"  {table}: ? ({str(e)[:60]})")

print("\nDone.")
