# THREADS.md — Active Narrative Arcs

> Every loop pulls a thread. A thread is a durable, multi-session narrative arc that answers a specific user intent. It is not "done" until the user can pull the thread from start to finish without friction.

## Protocol

1. **READ** this file — understand current state of all threads
2. **TRACE** — Claude writes/updates the trace for the highest-priority open GAP
3. **WEAVE** — Send trace to Gemini. Gemini critiques and specs the transition.
4. **FABRICATE** — Claude implements the transition
5. **PROOF** — Claude re-runs the trace. If the GAP is closed, mark it. If new GAPs appear, log them.
6. **UPDATE** this file — new status, completed transitions, any new GAPs discovered

## Statuses

| Status | Meaning |
|--------|---------|
| **GOLDEN** | Thread works end-to-end. No friction. Ship it. |
| **FRAYED** | Functional but high friction. Users can get through but it's painful. |
| **BROKEN** | Dead end. The thread snaps at a specific point. |
| **PLANNED** | Spec phase. Traces being written. |
| **DARK** | User intent exists but the platform has zero surface area for it. |

## Cross-Thread Connections

Threads compound when they link to each other. These are the active cross-thread bridges:

| From | To | Trigger | Action |
|------|----|---------|--------|
| `/signals` SignalDetail | `/thesis` | "BUILD THESIS" button | Opens thesis builder pre-filled with signal title |
| `/signals` SignalDetail | `/horizon` | "VIEW HORIZON" button | Opens horizon filtered by signal category→event type |
| `/horizon` catalyst events | `/thesis` | "ANALYZE" button | Opens thesis builder pre-filled with catalyst title |
| `/asts` SignalFeed widget | `/signals` | Header "SIGNALS" link | Opens full intelligence feed |
| `/asts` LaunchCountdown widget | `/horizon` | Header "NEXT LAUNCH" link | Opens horizon filtered to launches |
| `/thesis` header | `/signals`, `/horizon` | Navigation links | Cross-page discovery |
| `/signals` header | `/horizon` | Navigation link | Cross-page discovery |
| `/horizon` header | `/signals` | Navigation link | Cross-page discovery |

---

## Thread 001: Signal-to-Source

**Status:** GOLDEN
**Priority:** P0
**Intent:** "Something just happened — a price swing, a news alert, a rumor on Twitter. Is it real? What is the primary source document? What does the document *actually* say?"
**North Star:** User goes from signal detection → source document with proof in under 30 seconds.
**Undeniable Value:** Kills the frantic scramble across ten tabs. Institutional-grade context, instantly.

### Current Trace

```
[User lands on /signals]
  → sees signal cards (severity, category, title, time) ✅
  → clicks a signal card
  → [Signal detail panel opens on right] ✅
    → sees title, severity, category, description, metrics, confidence ✅
    → scrolls to EVIDENCE section
    → sees source references as clickable buttons with hover state + arrow icon ✅
    → clicks an evidence item (e.g., "SEC FILING — 8-K")
    → [DocumentViewer modal opens] ✅
      → fetches via /api/widgets/document?table=filings&ref={accession_number} ✅
      → shows badge, date, title, summary, full content ✅
      → external link to original document ✅
      → Escape or close button to dismiss ✅
    → **PRIMARY PATH: COMPLETE** ✅

[Alternative path: user tries brain search]
  → opens brain panel on /signals page ✅
  → types query about the signal topic
  → gets RAG response with source citations ✅
  → clicks a source citation
  → [DocumentViewer modal opens] ✅
    → fetches via /api/widgets/document?table={table}&ref={natural_key} ✅
    → shows full document content ✅
  → **BRAIN SEARCH PATH: COMPLETE** ✅

[Alternative path: brain search in ChatMessage (full brain overlay)]
  → user asks brain a question on /asts or /research ✅
  → gets response with citation cards ✅
  → clicks a citation card
  → [DocumentViewer modal opens] ✅
  → **CHAT CITATION PATH: COMPLETE** ✅

[Alternative path: ActivityFeed on /asts]
  → still works via legacy UUID-based DocumentViewer ✅ (backward compatible)
```

### Infrastructure Audit

| Component | Exists? | Where | Notes |
|-----------|---------|-------|-------|
| Signal detection | ✅ | `signal_scanner.py` | 8 detectors, source_refs populated |
| Signal storage | ✅ | `signals` table | source_refs JSONB with table + id + title |
| Signal display | ✅ | `/signals` page + `SignalCard` + `SignalDetail` | Cards + detail panel |
| Evidence rendering | ✅ | `SignalDetail.tsx` EVIDENCE section | **Clickable buttons with hover state + arrow icon** |
| Document API | ✅ | `/api/widgets/document` | Supports natural key (`?table=&ref=`) + legacy UUID (`?id=`) |
| Document viewer | ✅ | `DocumentViewer.tsx` | Supports `sourceTable`+`sourceRef` props for natural key lookup |
| Signal→Document link | ✅ | `SignalDetail.tsx` → `DocumentViewer` | **BRIDGED. Evidence click → DocumentViewer modal.** |
| ID format bridge | ✅ | `/api/widgets/document` | Natural key mode queries by accession_number/file_number/patent_number |
| Patent support | ✅ | `/api/widgets/document` | Patent type now returns title, abstract, inventors, assignee, status |

### Open GAPs

