# System Architecture

## Data Flow

```
External APIs → Python Workers → Supabase Tables → Embedding Worker → brain_chunks
                                       ↓
                              Next.js API Routes → React Hooks → HUD Components
```

## Deployment

- **Frontend:** Next.js 14 on Vercel (auto-deploy on push to `main`)
- **Workers:** GitHub Actions cron schedules (THE automation layer — `run_all.py` is local convenience only)
- **Database:** Supabase PostgreSQL + pgvector + Storage buckets
- **Embeddings:** OpenAI `text-embedding-3-small` (1536 dimensions)
- **AI:** Claude API (brain queries, summaries, glossary extraction)

## GitHub Actions Schedules (UTC)

| Workflow | Schedule | What |
|----------|----------|------|
| sec-filing-worker | Every 2h weekdays (13-21 UTC) + daily 8 UTC | SEC EDGAR polling |
| x-worker | Every 15min market hours, hourly off-hours | X/Twitter posts |
| news-worker | Daily 13:00 weekdays | Finnhub news |
| press-release-worker | Daily 14:00 | AccessWire press releases |
| icfs-worker | Daily 12:00 | FCC ICFS metadata |
| ecfs-worker | Daily 10:00 | FCC ECFS dockets |
| patent-worker | Daily 6:00 | Patent discovery pipeline |
| price-worker | Daily 22:00 weekdays | Stock OHLCV |
| launch-worker | Daily 15:30 | Launch schedule extraction |
| filing-embedding-worker | Daily 15:00 | Embed filings, fcc_filings, x_posts |
| signal-scanner | Twice daily 13:00 & 21:00 | Cross-source anomaly detection |
| staleness-alert | Daily 16:00 | Data freshness monitoring |
| ised-worker | Weekly Tue 11:00 | ISED Canada regulatory |
| ofcom-worker | Weekly Wed 09:00 | Ofcom UK regulatory |
| transcript-worker | Weekly Wed 14:00 | Earnings transcripts |
| glossary-worker | Weekly Sun 8:00 | Term extraction |
| widget-data-worker | Weekly Mon 15:00 | Widget cache refresh |
| uls-worker | Weekly Thu 10:00 | FCC ULS experimental licenses |

## Vercel Crons (vercel.json)

| Path | Schedule | What |
|------|----------|------|
| /api/cron/tle-refresh | Every 4h | Dual-source TLE sync + health anomaly detection |
| /api/cron/check-feeds | Every 5min | Feed monitoring |
| /api/cron/filings-sync | Every 15min | Filing sync |

## run_all.py Cadences (local convenience only)

| Cadence | Workers |
|---------|---------|
| Frequent (15min) | filing_worker, tle_worker |
| Hourly (4h) | news_worker, press_release_worker |
| Daily | exhibit_backfill, icfs_servicenow_worker, fcc_attachment_worker, ecfs_worker, cash_position_worker, patent_worker_v2, transcript_worker |
| Weekly | short_interest_worker, fcc_attachment_worker (ELS scan), patent_enricher, itu_worker, ised_worker, ofcom_worker |

## Frontend Architecture

- **Primary UI:** `/terminal` (immersive HUD v2)
- **Dev pages:** `/dev/hud-v2` (clean), `/dev/globe`, `/dev/3d`, `/bluebird-demo`
- **State:** React Query (server data) + Zustand (UI state)
- **3D:** Three.js globe + satellite.js TLE propagation
- **Search:** Hybrid vector (pgvector) + keyword, with LLM reranking

## Key Integration Points

## TLE Pipeline (Vercel Cron — exception to GH Actions pattern)

Single pipeline via Vercel cron (`/api/cron/tle-refresh`, every 4h):
- **CelesTrak** (PRIMARY) — AST SpaceMobile's operator-supplied ephemeris (~10x more accurate than radar)
- **Space-Track** (SECONDARY) — SSN radar tracking for independent validation
- CelesTrak preferred for `satellites` table. Both write to `tle_history` with source tag.
- Includes health anomaly detection (altitude drops, drag spikes, stale TLEs) → creates `signals`
- Frontend also uses `lib/celestrak.ts` for on-demand lookups with 6h in-memory cache

This is the ONE pipeline that runs via Vercel cron instead of GH Actions because it needs the TypeScript/Supabase client for health monitoring. The Python `tle_worker.py` in the parent repo is a local dev/backfill tool only.

## Key Integration Points

| Integration | Library/Client | Rate Limit |
|-------------|---------------|------------|
| CelesTrak | /api/cron/tle-refresh + lib/celestrak.ts | No auth, 6h cache |
| Space-Track.org | /api/cron/tle-refresh + lib/space-track.ts | 30/min, 300/hr |
| Finnhub | lib/finnhub.ts | 60/min |
| Alpha Vantage | lib/alpha-vantage.ts | 25/day |
| SEC EDGAR | lib/sec-edgar.ts | 10/sec |
| Supabase | lib/supabase.ts | PostgreSQL |
| Claude API | lib/anthropic.ts | Per plan |
| OpenAI | embedding_worker.py | Per plan |
| Patreon | /api/auth/patreon | OAuth |

## Storage Buckets

- `sec-filings` — SEC exhibit PDFs and documents
- `fcc-filings` — FCC filing attachments and PDFs
