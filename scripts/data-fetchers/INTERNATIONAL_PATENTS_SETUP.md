# International Patent Claims API Setup

To reach the full 3,800 claims target, we need claims from international jurisdictions.

## Current Status

| Source | Patents | Claims | Status |
|--------|---------|--------|--------|
| BigQuery (US) | 109 | ~2,052 | ✅ Complete |
| EPO (EP/WO) | 52 | ~429 | ✅ Complete |
| **Japan (JP)** | 30 | 0 | 🔧 Needs API |
| **Korea (KR)** | 31 | 0 | 🔧 Needs API |
| **Australia (AU)** | 18 | 0 | 🔧 Needs API |
| **Canada (CA)** | 10 | 0 | 🔧 Needs API |
| **Total** | 250 | 2,482 | **65% of target** |

## API Registration Guide

### 1. Japan (J-PlatPat / JPO)

**Status:** Trial phase, registration may be closed

**Steps:**
1. Email `contact@ip-data-support.jpo.go.jp` requesting API access
2. Visit https://ip-data.jpo.go.jp/pages/top_e.html
3. Mention you're researching AST SpaceMobile patent portfolio
4. Once approved, add to `.env`:
   ```
   JPO_API_KEY=your_key_here
   ```

**Run:** `python3 jplatpat_claims_fetcher.py`

---

### 2. Korea (KIPRIS Plus)

**Status:** Open registration, free tier (1,000 calls/month)

**Steps:**
1. Go to https://plus.kipris.or.kr
2. Click "회원가입" (Register) - use Google Translate if needed
3. Register as individual researcher
4. Browse OpenAPI list and apply for Patent Claims API access
5. Add to `.env`:
   ```
   KIPRIS_API_KEY=your_key_here
   ```

**Run:** `python3 kipris_claims_fetcher.py`

---

### 3. Australia (IP Australia)

**Status:** Developer portal available

**Steps:**
1. Go to https://portal.api.ipaustralia.gov.au
2. Create an account
3. Apply for Patent API access
4. Note: May require OAuth2 credentials (client ID + secret)
5. Add to `.env`:
   ```
   IPA_CLIENT_ID=your_client_id
   IPA_CLIENT_SECRET=your_client_secret
   ```

**Run:** `python3 ipaustralia_claims_fetcher.py`

---

### 4. Canada (CIPO)

**Status:** No REST API - alternatives available

**Option A: IP Horizons Bulk Data**
1. Register at https://ised-isde.canada.ca/site/canadian-intellectual-property-office/en
2. Request access to IP Horizons XML data
3. Download and process locally

**Option B: Website Scraping (implemented)**
- The `cipo_claims_fetcher.py` script can scrape the public website
- Rate-limited to be respectful (2s delay)
- No API key needed

**Run:** `python3 cipo_claims_fetcher.py`

---

## Expected Claim Counts

Based on similar patents in other jurisdictions:

| Country | Patents | Est. Claims/Patent | Est. Total |
|---------|---------|-------------------|------------|
| JP | 30 | ~20 | ~600 |
| KR | 31 | ~20 | ~620 |
| AU | 18 | ~20 | ~360 |
| CA | 10 | ~20 | ~200 |
| **Total** | 89 | - | **~1,780** |

Combined with current 2,482 claims = **~4,262 total** (exceeds 3,800 target)

---

## Quick Test

After setting up API keys, test each fetcher:

```bash
cd /Users/gabriel/Desktop/short_gravity/scripts/data-fetchers
export $(grep -v '^#' .env | xargs)

# Test Japan
python3 jplatpat_claims_fetcher.py

# Test Korea
python3 kipris_claims_fetcher.py

# Test Australia
python3 ipaustralia_claims_fetcher.py

# Test Canada (no API key needed)
python3 cipo_claims_fetcher.py
```

---

## Notes

1. **Rate Limits:** All fetchers include rate limiting. Don't remove delays.

2. **Language:** JP/KR claims will be in native languages. Consider adding translation later.

3. **Claim Numbers:** International claims may have different numbering. Verify after import.

4. **Duplicates:** Some claims may overlap with WO (PCT) filings. The database handles duplicates via unique constraint.

5. **Updates:** Re-running fetchers will skip patents that already have claims.