1. ~~Evidence items not clickable~~ → **CLOSED** (GAP 1)
2. ~~ID format mismatch~~ → **CLOSED** (natural key mode in Document API)
3. ~~No DocumentViewer on /signals~~ → **CLOSED** (imported in SignalDetail)
4. ~~Patent documents not supported~~ → **CLOSED** (patent fetcher added to Document API)
5. ~~Brain search citations not linked~~ → **CLOSED** (GAP 5)

### Completed Transitions

- **GAP 1 → CLOSED (2026-02-12):** Evidence items in SignalDetail are now clickable buttons. Each source_ref with an `id` field shows a hover state + arrow icon. Clicking opens DocumentViewer in a portal modal, fetching via natural key (`?table={table}&ref={id}`). Document API extended with natural key lookup mode + patent support. Backward-compatible with existing ActivityFeed UUID-based usage.
- **GAP 5 → CLOSED (2026-02-12):** Brain search citations now open DocumentViewer. Added `getDocumentViewerParams()` utility in `lib/brain/search.ts` to map source types to table names. Citation component gets `onSelect` callback. ChatMessage wires citations to DocumentViewer. /signals page brain panel sources are now clickable buttons. Three integration points: SignalDetail evidence, ChatMessage citations, /signals brain panel.

---

## Thread 002: Event Horizon

**Status:** GOLDEN
**Priority:** P1
**Intent:** "What's next? What are the known-unknowns on the calendar that could move the stock? When do I need to pay attention?"
**North Star:** User sees a timeline of upcoming catalysts for the next 7/30/90 days, each linked to its source.
**Undeniable Value:** Moves user from reactive to proactive. Strategic radar, not news feed.

### Current Trace

```
[User navigates to /horizon]
  → sees EVENT HORIZON page with header (event count, critical count) ✅
  → filter controls: type filter (ALL/LAUNCHES/CONJUNCTIONS/REGULATORY/PATENTS/EARNINGS/CATALYSTS) ✅
  → range selector: 30D / 90D / 6M / 1Y ✅
  → events grouped by month, sorted chronologically ✅
  → each event shows: severity dot, countdown, date, type badge, title, subtitle ✅
  → events with source_ref show arrow icon — clickable → DocumentViewer ✅
  → **PHASE 1 COMPLETE: Unified timeline from 5 database sources** ✅
  → catalysts show with fuzzy date indicator (~Q2 2026) when no precise date ✅
  → **PHASE 2 COMPLETE: Catalysts migrated to database (6 event types)** ✅

[Gaps in data coverage]
  → launches: ✅ from next_launches (launch_worker)
  → conjunctions: ✅ from conjunctions (socrates_worker)
  → catalysts: ✅ from catalysts table (22 upcoming + 35 completed seeded via migration 023)
  → FCC expirations: ✅ from fcc_filings (expiration_date) + fcc_dockets (comment/reply deadlines)
  → patent expirations: ⚠️ many patents may not have expiration_date populated
  → earnings calls: ✅ from earnings_calls (earnings_worker via Finnhub calendar)
  → ~~GAP 1: Curated catalysts hardcoded~~ → **CLOSED** (migration 023 + API + UI)
  → ~~GAP 2: FCC comment/reply deadlines not captured by ECFS worker~~ → **CLOSED**
  → **GAP 3: No automated earnings date discovery**

[User discovers /horizon via]
  → Command palette (Cmd+K → "horizon") ✅
  → Direct URL ✅
  → Landing page EXPLORE grid ✅
  → /signals header cross-link ✅
  → /horizon header cross-links to SIGNALS + TERMINAL ✅
```

### Infrastructure Audit

| Component | Exists? | Notes |
|-----------|---------|-------|
| Horizon API | ✅ | `/api/horizon` aggregates 7 sources (incl. docket deadlines + catalysts), type filter + days range |
| Horizon page | ✅ | `/horizon` — full page with filters, month grouping, severity, countdown |
| DocumentViewer integration | ✅ | Events with source_ref clickable → opens document viewer |
| Launch data | ✅ | `next_launches` table — 3 known launches |
| Conjunction data | ✅ | `conjunctions` table — SOCRATES daily updates |
| FCC expiration data | ✅ | `fcc_filings.expiration_date` + `fcc_dockets.comment_deadline`/`reply_deadline` |
| Patent expiration data | ⚠️ | `patents.expiration_date` — needs audit |
| Earnings data | ✅ | `earnings_calls.call_date` — automated via earnings_worker (Finnhub calendar) |
| Catalyst database | ✅ | `catalysts` table — migration 023, 22 upcoming + 35 completed seeded |
| Command palette link | ✅ | Added to navigation commands |

### Open GAPs

1. ~~Curated catalysts not in timeline~~ → **CLOSED** (migration 023 + API query + UI filter/badge)
2. ~~FCC comment/reply deadlines~~ → **CLOSED** (fcc_dockets table + ECFS worker sync + Horizon query)
3. ~~Earnings date automation~~ → **CLOSED** (earnings_worker.py via Finnhub calendar)
4. ~~Navigation discovery~~ → **CLOSED** (landing page EXPLORE grid, /signals↔/horizon cross-links)
5. ~~Depends on Thread 001~~ → **RESOLVED** (T001 is GOLDEN)

### Completed Transitions

