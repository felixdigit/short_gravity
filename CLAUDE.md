# Short Gravity

## Project Overview
Short Gravity is an autonomous space sector intelligence platform. The system runs itself — workers pull data on schedules, pipelines process and embed it, and the UI surfaces everything live from the database. Gabriel steers strategy and content; the platform handles collection, processing, and display without human intervention.

### Products
- **Spacemob Terminal** — Deep $ASTS intelligence. Current focus. Live at shortgravity.com.
- **$SPACE Dashboard** — Sector-wide space investing intelligence. Next release. Shares infrastructure with Spacemob.

### Scaling Principle: Parameters, Not Products
Don't reorganize directories or create abstractions for $SPACE prematurely. Instead, build shared infrastructure that takes parameters:
- **Hooks:** `useStockPrice('ASTS')` not `useASTSPrice()`. Ticker as argument, not in the name.
- **Workers:** Accept company/ticker params where practical so they can serve multiple products without rewriting.
- **Database:** Tables should support multi-company data (e.g. `daily_prices` keyed by symbol, not assumed ASTS-only).
- When $SPACE begins, split directories based on what actually needs splitting — not before.

### Brain / RAG
Shared intelligence layer across both products. Hybrid vector search (pgvector) + keyword matching with LLM reranking. All content (filings, patents, press releases, X posts, FCC filings) gets chunked and embedded into `brain_chunks`. Powers `/research-filings`, brain queries, and cross-source analysis. This is core infrastructure — not product-specific.

## Gabriel
Solo operator. Research, writing, content, visuals, code.
- Works intuitively, no hand-holding
- Space sector investor. Primary focus: $ASTS. Expanding to sector-wide coverage ($SPACE).
- **Execute. Don't over-explain. Don't ask unnecessary questions.**

## Tech Stack
- **Frontend:** Next.js 14, TypeScript, Tailwind CSS, Three.js
- **Backend:** Python 3, Playwright
- **Database:** Supabase (PostgreSQL + pgvector)
- **Automation:** GitHub Actions (all workers run on cron schedules)
- **Deploy:** Vercel (auto-deploy on push to `main`)

## Directory Structure

```
short_gravity/
├── short-gravity-web/           # Next.js app (Vercel)
│   ├── app/                     # Pages + API routes
│   ├── components/              # UI components
│   ├── lib/                     # Hooks, stores, brain search
│   ├── scripts/data-fetchers/   # Workers deployed via GitHub Actions
│   └── .github/workflows/       # Cron schedules for all workers
├── scripts/data-fetchers/       # Local worker dev copies
├── .claude/rules/               # Auto-loaded context (architecture, workers, database)
├── docs/                        # Documentation + system-map.html
├── design/                      # Style guide, Figma specs
└── research/                    # Alpha nuggets, notes
```

## Commands

```bash
cd short-gravity-web && npm run dev      # Dev server
cd short-gravity-web && npm run build    # Production build
```

## Git & Deployment

**CRITICAL: Never auto-commit or auto-push.** Only commit/push when Gabriel explicitly asks.

- `main` — production. Push to main auto-deploys to Vercel via GitHub.
- Work directly on `main` unless Gabriel specifies otherwise.
- Never use `vercel --prod` directly.

## UI Design (Spacemob Terminal)

These rules apply to the Spacemob Terminal. $SPACE will define its own palette when the time comes.

**Source of truth:** `short-gravity-web/app/globals.css`

### Color Philosophy — Tactical HUD
- **White is the hero** — crisp on true black
- **Orange is surgical** — selection/active states ONLY (5% of UI)
- No decorative color. No muddy grays.

```css
--void-black: #030305;        /* Page background */
--asts-orange: #FF6B35;       /* Selection, active — USE SPARINGLY */
--text-primary: #FFFFFF;      /* Key data */
--text-secondary: #E5E7EB;    /* Secondary */
--text-muted: #71717A;        /* Timestamps */
```

### Typography
- JetBrains Mono, uppercase labels, tracking-wider
- Large values: font-light (300 weight)

### Rules
- Dark mode only. Panel headers: white/gray, NOT orange.
- Chart lines: white. Selection: orange (only pop of color).
- Before placing new UI elements: read the component, check for overlaps, test in context.

## Core Design Principle: Autonomous, Dynamic, Real

Every feature follows the full pipeline: **Worker → Supabase → API Route → UI Component.**

