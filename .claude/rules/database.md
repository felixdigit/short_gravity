# Database Schema Reference

Supabase PostgreSQL with pgvector extension. All tables have RLS (public SELECT, service role full access).

## Core Tables

| Table | PK | Unique Constraint | Primary Writers |
|-------|----|--------------------|-----------------|
| satellites | norad_id TEXT | — | tle_worker |
| tle_history | id UUID | (norad_id, epoch, source) | tle_worker |
| conjunctions | id UUID | cdm_id | tle_worker, socrates_worker |
| space_weather | id UUID | date | space_weather_worker |
| filings | id UUID | accession_number | filing_worker |
| sec_filing_exhibits | id UUID | (accession_number, exhibit_number) | exhibit_backfill |
| fcc_dockets | docket_number TEXT | — | ecfs_worker (sync_docket_metadata) |
| fcc_filings | id UUID | (filing_system, file_number) | ecfs_worker, icfs_worker, uls_worker, ised_worker, ofcom_worker, itu_worker |
| fcc_filing_attachments | id UUID | — | fcc_attachment_worker |
| patents | id UUID | patent_number | patent_worker_v2, patent_enricher |
| patent_claims | id UUID | (patent_number, claim_number) | claims fetchers (6 jurisdictions) |
| patent_families | id UUID | family_number | populate_patent_families |
| patent_citations | id UUID | (citing, cited) | patent_worker_v2 |
| press_releases | id BIGSERIAL | source_id | press_release_worker |
| earnings_transcripts | id UUID | (company, fiscal_year, fiscal_quarter) | transcript_worker |
| inbox | id UUID | (source, source_id) | Multiple workers |
| x_posts | id BIGSERIAL | source_id | x_worker |
| glossary_terms | id UUID | normalized_term | glossary_worker |
| glossary_citations | id UUID | — | glossary_worker |
| short_interest | id UUID | — | short_interest_worker |
| cash_position | id UUID | — | cash_position_worker |
| daily_prices | id UUID | (symbol, date) | price_worker |
| next_launches | id UUID | — | launch_worker |
| signals | id BIGSERIAL | fingerprint | signal_scanner |
| source_cooccurrence | id BIGSERIAL | — | brain API |
| brain_chunks | id UUID | (source_table, source_id, chunk_index) | embedding_worker |
| brain_conversations | id UUID | — | brain API |
| brain_query_log | id BIGSERIAL | — | brain API |
| worker_runs | id BIGSERIAL | — | GitHub Actions |
| profiles | id UUID (FK auth.users) | patreon_id | auth system |
| catalysts | id UUID | — | manual / future worker |
| theses | id UUID | — | thesis API (session-based) |
| subscribers | id UUID | email | waitlist API |
| signal_alert_log | id BIGSERIAL | signal_fingerprint | signal-alerts cron |
| widget_cache | — | — | widget_data_worker |

## Key Constraints

- **fcc_filings.filing_system**: CHECK `IN ('ICFS', 'ECFS', 'ELS')` — cannot add new values without DB migration
- **fcc_filings.status**: CHECK `IN ('pending', 'processing', 'completed', 'failed')`
- **patents.status**: CHECK `IN ('pending', 'granted', 'abandoned', 'expired', 'unknown')`
- **profiles.tier**: CHECK `IN ('free', 'full_spectrum')`

## Vector Search

- **brain_chunks.embedding**: vector(1536) with HNSW index (cosine distance)
- **RPC function**: `brain_search(query_embedding, match_count, filter_sources)` — nearest neighbor search
- **RPC function**: `brain_crossref(source_a, source_b, ...)` — cross-source semantic matching
- **Embedding model**: OpenAI text-embedding-3-small

## Views

- `filings_feed` — completed SEC filings (excludes content_text)
- `fcc_filings_feed` — completed FCC filings
- `inbox_feed` — unified communications feed
- `satellite_freshness` — TLE age status (FRESH/OK/STALE/CRITICAL)
- `bstar_trends` — 30-day atmospheric drag analysis
- `source_divergence` — CelesTrak vs Space-Track comparison

## Record Counts (approximate)

| Table | Count |
|-------|-------|
| filings (SEC) | 530 |
| fcc_filings | 4,500+ |
| patents | 307 |
| patent_claims | 2,482 |
| press_releases | 100+ |
| x_posts | 2,000+ |
| glossary_terms | 500+ |
| brain_chunks | 13,000+ |
| tle_history | 50,000+ |
| space_weather | 25,000+ |