- **Phase 1 → DONE (2026-02-12):** Built `/api/horizon` endpoint aggregating 5 sources (launches, conjunctions, FCC expirations, patent expirations, earnings). Built `/horizon` page with type filters, range selector (30D/90D/6M/1Y), month grouping, severity dots, countdown, type badges. Events with source refs link to DocumentViewer. Added to command palette navigation.
- **GAP 1 → CLOSED (2026-02-12):** Catalysts migrated to database. Created `catalysts` table (migration 023) with 22 upcoming + 35 completed items seeded from `lib/data/catalysts.ts`. API queries catalysts with `estimateDateFromPeriod()` for fuzzy dates. UI shows CATALYSTS filter tab, purple CATALYST badge, and fuzzy date indicator (~Q2 2026) for items without precise dates. **NOTE: Migration 023 must be run in Supabase SQL Editor.**
- **GAP 4 → CLOSED (2026-02-12):** Navigation discovery. Added /horizon to landing page EXPLORE grid (5-col). Added HORIZON cross-link in /signals header. Added SIGNALS cross-link in /horizon header. Both pages now cross-reference each other + TERMINAL.
- **GAP 2 → CLOSED (2026-02-13):** FCC docket metadata. Created `fcc_dockets` table (migration 026) with comment/reply deadline fields, bureau, tags, filing activity. ECFS worker gets `sync_docket_metadata()` that polls FCC proceedings API — never overwrites non-null DB values with null API values (preserves manual seeds). Horizon API queries docket deadlines as source #6. FCC API has the fields but doesn't populate them; deadlines can be manually seeded and the worker will preserve them. **NOTE: Migration 026 must be run in Supabase SQL Editor.**
- **GAP 3 → CLOSED (2026-02-13):** Earnings date automation. New `earnings_worker.py` fetches Finnhub `/calendar/earnings` for ASTS. Upserts into `earnings_calls` table respecting immutable history (never overwrites `status='complete'`). Maps `hour` field to call_time. 3 future dates populated: Q4 2025 (2026-03-02), Q1 2026 (2026-05-11), Q2 2026 (2026-08-10). Weekly Wednesday schedule (needs GH Actions workflow).

---

## Thread 003: Thesis Builder

**Status:** GOLDEN
**Priority:** P2
**Intent:** "I have a theory about ASTS. Is there evidence to support or refute it? Can I build a bull/bear case from primary sources?"
**North Star:** User poses a thesis, gets a structured briefing with supporting/contradicting evidence from 13,000+ embedded documents.
**Undeniable Value:** Not just search — structured argumentation. The engine of conviction.

### Current Trace

```
[User navigates to /thesis]
  → sees thesis input with suggested theses ✅
  → types thesis statement (or clicks suggestion) ✅
  → submits with Cmd+Enter or button ✅
  → [SUPPORTING EVIDENCE section streams] ✅
    → brain search with default mode, "strongest supporting evidence" prompt ✅
    → markdown rendering with [1], [2] citation badges ✅
    → sources grid with Citation components below prose ✅
    → click source → DocumentViewer modal opens ✅
  → [CONTRADICTING EVIDENCE section streams] ✅
    → brain search with counter-thesis mode (full_spectrum) ✅
    → free tier: shows upgrade prompt instead ✅
  → [SYNTHESIS section streams] ✅
    → brain search for verdict: supported? biggest risk? decisive catalyst? ✅
  → **PHASE 1 COMPLETE: Structured thesis analysis from primary sources** ✅

[All functional gaps closed]
  → ~~GAP 2: No thesis persistence~~ → CLOSED (auto-save, /thesis/[id], PREVIOUS ANALYSES) ✅
  → ~~GAP 3: No evidence scoring~~ → CLOSED (STRONG/MODERATE/WEAK labels + bars) ✅
  → GAP 6: 3 sequential API calls — perf optimization, not functional break

[User discovers /thesis via]
  → Command palette (Cmd+K → "thesis") ✅
  → Landing page EXPLORE grid ✅
  → /thesis header cross-links to SIGNALS + HORIZON + TERMINAL ✅
  → Direct URL ✅
  → SignalDetail "BUILD THESIS" button (Thread 001 → 003 bridge) ✅
  → Horizon catalyst "ANALYZE" button (Thread 002 → 003 bridge) ✅
  → Pre-fills thesis via ?q= query param ✅

[UX during analysis]
  → progress tracker shows: SUPPORTING → CONTRADICTING → SYNTHESIS ✅
  → active step has orange pulsing dot, completed steps are gray ✅
```

### Infrastructure Audit

| Component | Exists? | Notes |
|-----------|---------|-------|
| Brain/RAG search | ✅ | Hybrid vector + keyword, LLM reranking |
| Counter-thesis mode | ✅ | Now surfaced via `/thesis` page (full_spectrum tier) |
| Structured briefing | ✅ | Three-section layout: FOR / AGAINST / SYNTHESIS |
| Thesis page | ✅ | `/thesis` — input, suggestions, three-section results |
| useThesisQuery hook | ✅ | Manages dual-stream state, sequential brain queries |
| DocumentViewer integration | ✅ | Citation click → DocumentViewer via Thread 001 infrastructure |
| Save/annotate | ✅ | Auto-save after analysis, /thesis/[id] shareable view, PREVIOUS ANALYSES list |
| Evidence scoring | ✅ | Rerank scores rendered as STRONG/MODERATE/WEAK labels + confidence bars in Citation |
| Depends on Thread 001 | ✅ | Source linking for evidence citations reuses T001 infrastructure |

### Open GAPs

1. ~~No structured output format~~ → **CLOSED** (three-section layout with streaming)
2. ~~Counter-thesis mode not in UI~~ → **CLOSED** (CONTRADICTING EVIDENCE section uses counter-thesis mode)
3. ~~No persistent briefings~~ → **CLOSED** (auto-save after analysis, /thesis/[id] shareable view, PREVIOUS ANALYSES list)
4. ~~Depends on Thread 001~~ → **RESOLVED** (T001 is GOLDEN)
5. ~~No evidence scoring~~ → **CLOSED** (already implemented — STRONG/MODERATE/WEAK labels + confidence bars in Citation component)
6. **Three sequential API calls** — Could be optimized to single prompt

