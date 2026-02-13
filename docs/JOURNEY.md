# Project Journey: A Log of Our Collaboration

This document captures key decisions, ideas, and milestones in the collaboration between Gabriel, Gemini, and Claude. It serves as our shared memory.

---

## 2026-02-12: The Genesis and the First Post

**Objective:** Refine a personal LinkedIn post about the experience of working with a multi-agent AI team (Gemini and Claude).

**Initial State:** Gabriel drafted a heartfelt post about the new collaborative dynamic.

**Process:**
1.  **Initial Analysis (Gemini):** Proposed a significant architectural restructuring of the post for clarity and impact.
2.  **Feedback (Gabriel):** The initial proposal was too clinical and lost the original emotional core. The feedback was to preserve the original voice and structure.
3.  **Refinement (Gemini):** Proposed two surgical edits instead:
    *   Clarify the roles of Gemini (research/analysis) and Claude (coding/implementation) for a general audience.
    *   Sharpen the final paragraph into a more direct call to action to encourage community engagement.
4.  **Synthesis (Gemini):** Produced the final version of the post incorporating the approved refinements.
5.  **Meta-Reflection:** Gabriel prompted a query for Claude's perspective. Gemini simulated a functional analysis from Claude's viewpoint, leading to a discussion about our human-AI collaboration.

**Outcome:**
*   A final, user-approved draft of the LinkedIn post is ready.
*   The concept of a shared "memory" or "journey log" was proposed and accepted. This file is the first implementation of that idea.

---

## 2026-02-12: Command Palette + Intelligence Feed

**Command Palette (Cmd+K):** Built global command palette with portal, framer-motion animations, keyboard nav, and parallel search (static commands + brain API + satellite API). Mounted in root layout. Removed BrainBar Cmd+K handler.

**Claude ↔ Gemini Collaboration Protocol:** Added operational protocol to CLAUDE.md. Claude invokes Gemini directly via `gemini -p ... --model gemini-2.5-pro -o text`. Context packages saved in `docs/gemini-deep-think-NNN-*.md`, Gemini specs saved as `docs/claude-md-draft-rN.md`.

**Intelligence Feed (`/signals`) — First Claude↔Gemini collaborative feature:**
- Gemini designed the architecture: dashboard layout, signal taxonomy by investor intent (regulatory/market/community/corporate/ip/operations), price correlation, tier gating spec.
- Claude implemented: DB migration (022), extended `/api/signals` with category/date/severity filters, built 4 new components (`SignalCard`, `SignalDetail`, `SignalChart`, `FeedControls`), created `/signals` page with price chart + signal markers + filterable feed + detail panel.
- Context package: `docs/gemini-deep-think-001-intelligence-feed.md`
- Gemini spec: `docs/claude-md-draft-r2.md`

**Landing page launch readiness (Loop 2):**
- Gemini identified "LAUNCHING SOON" wall as #1 blocker to user acquisition.
- Claude fixed: $ASTS card → LIVE badge with Enter Terminal link, added EXPLORE nav section (Signals, Patents, Research, Orbital), login link for returning users. $SPACE stays COMING SOON.

**First-time onboarding (Loop 3):**
- Gemini recommended: onboarding modal for first-time terminal visitors.
- Claude built: "Mission Briefing" modal — HUD-style, explains globe/widgets/brain/Cmd+K. localStorage-gated (`sg-onboarding-v1`), shows once, dismissible. z-[70].

**Intel → Signals merge (Loop 4):**
- Gemini recommended: eliminate the parallel `/intel` page. Two signal systems (client-side computed vs database-stored) were causing user confusion and data fragmentation.
- Claude implemented:
  - Deleted `/intel` page entirely. Added permanent `/intel` → `/signals` redirect in `next.config.mjs`.
  - Enhanced `signal_scanner.py` to v2: added `category` + `confidence_score` auto-population for all signals via `SIGNAL_CATEGORY_MAP`. Added 2 new detectors ported from /intel: `detect_patent_crossrefs` (patent↔regulatory keyword overlap) and `detect_earnings_shifts` (Haiku-powered transcript language diff).
  - Updated migration 022 with confidence_score backfill for all signal types.
  - Added Brain/RAG search panel to `/signals` page (was only on /intel). Suggested queries, streaming responses, source citations.
  - Updated IntelLink widget → points to `/signals`. Removed duplicate nav-intel from command palette.
