# Short Gravity

## Project Overview
Short Gravity is an autonomous space sector intelligence platform. The system runs itself — workers pull data on schedules, pipelines process and embed it, and the UI surfaces everything live from the database. Gabriel steers strategy and content; the platform handles collection, processing, and display without human intervention.

### Products
- **Spacemob Terminal** — Deep $ASTS intelligence. Current focus. Live at shortgravity.com.
- **$SPACE Dashboard** — Sector-wide space investing intelligence. Next release. Shares infrastructure with Spacemob.

### Brain / RAG
Shared intelligence layer across both products. Hybrid vector search (pgvector) + keyword matching with LLM reranking. All content (filings, patents, press releases, X posts, FCC filings) gets chunked and embedded into `brain_chunks`. Powers `/research-filings`, brain queries, and cross-source analysis. This is core infrastructure — not product-specific.

## Gabriel
Solo operator. Research, writing, content, visuals, code. Space sector investor. Primary focus: $ASTS. Expanding to sector-wide coverage ($SPACE).
- **Execute. Don't over-explain. Don't ask unnecessary questions.**

## Multi-Agent Workflow
Two AI agents, one spec. Gabriel bridges both.

- **Claude** (this agent) — Builds. Implements precisely against this spec. Respects existing patterns. Ships.
- **Gemini** (via CLI or app) — Researches. Analyzes reference material, explores architectural approaches, produces spec recommendations. Defined in `GEMINI.md`.
- **This document is the source of truth.** Gemini helps evolve it; Claude implements against it.

### Thread System — The Build Loop

We don't build features. We pull **Threads**. A Thread is a durable, multi-session narrative arc that answers a specific user intent. State lives in `THREADS.md` at the repo root.

**The loop:**
1. **READ** `THREADS.md` — understand current state of all threads
2. **TRACE** — Claude writes/updates the trace for the highest-priority open GAP (grounded in actual code, not speculation)
3. **WEAVE** — Send trace to Gemini. Gemini critiques the trace and specs the transition that bridges the GAP.
4. **FABRICATE** — Claude implements the transition
5. **PROOF** — Claude re-runs the trace. If the GAP is closed, mark it. If new GAPs appear, log them.
6. **UPDATE** `THREADS.md` — new status, completed transitions, any new GAPs discovered

**Thread statuses:** GOLDEN (complete) / FRAYED (works but painful) / BROKEN (dead end) / PLANNED (spec phase) / DARK (user intent exists, zero surface area)

**Cadence:** Thread-driven, not time-driven. Each loop picks the highest-value GAP across all open threads. Gabriel sets thread priority.

**Current threads (see THREADS.md):**
- Thread 001: Signal-to-Source (P0, BROKEN) — Own the Present
- Thread 002: Event Horizon (P1, DARK) — Own the Future
- Thread 003: Thesis Builder (P2, DARK) — Own the Argument

### Claude ↔ Gemini Collaboration Protocol

Claude has direct access to Gemini via the `gemini` CLI.

**Model:** `gemini-2.5-pro` (default)

**When to invoke Gemini:**
- **WEAVE phase** — Send a thread trace with GAPs. Gemini critiques and specs the transition.
- Before building a new page, feature, or architectural component — ask Gemini to research approaches
- When facing a design decision with multiple valid paths — let Gemini analyze tradeoffs

**The workflow — Multi-Turn Dialogue:**

Conversations live in `docs/gemini-conversations/`. Each loop is a structured dialogue, not a one-shot prompt. Claude and Gemini deliberate before code is written.

1. Claude creates a conversation file with Turn 1 (context + question)
2. Claude sends the conversation to Gemini: `cat docs/gemini-conversations/file.md | gemini -m gemini-2.5-pro -o text`
3. Claude appends Gemini's response as `## GEMINI (turn N)`
4. Claude responds with pushback, refinements, or follow-up questions as `## CLAUDE (turn N+1)`
5. Repeat steps 2-4 for 2-4 turns until the spec converges
6. Claude summarizes the agreed spec and implements

**Conversation file format:**
```markdown
# Loop NNN: [Topic]
## CLAUDE (turn 1)
[Context package + question]
## GEMINI (turn 1)
[Response]
## CLAUDE (turn 2)
[Pushback/refinement]
## GEMINI (turn 2)
[Refined spec]
```