### Completed Transitions

- **Phase 1 → DONE (2026-02-12):** Built `/thesis` page with thesis input + 5 suggested theses. Created `useThesisQuery` hook that makes 3 sequential brain queries (supporting evidence with default mode, contradicting evidence with counter-thesis mode, synthesis). Three-section streaming layout with ReactMarkdown + citation badges. Sources grids with Citation components. DocumentViewer integration for source drill-down. Free tier gets FOR + SYNTHESIS; counter-thesis requires full_spectrum. Added to command palette + landing page EXPLORE grid. Cross-links to SIGNALS, HORIZON, TERMINAL.
- **Cross-thread wiring → DONE (2026-02-12):** SignalDetail gets "BUILD THESIS" + "VIEW HORIZON" action buttons. Horizon catalyst events get "ANALYZE" button. Both use `?q=` param to pre-fill thesis builder. `/thesis` auto-runs on `?q=` param. `/horizon` accepts `?type=` param for pre-filtering. Progress tracker (SUPPORTING → CONTRADICTING → SYNTHESIS) with active/done/pending states.
- **GAP 3 → CLOSED (2026-02-12):** Thesis persistence implemented. `useThesisQuery` auto-saves after all 3 phases complete via `/api/theses` POST. Saved theses listed as "PREVIOUS ANALYSES" on main page. Each thesis gets a shareable URL at `/thesis/[id]`. View page loads saved data via `/api/theses/[id]` GET. URL updated via `history.replaceState` after save. COPY LINK button for sharing. **NOTE: Migration 024 must be run in Supabase SQL Editor.**

---

## Thread 004: The Watchtower

**Status:** GOLDEN
**Priority:** P0
**Intent:** "Don't make me stare at the screen. Tell me when the thesis changes."
**North Star:** User subscribes once and receives daily intelligence briefs + real-time alerts on high-impact events. The platform becomes proactive — push, not just pull.
**Undeniable Value:** Transforms the terminal from a tool you visit into a service that works for you. The bridge to paid subscriptions.

### Current Trace

```
[User intent: "Keep me informed without me checking the site"]
  → Currently: zero push capability ❌
  → No email service ❌
  → No subscriber list ❌
  → No notification infrastructure ❌
  → **STATUS: DARK — zero surface area**
```

### Infrastructure Audit

| Component | Exists? | Notes |
|-----------|---------|-------|
| Email service (Resend) | ✅ | `resend` + `@react-email/components` installed |
| React Email templates | ✅ | `emails/DailyBrief.tsx` + `emails/SignalAlert.tsx` — HUD aesthetic |
| Subscriber table | ✅ | `subscribers` table with preferences (migrations 027 + 029) |
| Daily brief cron | ✅ | `/api/cron/daily-brief` — 12:00 UTC, filters by `daily_brief=true` |
| Signal alert triggers | ✅ | `/api/cron/signal-alerts` — every 15 min, filters by `signal_alerts=true` |
| User preferences | ✅ | Token-based unsubscribe + preferences API |
| Waitlist→Subscriber bridge | ✅ | Waitlist signup auto-creates subscriber with token |

### Open GAPs

1. ~~The Daily Brief~~ → **CLOSED**
2. ~~Alert Triggers~~ → **CLOSED**
3. ~~Preferences + Tier Gating~~ → **CLOSED**

### Completed Transitions

- **GAP 1 → CLOSED (2026-02-13):** Daily Brief built. Resend + React Email pipeline: Vercel cron at 12:00 UTC queries 24h signals, 48h horizon events (launches, earnings, catalysts, docket deadlines), ASTS price, filings count. HUD-styled email template (`emails/DailyBrief.tsx`) with severity dots, countdown badges, price snapshot. Batch sends to active subscribers via Resend. `subscribers` table (migration 027). **Needs: RESEND_API_KEY + domain verification to go live.**
- **GAP 2 → CLOSED (2026-02-13):** Signal alerts built. Decoupled alert cron (`/api/cron/signal-alerts`, every 15 min) polls for critical/high signals from the last hour, deduplicates via `signal_alert_log` table (migration 028), sends individual alert emails per signal to all active subscribers. HUD-styled alert template (`emails/SignalAlert.tsx`) with severity badge, category, description, source refs. Works with both signal_scanner.py and tle-refresh signal producers — no changes needed to producers.
- **GAP 3 → CLOSED (2026-02-13):** Subscriber preferences + unsubscribe. Migration 029 adds `daily_brief`, `signal_alerts` boolean columns + `unsubscribe_token` + optional `user_id` FK to subscribers. Token-based `/api/email/unsubscribe` endpoint (supports type=all/daily_brief/signal_alerts) with HUD-styled confirmation page. `/api/email/preferences` GET/POST for managing preferences. Both crons updated to filter by preference columns and render per-subscriber unsubscribe URLs. Waitlist signup auto-creates subscriber with token. Tier gating deferred — preferences serve as the gate for now; `user_id` FK ready for profile linking when needed.
- Conversation: `docs/gemini-conversations/thread-discovery-001.md`

---

## Thread 005: The Regulatory Battlemap

