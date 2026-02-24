# SHORT GRAVITY: THE TERMINAL CONSTITUTION

**Date:** February 23, 2026
**Status:** Living Document (Patient Zero — Active Development)

---

## 1. WHAT SHORT GRAVITY IS

Short Gravity is an **AST SpaceMobile intelligence terminal** — a real-time research tool for investors, analysts, and space enthusiasts tracking $ASTS. It aggregates satellite telemetry, SEC/FCC regulatory filings, patents, earnings data, press releases, social media signals, and space weather into a unified command interface.

The flagship experience is an immersive 3D terminal at `/asts` — a full-screen WebGL globe displaying the BlueBird constellation with live orbital propagation, coverage footprints, and a surrounding HUD of intelligence widgets.

**Short Gravity is not a generic dashboard.** It is a domain-specific intelligence terminal with the aesthetic of a mission control room.

---

## 2. SHORT GRAVITY'S ROLE IN NEXOD

Short Gravity is **Patient Zero** — the first real-world project built using the NEXOD/Lingot architecture. It is both a product and a proving ground.

The relationship:
- **NEXOD** is the philosophy — the Epistemic Monorepo, the thermodynamics of code, the laws governing AI labor.
- **Lingot** is the engine — Maxwell's Demon, the orchestrator that spawns agents in isolated rooms.
- **Short Gravity** is the host organism — the living application where these principles are tested, refined, and proven at scale.

Everything we learn building Short Gravity feeds back into NEXOD. The architecture, the mandate patterns, the failure modes — all of it becomes reusable intellectual property.

---

## 3. THE LAWS OF PHYSICS (Inherited from NEXOD)

### Law 1: Absolute Zero (No Context Bleed)
An agent shall only be given the exact number of tokens required to perform its function, and not a single token more. Physical directory boundaries enforce this — not willpower.

### Law 2: The Cathedral (Strict Room Isolation)
The monorepo is a cathedral of isolated rooms. Each room has a single responsibility. An agent working in `packages/ui` cannot see the database. An agent working in `packages/core` cannot see React. The `CLAUDE.md` microkernel in each room defines its local laws of physics.

### Law 3: The Anti-Corruption Layer (ACL)
`apps/web` is the only place where rooms connect. It translates between pure packages — mapping `anomaly_type` from the database to `signal_type` for the UI. No package directly imports another's internal types without translation.

### Law 4: Graceful Degradation Over Hallucination
When an agent encounters something it cannot safely build (WebGL, complex animations, missing data), it MUST cap the live wire with a structural stub and move on. A beautiful empty shell with zero runtime errors is infinitely better than 3,000 lines of hallucinated slop that crashes the build.

### Law 5: The Circuit Breaker
Every mandate ends with `tsc --noEmit`. If TypeScript compiles, the work is accepted. If it fails, the assembly line halts. The compiler is the ground truth — not the agent's confidence.

---

## 4. THE CATHEDRAL (Monorepo Architecture)

```
short_gravity/
├── .architect/                    # THE CONTROL PLANE
│   ├── workbench/                 # The Architect's desk (conversation + planning)
│   │   └── CLAUDE.md              # Architect microkernel (NO coding, mandates only)
│   ├── queue/                     # Pending Work Orders (mandates)
│   ├── history/                   # Completed mandates (audit trail)
│   ├── research/                  # Research artifacts, session logs
│   ├── blueprints/                # Architecture documentation
│   ├── lingot.mjs                 # Maxwell's Demon (the orchestrator)
│   ├── NEXOD_CONSTITUTION.md      # The generic NEXOD philosophy
│   └── SHORT_GRAVITY_CONSTITUTION.md  # THIS FILE
│
├── apps/
│   └── web/                       # THE SENTENCES — Next.js 14 application
│       ├── CLAUDE.md              # "You wire packages together. You are the ACL."
│       └── src/
│           ├── app/               # Routes, API endpoints, layouts
│           ├── components/        # App-specific widgets, overlays, controls
│           └── lib/               # Hooks, stores, data, utilities
│
├── packages/
│   ├── ui/                        # THE ADJECTIVES — Pure visual primitives
│   │   ├── CLAUDE.md              # "You build React+Tailwind+WebGL. No data fetching."
│   │   └── src/
│   │       ├── components/        # Primitives, HUD layout, Globe3D, earth/
│   │       └── lib/               # Visual math (hexasphere, etc.)
│   │
│   ├── core/                      # THE VERBS — Pure TypeScript business logic
│   │   ├── CLAUDE.md              # "Pure logic. No UI. No HTTP. No React."
│   │   └── src/
│   │       ├── signals/           # Z-score anomaly detection
│   │       ├── physics/           # Earth radius, SGP4, haversine
│   │       ├── briefing/          # Claude prompt builders
│   │       ├── schemas/           # Zod schemas (the canonical type system)
│   │       ├── orbital.ts         # TLE propagation (satellite.js)
│   │       └── satellite-coverage.ts  # Coverage geometry math
│   │
│   └── database/                  # THE NOUNS — DB schema + Supabase clients
│       ├── CLAUDE.md              # "Schemas and clients only. No UI. No React."
│       └── src/
│           ├── schema.ts          # Drizzle ORM schema
│           └── index.ts           # getServiceClient(), getAnonClient()
│
├── _ARCHIVE_V1/                   # Quarantined legacy codebase (read-only reference)
├── _VAULT/                        # Archived human entropy (old CLAUDE.md, logs, plans)
├── scripts/data-fetchers/         # Python worker fleet (GitHub Actions)
└── docs/                          # Public documentation
```

