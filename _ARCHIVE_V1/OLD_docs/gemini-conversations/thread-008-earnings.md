# Thread 008: Earnings Command Center

## CLAUDE (turn 1)

### Context

Thread 008 is DARK. The goal: dedicated earnings experience before March 2 Q4 2025 earnings call. Here's what exists:

**Data already captured:**
- `inbox` table: 10+ quarters of full earnings transcripts (Q3 2021 → Q4 2025), fetched from roic.ai via transcript_worker, embedded in brain_chunks
- `earnings_calls` table: dates, fiscal_year/quarter, status, fields for webcast_url, transcript, summary, key_points, guidance, notable_quotes (most unpopulated)
- `daily_prices` table: complete OHLCV from IPO (2021-04-07 → present)
- Signal scanner Detector 8: earnings_language_shift (compares consecutive quarter narratives)

**APIs already built:**
- `/api/widgets/earnings-diff` — extracts 10 tracked topics per transcript, generates Q/Q diffs with direction (up/down/new/dropped), narrative shift summaries. Returns snapshots + diffs for last 8 quarters.
- `/api/horizon` — includes earnings_calls in timeline events
- `/api/cron/daily-brief` — includes upcoming earnings in email

**What's missing:**
- No `/earnings` page (zero UI)
- No transcript viewer (transcripts exist but no way to read them)
- No guidance tracking (promises vs reality)
- No earnings-day price reaction view
- No quarter selector / historical navigation

### GAPs from THREADS.md

1. **Earnings Page + Transcript Navigator** — `/earnings` page with quarter selector, transcript viewer, Brain RAG-powered smart highlights
2. **Guidance Ledger** — Management promises vs outcomes (quarter, category, promise_text, status, evidence)
3. **Price Reaction** — Earnings-day price chart (daily candle + volume minimum)

### Constraints

- March 2 deadline (17 days). Must be shippable by then.
- Solo operator. Can't build everything — need to pick the highest-value surface.
- No intraday price data (only daily OHLCV). Can show daily candles around earnings dates.
- Transcripts are in `inbox` table (source='earnings_call'), full text stored in content_text.
- The earnings-diff API already does heavy lifting for topic analysis.

### Proposal

**GAP 1 is the core.** Build `/earnings` page with:
- Quarter selector (dropdown or timeline of all earnings dates from earnings_calls)
- Transcript viewer panel (full text from inbox, scrollable)
- Topic heatmap from earnings-diff (10 topics × N quarters, heat by mention count)
- Narrative shifts panel (what changed Q/Q)
- Summary panel (if summary exists in inbox)

**GAP 2 (Guidance Ledger) is a stretch goal.** Could seed it with hardcoded data from known guidance items rather than building a full extraction pipeline. Management has made specific promises: "5 BlueBirds by Sep 2024", "first commercial service 2025", "funded through commercial launch". Track these with a simple data file + display.

**GAP 3 (Price Reaction) is doable with daily data.** Show a 10-day window around each earnings date (5 before, 5 after) with OHLCV candles. Not intraday, but shows the reaction clearly.

### Questions for Gemini

1. Should the transcript viewer be full-text scroll or Brain RAG-powered highlights? Full text is simpler but walls of text aren't useful. RAG highlights need a query — could default to "key themes" extraction.
2. For the topic heatmap: should it be the full 8-quarter × 10-topic matrix, or focus on the latest Q/Q diff with expandable history?
3. Is the Guidance Ledger worth building as a static data file for March 2, or should we skip it entirely and focus on transcript + price?
4. Page layout: single scrollable page (like /regulatory) or tabbed interface (like /competitive entity cards)?

## GEMINI (turn 1)

### Decisions on Questions

1. **Transcript Viewer: Structured Reader.**
   - "Wall of text" is useless. Pure RAG summaries are often too abstract. The "AlphaSense" pattern is best: Full text on the right, *extracted topics* as a navigation rail on the left.
   - Render the full text. Use the existing `/api/widgets/earnings-diff` topics as the navigation rail. Clicking a topic executes a client-side search/highlight for that term in the text view. Do not rely on live RAG for the view itself — latency is the enemy of the HUD aesthetic.

2. **Topic Heatmap: Full Matrix (Sparkline View).**
   - Context is king. Knowing "Direct-to-Device" was mentioned 50 times this quarter is meaningless without knowing it was 0 times two years ago.
   - Show the 8-quarter history. A dense matrix (Rows = Topics, Columns = Quarters, Cell = Count/Intensity) fits the "Bloomberg-grade" density we want.

3. **Guidance Ledger: Static JSON (Manual).**
   - Automated extraction of promises is error-prone and high-effort. For a single-stock terminal, the truth is finite. There are fewer than 15 critical promises in ASTS history.
   - Create `data/guidance.json`. Curate it manually. Display it programmatically. This ensures 100% accuracy for the "Management Trust Score" without building a fragile pipeline.

4. **Layout: The "Earnings Brief" (Single View).**
   - Tabs hide data. A cockpit shows status at a glance.
   - Three-pane dashboard. Top: Macro (Price reaction + Guidance). Middle: Trends (Topic Matrix). Bottom: Detail (Transcript Reader).

### Architecture Specification

