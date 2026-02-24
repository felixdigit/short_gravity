# Data Fetchers Audit Notes

Audit date: 2026-02-23
Scope: All 25 Python scripts (23 workers + 2 shared utilities) migrated from `_ARCHIVE_V1/` to `scripts/data-fetchers/`.

---

## Bugs Found & Fixed

### 1. earnings_worker.py — Wrong table name (CRITICAL)

**Issue:** All references to `earnings_calls` should be `earnings_transcripts`. The DB schema has `earnings_transcripts` with unique constraint `(company, fiscal_year, fiscal_quarter)`, but the worker was writing to a non-existent `earnings_calls` table.

**Fix:** Replaced all occurrences of `earnings_calls` with `earnings_transcripts` (lines 131, 134, 146, 223, 244).

### 2. uls_worker.py — Deprecated Claude model ID

**Issue:** Used `"claude-3-5-haiku-20241022"` (old naming convention) for API calls. This model ID is deprecated.

**Fix:** Replaced with `"claude-haiku-4-5-20251001"` (lines 364, 490).

### 3. filing_worker.py — Mismatched summary_model metadata

**Issue:** The actual API call uses `"claude-haiku-4-5-20251001"` (line 281), but the `summary_model` metadata field stored `"claude-3-5-sonnet-20241022"`. This causes the DB record to misreport which model generated the summary.

**Fix:** Updated `summary_model` metadata to `"claude-haiku-4-5-20251001"` (lines 344, 479).

### 4. news_worker.py — Hardcoded API key in source

**Issue:** `FINNHUB_API_KEY` had a hardcoded default value (`d5p3731r01qqu4br1230d5p3731r01qqu4br123g`) instead of an empty string. API keys should never appear in source code.

**Fix:** Changed default to empty string `""`.

---

## Per-Script Audit Results

### Shared Utilities

| Script | Status | Notes |
|--------|--------|-------|
| storage_utils.py | PASS | Correct bucket names (`sec-filings`, `fcc-filings`). Correct Storage API URL pattern. |
| pdf_extractor.py | PASS | Uses pdfplumber + PyPDF2 + pdfminer.six (allowed non-stdlib deps). |

### Workers

| Script | Table(s) | Upsert Key | Status | Notes |
|--------|----------|------------|--------|-------|
| filing_worker.py | filings | accession_number | FIXED | summary_model metadata corrected |
| x_worker.py | x_posts | source_id | PASS | — |
| news_worker.py | inbox | source, source_id | FIXED | Removed hardcoded API key |
| press_release_worker.py | press_releases | source_id | PASS | Uses Playwright |
| ecfs_worker_v2.py | fcc_filings (ECFS) | file_number, filing_system | PASS | Imports storage_utils, pdf_extractor |
| icfs_servicenow_worker.py | fcc_filings (ICFS) | file_number, filing_system | PASS | Uses Playwright |
| embedding_worker.py | brain_chunks | source_table, source_id, chunk_index | PASS | text-embedding-3-small, 1536 dims, 2000/200 chunking |
| signal_scanner.py | signals | fingerprint | PASS | Cross-source anomaly detection, severity levels |
| price_worker.py | daily_prices | symbol, date | PASS | Uses yfinance |
| launch_worker.py | next_launches | — | PASS | — |
| patent_worker_v2.py | patents, patent_claims | patent_number; (patent_number, claim_number) | PASS | Uses Playwright |
| glossary_worker.py | glossary_terms, glossary_citations | normalized_term | PASS | — |
| transcript_worker.py | inbox | source, source_id | PASS | Uses Playwright (roic.ai) |
| widget_data_worker.py | short_interest, cash_position, next_launches | — | PASS | Uses yfinance |
| earnings_worker.py | earnings_transcripts | (company, fiscal_year, fiscal_quarter) | FIXED | Table name corrected from earnings_calls |
| itu_worker.py | fcc_filings (ICFS) | file_number, filing_system | PASS | file_number prefix: `ITU-*` |
| ised_worker.py | fcc_filings (ICFS) | file_number, filing_system | PASS | file_number prefix: `ISED-*` |
| ofcom_worker.py | fcc_filings (ICFS) | file_number, filing_system | PASS | file_number prefix: `OFCOM-*` |
| uls_worker.py | fcc_filings (ELS) | file_number, filing_system | FIXED | Model ID updated |
| space_weather_worker.py | space_weather | date | PASS | CelesTrak CSV, batch upsert |
| socrates_worker.py | conjunctions | cdm_id | PASS | CelesTrak SOCRATES |
| short_interest_worker.py | short_interest | — | PASS | Uses yfinance |
| cash_position_worker.py | cash_position | — | PASS | Regex extraction from SEC filings |

---

## Observations (non-blocking)

### Hardcoded Supabase URL defaults

11 of 25 scripts include the project Supabase URL as a fallback default in `os.environ.get()`. This is a convenience pattern — the workers will fail on auth without `SUPABASE_SERVICE_KEY` regardless, so this doesn't constitute a security risk. Scripts without the default: short_interest_worker.py, cash_position_worker.py, price_worker.py, launch_worker.py, patent_worker_v2.py, widget_data_worker.py, transcript_worker.py, space_weather_worker.py, socrates_worker.py, embedding_worker.py, icfs_servicenow_worker.py, ised_worker.py, itu_worker.py, pdf_extractor.py.

### International filing system workaround

itu_worker.py, ised_worker.py, and ofcom_worker.py correctly use `filing_system='ICFS'` with prefixed `file_number` values (`ITU-*`, `ISED-*`, `OFCOM-*`) to work within the `fcc_filings` CHECK constraint (`filing_system IN ('ICFS', 'ECFS', 'ELS')`). The ofcom_worker.py docstring mentions a future schema migration to add `'OFCOM'` as a valid filing_system, but the code itself correctly uses the workaround.

### Playwright dependency

5 workers require Playwright (not stdlib): press_release_worker.py, icfs_servicenow_worker.py, patent_worker_v2.py, transcript_worker.py, ecfs_worker_v2.py. These need `pip install playwright && playwright install chromium` in their GitHub Actions workflows.

### yfinance dependency

3 workers require yfinance: price_worker.py, short_interest_worker.py, widget_data_worker.py.

### Supabase request helper consistency

All workers implement a `supabase_request()` helper with the correct pattern:
- URL: `{SUPABASE_URL}/rest/v1/{endpoint}`
- Headers: `apikey` + `Authorization: Bearer` + `Content-Type: application/json`
- Upsert: `Prefer: return=minimal,resolution=merge-duplicates` (or `return=representation` for workers that need the response)

Minor variation: some use positional args `(path, method, data)`, others use `(method, path, data)`. This is cosmetic and doesn't affect correctness.

---

## Files Migrated

26 files total: 23 workers + 2 utilities + run_all.py + .env.example (created new).

Source locations in archive:
- 23 files from `_ARCHIVE_V1/short-gravity-web/scripts/data-fetchers/`
- 2 files from `_ARCHIVE_V1/scripts/data-fetchers/` (short_interest_worker.py, cash_position_worker.py)
- 1 file from `_ARCHIVE_V1/scripts/data-fetchers/` (run_all.py)
