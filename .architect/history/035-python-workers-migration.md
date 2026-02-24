TARGET: .
---

MISSION:
Migrate all 23 Python worker scripts and 2 shared utility modules from the V1 archive to `scripts/data-fetchers/` in the main repository. These scripts are invoked by GitHub Actions workflows and handle all external data collection.

DIRECTIVES:

1. Create the `scripts/data-fetchers/` directory at the repo root.

2. Copy ALL Python files from `_ARCHIVE_V1/short-gravity-web/scripts/data-fetchers/` to `scripts/data-fetchers/`:
   ```
   cp _ARCHIVE_V1/short-gravity-web/scripts/data-fetchers/*.py scripts/data-fetchers/
   ```

   Complete file list (verify all 25 files are copied):
   **Worker scripts (23):**
   - `filing_worker.py` — SEC EDGAR → `filings`
   - `x_worker.py` — X/Twitter API v2 → `x_posts`
   - `news_worker.py` — Finnhub → `inbox`
   - `press_release_worker.py` — AccessWire → `press_releases`
   - `ecfs_worker_v2.py` — FCC ECFS → `fcc_filings` (ECFS)
   - `icfs_servicenow_worker.py` — FCC ICFS → `fcc_filings` (ICFS)
   - `patent_worker_v2.py` — PatentsView/EPO/Google → `patents`, `patent_claims`
   - `price_worker.py` — yfinance → `daily_prices`
   - `launch_worker.py` — press_releases (internal) → `next_launches`
   - `embedding_worker.py` — OpenAI → `brain_chunks`
   - `signal_scanner.py` — cross-source analysis → `signals`
   - `glossary_worker.py` — Claude API → `glossary_terms`, `glossary_citations`
   - `transcript_worker.py` — roic.ai → `earnings_transcripts`
   - `widget_data_worker.py` — multiple → `widget_cache`
   - `itu_worker.py` — ITU → `fcc_filings` (file_number like 'ITU-*')
   - `ised_worker.py` — ISED Canada → `fcc_filings` (file_number like 'ISED-*')
   - `ofcom_worker.py` — Ofcom UK → `fcc_filings` (file_number like 'OFCOM-*')
   - `uls_worker.py` — fcc.report → `fcc_filings` (ELS)
   - `space_weather_worker.py` — CelesTrak SW CSV → `space_weather`
   - `socrates_worker.py` — CelesTrak SOCRATES → `conjunctions`
   - `earnings_worker.py` — Finnhub → `earnings_calls` or `earnings_transcripts`
   - `short_interest_worker.py` — Yahoo Finance → `short_interest`
   - `cash_position_worker.py` — SEC filings → `cash_position`

   **Shared utilities (2):**
   - `storage_utils.py` — Supabase Storage upload/download helpers
   - `pdf_extractor.py` — PDF text extraction (pdfplumber + PyPDF2 fallback)

3. Create `scripts/data-fetchers/.env.example` with all required environment variables (values blank):
   ```
   # Core — required by all workers
   SUPABASE_URL=
   SUPABASE_SERVICE_KEY=

   # AI / Embeddings
   ANTHROPIC_API_KEY=
   OPENAI_API_KEY=

   # External APIs
   X_BEARER_TOKEN=
   FINNHUB_API_KEY=
   PATENTSVIEW_API_KEY=
   EPO_CONSUMER_KEY=
   EPO_CONSUMER_SECRET=
   ```

4. Check if `run_all.py` exists in the archive at either:
   - `_ARCHIVE_V1/short-gravity-web/scripts/data-fetchers/run_all.py`
   - `_ARCHIVE_V1/short-gravity-web/run_all.py`
   If found, copy to `scripts/data-fetchers/run_all.py`. This is a local convenience script for manual worker execution — NOT the automation layer.

5. AUDIT every Python worker script for reliability. For EACH script, verify:

   a. **Supabase connection**: Uses `os.environ.get('SUPABASE_URL')` and `os.environ.get('SUPABASE_SERVICE_KEY')` or `os.getenv()`. Must fail clearly if either is missing — check for explicit error messages or assertions.

   b. **supabase_request() helper**: Most workers define this inline. Verify it:
      - Constructs URL as `f"{SUPABASE_URL}/rest/v1/{endpoint}"`
      - Sets headers: `apikey`, `Authorization: Bearer`, `Content-Type: application/json`
      - For upserts: uses `Prefer: return=minimal,resolution=merge-duplicates`
      - Handles HTTP errors (non-2xx responses) with logging

   c. **Stdlib-only requirement**: Workers must use only Python stdlib (`urllib.request`, `json`, `os`, `sys`, `datetime`, `hashlib`, `re`, `ssl`, `time`, `csv`, `io`, `base64`, etc.) — NO `requests` library.
      Exceptions:
      - `price_worker.py`, `widget_data_worker.py`, `short_interest_worker.py` may import `yfinance`
      - `icfs_servicenow_worker.py`, `patent_worker_v2.py`, `transcript_worker.py` may import `playwright`
      - `pdf_extractor.py`, `uls_worker.py`, `ecfs_worker_v2.py` may import `pdfplumber`, `PyPDF2`

   d. **Table name correctness**: Verify each worker writes to the correct table. Key issues to check:
      - `earnings_worker.py` — does it write to `earnings_calls` or `earnings_transcripts`? The schema has `earnings_transcripts`. If it writes to `earnings_calls`, this is a bug — fix the table name.
      - `news_worker.py` — should write to `inbox` table.
      - International workers (`itu_worker.py`, `ised_worker.py`, `ofcom_worker.py`) must use `filing_system='ICFS'` (not custom values) with prefixed `file_number` for identification.

   e. **Upsert conflict columns**: Verify each worker's upsert `on_conflict` parameter matches the table's unique constraint:
      - `filings` → `accession_number`
      - `x_posts` → `source_id`
      - `press_releases` → `source_id`
      - `fcc_filings` → `filing_system,file_number`
      - `patents` → `patent_number`
      - `patent_claims` → `patent_number,claim_number`
      - `brain_chunks` → `source_table,source_id,chunk_index`
      - `conjunctions` → `cdm_id`
      - `space_weather` → `date`
      - `daily_prices` → `symbol,date`
      - `glossary_terms` → `normalized_term`
      - `signals` → `fingerprint`

6. Verify `storage_utils.py` references correct Supabase Storage bucket names: `sec-filings` and `fcc-filings`. Verify it uses the Storage API URL pattern: `{SUPABASE_URL}/storage/v1/object/{bucket}/{path}`.

7. Verify `embedding_worker.py`:
   a. Uses OpenAI `text-embedding-3-small` model (NOT `text-embedding-ada-002`).
   b. Output dimension is 1536.
   c. Writes to `brain_chunks` with columns: `source_table`, `source_id`, `chunk_index`, `content`, `embedding`, `metadata`.
   d. Supports `--table` argument to target specific source tables.
   e. Chunks text appropriately (2000 char size, 200 char overlap is the standard).

8. Verify `signal_scanner.py`:
   a. Queries multiple source tables for cross-source anomaly detection.
   b. Uses `fingerprint` for signal deduplication.
   c. Assigns severity levels: `critical`, `high`, `medium`, `low`.
   d. Creates signals with `signal_type` and `category` fields.

9. After all audits, list any scripts that reference tables or columns not in the known schema. Document these in `scripts/data-fetchers/AUDIT_NOTES.md`.
