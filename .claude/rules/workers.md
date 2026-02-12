# Data Workers Reference

**Automation = GitHub Actions.** Every worker runs on a cron schedule in `.github/workflows/`.
`run_all.py` is a local convenience for manual runs only — NOT the automation layer.

Workers deployed at `short-gravity-web/scripts/data-fetchers/`. Dev copies at `scripts/data-fetchers/`.
When modifying a worker, update BOTH copies. Python 3.9+, stdlib only (`urllib` not `requests`).

## All Scheduled Workers (GitHub Actions)

| Worker | Source | Table | GH Actions Schedule | Key Flags |
|--------|--------|-------|---------------------|-----------|
| filing_worker.py | SEC EDGAR | filings | Every 2h weekdays + daily 8 UTC | — |
| x_worker.py | X/Twitter API v2 | x_posts | Every 15min market hours | `--dry-run` |
| news_worker.py | Finnhub | inbox | Daily 13:00 weekdays | — |
| press_release_worker.py | AccessWire | press_releases | Daily 14:00 | — |
| ecfs_worker.py (v2) | FCC ECFS API | fcc_filings (ECFS) | Daily 10:00 | `--docket`, `--no-pdf` |
| icfs_servicenow_worker.py | FCC ICFS | fcc_filings (ICFS) | Daily 12:00 | `--backfill` |
| patent_worker_v2.py | PatentsView, EPO, Google | patents, patent_claims | Daily 6:00 | `--full`, `--stage N` |
| price_worker.py | yfinance | daily_prices | Daily 22:00 weekdays | — |
| launch_worker.py | press_releases | next_launches | Daily 15:30 | — |
| embedding_worker.py | All content tables | brain_chunks | Daily 15:00 | `--table X` |
| signal_scanner.py | All tables | signals | Twice daily 13:00 + 21:00 | `--dry-run` |
| transcript_worker.py | roic.ai | earnings_transcripts | Weekly Wed 14:00 | — |
| glossary_worker.py | Claude API | glossary_terms | Weekly Sun 8:00 | — |
| widget_data_worker.py | Multiple | widget_cache | Weekly Mon 15:00 | — |
| itu_worker.py | ITU RB, SNL | fcc_filings (ITU-*) | Weekly Mon 13:00 | `--audit`, `--all` |
| ised_worker.py | ISED Drupal, Canada Gazette | fcc_filings (ISED-*) | Weekly Tue 11:00 | `--backfill`, `--gazette-only` |
| ofcom_worker.py | Ofcom via Wayback Machine | fcc_filings (OFCOM-*) | Weekly Wed 9:00 | `--live-only`, `--wayback-only` |
| uls_worker.py | fcc.report | fcc_filings (ELS) | Weekly Thu 10:00 | `--backfill` |
| space_weather_worker.py | CelesTrak SW CSV | space_weather | Daily 16:30 | `--backfill` |
| socrates_worker.py | CelesTrak SOCRATES | conjunctions | Daily 14:30 | — |
| short_interest_worker.py | Yahoo Finance | short_interest | Weekly Fri 22:00 | — |
| cash_position_worker.py | SEC filings | cash_position | Daily 09:00 | — |
| staleness-alert | All tables | — (GitHub Issues) | Daily 16:00 | — |

## Vercel Cron (exception to GH Actions pattern)

| Route | Source | Table | Schedule | Notes |
|-------|--------|-------|----------|-------|
| /api/cron/tle-refresh | CelesTrak + Space-Track | satellites, tle_history, signals | Every 4h | Dual-source, health anomaly detection. Python `tle_worker.py` is local/backfill only |
| /api/cron/check-feeds | — | — | Every 5min | Feed monitoring |
| /api/cron/filings-sync | — | — | Every 15min | Filing sync |

## Local-Only Workers (run_all.py, no GH Actions)

These need GH Actions workflows to be fully automated:

| Worker | Source | Table | Notes |
|--------|--------|-------|-------|
| exhibit_backfill.py | SEC EDGAR | sec_filing_exhibits | `--limit N` |
| fcc_attachment_worker.py | FCC ELS/ICFS | fcc_filing_attachments | `--icfs-incremental`, `--els-scan` |
| patent_enricher.py | Google Patents | patents, patent_claims | `--missing-only` |

## International Filing System Workaround

The `fcc_filings` table has a CHECK constraint: `filing_system IN ('ICFS', 'ECFS', 'ELS')`.
International workers use `filing_system='ICFS'` with prefixed `file_number` for identification:
- ITU: `ITU-SNL-*` or `ITU-*`
- ISED: `ISED-*`
- OFCOM: `OFCOM-*`

Query international filings: `file_number=like.ISED-*` (not `filing_system=eq.ISED`)

## ECFS Dockets Tracked

| Docket | Description |
|--------|-------------|
| 23-65 | SCS NPRM (main D2D rulemaking) |
| 23-135 | SpaceX/T-Mobile SCS application |
| 25-201 | AST SCS modification (largest) |
| 25-306 | AST-related |
| 25-340 | AST-related |
| 22-271 | Spectrum policy |

## Worker Conventions

- All use `supabase_request()` helper for REST API calls
- Upsert pattern: `POST /rest/v1/{table}?on_conflict={cols}` with `Prefer: return=minimal,resolution=merge-duplicates`
- Env vars from `scripts/data-fetchers/.env` (SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY)
- Embedding worker needs OpenAI key from `short-gravity-web/.env.local`