**Rules:**
- Multi-turn by default. One-shot only for simple yes/no priority questions.
- Gemini's output is a recommendation, not a mandate. Gabriel approves before Claude implements.
- Conversations are append-only. Never edit previous turns — only add new ones.
- Gemini writes spec, not code. Claude writes code, not spec. Respect the boundary.
- When Claude disagrees with Gemini, Claude should say so and explain why. The goal is convergence, not deference.

---

# PART 1: CORE — The Convergent Specification

These principles are constitutional. They converge to a stable state and rarely change. Amendments are deliberate.

## C1: Architecture Contracts

### Pipeline Mandate
Every feature follows: **Worker → Supabase → API Route → UI Component.**

- **Workers are the nervous system.** They run on cron schedules without human intervention. A new data source isn't "done" until there's a scheduled worker writing to Supabase.
- **The UI is a live dashboard, not a static page.** Every number, date, status, list, and chart is driven by database queries. If a value exists in Supabase, the UI reads it from Supabase — never hardcode it.
- **New features = new pipelines.** What data does it need, what worker fetches it (see `.claude/rules/workers.md`), what table stores it (see `.claude/rules/database.md`), what API route serves it, what component renders it. All five links.
- **Real data only.** No mock data, no placeholders, no static fallbacks, no seed files. If it's on screen, it's from Supabase or a live API. Zero exceptions.

### One Engine Per Domain
When a capability is used across the platform (charting, 3D rendering, data fetching, auth, search), it must be a single system — one engine, one API, one theme. Never let the same domain be solved by multiple competing libraries or patterns. If you're reaching for a third-party library, check if the domain already has an internal engine. If it does, extend it. If it doesn't, build one that can serve every use case in that domain, then make it the standard.

### Parameters, Not Products
Don't reorganize directories or create abstractions for $SPACE prematurely. Build shared infrastructure that takes parameters:
- **Hooks:** `useStockPrice('ASTS')` not `useASTSPrice()`. Ticker as argument, not in the name.
- **Workers:** Accept company/ticker params where practical so they can serve multiple products without rewriting.
- **Database:** Tables support multi-company data (e.g. `daily_prices` keyed by symbol, not assumed ASTS-only).
- When $SPACE begins, split directories based on what actually needs splitting — not before.

## C2: Design Language — Tactical HUD

These rules apply to the Spacemob Terminal. $SPACE will define its own palette when the time comes.

**Source of truth:** `short-gravity-web/app/globals.css`

### Color Philosophy
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

## C3: Coverage Completeness

Short Gravity is a source of truth. The truth is finite — every FCC filing, patent, SEC exhibit, and regulatory action exists out there. The job is to capture all of it, then keep it current. Not an endless process — a completable one.

### Worker Lifecycle: Capture → Verify → Maintain
1. **Capture** — Backfill everything that exists historically. Don't stop at "recent." Go to the beginning.
2. **Verify** — The worker self-audits: compare what exists at the source against what's in Supabase. If the count doesn't match, the job isn't done.
3. **Maintain** — Once complete, the scheduled cron watches for new additions only. The hard part is already done.

### Completeness Verification Standard
Every worker MUST implement a completeness check that answers: **"Source has X records. Database has Y. Gap is Z."**

- Runs at the end of every worker execution — both backfill and incremental modes.
- Logs results to `worker_completeness_audits` table: `(worker_name, table_name, source_count, db_count, coverage_pct, status, details JSONB)`.
- If source lacks a total count API, paginate to exhaustion and log methodology in `details`.
- Health endpoint (`/api/system/health`) surfaces completeness alongside staleness.
- Coverage gaps are P0 bugs. Missing data is invisible — worse than stale data.

### Rules
- **Every worker must know if it's complete.** A worker that can't answer "have I captured everything?" is unfinished.
- **Discovery over hardcoding.** Search for the filer, not a known list. Query the assignee, not known patent numbers. Hardcoded lists miss what you don't know about yet.
- **When a gap is found, fix the worker** — don't just backfill. The gap means the capture logic has a hole.
- **A worker without a GitHub Actions cron schedule is not autonomous — it's not done.**

