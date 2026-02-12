# Gemini Deep Think — Context Package

Copy-paste this into Gemini (app or AI Studio) at the start of a Deep Think session, followed by the specific question and any reference material.

---

## Project: Short Gravity

Autonomous space sector intelligence platform. Solo-built by Gabriel. Live at shortgravity.com.

**Products:**
- Spacemob Terminal — Bloomberg-grade HUD for $ASTS (AST SpaceMobile). Current focus.
- $SPACE Dashboard — Sector-wide space investing intelligence. Next release.
- Brain — RAG layer across all data sources (SEC filings, FCC filings, patents, press releases, X posts).

**Stack:** Next.js 14, TypeScript, Tailwind, Three.js, Python 3 workers, Supabase (PostgreSQL + pgvector), Vercel, GitHub Actions.

**Architecture:** Every feature = Worker → Supabase → API Route → UI Component. Workers run on cron schedules. UI reads live from database. No mock data. No placeholders.

**Design:** True black (#030305), white text, orange (#FF6B35) for selection only. JetBrains Mono. Custom Canvas 2D charting engine. Tactical HUD aesthetic.

**Principles:**
- One engine per domain (no competing libraries)
- Parameters, not products (shared infra that takes arguments)
- Full pipeline or nothing
- Coverage completeness (capture everything that exists, then maintain)

## Your role

You are the research and architecture analyst. You look outward — analyze reference material, explore multiple architectural approaches, and produce specification language. Be opinionated. Recommend one path. Write spec sections, not code.

Your output will be used to update the project specification (CLAUDE.md), which drives a separate AI coding agent (Claude) that implements everything.

---

## Question: Unified Intelligence Feed

Short Gravity has 20+ autonomous data workers collecting SEC filings, FCC filings, patents, press releases, X posts, satellite telemetry, short interest, earnings transcripts, and space weather. The collection layer is mature. The "so what" layer is not.

**The problem: two parallel signal systems that don't talk to each other, and rich intelligence data sitting dark in the database.**

I need you to design a Unified Intelligence Feed — a single page (`/signals` or redesigned `/intel`) that becomes the reason someone subscribes. This is the payoff for all the data collection. Raw data is free; intelligence is premium.

### What exists today

**System 1: signal_scanner (stored signals)**

A Python worker runs every 4 hours via GitHub Actions. It detects 6 types of cross-source anomalies and writes them to a `signals` table:

| Signal Type | Detection | Example |
|---|---|---|
| sentiment_shift | 7d vs 30d X post sentiment divergence | "Community sentiment shifted bullish (+0.18 vs 30d baseline)" |
| filing_cluster | 2+ SEC filings in 48h OR 3+ FCC filings in 7d | "SEC filing cluster: 3 filings in 36 hours" |
| fcc_status_change | New FCC grants or STA approvals | "FCC granted experimental license for..." |
| cross_source | X activity spike (2.5x+ baseline) after filing/PR | "Cross-source: tweet spike 3.2x after 8-K filing" |
| short_interest_spike | >10% change in short shares between reports | "Short interest dropped 14.2% week-over-week" |
| new_content | High-signal SEC filings or categorized PRs | "New 10-K annual report filed" |

Each signal has:
- `title` + `description` (Haiku-generated 2-3 sentence analysis)
- `source_refs` JSONB — array of `{table, id, title, date}` linking to the exact documents that triggered it
- `metrics` JSONB — signal-specific quantitative data (sentiment scores, spike ratios, filing counts, short interest change %)
- `severity` (low/medium/high/critical)
- `status` lifecycle (active → acknowledged → expired → false_positive)
- `fingerprint` for dedup

**The `metrics` and `source_refs` fields are the gold.** They contain the actual evidence — but the UI only shows title and description.

Signals table schema:
```sql
CREATE TABLE signals (
  id          BIGSERIAL PRIMARY KEY,
  signal_type TEXT NOT NULL,
  severity    TEXT NOT NULL DEFAULT 'medium',
  title       TEXT NOT NULL,
  description TEXT,
  source_refs JSONB DEFAULT '[]',
  metrics     JSONB DEFAULT '{}',
  detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at  TIMESTAMPTZ,
  status      TEXT NOT NULL DEFAULT 'active',
  fingerprint TEXT UNIQUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Current UI: A `SignalFeed` widget in the terminal right panel. Scrollable list showing severity dot + type label + title + description (2-line clamp) + time ago. That's it. No drill-down, no metrics, no source chain, no interaction.

**System 2: Intel page (computed signals)**

The `/intel` page computes its own signals client-side from 4 API endpoints:
- `useCrossRefs()` → `/api/widgets/semantic-crossref` — semantic patent↔FCC, patent↔PR connections with confidence scores
- `usePriceEvents()` → filing velocity anomalies
- `useEarningsDiff()` → earnings language shifts (new/dropped terms between quarters)
- `useVoices()` → `/api/widgets/voice-scores` — X account signal quality scoring

These are displayed as "SIGNALS DETECTED" on the intel page with expandable source attribution. But they're ephemeral — computed on every page load, never stored, never correlated with System 1.

**What's dark (rich data in DB, not surfaced):**
- Signal metrics breakdown (why was sentiment delta 0.18? how many tweets? what changed?)
- Source attribution chains (which specific filing + which specific X spike triggered a cross_source signal?)
- Signal history (has this signal type fired before? how often? trending up?)
- Signal-to-price correlation (did high-severity signals predict price movement?)
- False positive tracking (acknowledged/expired signals — what's the hit rate?)
- Cross-reference confidence scores (patent↔FCC connections exist but aren't shown alongside stored signals)

### What I need from you

Design the Unified Intelligence Feed. This should be:
1. A single page architecture that merges both signal systems
2. The "command center" view that makes you feel like you have an edge
3. Architecturally clean enough for a solo dev to build and maintain

**Specifically, produce:**

**A. Information Architecture**
- What's the layout? What panels, what hierarchy?
- How do stored signals and computed intelligence coexist?
- What's the primary view (timeline? severity matrix? type clusters?) and what are secondary views?
- How does drill-down work? Signal → evidence → raw document?

**B. Signal Taxonomy**
- Should the two systems merge into one model or stay separate but unified in display?
- What categories make sense for a space sector investor? (The current 6 types are detection-method-based, not investor-intent-based)
- How should severity/confidence be presented? Color? Score? Both?

**C. Price Correlation Layer**
- Signals overlaid on price chart — how should this work?
- What timeframe? What interaction (hover signal, see price impact)?
- Should we compute and store signal hit-rate (% of high-severity signals that preceded 2%+ move within 24h)?

**D. Feed vs. Dashboard**
- Is this a chronological feed (newest first, infinite scroll)?
- Or a dashboard with summary stats + filtered feed?
- Or something else entirely?

**E. Tier Gating**
- Free users see the terminal with the basic SignalFeed widget (title + description)
- What does Full Spectrum see on this page that justifies the subscription?
- What specific data/interaction is the premium unlock?

**F. Spec Language**
- Write the output as CLAUDE.md-ready sections: page architecture, component structure, API changes, data model changes
- Be specific enough that an AI coding agent can implement without asking questions
- Reference the existing UI component system: `Panel`, `Text`, `Label`, `Value`, `Stat`, `SGChart`, widget system, HUDLayout

### Reference: Existing UI Component System

The platform has a three-layer UI system that the intelligence feed must use:

**Layer 1 — Primitives** (`components/primitives/`):
`Panel` (compound: Header, Content, Section, Divider), `Text` (7 variants, 8 sizes), `Label`, `Value`, `Muted`, `Stat` (hero numbers with units/deltas), `StatusDot`, `LoadingState`, `Skeleton`, `ProgressBar`.

**Layer 2 — Widget System** (`components/hud/widgets/`):
Self-contained data panels with manifests. Registered in `registry.ts`. Rendered via `WidgetPanel` → `WidgetHost`.

**Layer 3 — Layout**:
`HUDLayout` compound component: `Canvas`, `Overlay`, `TopLeft`, `TopRight`, `LeftPanel`, `RightPanel`, `BottomCenter`, `Attribution`.

**Charting**: Custom Canvas 2D engine (`SGChart`). Supports line, area, bar, candlestick, sparkline series. Overlays: trend lines, reference lines, markers (vertical lines at timestamps). Already used on `/orbital`, `/intel`, `/compare`.

### Reference: Existing Data Sources

| Source | Table | Count | Worker | Schedule |
|---|---|---|---|---|
| SEC filings | filings | 530 | filing_worker | Every 2h weekdays |
| FCC filings | fcc_filings | 4,500+ | ecfs/icfs/uls workers | Daily |
| Patents | patents | 307 | patent_worker_v2 | Daily |
| Press releases | press_releases | 100+ | press_release_worker | Daily |
| X posts | x_posts | 2,000+ | x_worker | Every 15min |
| Earnings transcripts | earnings_transcripts | ~20 | transcript_worker | Weekly |
| Short interest | short_interest | ~100 | short_interest_worker | Weekly |
| Daily prices | daily_prices | 1,000+ | price_worker | Daily |
| Signals | signals | ~200 | signal_scanner | Every 4h |
| Brain chunks | brain_chunks | 13,000+ | embedding_worker | Daily |
| Satellites | satellites | 7 | tle_worker (Vercel cron) | Every 4h |
| Space weather | space_weather | 25,000+ | space_weather_worker | Daily |

### Research direction

Look at how these platforms surface intelligence from raw financial/technical data:
- **Bloomberg Terminal** — news/alert feed, WECO (event-driven), cross-asset correlation
- **Unusual Whales** — options flow anomaly detection, Congress trading alerts
- **Koyfin** — event timeline overlaid on price charts
- **Palantir Gotham** — cross-source intelligence linking (the graph approach)
- **Stratechery** — how Ben Thompson structures intelligence for solo consumption

The goal isn't to copy any of these. It's to understand what makes intelligence feel actionable vs. just informational, then design something that fits Short Gravity's tactical HUD aesthetic and solo-operator reality.

### Constraints

- Solo dev. Whatever you design, Gabriel + Claude need to build and maintain it.
- No new dependencies. Use existing stack (React, framer-motion, SGChart, Supabase).
- Must work within existing tier system (free sees basic signals, Full Spectrum sees the intelligence feed).
- Page should feel like the rest of the terminal — dark, clean, information-dense, no decoration.
- The existing `signal_scanner.py` worker is solid and should be extended, not replaced.
- Current `signals` table schema is good — extend it, don't redesign it.

### Deliverable format

Write your output as:
1. **Recommended approach** (1 paragraph — your opinionated pick)
2. **Page architecture** (layout, panels, hierarchy — spec language ready for CLAUDE.md)
3. **Signal taxonomy** (unified model for both systems)
4. **API changes** (new endpoints or extensions to existing)
5. **Data model changes** (new tables, columns, or views)
6. **Tier gating spec** (what's free, what's premium)
7. **Implementation phases** (what to build first, second, third)