- **Workers are the nervous system.** They run on cron schedules and pull data without human intervention. When building a new data source, the job isn't done until there's a scheduled worker writing to Supabase.
- **The UI is a live dashboard, not a static page.** Every number, date, status, list, and chart must be driven by database queries. If a value exists in Supabase, the UI reads it from Supabase — never hardcode it.
- **New features = new pipelines.** Adding a feature means: what data does it need, what worker fetches it, what table stores it, what API route serves it, what component renders it. All five links in the chain.
- **Real data only.** No mock data, no placeholders, no static fallbacks, no seed files. If it's on screen, it's from Supabase or a live API. Satellite visualization uses TLE propagation via satellite.js — never geometric approximations. Stock prices from Finnhub/Alpha Vantage. SEC filings from EDGAR. Zero exceptions.

## Code Conventions
- Read before modifying. Follow existing patterns exactly.
- TypeScript strict mode. No over-engineering. No unnecessary comments.

## Behavior Rules

1. **Just do it** — If a follow-up action is obvious, do it.
2. **Git: suggest, never act** — Never auto-commit/push. Suggest commits at good checkpoints.
3. **Historical completeness** — Fetch ALL data, never stop early. Backfill to the earliest available record.
4. **When Gabriel provides credentials** → Write to `.env` immediately.
5. **Error resilience** — Retry 3x with exponential backoff.
6. **Always start the dev server** — When testing UI changes, start `npm run dev` in background.
7. **Automation = GitHub Actions** — Every worker must have a GitHub Actions workflow with a cron schedule. `run_all.py` is a local convenience only, NOT the automation layer. A worker without a GH Actions workflow is not autonomous — it's not done.
8. **Worker deployment** — Workers run from `short-gravity-web/scripts/data-fetchers/`. When creating/modifying a worker, update BOTH copies (parent repo + web app repo) and ensure the GH Actions workflow exists.
9. **Full pipeline or nothing** — A new data source isn't "done" until: worker fetches it → table stores it → API route serves it → UI component renders it live. Partial pipelines are tech debt.

## Skills

All skills are atomic — chain them conversationally.

- `/research-filings [topic]` — Search SEC/FCC filings for citations via RAG
- `/write-article` — Draft long-form article in Short Gravity voice
- `/write-x-post single` or `/write-x-post thread` — X content
- `/nano-banana` — Generate Gemini image prompts for visual assets
- `/satellite-data` — Query SpaceTrack for orbital data and TLE info
- `/run-filing-worker` — Run SEC filing worker to fetch new filings + AI summaries

## Debugging Rules

**Isolate before fixing.** Use dev pages:
- `/dev/hud-v3` — Latest HUD iteration
- `/dev/hud-v2` — Stable HUD reference
- `/dev/globe` — Globe isolation
- `/dev/3d` — Three.js experiments
- `/dev/constellation` — Constellation visualization
- `/dev/system-health` — System health dashboard
- `/dev/workers` — Worker status

## CRITICAL: Coverage Completeness

Short Gravity is a source of truth. The truth is finite — every FCC filing, patent, SEC exhibit, and regulatory action exists out there. The job is to capture all of it, then keep it current. Not an endless process — a completable one.

### Worker lifecycle: Capture → Verify → Maintain
1. **Capture** — Backfill everything that exists historically. Don't stop at "recent." Go to the beginning.
2. **Verify** — The worker self-audits: compare what exists at the source against what's in Supabase. If the count doesn't match, the job isn't done.
3. **Maintain** — Once complete, the scheduled cron watches for new additions only. The hard part is already done.

### Rules
- **Every worker must know if it's complete.** A worker that can't answer "have I captured everything?" is unfinished. Build in source-count checks, discovery queries, or coverage reports.
- **Discovery over hardcoding.** Don't just fetch a list of known docket numbers — search for the filer. Don't just fetch known patent numbers — query the assignee. Hardcoded lists miss what you don't know about yet.
- **When a gap is found, fix the worker** — don't just backfill. The gap means the capture logic has a hole. Patch the hole.
- **Coverage gaps are worse than stale data.** Stale data is visible. Missing data is invisible.

## Access Tiers

Patreon-based gating via `lib/auth/tier.ts`. Two tiers:

| | **free** | **full_spectrum** (Patreon) |
|---|---|---|
| Brain model | Haiku | Sonnet |
| Max tokens | 2048 | 4096 |
| Sources per query | 8 | 16 |
| Conversation history | 4 turns | 10 turns |
| Rate limit | 20/min | 60/min |
| Modes | default | default, counter-thesis |

### What's public (ungated)
All data display: filings, satellites, charts, patents, regulatory status, signals, press releases. The Terminal is a public intelligence tool.

### What's tiered
Brain search works for everyone — free tier gets Haiku with shorter context. Full Spectrum gets Sonnet, deeper search, longer conversations, counter-thesis mode, raw dataset access, and API access. When building brain/AI features, respect `TIER_CONFIG` from `lib/auth/tier.ts`.