### The Naming Convention
| Package | Metaphor | Rule |
|---------|----------|------|
| `@shortgravity/database` | The Nouns | Defines what things ARE (schemas, types, clients) |
| `@shortgravity/core` | The Verbs | Defines what things DO (analyze, propagate, calculate) |
| `@shortgravity/ui` | The Adjectives | Defines what things LOOK LIKE (render, animate, display) |
| `@shortgravity/web` | The Sentences | Wires nouns, verbs, and adjectives into coherent pages |

---

## 5. THE MANDATE SYSTEM (How Work Gets Done)

### The Architect (`.architect/workbench/`)
The Principal Architect sits in the workbench. It converses with Gabriel, diagnoses system state, reads any file in the repo, and plans architecture. It is **strictly forbidden from writing application code**. Its only output mechanism is writing Work Orders (mandates) into `../queue/`.

### Mandate Format
```markdown
TARGET: <path_relative_to_monorepo_root>
---
MISSION:
<High-level goal>

DIRECTIVES:
1. <Exact step-by-step instructions for the amnesiac worker agent>
```

### The Assembly Line (lingot.mjs)
1. Reads the next mandate from `.architect/queue/`
2. Identifies the TARGET room
3. Spawns a headless, amnesiac Claude worker trapped inside that directory (`cwd`)
4. The worker reads its local `CLAUDE.md` microkernel — its only knowledge of the world
5. The worker executes the mandate autonomously (YOLO mode)
6. **Circuit Breaker:** `tsc --noEmit` runs in the target room
7. Pass: mandate archived to `history/`. Fail: assembly line halts.

### Completed Mandates (Build History)
| # | Mandate | Target | What Happened |
|---|---------|--------|---------------|
| 001 | ui-globe | packages/ui | Built initial wireframe Globe.tsx with R3F |
| 002 | web-globe-widget | apps/web | Wired GlobeWidget ACL (SSR-safe dynamic import) |
| 003 | root-bootstrap | . | Restored root package.json, turbo.json, tsconfig.json |
| 004 | typecheck-wiring | . | Added typecheck scripts to all 4 workspaces |
| 005 | r3f-downgrade | packages/ui | Fixed R3F 9 → R3F 8 (React 18 compatibility) |
| 006 | globe-migration | . | Full Globe3D migration from V1 archive (8 files) |
| 007 | api-routes | . | Migrated 7 API routes from V1 with import rewrites |

---

## 6. THE TERMINAL (What We Are Building)

### Primary Interface: `/asts`
The immersive full-screen terminal. ~115 lines of pure composition:

```
TerminalDataProvider (satellite data context)
  └── Suspense
       └── TerminalContent (Zustand store + data hooks)
            └── FocusPanelProvider
                 └── HUDLayout
                      ├── .Canvas → GlobeWidget (Globe3D with WebGL earth, orbits, coverage)
                      ├── .LeftPanel → WidgetPanel (intelligence widgets)
                      ├── .RightPanel → WidgetPanel (financial/event widgets)
                      ├── .BottomCenter → GlobeControls (mode toggles)
                      └── SatelliteInfoCard (per-satellite detail)
                 └── BrainSearch (AI-powered overlay)
```

### Three-Layer UI System