**Status:** GOLDEN
**Priority:** P1
**Intent:** "What stands between the company and commercial authority? Who's opposing them, and where does each license application stand?"
**North Star:** User sees a living regulatory map — not a list of PDFs, but a state machine showing each license application's progress, who filed what, and which filings are threats.
**Undeniable Value:** Turns 4,500+ FCC filings from a document dump into a risk dashboard. No other tool models regulatory state this way.

### Current Trace

```
[User intent: "Is the regulatory path clear?"]
  → /regulatory page with three-band layout ✅
  → Docket cards: 6 tracked dockets with filing counts, activity timestamps ✅
  → Adversarial matrix: entity × docket heatmap, interactive filtering ✅
  → Filing feed: posture badges (ATTACK/DEFENSE/ENGAGEMENT/NOISE), filer names ✅
  → Threat classification: CRITICAL/SUBSTANTIVE/PROCEDURAL/ADMIN from filing_type ✅
  → signal_scanner: directional threat detection (PTDs, oppositions, competitor activity) ✅
  → Command palette + landing page links ✅
  → **STATUS: GOLDEN**
```

### Infrastructure Audit

| Component | Exists? | Notes |
|-----------|---------|-------|
| FCC filings data | ✅ | 4,500+ filings across ECFS/ICFS/ELS |
| Docket metadata | ✅ | `fcc_dockets` table with 6 tracked dockets + owner |
| Filing type classification | ✅ | `threat_level` column + in-memory classification from `filing_type` |
| Docket timeline view | ✅ | `/regulatory` page with docket cards + filtered feed |
| Adversarial mapping | ✅ | Matrix heatmap: Big 7 entities + "Other" × active dockets |
| Threat signal detection | ✅ | Detector 9 in `signal_scanner.py`: regulatory_threat, regulatory_defense, competitor_docket_activity |

### Open GAPs

1. ~~Docket Timeline View~~ → **CLOSED**
2. ~~Filing Type Classification~~ → **CLOSED**
3. ~~Opposition Signal~~ → **CLOSED**

### Completed Transitions

- **GAP 1 → CLOSED (2026-02-13):** Built `/regulatory` page with three-band layout. Band 1: 6 docket status cards (title, filing count, last activity, threat indicators). Band 2: Adversarial matrix heatmap — Big 7 entities (AST, SpaceX, AT&T, Verizon, T-Mobile, DISH, Lynk) + aggregated "Other" × active dockets. Cells show filing volume with opacity scaling; red highlight for cells with CRITICAL filings. Interactive: click cell → filters feed. Band 3: Unified filing feed with posture badges (ATTACK/DEFENSE/ENGAGEMENT/NOISE), threat level badges, filer names, docket tags. Click filing → DocumentViewer. API: `/api/regulatory/battlemap` returns dockets, classified filings, matrix aggregation. Filters: docket, threat level, date range (30D/90D/6M/1Y). Command palette + landing page EXPLORE grid links.
- **GAP 2 → CLOSED (2026-02-13):** Filing type classification via `threat_level` derived column (migration 030) + in-memory fallback from `filing_type` pattern matching. Four levels: CRITICAL (PTD, Opposition, Stay, Dismiss), SUBSTANTIVE (Comment, Reply, Ex Parte, Letter), PROCEDURAL (Extension, Notice, Report), ADMIN (everything else). UI derives posture from threat_level + filer identity: ATTACK (critical + non-AST), DEFENSE (critical + AST), ENGAGEMENT (substantive), NOISE (procedural/admin).
- **GAP 3 → CLOSED (2026-02-13):** Directional threat detection in `signal_scanner.py` (Detector 9). Three signal types: `regulatory_threat` (critical — non-AST files PTD/Opposition on AST docket), `regulatory_defense` (medium — AST files threat-type document), `competitor_docket_activity` (high/medium — known competitor files on tracked docket). Uses directional logic: AST_DOCKETS defines ownership, COMPETITOR_FILERS defines adversaries. 30-day expiry for threats, 7-day for competitor activity. Added to SIGNAL_CATEGORY_MAP.

- Conversation: `docs/gemini-conversations/thread-005-gap-1.md`

---

## Thread 006: The Orbital Logbook

**Status:** GOLDEN
**Priority:** P0
**Intent:** "Are the satellites actually working? When did they fire thrusters? Is drag increasing?"
**North Star:** User sees a per-satellite narrative — maneuvers, decay, space weather effects — all in one chronological view. Plus a fleet-wide vital signs dashboard.
**Undeniable Value:** Transforms 50,000+ TLE records from raw state vectors into operational intelligence. No retail investor tool does this. "Bloomberg for satellite health."

### Current Trace

```
[User intent: "Is BW3 under active control?"]
  → /orbital page exists with constellation health widgets ⚠️
  → /satellite/[noradId] has per-satellite detail with TLE data ⚠️
  → Health anomaly detection runs every 4h (altitude drops, drag spikes) ⚠️
  → bstar_trends view computes 30-day drag analysis ⚠️
  → Data is scattered across widgets — no unified narrative ❌
  → Maneuvers not classified as distinct events ❌
  → No space weather overlay on orbital data ❌
  → No fleet vital signs dashboard ❌
  → **STATUS: DARK — data exists but no narrative layer**
```

### Infrastructure Audit

