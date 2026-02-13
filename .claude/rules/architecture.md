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
| space-weather-worker | Daily 16:30 | CelesTrak solar flux, Kp, Ap, sunspots |
| socrates-worker | Daily 14:30 | CelesTrak SOCRATES conjunction data |
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

- **Primary UI:** `/asts` (immersive terminal — the reference implementation)
- **Intelligence Feed:** `/signals` — unified signals dashboard with price correlation, filtering, detail drill-down
- **Orbital Intelligence:** `/orbital` — constellation health, orbital analysis, space weather
- **Satellite Detail:** `/satellite/[noradId]` — per-satellite telemetry, orbit, coverage
- **Dev pages:** `/dev/hud-v2`, `/dev/hud-v3`, `/dev/globe`, `/dev/3d`, `/dev/constellation`
- **State:** React Query (server data) + Zustand (UI state via `terminal-store`)
- **3D:** Three.js globe + satellite.js TLE propagation
- **Search:** Hybrid vector (pgvector) + keyword, with LLM reranking

### UI Component System

Three-layer architecture. **All pages must use this system. No raw Tailwind for panels, stats, text, or loading states.**

**Layer 1 — Primitives** (`components/primitives/`):
Atomic building blocks: `Panel` (compound: Header, Content, Section, Divider), `Text` (7 variants, 8 sizes), `Label`, `Value`, `Muted`, `Stat` (hero numbers with units/deltas), `StatusDot`, `LoadingState`, `Skeleton`, `ProgressBar`. Chart primitives: `Crosshair`, `HairlinePath`, `ValueReadout`, `CornerBrackets`, `Baseline`, `GhostTrend`.

**Layer 2 — Widget System** (`components/hud/widgets/`):
Self-contained data panels. Each widget exports a component + `WidgetManifest` (id, name, category, sizing). Registered in `registry.ts`. Rendered via `WidgetPanel` which takes `WidgetSlot[]`. Wrapped by `WidgetHost` (ErrorBoundary, sizing, spacing).

Registered widgets: `telemetry-feed`, `constellation-progress`, `fm1-watch`, `mercator-map`, `short-interest`, `cash-position`, `launch-countdown`, `activity-feed`, `patreon-strip`, `signal-feed`, `regulatory-status`, `intel-link`, `email-signup`.

**Layer 3 — Layout + Presets**:
`HUDLayout` compound component (`Canvas`, `Overlay`, `TopLeft`, `TopRight`, `LeftPanel`, `RightPanel`, `BottomCenter`, `Attribution`). Named presets in `lib/terminal/presets.ts` (`default`, `launch-day`, `post-unfold`, `earnings-week`) define which widgets go where.

**Reference implementation:** `/asts` page — ~50 lines of composition. That's the target for every page.

## Key Integration Points

## TLE Pipeline (Vercel Cron — exception to GH Actions pattern)

Single pipeline via Vercel cron (`/api/cron/tle-refresh`, every 4h):
- **CelesTrak** (PRIMARY for position) — Supplemental GP data. CelesTrak is a third-party platform that receives operator-informed positions and fits its own GP elements. Better positional accuracy than radar, but GP fitting introduces BSTAR volatility artifacts.
- **Space-Track** (PRIMARY for BSTAR) — US Space Force SSN radar tracking. Independent source. Smoother BSTAR output — preferred for drag trend analysis.
- CelesTrak preferred for `satellites` table (positional state). Both always write to `tle_history` with source tag.
- **Source trust by use case:** Positional accuracy & maneuver detection → CelesTrak. BSTAR/drag/altitude trends → Space-Track. Long-term baselines → both converge.
- **SOURCE-AWARE MANDATE:** All queries to `tle_history` for trend analysis MUST filter by `source`. Never mix CelesTrak and Space-Track in the same calculation — CelesTrak GP fitting noise creates false anomaly detections. Health anomaly detection and constellation health widgets use Space-Track exclusively. Maneuver detection uses CelesTrak exclusively.
- Health anomaly detection (altitude drops, drag spikes, stale TLEs) uses Space-Track data only → creates `signals`
- Frontend also uses `lib/celestrak.ts` for on-demand lookups with 6h in-memory cache
- `source_divergence` view compares latest CelesTrak vs Space-Track BSTAR per satellite (threshold: delta > 0.0001, requires epochs within 6 hours)

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