**Layer 1 — Primitives** (`packages/ui/src/components/primitives/`):
Atomic building blocks. `Panel` (compound: Header, Content, Section, Divider), `Text` (7 variants, 8 sizes), `Label`, `Value`, `Muted`, `Stat` (hero numbers with units/deltas), `StatusDot`, `LoadingState`, `Skeleton`, `ProgressBar`. Chart primitives: `Crosshair`, `HairlinePath`, `ValueReadout`, `CornerBrackets`, `Baseline`, `GhostTrend`.

**Layer 2 — Widget System** (`apps/web/src/components/hud/widgets/`):
Self-contained data panels. Each exports a component + `WidgetManifest`. 15 registered widgets:

| Widget | What It Shows |
|--------|--------------|
| constellation-matrix | Per-satellite table (TLE age, altitude, period, B*, divergence) |
| signal-feed | Live anomaly signals |
| regulatory-status | FCC filing status tracker |
| short-interest | Short interest data |
| cash-position | Cash reserves + burn rate |
| next-event | Countdown to next launch/earnings/regulatory event |
| earnings-ledger | Management guidance tracker (10 promises, MET/PENDING/DELAYED) |
| environment-strip | Space weather conditions |
| fm1-monitor | FM1 satellite health monitor |
| fm1-watch | FM1 watch panel |
| mercator-map | 2D satellite ground track map |
| launch-countdown | Launch countdown timer |
| activity-feed | Activity feed |
| telemetry-feed | Raw telemetry stream |
| constellation-progress | Constellation build progress |

**Layer 3 — Layout + Presets** (`lib/terminal/presets.ts`):
Named configurations that define which widgets appear where:
- **default** — Full intelligence overview
- **launch-day** — FM1 focus, environment monitoring, countdown
- **post-unfold** — Post-deployment constellation monitoring
- **earnings-week** — Financial focus, earnings + cash + short interest

### Globe3D (The Visual Crown Jewel)
Production-quality WebGL 3D Earth in `packages/ui/src/components/earth/`:
- Dot-density landmasses (custom shader, 356KB point cloud)
- Lat/lon grid lines
- Per-satellite orbit paths (TLE propagation via satellite.js)
- Coverage footprints (spherical geometry)
- Hexasphere cell grid (revealed by satellite footprints)
- 3D BlueBird satellite models (bus + solar array geometry)
- Camera-aware visibility fading
- OrbitControls

---

## 7. THE DATA BACKBONE

### Supabase (PostgreSQL + pgvector)
35+ tables powering the intelligence pipeline. Key tables:
- `satellites`, `tle_history` — Orbital telemetry (CelesTrak + Space-Track)
- `filings` — SEC EDGAR documents
- `fcc_filings` — FCC/ICFS/ECFS/ELS + international (ITU, ISED, Ofcom)
- `patents`, `patent_claims` — 307 patents, 2,482 claims
- `signals` — Cross-source anomaly detections
- `brain_chunks` — 13,000+ vector embeddings for RAG search
- `daily_prices`, `short_interest`, `cash_position` — Financial data
- `space_weather`, `conjunctions` — Space environment data

### Worker Fleet (25+ Python Workers on GitHub Actions)
Every worker runs on a cron schedule. `run_all.py` is local convenience only.
Key cadences:
- **Every 15min:** X/Twitter posts (market hours)
- **Every 2h:** SEC EDGAR polling (weekdays)
- **Daily:** News, press releases, patents, prices, launches, embeddings, signals, space weather
- **Weekly:** Transcripts, glossary, international regulators, short interest

### Vercel Crons (Exception to GH Actions Pattern)
- `/api/cron/tle-refresh` (every 4h) — Dual-source TLE sync + health anomaly detection
- `/api/cron/check-feeds` (every 5min) — Feed monitoring
- `/api/cron/filings-sync` (every 15min) — Filing sync
- `/api/cron/daily-brief` (daily) — Morning intelligence email
- `/api/cron/signal-alerts` (every 15min) — Critical signal email alerts

### TLE Source Trust (Critical Rule)
- **CelesTrak** — PRIMARY for positional accuracy + maneuver detection
- **Space-Track** — PRIMARY for BSTAR/drag/altitude trends
- **NEVER mix sources in the same calculation.** CelesTrak GP fitting noise creates false anomaly detections when blended with Space-Track data.

---

## 8. LIVE API ROUTES (7 Migrated from V1)

