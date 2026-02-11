# Patent Claims Implementation - Handoff Document

## Status: 65% Complete

**Created:** Feb 4, 2025
**Purpose:** Resume patent claims capture in a new Claude session

---

## Current Database State

```
Total claims: 2,482 (target: ~3,800)
- US claims: ~2,052 (BigQuery) ✅
- EP/WO claims: ~430 (EPO OPS) ✅
- JP/KR/AU/CA claims: 0 (need ~1,300 more)

Patents: 307 across 29 families (target: 36 families)
```

---

## What's Done ✅

1. **BigQuery US Claims** - `bigquery_ast_claims.py` - WORKING
2. **EPO EP/WO Claims** - `epo_claims_fetcher.py` - WORKING
3. **Claim splitting** - `split_claims.py` - WORKING
4. **Database table** - `patent_claims` exists with 2,482 records

---

## What's Next 🔧

### Immediate: SerpApi for International Claims

**Decision made:** Use SerpApi ($50/mo) to fetch JP/KR/AU/CA claims immediately.

**Steps:**
1. Sign up at https://serpapi.com ($50/month plan)
2. Get API key
3. Add to `.env`: `SERPAPI_API_KEY=your_key`
4. Create `serpapi_claims_fetcher.py` (see template below)
5. Run fetcher for 89 international patents

### Parallel: Apply for Lens.org (free long-term)

1. Go to https://www.lens.org
2. Create account → API tab → Request Trial Access
3. Once approved (~1-2 weeks), switch from SerpApi to save $50/mo

---

## Patents Needing Claims

```
JP: 30 patents (e.g., JP2019001446A, JP2022173202A)
KR: 31 patents (e.g., KR102454426B1, KR102477970B1)
AU: 18 patents (e.g., AU2018283981B2, AU2020241308A1)
CA: 10 patents (e.g., CA3066691A1, CA3134030C)
Total: 89 patents → ~1,300 claims expected
```

---

## SerpApi Fetcher Template

```python
#!/usr/bin/env python3
"""
SerpApi Patent Claims Fetcher
Fetches JP/KR/AU/CA claims via Google Patents scraping
"""

import json
import os
import re
import urllib.request
from datetime import datetime

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY", "")

SERPAPI_BASE = "https://serpapi.com/search.json"


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def serpapi_patent_details(patent_id):
    """Fetch patent details including claims from SerpApi."""
    params = {
        "engine": "google_patents",
        "patent_id": patent_id,
        "api_key": SERPAPI_API_KEY,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{SERPAPI_BASE}?{query}"

    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode())


def convert_to_google_patent_id(patent_number):
    """Convert our format to Google Patents format.
    JP2019001446A -> JP-2019001446-A
    KR102454426B1 -> KR-102454426-B1
    """
    match = re.match(r'^([A-Z]{2})(\d+)([A-Z]\d?)$', patent_number)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return patent_number


# ... rest of implementation
```

---

## Environment Variables Needed

```bash
# scripts/data-fetchers/.env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=xxx
SERPAPI_API_KEY=xxx  # NEW - get from serpapi.com
```

---

## Verification Command

```bash
cd /Users/gabriel/Desktop/short_gravity/scripts/data-fetchers
export $(grep -v '^#' .env | xargs)

# Check total claims
curl -s -G -H "apikey: $SUPABASE_SERVICE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  -H "Prefer: count=exact" \
  "$SUPABASE_URL/rest/v1/patent_claims?select=id" -I | grep content-range

# Expected after SerpApi: content-range: 0-0/~3800
```

---

## Key Files

| File | Purpose |
|------|---------|
| `scripts/data-fetchers/.env` | API credentials |
| `scripts/data-fetchers/bigquery_ast_claims.py` | US claims fetcher ✅ |
| `scripts/data-fetchers/epo_claims_fetcher.py` | EP/WO claims fetcher ✅ |
| `scripts/data-fetchers/serpapi_claims_fetcher.py` | TO CREATE |
| `docs/DATA_SOURCES.md` | Documentation |
| `CLAUDE.md` | Project context |

---

## New Session Prompt

Copy this to start a new session:

```
Continue patent claims implementation for Short Gravity.

Read: /Users/gabriel/Desktop/short_gravity/scripts/data-fetchers/PATENT_CLAIMS_HANDOFF.md

Current state: 2,482 claims captured (US + EP/WO). Need ~1,300 more from JP/KR/AU/CA.

Next step: Create serpapi_claims_fetcher.py using the SerpApi Google Patents API.
I have signed up for SerpApi - my API key is: [PASTE KEY HERE]

Target: Reach ~3,800 total claims to match official AST SpaceMobile disclosure.
```