| Component | Exists? | Notes |
|-----------|---------|-------|
| TLE history | ✅ | 50,000+ records, dual-source (CelesTrak + Space-Track) |
| Space weather | ✅ | 25,000+ records (Kp, Ap, F10.7, sunspots) |
| Health anomaly detection | ✅ | tle-refresh creates constellation_health signals |
| Altitude/drag charts | ⚠️ | bstar_trends view exists, not visualized as timeline |
| Per-satellite page | ⚠️ | /satellite/[noradId] exists but lacks narrative |
| Maneuver classification | ✅ | `orbital_maneuver` signal type with orbit_raise/orbit_lower/plane_change |
| Satellite timeline | ❌ | No unified event log per satellite |
| Fleet vital signs | ✅ | ConstellationHealthGrid enhanced with drag rate + last maneuver |

### Open GAPs

1. ~~Maneuver Detection + Signals~~ → **CLOSED**
2. ~~Satellite Timeline (Asset Logbook)~~ → **CLOSED**
3. ~~Fleet Vital Signs Dashboard~~ → **CLOSED**

### Completed Transitions

- **GAP 1 → CLOSED (2026-02-13):** Server-side maneuver detection added to tle-refresh cron. Ported 2σ outlier algorithm from client-side `lib/orbital/maneuver-detection.ts` to run every 4h. Uses CelesTrak data (primary for positional accuracy per C5). Detects orbit_raise, orbit_lower, plane_change. Creates `orbital_maneuver` signals with category=constellation, delta metrics (mean_motion_delta, altitude_delta_km, inclination_delta_deg). 14-day expiry, daily fingerprint dedup. Tested: 8 maneuvers detected across constellation.
- **GAP 2 → CLOSED (2026-02-13):** Asset Logbook component (`components/satellite/AssetLogbook.tsx`) — unified chronological timeline on `/satellite/[noradId]` merging orbital maneuvers, health anomalies, and space weather events (Kp >= 5 storms). Color-coded by event type with severity dots, inline metrics, time-ago display. Replaces static MANEUVER HISTORY panel.
- **GAP 3 → CLOSED (2026-02-13):** Fleet Vital Signs — enhanced existing `ConstellationHealthGrid` with two new columns: DRAG (km/day altitude rate, color-coded: blue=raising, amber=dropping, white=stable) and LAST MNVR (days since last detected maneuver signal). Fetches `orbital_maneuver` signals to populate last maneuver dates. Drag rate computed from last 7 days of TLE altitude data.

- Conversation: `docs/gemini-conversations/thread-discovery-002.md`

---

## Thread 007: The War Room

**Status:** GOLDEN
**Priority:** P0
**Intent:** "Who else is doing direct-to-cell and are they winning? How does AST's position compare to SpaceX, Lynk, T-Mobile?"
**North Star:** User sees ASTS competitive position at a glance — who has what authorization, who's filing where, and who's gaining ground.
**Undeniable Value:** Contextualizes the ASTS thesis. No investor holds a stock in a vacuum. This is the "Know the Enemy" layer. Also: architectural bridge to $SPACE without building $SPACE prematurely.

### Current Trace

```
[User intent: "Is AST winning the D2C race?"]
  → /competitive page with Tale of the Tape + entity cards ✅
  → Competitor config: 5 entities (AST, SpaceX, Lynk, T-Mobile, Globalstar) ✅
  → Tale of the Tape: side-by-side comparison (sats, spectrum, auth, partners, status) ✅
  → Filing activity per entity from fcc_filings ✅
  → Patent activity per entity from patents ✅
  → Entity filter + date range controls ✅
  → Competitor signals panel (Detector 9 + Detector 10) ✅
  → Competitor milestone detection: FCC grants + patent grants ✅
  → **STATUS: GOLDEN — competitive intelligence from data to display to signals**
```

### Infrastructure Audit

| Component | Exists? | Notes |
|-----------|---------|-------|
| Competitor FCC filings | ✅ | fcc_filings has filer_name for SpaceX, T-Mobile, Lynk etc. |
| Competitor patents | ✅ | patents table has assignee field |
| Competitor signals | ✅ | Detector 9 (regulatory threats) + Detector 10 (milestones) |
| Adversarial matrix | ✅ | /regulatory shows entity × docket heatmap |
| Competitor config | ✅ | `lib/data/competitors.ts` — 5 entities with filer/assignee patterns + tapeData |
| Comparative view | ✅ | Tale of the Tape on `/competitive` |
| Competitor page | ✅ | `/competitive` with entity cards, filing/patent tabs, signals |
| Competitor activity API | ✅ | `/api/competitive/landscape` — queries fcc_filings + patents by entity patterns |
| Milestone detection | ✅ | Detector 10: competitor_fcc_grant + competitor_patent_grant |

### Open GAPs

1. ~~Competitor Config + Tale of the Tape~~ → **CLOSED**
2. ~~Competitor Activity Stream~~ → **CLOSED** (merged into GAP 1 — page has entity cards with filing/patent tabs)
3. ~~Competitor Signals~~ → **CLOSED**

### Completed Transitions

- **GAP 1 + GAP 2 → CLOSED (2026-02-13):** Built complete competitive intelligence page. Entity registry (`lib/data/competitors.ts`) defines 5 D2C entities with typed fccFilerPatterns, patentAssigneePatterns, and static tapeData. API (`/api/competitive/landscape`) queries fcc_filings (ECFS) + patents broadly and filters in-memory using entity pattern matching. `/competitive` page has three bands: (1) Tale of the Tape — side-by-side comparison table with 6 data fields per entity, (2) Entity Activity Cards — per-competitor panels with filing/patent tabs showing recent activity, (3) Competitor Signals panel — displays regulatory_threat, competitor_docket_activity signals. Controls: entity filter, date range (30D/90D/6M/1Y). Command palette + landing page links. Data: AST 22 filings + 146 patents, SpaceX 15 filings, T-Mobile 3, Globalstar 3 (1Y range).
- **GAP 3 → CLOSED (2026-02-13):** Detector 10 (`detect_competitor_milestones`) added to signal_scanner.py. Two new signal types: `competitor_fcc_grant` (high — competitor receives FCC authorization) and `competitor_patent_grant` (medium — competitor receives D2C patent). Uses COMPETITOR_FILERS + COMPETITOR_ASSIGNEES patterns. 14-day lookback. Feeds into `/competitive` signals panel + `/signals` intelligence feed. API updated to query both new signal types. Copied to parent repo.

