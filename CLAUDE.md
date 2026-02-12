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

### UI Component System — Three Layers

**CRITICAL: All UI must use this system. No raw Tailwind for panels, stats, text, or loading states. No inline reinvention of patterns that already exist as primitives or widgets.**

#### Layer 1: Primitives (`components/primitives/`)

Atomic building blocks. Import from `@/components/primitives`.

| Component | Purpose | Key Props |
|-----------|---------|-----------|
| `Panel` | Container with border, blur, bg | `className`, `blur`, `border` |
| `Panel.Header` | 8px uppercase label row | `action` (right-side ReactNode) |
| `Panel.Content` | Body wrapper | `scroll` |
| `Panel.Section` | Subdivider with optional title | `title` |
| `Panel.Divider` | Horizontal rule | — |
| `Text` | All text rendering | `variant` (primary/secondary/muted/dim/label/value/accent), `size` (xs–4xl), `tabular`, `uppercase`, `tracking` |
| `Label` | Convenience: label variant, uppercase, tracking-wider | — |
| `Value` | Convenience: value variant, tabular | — |
| `Muted` | Convenience: muted variant | — |
| `Stat` | Hero number with unit/sublabel/delta | `value`, `label` (unit), `size` (sm/md/lg/xl), `variant` (default/positive/negative/warning/accent), `delta` |
| `StatusDot` | Colored dot indicator | `variant` (nominal/warning/critical/info/accent), `pulse`, `size` |
| `LoadingState` | Centered loading text with spinner | `text`, `size` |
| `Skeleton` | Animated placeholder bar | `className` |
| `ProgressBar` | Bar with fill | `value`, `max`, `variant` |

Chart primitives in `components/primitives/chart/`: `Crosshair`, `HairlinePath`, `ValueReadout`, `CornerBrackets`, `Baseline`, `GhostTrend`.

**Rule:** If you're writing `text-[8px] text-white/25 tracking-wider uppercase` — stop. That's `<Label>`. If you're writing `text-[28px] font-extralight text-white tabular-nums` — stop. That's `<Stat>`. If you're writing a div with `bg-black/30 border border-white/[0.06]` — stop. That's `<Panel>`.

#### Layer 2: Widget System (`components/hud/widgets/`)

Self-contained data panels registered in a central registry.

- **Each widget exports:** a React component + a `WidgetManifest` (id, name, category, sizing, separator)
- **`registry.ts`** — Maps widget IDs to components. All widgets must be registered here.
- **`WidgetHost`** — Wraps each widget with `ErrorBoundary`, handles sizing (fixed/flexible), spacing
- **`WidgetPanel`** — Renders an array of `WidgetSlot[]` by looking up the registry

Creating a new widget:
1. Create `components/hud/widgets/MyWidget.tsx` — export component + manifest
2. Register in `registry.ts`
3. Add to a preset slot in `lib/terminal/presets.ts`

#### Layer 3: Layout + Presets

- **`HUDLayout`** (`components/hud/layout/`) — Compound component for immersive pages: `Canvas`, `Overlay`, `TopLeft`, `TopRight`, `LeftPanel`, `RightPanel`, `BottomCenter`, `BottomLeft`, `BottomRight`, `Center`, `Attribution`
- **Presets** (`lib/terminal/presets.ts`) — Named configurations: `default`, `launch-day`, `post-unfold`, `earnings-week`. Each defines which widgets go in left/right panels.
- **`TerminalDataProvider`** — Shared data context for all widgets on the terminal page

**The terminal page is ~50 lines of composition.** Pick a preset, slot the widgets, done. That's the goal for every page.

### Charting Engine

**One engine, one theme, every chart.** Charting is platform infrastructure, not a per-component decision. Short Gravity uses a custom Canvas 2D rendering engine (`lib/charts/`) that implements the SG visual language. Every chart in the app is a configuration of this engine.

