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

**Status:** FRAYED
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
  → FCC expirations: ⚠️ sparse — only populated where expiration_date is set
  → patent expirations: ⚠️ many patents may not have expiration_date populated
  → earnings calls: ⚠️ manually populated, not automated
  → ~~GAP 1: Curated catalysts hardcoded~~ → **CLOSED** (migration 023 + API + UI)
  → **GAP 2: FCC comment/reply deadlines not captured by ECFS worker**
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
| Horizon API | ✅ | `/api/horizon` aggregates 6 sources (incl. catalysts), type filter + days range |
| Horizon page | ✅ | `/horizon` — full page with filters, month grouping, severity, countdown |
| DocumentViewer integration | ✅ | Events with source_ref clickable → opens document viewer |
| Launch data | ✅ | `next_launches` table — 3 known launches |
| Conjunction data | ✅ | `conjunctions` table — SOCRATES daily updates |
| FCC expiration data | ⚠️ | `fcc_filings.expiration_date` — sparse population |
| Patent expiration data | ⚠️ | `patents.expiration_date` — needs audit |
| Earnings data | ⚠️ | `earnings_calls.call_date` — manual only |
| Catalyst database | ✅ | `catalysts` table — migration 023, 22 upcoming + 35 completed seeded |
| Command palette link | ✅ | Added to navigation commands |

### Open GAPs

1. ~~Curated catalysts not in timeline~~ → **CLOSED** (migration 023 + API query + UI filter/badge)
2. **FCC comment/reply deadlines** — ECFS dockets have comment windows but workers don't capture them.
3. **Earnings date automation** — No worker discovers next earnings dates from SEC filings.
4. ~~Navigation discovery~~ → **CLOSED** (landing page EXPLORE grid, /signals↔/horizon cross-links)
5. ~~Depends on Thread 001~~ → **RESOLVED** (T001 is GOLDEN)

### Completed Transitions

- **Phase 1 → DONE (2026-02-12):** Built `/api/horizon` endpoint aggregating 5 sources (launches, conjunctions, FCC expirations, patent expirations, earnings). Built `/horizon` page with type filters, range selector (30D/90D/6M/1Y), month grouping, severity dots, countdown, type badges. Events with source refs link to DocumentViewer. Added to command palette navigation.
- **GAP 1 → CLOSED (2026-02-12):** Catalysts migrated to database. Created `catalysts` table (migration 023) with 22 upcoming + 35 completed items seeded from `lib/data/catalysts.ts`. API queries catalysts with `estimateDateFromPeriod()` for fuzzy dates. UI shows CATALYSTS filter tab, purple CATALYST badge, and fuzzy date indicator (~Q2 2026) for items without precise dates. **NOTE: Migration 023 must be run in Supabase SQL Editor.**
- **GAP 4 → CLOSED (2026-02-12):** Navigation discovery. Added /horizon to landing page EXPLORE grid (5-col). Added HORIZON cross-link in /signals header. Added SIGNALS cross-link in /horizon header. Both pages now cross-reference each other + TERMINAL.

---

## Thread 003: Thesis Builder

**Status:** BROKEN
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

[Gaps remaining]
  → **GAP 2: No thesis persistence** — can't save, share, or revisit a thesis
  → **GAP 3: No evidence scoring** — rerank scores exist but not surfaced
  → **GAP 4: Single-prompt optimization** — currently 3 sequential API calls, could be 1

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
| Save/annotate | ❌ | No persistent user documents or annotations |
| Evidence scoring | ❌ | Rerank scores available but not rendered |
| Depends on Thread 001 | ✅ | Source linking for evidence citations reuses T001 infrastructure |

### Open GAPs

1. ~~No structured output format~~ → **CLOSED** (three-section layout with streaming)
2. ~~Counter-thesis mode not in UI~~ → **CLOSED** (CONTRADICTING EVIDENCE section uses counter-thesis mode)
3. **No persistent briefings** — User can't save or revisit a thesis
4. ~~Depends on Thread 001~~ → **RESOLVED** (T001 is GOLDEN)
5. **No evidence scoring** — Rerank scores exist but aren't displayed to user
6. **Three sequential API calls** — Could be optimized to single prompt

### Completed Transitions

- **Phase 1 → DONE (2026-02-12):** Built `/thesis` page with thesis input + 5 suggested theses. Created `useThesisQuery` hook that makes 3 sequential brain queries (supporting evidence with default mode, contradicting evidence with counter-thesis mode, synthesis). Three-section streaming layout with ReactMarkdown + citation badges. Sources grids with Citation components. DocumentViewer integration for source drill-down. Free tier gets FOR + SYNTHESIS; counter-thesis requires full_spectrum. Added to command palette + landing page EXPLORE grid. Cross-links to SIGNALS, HORIZON, TERMINAL.
- **Cross-thread wiring → DONE (2026-02-12):** SignalDetail gets "BUILD THESIS" + "VIEW HORIZON" action buttons. Horizon catalyst events get "ANALYZE" button. Both use `?q=` param to pre-fill thesis builder. `/thesis` auto-runs on `?q=` param. `/horizon` accepts `?type=` param for pre-filtering. Progress tracker (SUPPORTING → CONTRADICTING → SYNTHESIS) with active/done/pending states.