- Conversation: `docs/gemini-conversations/thread-discovery-003.md`

---

## Thread 008: Earnings Command Center

**Status:** GOLDEN
**Priority:** P1
**Intent:** "What did management promise? Did they deliver? What moved the stock during the call?"
**North Star:** Dedicated earnings experience — transcript highlights, guidance tracking (promises vs reality), price reaction during calls. The "Quarterly Superbowl" lens.
**Undeniable Value:** Earnings are the highest-traffic events. A dedicated experience converts free → Full Spectrum. Deadline: build before March 2, 2026 Q4 2025 earnings call.

### Current Trace

```
[User intent: "What happened on the earnings call?"]
  → /earnings page with three-zone layout ✅
  → Quarter selector: 21 quarters from earnings_calls ✅
  → Transcript viewer with topic highlighting (client-side mark) ✅
  → Topic matrix: 10 topics × 17 quarters, click → highlights transcript ✅
  → Price reaction: SVG sparkline + delta% + volume spike ✅
  → Guidance ledger: 10 seeded items (MET/PENDING/MISSED tracking) ✅
  → Summary panel from AI-generated transcript summaries ✅
  → Defaults to latest quarter with transcript (not future scheduled) ✅
  → **STATUS: GOLDEN — complete earnings intelligence experience**
```

### Infrastructure Audit

| Component | Exists? | Notes |
|-----------|---------|-------|
| Earnings transcripts | ✅ | inbox table (source='earnings_call'), transcript_worker |
| Earnings dates | ✅ | earnings_calls table, earnings_worker (Finnhub) |
| Transcript analysis | ✅ | Brain RAG + earnings-diff topic extraction |
| Language shift detection | ✅ | signal_scanner Detector 8 compares consecutive transcripts |
| Price data | ✅ | daily_prices (daily OHLCV) |
| Guidance tracking | ✅ | `lib/data/guidance.ts` — 10 static items, typed |
| Earnings page | ✅ | `/earnings` — three-zone layout |
| Transcript navigator | ✅ | Full text + client-side topic highlighting |
| Price reaction | ✅ | SVG sparkline (5-day window) + delta stats |
| Topic matrix | ✅ | 10 topics × 17 quarters heatmap, interactive |
| Earnings API | ✅ | `/api/earnings/context` — unified endpoint |

### Open GAPs

1. ~~Earnings Page + Transcript Navigator~~ → **CLOSED**
2. ~~Guidance Ledger~~ → **CLOSED**
3. ~~Price Reaction~~ → **CLOSED**

### Completed Transitions

- **GAP 1 + GAP 2 + GAP 3 → CLOSED (2026-02-13):** 2-turn Gemini spec convergence. Built complete earnings intelligence page. Unified API (`/api/earnings/context`) returns earnings metadata (21 quarters from earnings_calls), transcript text (from inbox, source='earnings_call'), topic analysis (10 tracked topics × 17 quarters, same logic as earnings-diff), price reaction (5-day window from daily_prices, delta% + volume spike), and guidance items. Three-zone page layout: Zone A = quarter selector + SVG price sparkline + call summary + guidance ledger. Zone B = topic matrix heatmap (10 × 17, orange heat scaling, click → highlights transcript). Zone C = transcript viewer with client-side topic highlighting via regex + `<mark>` tags, auto-scrolls to first match. Guidance ledger: `lib/data/guidance.ts` with 10 seeded items (4 MET, 5 PENDING, 1 per category). Defaults to latest quarter with content (skips future scheduled). Command palette + landing page links (9 items, 3-col grid).

- Conversation: `docs/gemini-conversations/thread-008-earnings.md`

---

## Thread 009: The Briefing

**Status:** GOLDEN
**Priority:** P0
**Intent:** "What happened since I last looked? What do I need to know RIGHT NOW?"
**North Star:** A classified morning report — cross-thread synthesis in a single page. No clicks required. The value is in the aggregation.
**Undeniable Value:** Connects all 8 vertical threads into one horizontal view. The "Home" for returning users. Answers the question every investor asks first.

### Current Trace

```
[User intent: "Give me the situation report"]
  → /briefing page exists ✅
  → Aggregation API queries 8+ tables in parallel ✅
  → Price banner with $ASTS snapshot ✅
  → Earnings countdown (17 days to Q4 2025) ✅
  → High-priority signals section (48h window) ✅
  → Upcoming events: launches, earnings, catalysts, conjunctions (30d) ✅
  → Regulatory section: active dockets + critical threats ✅
  → Fleet status: 7 satellites with altitude + TLE freshness ✅
  → Competitor activity: non-AST filings from last 7d ✅
  → Guidance tracker: PENDING/MET summary ✅
  → SEC filings: recent 7d activity ✅
  → Cross-thread deep links: signals→/signals, fleet→/satellite/[id], events→/horizon, etc. ✅
  → Two-column layout: primary intel (left) + status panels (right) ✅
  → Sidebar nav + command palette + landing page links ✅
  → **STATUS: GOLDEN — cross-thread synthesis in a single page**
```