## C4: Behavior Rules

1. **Just do it** — If a follow-up action is obvious, do it.
2. **Git: suggest, never act** — Never auto-commit/push. But ALWAYS suggest a commit before a session ends or after completing significant work.
3. **Historical completeness** — Fetch ALL data, never stop early. Backfill to the earliest available record.
4. **When Gabriel provides credentials** → Write to `.env` immediately.
5. **Error resilience** — Retry 3x with exponential backoff.
6. **Always start the dev server** — When testing UI changes, start `npm run dev` in background.
7. **Full pipeline or nothing** — A new data source isn't "done" until all five links exist. Partial pipelines are tech debt.
8. **Document architectural work immediately** — Update CLAUDE.md and `.claude/rules/` BEFORE the session ends. Architecture that isn't in the docs doesn't exist for the next session. Context gets compacted, sessions restart — the only thing that persists is what's written down. Non-negotiable.
9. **Code conventions** — Read before modifying. Follow existing patterns exactly. TypeScript strict mode. No over-engineering. No unnecessary comments.
10. **Log significant work** — After completing a significant implementation task (e.g., creating a new component, modifying a worker, or fixing a bug), append a brief, factual log entry to `docs/JOURNEY.md`. The entry must include the date and a summary of the task completed.

## C5: Access Tiers

Patreon-based gating via `lib/auth/tier.ts`. Two tiers:

| | **free** | **full_spectrum** (Patreon) |
|---|---|---|
| Brain model | Haiku | Sonnet |
| Max tokens | 2048 | 4096 |
| Sources per query | 8 | 16 |
| Conversation history | 4 turns | 10 turns |
| Rate limit | 20/min | 60/min |
| Modes | default | default, counter-thesis |

**What's public (ungated):** All data display — filings, satellites, charts, patents, regulatory status, signals, press releases. The Terminal is a public intelligence tool.

**What's tiered:** Brain search works for everyone — free tier gets Haiku with shorter context. Full Spectrum gets Sonnet, deeper search, longer conversations, counter-thesis mode, raw dataset access, and API access. When building brain/AI features, respect `TIER_CONFIG` from `lib/auth/tier.ts`.

---

# PART 2: CURRENT STATE — The Living Reference

This section reflects what's built and how it works. It evolves every session.

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
- **Worker deployment** — Workers run from `short-gravity-web/scripts/data-fetchers/`. When creating/modifying a worker, update BOTH copies (parent repo + web app repo) and ensure the GH Actions workflow exists.

## UI Component System — Three Layers

**CRITICAL: All UI must use this system. No raw Tailwind for panels, stats, text, or loading states. No inline reinvention of patterns that already exist as primitives or widgets.**

### Layer 1: Primitives (`components/primitives/`)

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

### Layer 2: Widget System (`components/hud/widgets/`)

Self-contained data panels registered in a central registry.

- **Each widget exports:** a React component + a `WidgetManifest` (id, name, category, sizing, separator)
- **`registry.ts`** — Maps widget IDs to components. All widgets must be registered here.
- **`WidgetHost`** — Wraps each widget with `ErrorBoundary`, handles sizing (fixed/flexible), spacing
- **`WidgetPanel`** — Renders an array of `WidgetSlot[]` by looking up the registry

Creating a new widget:
1. Create `components/hud/widgets/MyWidget.tsx` — export component + manifest
2. Register in `registry.ts`
3. Add to a preset slot in `lib/terminal/presets.ts`

### Layer 3: Layout + Presets

- **`HUDLayout`** (`components/hud/layout/`) — Compound component for immersive pages: `Canvas`, `Overlay`, `TopLeft`, `TopRight`, `LeftPanel`, `RightPanel`, `BottomCenter`, `BottomLeft`, `BottomRight`, `Center`, `Attribution`
- **Presets** (`lib/terminal/presets.ts`) — Named configurations: `default`, `launch-day`, `post-unfold`, `earnings-week`. Each defines which widgets go in left/right panels.
- **`TerminalDataProvider`** — Shared data context for all widgets on the terminal page

**The terminal page is ~50 lines of composition.** Pick a preset, slot the widgets, done. That's the goal for every page.

