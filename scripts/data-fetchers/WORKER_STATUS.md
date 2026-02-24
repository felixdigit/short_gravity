# Worker Status

## Active Workers

- **filing_worker.py** — SEC EDGAR polling → `filings` table
- **x_worker.py** — X/Twitter posts → `x_posts` table
- **news_worker.py** — Finnhub news → `inbox` table
- **press_release_worker.py** — AccessWire press releases → `press_releases` table
- **ecfs_worker.py** — FCC ECFS dockets → `fcc_filings` (ECFS)
- **icfs_servicenow_worker.py** — FCC ICFS metadata → `fcc_filings` (ICFS)
- **patent_worker_v2.py** — Patent discovery pipeline → `patents`, `patent_claims`
- **price_worker.py** — Stock OHLCV → `daily_prices`
- **launch_worker.py** — Launch schedule extraction → `next_launches`
- **embedding_worker.py** — Embed content tables → `brain_chunks`
- **signal_scanner.py** — Cross-source anomaly detection → `signals`
- **transcript_worker.py** — Earnings call transcripts from roic.ai → `inbox` (source=earnings_call)
- **earnings_worker.py** — Earnings date discovery from Finnhub → `earnings_transcripts`
- **glossary_worker.py** — Term extraction → `glossary_terms`
- **widget_data_worker.py** — Short interest, cash position, launch status → `short_interest`, `cash_position`, `next_launches`
- **itu_worker.py** — ITU regulatory filings → `fcc_filings` (ICFS with ITU-* prefix)
- **ised_worker.py** — ISED Canada regulatory → `fcc_filings` (ICFS with ISED-* prefix)
- **ofcom_worker.py** — Ofcom UK regulatory → `fcc_filings` (ICFS with OFCOM-* prefix)
- **uls_worker.py** — FCC ULS experimental licenses → `fcc_filings` (ELS)
- **space_weather_worker.py** — CelesTrak solar flux/Kp/Ap → `space_weather`
- **socrates_worker.py** — CelesTrak SOCRATES conjunctions → `conjunctions`
- **short_interest_worker.py** — Yahoo Finance short interest → `short_interest`

## Disabled Workers

- **cash_position_worker.py** — DISABLED: Functionality fully covered by `widget_data_worker.py` `sync_cash_position()`. The widget worker is a strict superset — it extracts pro forma liquidity from earnings transcripts AND falls back to the same 10-Q/10-K regex parsing. Both write to `cash_position`. GitHub Actions workflow (`cash-position-worker.yml`) also disabled with `if: false`.

## Notes

- **earnings_worker.py vs transcript_worker.py**: NOT redundant. `earnings_worker` discovers call **dates** from Finnhub → `earnings_transcripts` table. `transcript_worker` fetches full **transcript text** from roic.ai → `inbox` table. Different sources, different tables, complementary data.
- **widget_data_worker.py** handles three concerns: short interest (Yahoo Finance), cash position (transcripts + 10-Q fallback), and launch status cleanup. It runs weekly, which is sufficient since the underlying data (quarterly filings, earnings calls) changes infrequently.