| Route | Data Source | Status |
|-------|------------|--------|
| GET /api/signals | `generateMockSignals()` | **MOCK** — needs wiring to real `signals` table |
| GET /api/horizon | Supabase (6 parallel queries) | LIVE (15min cache) |
| GET /api/widgets/regulatory | `fcc_filings` | LIVE |
| GET /api/widgets/short-interest | `short_interest` | LIVE |
| GET /api/widgets/cash-position | `cash_position`, `filings` | LIVE |
| GET /api/widgets/next-launch | `next_launches` | LIVE |
| GET /api/stock/[symbol] | Finnhub proxy | LIVE |
| GET /api/earnings/context | `earnings_calls`, `inbox`, `daily_prices` | LIVE |

---

## 9. CURRENT STATE (What Works, What Doesn't)

### What Works
1. The monorepo boots — root package.json, turbo.json, tsconfig.json all wired
2. TypeScript compiles across all workspaces (`turbo run typecheck` passes)
3. Globe3D is a full production-quality WebGL visualization
4. 7 API routes serve real Supabase data
5. All 15 widgets are defined and registered in the widget system
6. The HUD layout system and 4 widget presets are complete
7. Landing page at `/` is complete with domain context
8. The full worker fleet runs on GitHub Actions schedules

### The Core Gap: TerminalDataProvider is a Stub
`TerminalDataProvider` returns empty arrays. The globe shows no satellites. The ConstellationMatrix shows "ACQUIRING TELEMETRY...". Wiring this requires:
- A satellite data API (reading from the `satellites` Supabase table)
- Real-time SGP4 position propagation via satellite.js
- Feeding `SatelliteData[]` into Globe3D through GlobeWidget
- Populating freshness, divergence, space weather, and conjunction data

### Secondary Gaps
- **BrainSearch** — stub overlay, not wired to vector search
- **/api/signals** — returns mock data, needs real `signals` table wiring
- **Missing pages** — `/signals`, `/orbital`, `/patents`, `/research`, `/regulatory`, `/competitive`, `/earnings`, `/briefing`, `/horizon`, `/thesis`, `/satellite/[noradId]` (referenced on landing page but no page files exist in the monorepo)
- **Drizzle schema divergence** — `packages/database/src/schema.ts` is an idealized subset; actual API routes use raw Supabase REST calls via `getAnonClient()` directly
- **Stubs needing implementation** — CommandPalette, ClearanceModal, MercatorMap, DocumentViewer, DragChart, FocusPanel (animation)

---

## 10. THE NEXT FRONTIER (Prioritized Work)

### Priority 1: Satellite Telemetry (Make the Globe Live)
Wire `TerminalDataProvider` to real satellite data. This is the single highest-impact change — it transforms the terminal from a beautiful skeleton into a living intelligence display.

### Priority 2: Real Signals Pipeline
Replace mock signals with the real `signals` Supabase table. The signal scanner worker already runs twice daily — the data exists, the API route just needs wiring.

### Priority 3: Page Buildout
The landing page promises 10+ pages. Each is a mandate:
- `/signals` — Unified signals dashboard with price correlation
- `/orbital` — Constellation health, orbital analysis, space weather
- `/satellite/[noradId]` — Per-satellite telemetry detail
- `/patents` — Patent portfolio browser
- `/regulatory` — FCC battlemap
- And the rest...

### Priority 4: Brain Search
Wire the BrainSearch overlay to the existing pgvector + Claude RAG system. 13,000+ embedded chunks are already in Supabase — they just need a search API and a UI.

---

## 11. RULES FOR BUILDING (Non-Negotiable)

1. **Every page must use the three-layer UI system.** No raw Tailwind for panels, stats, text, or loading states. Use Primitives.
2. **All new visual components go in `packages/ui`.** No WebGL, no Three.js, no complex animations in `apps/web`.
3. **All new business logic goes in `packages/core`.** No z-score calculations, no orbital math, no prompt builders in `apps/web`.
4. **All Supabase client access goes through `@shortgravity/database`.** No creating local supabase.ts files.
5. **`apps/web` is the ACL.** It translates, wires, and routes. It does not contain domain logic or visual primitives.
6. **The Architect does not code.** It converses, plans, and writes mandates. Period.
7. **The worker is amnesiac.** Each mandate is self-contained. The worker knows nothing about previous mandates, the broader system, or the business context. Write mandates accordingly.
8. **The compiler is the judge.** `tsc --noEmit` is the only quality gate. If it compiles, it ships. If it doesn't, the line halts.
9. **TLE source discipline.** CelesTrak for positions/maneuvers. Space-Track for BSTAR/drag. Never mix.
10. **Python workers use stdlib only.** `urllib` not `requests`. No pip dependencies beyond the standard library.