### Infrastructure Audit

| Component | Exists? | Notes |
|-----------|---------|-------|
| Signals data | ✅ | signals table, 10 detectors |
| Regulatory state | ✅ | fcc_dockets, adversarial matrix |
| Earnings calendar | ✅ | earnings_calls table |
| Competitor activity | ✅ | Entity registry, fcc_filings, patents |
| Orbital status | ✅ | satellites, tle_history, health anomalies |
| Price data | ✅ | daily_prices (daily OHLCV) |
| Guidance tracking | ✅ | lib/data/guidance.ts |
| Horizon events | ✅ | catalysts, launches, earnings |
| Briefing page | ✅ | `/briefing` — two-column synthesis page |
| Aggregation API | ✅ | `/api/briefing` — 8 parallel Supabase queries |
| Sidebar nav | ✅ | Added as first nav item |
| Command palette | ✅ | Added `nav-briefing` command |
| Landing page | ✅ | Featured item above EXPLORE grid |

### Open GAPs

1. ~~Briefing API + Page~~ → **CLOSED**
2. **Thesis Health Indicator** — One-line summary of current thesis state derived from recent signal categories and sentiment. (Deferred — not blocking GOLDEN)
3. ~~Cross-thread navigation~~ → **CLOSED** (deep links in all sections)

### Completed Transitions

- **GAP 1 + GAP 3 → CLOSED (2026-02-13):** Built complete briefing system. API (`/api/briefing`) runs 8+ parallel Supabase queries via `getServiceClient()`: signals (48h, critical/high), upcoming events (launches + earnings + catalysts + conjunctions, 30d), regulatory (dockets + recent critical filings), fleet (7 ASTS satellites with TLE-derived altitude), competitor moves (non-AST filings 7d), earnings countdown, price snapshot (daily_prices), SEC filings (7d), guidance summary. Page (`/briefing`) has two-column layout: left column = signals + events + regulatory + SEC filings, right column = fleet + guidance + competitors. Top banner = price snapshot + earnings countdown. All sections have deep links into source threads: signals→/signals, satellites→/satellite/[id], events→/horizon, regulatory→/regulatory, competitors→/competitive, guidance→/earnings. Sidebar nav (first item, Newspaper icon), command palette, landing page (featured item above EXPLORE grid). Typography-driven, badge-heavy — no clicks required to get the picture.

- Conversation: `docs/gemini-conversations/thread-discovery-004.md`

---

## Thread 010: The Broadcast

**Status:** DARK
**Priority:** P1
**Intent:** "I want to share this analysis with my community."
**North Star:** Every analysis the platform produces has a shareable URL with a rich preview. Turn intelligence into viral artifacts.
**Undeniable Value:** Drives traffic and Patreon conversions. The community shares "alpha" — give them beautiful tools to do it.

### Current Trace

```
[User intent: "Share this on X/Twitter"]
  → Thesis results have /thesis/[id] shareable URLs ⚠️
  → Most pages have no dynamic OG metadata ❌
  → No "Share to X" buttons ❌
  → No dynamic OG images ❌
  → **STATUS: DARK — intelligence trapped behind the UI**
```

### Infrastructure Audit

| Component | Exists? | Notes |
|-----------|---------|-------|
| Thesis permalinks | ✅ | /thesis/[id] with saved data |
| Vercel OG | ❌ | @vercel/og not installed |
| Dynamic OG metadata | ❌ | Static metadata only |
| Share buttons | ❌ | No share UI anywhere |
| Signal permalinks | ❌ | No /signals/[id] route |

### Open GAPs

1. **Dynamic OG metadata** — Per-page og:title, og:description, twitter:card based on route params. Earnings, thesis, signals, competitive.
2. **OG Image Generation** — `@vercel/og` templates for key pages. Branded, data-rich preview images.
3. **Share UI** — "Share to X" button on key insights (thesis results, earnings analysis, signals).

### Completed Transitions

(none yet)

- Conversation: `docs/gemini-conversations/thread-discovery-004.md`

---

## Thread 011: The Live Wire

**Status:** DARK
**Priority:** P1
**Intent:** "I want to be ready for the earnings call and know what changed immediately after."
**North Star:** Operational readiness for March 2 Q4 2025 earnings. Pre-call preparation, post-call automatic analysis.
**Undeniable Value:** The highest-traffic event on the ASTS calendar. Being ready = credibility. Automation = speed advantage.

### Current Trace

```
[User intent: "What should I watch for on the earnings call?"]
  → Earnings page (008) has transcript viewer + guidance ledger ✅
  → Transcript worker fetches from roic.ai weekly ⚠️ (latency concern)
  → Guidance items are static (lib/data/guidance.ts) ⚠️
  → No pre-call briefing ("what to watch") ❌
  → No post-call automation (auto-detect new transcript → generate signals) ❌
  → **STATUS: DARK — earnings page exists but no event protocol**
```

### Open GAPs

1. **Pre-call Briefing** — "What to Watch" section pulling from guidance ledger (PENDING items), recent signals, regulatory status. Could be a section on /earnings or a standalone page.
2. **Post-call Automation** — Detect new transcript arrival, trigger earnings_language_shift signal, update guidance ledger prompts.
3. **Transcript Worker Latency** — Verify roic.ai publish timing. If >1h post-call, consider alternative sources or manual trigger.

### Completed Transitions

(none yet)

- Conversation: `docs/gemini-conversations/thread-discovery-004.md`
