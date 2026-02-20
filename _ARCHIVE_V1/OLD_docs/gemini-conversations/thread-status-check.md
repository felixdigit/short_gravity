# Thread System Status Check — What's Next?

## Current State

Three threads, all with surface area. Cross-linked into a compound loop.

### Thread 001: Signal-to-Source — GOLDEN
User sees a signal → clicks evidence → DocumentViewer opens with source document. Works across all three paths: SignalDetail evidence, brain citations in chat, /signals brain panel. Done.

### Thread 002: Event Horizon — FRAYED
`/horizon` page aggregates 6 sources: launches, conjunctions, FCC expirations, patent expirations, earnings, catalysts (22 upcoming). Type filter, range selector, month grouping, severity dots, countdown timers. Catalysts show fuzzy dates (~Q2 2026).

**Open gaps (both worker-level):**
- FCC comment/reply deadlines — ECFS API doesn't expose procedural deadlines. Would need new data source (FCC Proceedings API, Federal Register, or parse from PDFs).
- Earnings date automation — No worker discovers next earnings dates. Currently manual.

### Thread 003: Thesis Builder — FRAYED
`/thesis` page accepts a thesis statement, runs 3 sequential brain queries (supporting evidence, contradicting evidence via counter-thesis mode, synthesis). Three-section streaming layout with citations and DocumentViewer. Free tier gets FOR + SYNTHESIS; counter-thesis requires Full Spectrum. 5 suggested theses. Auto-saves to DB after completion. Shareable URLs at `/thesis/[id]`. Previous analyses listed on creation page.

**Open gaps:**
- No evidence scoring — rerank scores (0-10) exist but aren't surfaced
- 3 sequential API calls — slow, could be single prompt

### Cross-Thread Wiring (done)
- Signal → "BUILD THESIS" → /thesis?q={title}
- Signal → "VIEW HORIZON" → /horizon?type={mapped}
- Horizon catalyst → "ANALYZE" → /thesis?q={title}
- Terminal widgets → /signals, /horizon
- IntelLink widget → SIGNALS / HORIZON / THESIS
- Onboarding v2 describes all three pages
- Landing page EXPLORE: 6 items in 3-col grid

## Platform Stats
- 13,000+ brain chunks across 10 source tables
- 530 SEC filings, 4,500+ FCC filings, 307 patents
- 22 workers on GitHub Actions cron schedules
- 6 event types on horizon timeline

## The Question

Given the current state — three threads with surface area, all cross-linked — what should we focus on next?

Options I see:
1. **Thread 002 → GOLDEN**: Close the worker gaps (FCC deadlines, earnings dates). Heavy infrastructure work.
2. **Thread 003 → FRAYED**: Add persistence (save theses to DB, shareable URLs). Or optimize to single prompt.
3. **New thread**: Is there a fourth user intent we're missing that would compound with the existing three?
4. **Polish**: The three threads work but the UX could be tighter — better loading states, error handling, mobile responsiveness.
5. **Ship**: Push to production. Get real users on it. Iterate based on usage.

What's the highest-leverage next move? Should we deepen what exists or widen to a new thread? Or is this the right moment to ship and observe?
