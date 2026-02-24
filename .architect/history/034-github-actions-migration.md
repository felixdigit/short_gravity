TARGET: .
---

MISSION:
Migrate all 24 GitHub Actions workflow YAML files from the V1 archive to the main repository. These scheduled workflows are the entire data collection automation layer — SEC filings, X/Twitter posts, FCC regulatory filings, patents, news, press releases, space weather, conjunctions, stock prices, embeddings, signal detection, and more.

DIRECTIVES:

1. Read the current state of `.github/workflows/`. There should be 2 disabled stub workflows (`x-worker.yml` and `signal-scanner.yml` that just echo deprecation messages). Delete both stubs.

2. Copy ALL 24 workflow YAML files from `_ARCHIVE_V1/short-gravity-web/.github/workflows/` to `.github/workflows/`. Use a bulk copy:
   ```
   cp _ARCHIVE_V1/short-gravity-web/.github/workflows/*.yml .github/workflows/
   ```
   If the archive uses `.yaml` extension instead of `.yml`, adjust accordingly. Copy all workflow files regardless of extension.

3. AUDIT every copied workflow file. Read each one and verify/fix the following:

   a. **Script paths**: Every `run:` step that invokes `python scripts/data-fetchers/<script>.py` must use the correct path relative to the repo root. The archive may use different paths — fix ALL to `scripts/data-fetchers/<script>.py`. Check for any path like `short-gravity-web/scripts/data-fetchers/` and remove the `short-gravity-web/` prefix.

   b. **Checkout action**: Must use `actions/checkout@v4` (not v2 or v3). Update if needed.

   c. **Python setup**: Must use `actions/setup-python@v5` with `python-version: '3.11'` or `'3.12'`. Update from `3.9` or `3.10` if found.

   d. **Secrets syntax**: All environment variables from GitHub secrets must use `${{ secrets.VARIABLE_NAME }}` syntax. Verify no hardcoded credentials.

   e. **Working directory**: If any workflow uses `working-directory: short-gravity-web` or similar, remove it — scripts are now at the repo root level.

4. Verify and fix each specific workflow:

   **High-frequency workers (run multiple times daily):**
   - `sec-filing-worker.yml` — Cron: market hours + off-hours + weekends. Script: `filing_worker.py`. Secrets: SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY.
   - `x-worker.yml` — Cron: every 15min market hours. Script: `x_worker.py`. Secrets: SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY, X_BEARER_TOKEN, OPENAI_API_KEY. Should have `concurrency` group to cancel in-progress runs.
   - `filing-embedding-worker.yml` — Cron: every 4h. Script: `embedding_worker.py --table filings`, then `--table fcc_filings`, then `--table x_posts`, then `--table press_releases` (4 sequential calls). Secrets: SUPABASE_URL, SUPABASE_SERVICE_KEY, OPENAI_API_KEY.
   - `signal-scanner.yml` — Cron: every 4h. Script: `signal_scanner.py`. Secrets: SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY.
   - `press-release-worker.yml` — Cron: every 4h. Script: `press_release_worker.py`. Secrets: SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY. Needs playwright + chromium.
   - `launch-worker.yml` — Cron: every 4h. Script: `launch_worker.py`. Secrets: SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY.
   - `news-worker.yml` — Cron: every hour weekdays. Script: `news_worker.py`. Secrets: SUPABASE_URL, SUPABASE_SERVICE_KEY, FINNHUB_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY.

   **Daily workers:**
   - `ecfs-worker.yml` — Cron: daily 10:00 UTC. Script: `ecfs_worker_v2.py` (two-phase). Secrets: SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY. Needs pdfplumber, PyPDF2, playwright, firefox.
   - `icfs-worker.yml` — Cron: every 8h. Script: `icfs_servicenow_worker.py`. Secrets: SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY. Needs playwright, chromium. 60-minute timeout.
   - `space-weather-worker.yml` — Cron: daily 16:30 UTC. Script: `space_weather_worker.py`. Secrets: SUPABASE_URL, SUPABASE_SERVICE_KEY.
   - `socrates-worker.yml` — Cron: daily 14:30 UTC. Script: `socrates_worker.py`. Secrets: SUPABASE_URL, SUPABASE_SERVICE_KEY.
   - `price-worker.yml` — Cron: daily 22:00 UTC weekdays. Script: `price_worker.py --mode update`. Secrets: SUPABASE_URL, SUPABASE_SERVICE_KEY. Needs yfinance.
   - `cash-position-worker.yml` — Cron: daily 9:00 UTC. Script: `cash_position_worker.py`. Secrets: SUPABASE_URL, SUPABASE_SERVICE_KEY.
   - `staleness-alert.yml` — Cron: daily 16:00 UTC. Uses bash/curl (no Python script). Secrets: SUPABASE_URL, SUPABASE_SERVICE_KEY, GH_TOKEN. Creates GitHub issues for stale data.
   - `patent-worker.yml` — Cron: daily 6:00 UTC. Script: `patent_worker_v2.py`. Secrets: PATENTSVIEW_API_KEY, EPO_CONSUMER_KEY, EPO_CONSUMER_SECRET, SUPABASE_URL, SUPABASE_SERVICE_KEY, OPENAI_API_KEY. Needs playwright, chromium.

   **Weekly workers:**
   - `transcript-worker.yml` — Cron: Wed 14:00 UTC. Script: `transcript_worker.py`. Needs playwright, chromium.
   - `glossary-worker.yml` — Cron: Sun 8:00 UTC. Script: `glossary_worker.py`. Secrets: SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY.
   - `widget-data-worker.yml` — Cron: Mon 15:00 UTC. Script: `widget_data_worker.py`. Needs yfinance.
   - `itu-worker.yml` — Cron: Mon 13:00 UTC. Script: `itu_worker.py`. Includes embedding step.
   - `ised-worker.yml` — Cron: Tue 11:00 UTC. Script: `ised_worker.py`. Includes embedding step.
   - `ofcom-worker.yml` — Cron: Wed 9:00 UTC. Script: `ofcom_worker.py`. 45-minute timeout. Includes embedding step.
   - `uls-worker.yml` — Cron: Thu 10:00 UTC. Script: `uls_worker.py`. Needs playwright, pdfplumber, PyPDF2, chromium.
   - `short-interest-worker.yml` — Cron: Fri 22:00 UTC. Script: `short_interest_worker.py`. Needs yfinance.
   - `earnings-worker.yml` — Cron: Wed 14:30 UTC. Script: `earnings_worker.py`. Secrets: SUPABASE_URL, SUPABASE_SERVICE_KEY, FINNHUB_API_KEY.

5. After auditing all workflows, compile a complete list of ALL unique GitHub secrets required. Write this to `.github/SECRETS_REQUIRED.md`:
   ```
   # Required GitHub Repository Secrets

   ## Core (all workers)
   - SUPABASE_URL
   - SUPABASE_SERVICE_KEY

   ## AI / Embeddings
   - ANTHROPIC_API_KEY
   - OPENAI_API_KEY

   ## External APIs
   - X_BEARER_TOKEN
   - FINNHUB_API_KEY
   - PATENTSVIEW_API_KEY
   - EPO_CONSUMER_KEY
   - EPO_CONSUMER_SECRET

   ## Infrastructure
   - GH_TOKEN (for staleness-alert GitHub issues)
   ```
   Add any other secrets found during the audit.

6. Verify no workflow has `workflow_dispatch` disabled — all workflows should allow manual triggering via `workflow_dispatch:` in addition to their cron schedules.

7. Verify no two workflows have overlapping cron schedules that could cause resource contention. Flag any conflicts.