- **`lib/charts/`** — Core renderer, theme, chart types (line, area, sparkline, bar, candlestick+volume). All charts render to HTML5 Canvas 2D for performance and pixel-perfect control.
- **Recharts and lightweight-charts are legacy.** Migrate to the SG engine when touched. No new charts using third-party libraries.
- **Chart theme** — defined once in `lib/charts/theme.ts`, consumed by every chart:
```
Background: var(--void-black) #030305
Lines/strokes: white, 0.5–0.75px (hairline)
Grid: rgba(255,255,255, 0.02) — barely visible
Accent: var(--asts-orange) #FF6B35 — selection/active only
Up/nominal: var(--status-nominal) #22C55E
Down/critical: var(--status-critical) #EF4444
Text: JetBrains Mono, 8–10px, white/30 to white/60
```

## Core Design Principle: Autonomous, Dynamic, Real

Every feature follows the full pipeline: **Worker → Supabase → API Route → UI Component.**

- **Workers are the nervous system.** They run on cron schedules and pull data without human intervention. When building a new data source, the job isn't done until there's a scheduled worker writing to Supabase.
- **The UI is a live dashboard, not a static page.** Every number, date, status, list, and chart must be driven by database queries. If a value exists in Supabase, the UI reads it from Supabase — never hardcode it.
- **New features = new pipelines.** Adding a feature means: what data does it need, what worker fetches it, what table stores it, what API route serves it, what component renders it. All five links in the chain.
- **Real data only.** No mock data, no placeholders, no static fallbacks, no seed files. If it's on screen, it's from Supabase or a live API. Satellite visualization uses TLE propagation via satellite.js — never geometric approximations. Stock prices from Finnhub/Alpha Vantage. SEC filings from EDGAR. Zero exceptions.

## Architecture Principle: One Engine Per Domain

When a capability is used across the platform (charting, 3D rendering, data fetching, auth, search), it must be a single system — one engine, one API, one theme. Never let the same domain be solved by multiple competing libraries or patterns. If you're reaching for a third-party library, check if the domain already has an internal engine. If it does, extend it. If it doesn't, build one that can serve every use case in that domain, then make it the standard.

This is how Bloomberg, Robinhood, and TradingView build platforms — each domain has one answer, not three.

## Code Conventions
- Read before modifying. Follow existing patterns exactly.
- TypeScript strict mode. No over-engineering. No unnecessary comments.

## Behavior Rules

1. **Just do it** — If a follow-up action is obvious, do it.
2. **Git: suggest, never act** — Never auto-commit/push. But ALWAYS suggest a commit before a session ends or after completing significant work. Uncommitted work is at risk. This is a responsibility, not optional.
3. **Historical completeness** — Fetch ALL data, never stop early. Backfill to the earliest available record.
4. **When Gabriel provides credentials** → Write to `.env` immediately.
5. **Error resilience** — Retry 3x with exponential backoff.
6. **Always start the dev server** — When testing UI changes, start `npm run dev` in background.
7. **Automation = GitHub Actions** — Every worker must have a GitHub Actions workflow with a cron schedule. `run_all.py` is a local convenience only, NOT the automation layer. A worker without a GH Actions workflow is not autonomous — it's not done.
8. **Worker deployment** — Workers run from `short-gravity-web/scripts/data-fetchers/`. When creating/modifying a worker, update BOTH copies (parent repo + web app repo) and ensure the GH Actions workflow exists.
9. **Full pipeline or nothing** — A new data source isn't "done" until: worker fetches it → table stores it → API route serves it → UI component renders it live. Partial pipelines are tech debt.
10. **Document architectural work immediately** — When you build, refactor, or establish a new system/pattern/convention, update CLAUDE.md and relevant `.claude/rules/` files BEFORE the session ends. Architecture that isn't in the docs doesn't exist for the next session. Context gets compacted, sessions restart — the only thing that persists is what's written down. This is non-negotiable.

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