#### 1. Data Structure: Guidance
Create `lib/data/guidance.ts`. Source of truth for the Ledger.
```typescript
type GuidanceStatus = 'PENDING' | 'MET' | 'MISSED' | 'DELAYED';

interface GuidanceItem {
  id: string;
  quarter_promised: string; // "2023-Q4"
  category: 'LAUNCH' | 'FINANCIAL' | 'COMMERCIAL' | 'REGULATORY';
  promise_text: string;     // "First 5 satellites launch by Sept"
  outcome_text?: string;    // "Launched Sept 12"
  status: GuidanceStatus;
  evidence_url?: string;    // Link to filing/press release
}
```

#### 2. Component: Price Reaction Chart
- Do not use TradingViewWidget. Use custom Canvas 2D engine.
- Data: 10-day window centered on Earnings Date.
- Visuals: X-Axis T-5 to T+5, center dashed orange line at T=0, daily OHLC candles, percentage move annotation (Close T-1 to Close T+1).

#### 3. Page Layout: `/earnings`
**Header:** Quarter Selector (Dropdown) | Date | Summary stats

**Zone A: Impact (Top Row)**
- Left: `PriceReactionChart` (The market's vote)
- Right: `GuidanceLedger` (The reality check). Filter guidance for items due/updated this quarter.

**Zone B: Narrative (Middle Row)**
- `TopicMatrix`: Rows = Topics, Columns = Last 8 Quarters, Cell = Count/Intensity. Click cell → updates Transcript Reader filter.

**Zone C: The Record (Bottom Row - Tall)**
- `TranscriptReader`: Left rail = topic index, Main area = full text with keyword highlighting. Cmd+F style for selected topic.

### Implementation Plan

1. Create `lib/data/guidance.ts` — seed with top 5-10 historic promises
2. Create `/api/earnings/context` — returns transcript, topic analysis, price window, earnings metadata
3. Build `/earnings/page.tsx` — three-zone layout
4. Build components: GuidanceLedger, PriceReaction, TopicMatrix, TranscriptReader

## CLAUDE (turn 2)

Strong spec. Mostly agree. A few adjustments:

### 1. Guidance Ledger location — `lib/data/guidance.ts` not JSON file

Agree on static data. But put it in `lib/data/guidance.ts` (same pattern as `lib/data/competitors.ts`) — typed, importable, no JSON parsing. C1 says "Parameters, not Products."

### 2. Price Reaction — skip the Canvas engine for this

The SGChart engine is built for time series with crosshair/animation. For a 10-day reaction view, a simple bar chart or stat display is cleaner:
- Show: closing price T-1, T, T+1
- Percentage move from close T-1 → close T+1
- Volume spike indicator
- Maybe a tiny sparkline, but not a full OHLC candle chart for 10 data points

Counter-proposal: simple stat row showing the reaction numbers, with an optional "EXPAND" to see the 10-day chart via SGChart. Start with the stat row — it's faster and more scannable.

### 3. Single API endpoint — agree

`/api/earnings/context` is the right approach. One fetch per quarter selection, returns everything the page needs:
- Earnings call metadata (from earnings_calls)
- Transcript text (from inbox)
- Topic analysis (from earnings-diff logic, inline)
- Price window (from daily_prices, 5 days before/after)
- Guidance items due that quarter (from static data)

### 4. TranscriptReader — simplify for v1

Full text + client-side highlight is the right call. Skip the left rail for v1 — just have the topic matrix above act as the filter. Clicking a topic in the matrix highlights all mentions in the transcript below. One component, not two.

### Revised build order:

1. `lib/data/guidance.ts` — 10 seeded guidance items
2. `/api/earnings/context` — unified endpoint
3. `/earnings` page — three zones:
   - Zone A: Quarter selector + price reaction stats + guidance status
   - Zone B: Topic matrix (8Q × 10 topics)
   - Zone C: Transcript with topic highlighting
4. Nav links (command palette + landing page)

Agree?

## GEMINI (turn 2)

Approved with one refinement:

**Price Reaction: SVG Micro-Chart, not stats-only.** A text-only stat row is insufficient for a "Bloomberg-grade" HUD. Price reaction is about *shape* and *gap*, not just a percentage. Build a `<PriceSparkline />` using simple SVG — 5 bars (T-2 to T+2), earnings date bar in orange, green/red for post-earnings delta.

**Final layout agreed:**
- Header: Quarter selector + PriceSparkline + reaction stats
- Body left (30%): GuidanceLedger (vertical list)
- Body right (70%): TopicMatrix (8Q × 10 topics, click → highlights transcript) + TranscriptViewer (full text with topic highlighting)

Execution order: guidance data → API → UI components → page assembly. Proceed.

## Agreed Spec Summary

Converged after 2 turns:
- `/earnings` page with quarter selector, three-zone layout
- `lib/data/guidance.ts` — static typed guidance items (5-10 seeded promises)
- `/api/earnings/context` — unified endpoint returning transcript, topics, price window, guidance
- PriceSparkline (SVG micro-chart, 5-day window)
- TopicMatrix (8Q × 10 topics heatmap, click → highlights transcript)
- TranscriptViewer (full text, client-side topic highlighting)
- GuidanceLedger (status cards: MET/MISSED/PENDING/DELAYED)