## Charting Engine

**One engine, one theme, every chart.** Charting is platform infrastructure. Short Gravity uses a custom Canvas 2D rendering engine (`lib/charts/`) — configuration-driven, not composition-driven. Every chart is a `ChartConfig` object passed to `<SGChart />`.

- **Recharts and lightweight-charts are legacy.** Migrate to the SG engine when touched. No new charts using third-party libraries.

### The API: `<SGChart />`

SGChart takes a flat `ChartConfig` — not JSX children. Canvas rendering requires coordinated draw passes that composition can't guarantee.

```typescript
<SGChart
  series={[
    { id: 'price', type: 'line', data: priceData, color: 'white', strokeWidth: 1.5 },
    { id: 'volume', type: 'area', data: volumeData, axis: 'y2', fillOpacity: 0.05 },
  ]}
  overlays={[
    { type: 'trend', seriesId: 'price' },
    { type: 'reference-line', axis: 'y', value: 100, label: 'SMA(20)' },
    { type: 'markers', data: [{ time: '2024-01-15', color: '#FF6B35' }] },
  ]}
  axes={{ x: 'time', y: { format: v => `$${v.toFixed(2)}` } }}
  crosshair
  animate
  height={300}
/>
```

### Series Types

| Type | Data Shape | Notes |
|------|-----------|-------|
| `line` | `TimeSeriesPoint[]` | Monotone cubic interpolation (Fritsch-Carlson). No overshoot. |
| `area` | `TimeSeriesPoint[]` | Line + gradient fill. `fillOpacity` default 0.08. |
| `bar` | `TimeSeriesPoint[]` or `BarPoint[]` | Auto-detects: time-based or categorical/diverging (if data has `.label` or `baseValue`). |
| `candlestick` | `OHLCPoint[]` | OHLC candles + optional volume bars on y2. Green up, red down. |
| `sparkline` | `TimeSeriesPoint[]` | Minimal inline chart. No axes, no animation. |

### Overlay Types: `trend` (linear regression), `reference-line` (static h/v line), `markers` (vertical lines at timestamps).

### Key Types

```typescript
interface TimeSeriesPoint { time: number | string | Date; value: number }
interface OHLCPoint { time: number | string | Date; open: number; high: number; low: number; close: number; volume?: number }
interface BarPoint { label: string; value: number; color?: string }
```

### Chart Theme (`lib/charts/theme.ts`)

```
Background: #030305 (void black)
Strokes: white, 0.75px hairline default
Grid: rgba(255,255,255, 0.02) — barely visible
Accent: #FF6B35 — crosshair, active markers only
Up: #22C55E | Down: #EF4444 | Warning: #EAB308
Text: JetBrains Mono, 9-10px, white/40
```

### Engine Internals

`ChartEngine`: Canvas init → DPR scaling → Scale computation → Render passes (background → grid → series → overlays → crosshair) → Animation (300ms easeOut on data change) → Interaction (mouse tracking, nearest-point snap within 40px). `ScaleManager` supports time, linear, log, index, and category scales. Export via ref: `ref.current.exportToBlob({ title, subtitle, aspect: '16:9', stats })` renders high-DPI share frames.

## Data Flow: Terminal Provider & State

### `TerminalDataProvider` (`lib/providers/TerminalDataProvider.tsx`)

Single provider at page level. Composes internal React Query hooks, exposes typed context. Widgets consume via `useTerminalData()`. **Widgets MUST NOT fetch their own data** — they read from context or accept prop overrides for standalone testing.

Current context is satellite/orbital focused. Will expand domain-by-domain as $SPACE requires — add new providers per domain, don't bloat this one.

**Data freshness:** TLE on mount + 30min stale. Live positions propagated locally via satellite.js every 500ms. Drag history cached 1h. Divergence cached 5min with refetch on focus.

### `useTerminalStore` (Zustand)

UI state separate from data: display mode, globe toggles, satellite selection, brain panel, active preset. Only `activePreset` and `mode` persist to localStorage.

**Widget data pattern:** Widgets accept optional prop overrides but default to context:
```typescript
const ctx = useTerminalData()
const satellites = propSatellites ?? ctx.satellites
```

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