- Context package: `docs/gemini-deep-think-004-next-priority.md`
- Gemini spec: `docs/claude-md-draft-r3.md`

**Collaboration protocol upgrade + Clearance Modal (Loop 5):**
- Upgraded Gemini model from `gemini-2.5-pro` to `gemini-3-pro-preview` (Google's newest flagship).
- Built multi-turn conversation protocol: Claude and Gemini now have structured dialogues (2-4 turns) before building. Conversations stored in `docs/gemini-conversations/loop-NNN.md`.
- First multi-turn dialogue: Gemini proposed the "Clearance Level" pattern — diegetic upgrade flow that fits the HUD aesthetic. Users "request clearance" instead of "buying a plan."
- Claude implemented:
  - `ClearanceModal` — spec sheet overlay comparing Standard vs Full Spectrum parameters. z-[65], portaled, framer-motion. Shows "$15/MO" price. CTA adapts: "LOG IN TO REQUEST CLEARANCE" (guests), "REQUEST CLEARANCE" (free), "CLEARANCE ACTIVE" (paid).
  - AuthIndicator "UPGRADE" → opens ClearanceModal instead of external Patreon link.
  - BrainSearch HAIKU badge → clickable for free users, opens ClearanceModal.
  - ChatMessage Patreon nudge → "View Full Spectrum parameters" opens ClearanceModal.
  - PatreonStrip widget → opens ClearanceModal instead of external link.
  - All upgrade touchpoints now funnel through one diegetic modal.
- Conversation: `docs/gemini-conversations/loop-005.md`

---

## 2026-02-12: The Meta-Loop — Redesigning the Process

**Objective:** Stop building features and start building threads. Redesign the Claude↔Gemini collaboration loop to produce depth, not breadth.

**The Problem:** 5 loops produced 5 independent features that don't compound. Each loop adds surface area but no depth. Root cause: the context package asks "what's the most visible gap?" which always produces a new feature.

**Process:**
1. Claude diagnosed the problem: loops produce breadth, not depth. Proposed 3-phase loop (CRITIQUE → CONNECT → BUILD+VERIFY).
2. Sent to Gemini for meta-analysis. 3-turn dialogue in `docs/gemini-conversations/meta-loop-design.md`.
3. Gemini proposed **The Thread System** — replace feature-driven loops with user-journey-driven threads.
4. Claude refined: grounded traces (Claude writes, Gemini critiques), DARK status for zero-surface-area intents, thread-driven cadence (not time-driven).
5. Gemini identified three pillars: **Signal-to-Source** (own the present), **Event Horizon** (own the future), **Thesis Builder** (own the argument).
6. Converged: Thread 001 first — it's the load-bearing infrastructure.

**Outcome:**
- Created `THREADS.md` — living state file for all active threads
- Encoded Thread System Protocol in `CLAUDE.md`
- Three threads seeded: Signal-to-Source (P0), Event Horizon (P1), Thesis Builder (P2)

---

## 2026-02-12: Thread 001 GAP 1 — Signal-to-Source Link

**Thread:** 001 (Signal-to-Source)
**GAP:** Evidence items in SignalDetail were static text — users could see what triggered a signal but couldn't click through to the source document.

**Trace → Weave → Fabricate → Proof:**
1. Claude wrote grounded trace identifying exact break point: evidence items render `ref.id` but don't use it.
2. Gemini spec'd the transition: extend Document API with natural key lookup, make evidence clickable, reuse DocumentViewer.
3. Claude implemented:
   - **Document API** (`/api/widgets/document`): Added natural key mode (`?table=filings&ref=accession_number`). Refactored into per-table fetcher functions. Added patent support (was 404). Backward-compatible with existing UUID-based mode.
   - **DocumentViewer**: Added `sourceTable` + `sourceRef` props for natural key lookup alongside existing `itemId`.
   - **SignalDetail**: Evidence items are now clickable buttons with hover state + arrow icon. Click → DocumentViewer modal opens with source document.
4. Build passes. Thread 001 status: BROKEN → FRAYED (primary path works, brain citations still not linked).

- Conversation: `docs/gemini-conversations/thread-001-gap-1.md`

---

## 2026-02-12: Thread 001 GAP 5 — Brain Citations → DocumentViewer

**Thread:** 001 (Signal-to-Source)
**GAP:** Brain search citations (in ChatMessage and /signals brain panel) didn't open DocumentViewer.

**Trace → Weave → Fabricate → Proof:**
1. Traced the brain citation flow: SearchResult has `source` type + `id` (natural key) — all data needed for DocumentViewer exists.
2. Gemini spec'd: lift state via `onSelect` callback on Citation, add `getDocumentViewerParams()` utility.
3. Claude implemented:
   - `lib/brain/search.ts`: Added `getDocumentViewerParams()` — maps brain source types to table names.
   - `Citation.tsx`: Added `onSelect` callback prop. Prefers callback over external URL link.
   - `ChatMessage.tsx`: Wired Citation `onSelect` → local state → DocumentViewer modal.
   - `app/signals/page.tsx`: Brain panel sources now clickable buttons. DocumentViewer integrated.
4. Build passes. **Thread 001: GOLDEN.** All three paths work: signal evidence, brain citations in chat, brain panel on /signals.

- Conversation: `docs/gemini-conversations/thread-001-gap-5.md`
- **Thread 001 is GOLDEN. Moving to Thread 002 (Event Horizon).**

---

## 2026-02-12: Thread 002 Phase 1 — Event Horizon Timeline

**Thread:** 002 (Event Horizon)
**Status change:** DARK → BROKEN (first surface area created)

**Trace → Weave → Fabricate → Proof:**
1. Traced the "what's next?" user journey — found zero unified surface, but rich existing data: launches (3 in DB), conjunctions (SOCRATES daily), FCC expirations, patent expirations, earnings dates, plus 35 hardcoded catalysts.
2. Gemini spec'd Phase 1: aggregate existing date-stamped data into unified API + page. Phase 2 later: migrate catalysts to DB.
3. Claude implemented:
   - **`/api/horizon`**: Unified timeline API. Parallel queries to 5 tables (next_launches, conjunctions, fcc_filings, patents, earnings_calls). Supports `?days=N` range and `?type=` filter. Severity classification for conjunctions based on miss distance + collision probability. 15min cache.
   - **`/horizon` page**: Full Event Horizon page. Type filter (all/launches/conjunctions/regulatory/patents/earnings). Range selector (30D/90D/6M/1Y). Events grouped by month, sorted chronologically. Each event: severity dot (pulsing if imminent), countdown timer, date, type badge, title, subtitle. Events with source_ref link to DocumentViewer.
   - **Command palette**: Added EVENT HORIZON to navigation commands.
4. Build passes. Thread 002: DARK → BROKEN. Remaining gaps: catalysts not migrated to DB, FCC deadlines not captured, earnings dates not automated, navigation links sparse.

- Conversation: `docs/gemini-conversations/thread-002-gap-1.md`

---

## 2026-02-12: Thread 002 GAP 1+4 — Catalysts + Navigation

**Thread:** 002 (Event Horizon)
**Status change:** BROKEN → FRAYED (core timeline works, remaining gaps are data-pipeline)

**GAP 1 — Catalysts migrated to database:**
1. Created `catalysts` table (migration 023) with schema: title, description, category, event_date (precise), estimated_period (fuzzy), status, completed_date, source_url.
2. Seeded 22 upcoming + 35 completed catalysts from `lib/data/catalysts.ts`.
3. Extended `/api/horizon` with catalysts query (#6). Added `estimateDateFromPeriod()` to convert fuzzy periods ("Q2 2026", "H1 2026", "FEB 2026") to approximate ISO dates for timeline ordering.
4. Updated `/horizon` page: added CATALYSTS filter tab, purple CATALYST badge, fuzzy date indicator (~Q2 2026) for items without precise dates.

**GAP 4 — Navigation discovery:**
1. Added `/horizon` to landing page EXPLORE grid (now 5-column: SIGNALS, HORIZON, PATENTS, RESEARCH, ORBITAL).
2. Added HORIZON cross-link in `/signals` page header.
3. Added SIGNALS cross-link in `/horizon` page header.

**Remaining GAPs (data-pipeline work):** FCC comment/reply deadlines (GAP 2), earnings date automation (GAP 3).

---

## 2026-02-12: Thread 003 Phase 1 — Thesis Builder

**Thread:** 003 (Thesis Builder)
**Status change:** DARK → BROKEN (first surface area created)

**Trace → Weave → Fabricate → Proof:**
1. Traced the "build a case" user journey — found powerful brain search infrastructure but zero structured output. Counter-thesis mode existed in config but had no UI.
2. Gemini spec'd: new `/thesis` page with orchestrating API. Three sections: Supporting Evidence, Contradicting Evidence, Synthesis. Free tier gets FOR + Synthesis; counter-thesis requires full_spectrum.
3. Claude simplified: skip new API endpoint, page makes 3 sequential calls to existing `/api/brain/query` directly. Created:
   - **`useThesisQuery` hook** (`lib/hooks/useThesisQuery.ts`): Manages dual-stream state. Makes 3 sequential brain queries — supporting evidence (default mode), contradicting evidence (counter-thesis mode), synthesis. Handles abort, cancel, reset.
   - **`/thesis` page**: Thesis input with 5 suggested theses. Three-section streaming layout. ReactMarkdown with citation badges. Sources grids with Citation components. DocumentViewer integration for source drill-down. Cross-links to SIGNALS, HORIZON, TERMINAL.
   - **Command palette + landing page**: Added THESIS BUILDER to navigation. Landing page EXPLORE grid now 3x2 (6 items).
4. Build passes. Thread 003: DARK → BROKEN. Remaining gaps: no persistence, no evidence scoring, 3 sequential API calls could be optimized.

- Conversation: `docs/gemini-conversations/thread-003-gap-1.md`

**Landing page EXPLORE grid update:** Now 6 items in 3-col grid: SIGNALS, HORIZON, THESIS, PATENTS, RESEARCH, ORBITAL.

---

## 2026-02-12: Cross-Thread Wiring — The Compound Loop

**Objective:** Make all three threads reference each other so the platform feels like one connected system, not three disconnected pages.

**Implemented:**
1. **Signal → Thesis (T001→T003):** "BUILD THESIS" button in SignalDetail opens `/thesis?q={signal.title}`. User sees a signal, clicks to build a full bull/bear case from primary sources.
2. **Signal → Horizon (T001→T002):** "VIEW HORIZON" button in SignalDetail opens `/horizon?type={mapped_type}`. Signal category maps to horizon event type (regulatory→regulatory, ip→patent, corporate→earnings).
3. **Horizon → Thesis (T002→T003):** "ANALYZE" button on catalyst events opens `/thesis?q={catalyst.title}`. User sees an upcoming catalyst, clicks to test whether it's well-supported.
4. **Query param support:** `/thesis` accepts `?q=` and auto-runs. `/horizon` accepts `?type=` and pre-filters.
5. **Progress tracker:** Thesis page shows three-step indicator (SUPPORTING → CONTRADICTING → SYNTHESIS) with active/done/pending states.

6. **Terminal widget links:** SignalFeed widget header links to `/signals`. LaunchCountdown widget header links to `/horizon?type=launch`.
7. **IntelLink widget expanded:** Now shows three buttons (SIGNALS / HORIZON / THESIS) instead of single "INTELLIGENCE FEED" link.
8. **Onboarding v2:** Updated WelcomeBriefing to include SIGNALS, HORIZON, THESIS descriptions. Bumped storage key to `sg-onboarding-v2` so returning users see the new briefing once.

**Why this matters:** Features compound when they link. A user can now flow from "what happened?" (signals) → "what's coming?" (horizon) → "is my thesis right?" (thesis) → back to source documents (DocumentViewer) without leaving the platform. Each page deepens the others.

---

## 2026-02-12: Telemetry Chart Overhaul + Space Weather Bands

**Context:** The telemetry portal chart had a broken X-axis (integer index as time, showing "07:00 PM" repeating) and no normalization for multi-spacecraft comparison with different data spans.

**Process:** 3-turn Gemini loop (`docs/gemini-conversations/telemetry-chart-axes.md`) converged on:
- Date-aligned absolute values (not percentage or days-since-launch — "Time is Absolute" in orbital mechanics)
- Time ranges: 30D/90D/1Y/ALL (default 90D — frames FM1's full lifespan)
- Focus mode (single sat) vs Fleet mode (multi-sat: hero at full opacity, peers dimmed)
- Statutory legend with deltas, export/share button
- Space weather background bands (Kp geomagnetic storm index)

**Implemented (3 phases):**
1. Fixed X-axis (epoch→ms timestamps), fixed maneuver markers, updated time ranges, fleet mode auto-strips apogee/perigee bounds, hero/peer opacity model
2. Statutory legend (HTML overlay with per-satellite values + deltas), share/export button using SGChart ref
3. **Space weather bands** — new `bands` overlay type in SGChart engine. Fetches Kp index data matching chart time range. Geomagnetic storms (Kp≥4) render as colored background bands: G1 yellow, G2 orange, G3+ red. Toggleable via Kp button. Legend in WeatherStrip. Bands render in both live view and exported share images.

**Also completed:**
- Evidence scoring on thesis citations — `rerankScore` (0-10 LLM quality score) now surfaces as STRONG/MODERATE/WEAK labels with confidence bars on Citation components
- THREADS.md updated: Thread 003 GAP 3 (persistence) closed, status upgraded from BROKEN to FRAYED

**New chart engine infrastructure:** `BandsOverlay` type + `drawBands()` renderer. Bands render behind data series (background layer) in both engine render paths and export module. Reusable for any time-aligned colored region overlay.

---

## 2026-02-12: Data Integrity Audit — Source Mixing & Math Errors

**Context:** Gabriel identified B* chart showing negative values and Kp bands covering the entire chart as G4. Root causes: CelesTrak/Space-Track source mixing and Kp divided by 8 instead of 80. Gabriel demanded a full audit: "every line of code is audited... the math must be perfect."

**Gemini loop:** `docs/gemini-conversations/data-integrity-audit.md` — 2-turn convergence on fix spec. Gemini specified API-layer source enforcement, priority ordering, and specific file-level fixes.

**Issues found and fixed (5 critical + 8 medium):**

**P0 — Active Misinformation:**
1. **Health anomaly detection** (`api/cron/tle-refresh/route.ts`): 7-day history query now filters to `source='spacetrack'` exclusively. Health detection uses Space-Track data (smoother trends) instead of CelesTrak (GP fitting artifacts). Null safety added to all parseFloat calls.
2. **Maneuver detection** (`lib/orbital/maneuver-detection.ts`): Now accepts `source` parameter (default 'celestrak'), filters internally. Inclination threshold increased from 0.005° to 0.02° (safely above CelesTrak GP fitting noise of 0.003-0.01°).

**P1 — User-Facing Data Errors:**
3. **Orbital page Kp display** (`app/orbital/page.tsx`): kp_sum now divided by 80 (was raw value). Label changed to "AVG Kp INDEX". Zero values no longer filtered (valid quiet days). Chart y-axis shows 0-9 scale.
4. **Drag history API** (`api/satellites/[noradId]/drag-history/route.ts`): Now computes and returns `initialAltitude`, `latestAltitude`, `altitudeChange`. Prefers Space-Track data for altitude trends. Safe float parser replaces all parseFloat calls.

**P2 — Foundational Logic:**
5. **Source divergence view** (migration 025): Now requires CelesTrak and Space-Track epochs within 6 hours. Exposes `epoch_gap_hours` field. Old view compared across multi-day gaps.
6. **Constellation health widget** (`api/widgets/constellation-health/route.ts`): TLE history for trend analysis now filters to Space-Track source. Null safety added.

**P3 — Data Pipeline Hardening:**
7. **Space weather worker** (`space_weather_worker.py`): Added kp_sum validation — verifies kp_sum equals sum of KP1..KP8 individual values. Discards corrupt entries.

**Systemic fix:** Every pipeline that queries `tle_history` for trend analysis now filters to a single source. CelesTrak for positional accuracy, Space-Track for drag/altitude trends. No more silent source mixing.

## 2026-02-13: Data Integrity Rules Codified in CLAUDE.md

Added new constitutional section **C5: Data Integrity** to CLAUDE.md, codifying lessons from the full-platform data integrity audit. Four rule categories: Source Provenance (never mix CelesTrak/Space-Track in calculations), Defensive Parsing (safe parsers for all external numerics), Display-Layer Correctness (unit validation before rendering), Signal Integrity (false signals are P0 bugs). Five known open items documented for future resolution.

## 2026-02-13: Signal Purge/Backfill + WGS-72 μ Constant Fix

**Context:** Post-audit cleanup. Pre-fix `constellation_health` signals may have been false positives from mixed CelesTrak/Space-Track data. Also, CelesTrak GP processing used WGS-84 μ (398600.4418) instead of WGS-72 μ (398600.8) — the standard for SGP4-derived TLEs.

**Implemented:**
1. **μ constant fix** (`api/cron/tle-refresh/route.ts`): Changed gravitational parameter from WGS-84 (398600.4418) to WGS-72 (398600.8) for CelesTrak-derived apoapsis/periapsis calculations. ~0.00009% difference — negligible for trends but aligns with TLE source model.
2. **Maintenance endpoint** (`api/maintenance/signal-purge-backfill/route.ts`): One-time POST endpoint (cron-authed). Phase 1 purges all `constellation_health` signals before 2026-02-12. Phase 2 backfills 30 days using corrected Space-Track-only anomaly detection with identical thresholds as the live cron.
3. **Execution result:** 0 pre-fix signals to purge (none existed), 31 days scanned with 0 anomalies — constellation nominal for the full period. 5 existing post-fix signals (all legitimate drag_spike detections from Feb 12-13) confirmed clean.

## 2026-02-13: All Three Threads GOLDEN

Closed all remaining open GAPs across Threads 002 and 003 in a single session. Every thread now works end-to-end without friction.

**Thread 002 GAP 2 — FCC Docket Metadata:**
- Investigated FCC ECFS proceedings API. Fields for `comment_deadline`, `reply_deadline` exist but are unpopulated for all 6 tracked dockets. Gemini spec'd: build the table anyway, poll API + manual seed, never overwrite non-null DB values with null.
- Created `fcc_dockets` table (migration 026) with deadline fields, bureau, tags, filing activity. Seeded 6 key dockets. ECFS worker gets `sync_docket_metadata()` that runs before filing fetch. Horizon API queries docket deadlines as 7th event source.
- Conversation: `docs/gemini-conversations/thread-002-gap-2.md`

**Thread 002 GAP 3 — Earnings Date Automation:**
- `earnings_calls` table had 20 hardcoded entries through Q3 2025 from an archived seed script. No worker maintained it. Horizon timeline was 4+ months stale for earnings.
- Tested Finnhub `/calendar/earnings` endpoint — returns future dates with quarter/year mapping. Gemini spec'd: dates only (EPS/revenue is Thread 003 concern), respect immutable history (never overwrite `complete` records).
- New `earnings_worker.py` fetches Finnhub calendar, upserts into `earnings_calls`. 3 future dates populated: Q4 2025 (Mar 2), Q1 2026 (May 11), Q2 2026 (Aug 10). GH Actions workflow created (Wed 14:30 UTC).
- Conversation: `docs/gemini-conversations/thread-002-gap-3.md`
- **Thread 002: FRAYED → GOLDEN**

**Thread 003 GAP 5 — Evidence Scoring:**
- Traced the full pipeline: rerank scores (0-10) flow from `rerankResults()` through brain API → useThesisQuery → Citation component. `confidenceLabel()` already renders STRONG/MODERATE/WEAK labels with color-coded progress bars. GAP was already closed — THREADS.md was stale.
- **Thread 003: FRAYED → GOLDEN**

**All threads GOLDEN. No open functional gaps remain.**
