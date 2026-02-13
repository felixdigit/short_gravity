# What's Next — Post-Ship Strategic Check

## Platform State (just pushed to production)

Three narrative threads, all cross-linked into a compound loop. Command palette (Cmd+K) gives unified navigation across everything.

### Thread 001: Signal-to-Source — GOLDEN
Signal → evidence → DocumentViewer opens source document. Works across SignalDetail, brain citations, /signals brain panel. Complete.

### Thread 002: Event Horizon — FRAYED
`/horizon` aggregates 6 event types: launches, conjunctions, FCC expirations, patent expirations, earnings, catalysts. Type filter, range selector, month grouping, severity dots, countdown timers.

**Remaining gaps (worker-level):**
- FCC comment/reply deadlines — ECFS API doesn't expose procedural deadlines
- Earnings date automation — no worker discovers next earnings dates

### Thread 003: Thesis Builder — FRAYED
`/thesis` runs 3 sequential brain queries (supporting, contradicting via counter-thesis, synthesis). Streaming layout with citations. Auto-saves to DB. Shareable URLs at `/thesis/[id]`. Previous analyses listed.

**Remaining gaps:**
- Evidence scoring — rerank scores (0-10) exist but aren't surfaced
- 3 sequential API calls — slow, could be single prompt

### Cross-Thread Wiring — COMPLETE
- Signal → BUILD THESIS → /thesis?q={title}
- Signal → VIEW HORIZON → /horizon?type={mapped}
- Horizon catalyst → ANALYZE → /thesis?q={title}
- Terminal widgets → /signals, /horizon
- IntelLink widget → SIGNALS / HORIZON / THESIS
- Onboarding v2 describes all pages
- Landing page EXPLORE: 6 items in 3-col grid
- Command Palette (Cmd+K): navigation, brain search, satellite search, presets, toggles

## Platform Numbers

| Metric | Count |
|--------|-------|
| User-facing pages | 13 (excl. dev) |
| API routes | 70+ |
| Registered widgets | 13 |
| GitHub Actions workers | 23 |
| Terminal presets | 4 |
| Vercel crons | 3 |
| Brain chunks | 13,000+ |
| SEC filings | 530 |
| FCC filings | 4,500+ |
| Patents | 307 |
| X posts | 2,000+ |

## Key Pages

- `/` — Landing page (product grid, explore links)
- `/asts` — Immersive terminal (3D globe, widgets, brain search)
- `/orbital` — Constellation health, orbital analysis, space weather
- `/satellite/[noradId]` — Per-satellite telemetry, orbit, coverage
- `/signals` — Intelligence feed with price chart markers
- `/horizon` — Event timeline (6 sources)
- `/thesis` — Thesis builder (3-phase, persistent, shareable)
- `/research` — Brain search interface
- `/patents` — Patent portfolio (270 patents, 3 views)
- `/compare` — Constellation comparison charts

## The Question

We just shipped. Three threads with surface area, all cross-linked, command palette unifying navigation. The platform is fast and the data is real.

What's the highest-leverage next move? Options I see:

1. **Deepen existing threads to GOLDEN** — Close the worker gaps (earnings automation, FCC deadlines), surface rerank scores in thesis, optimize thesis to single prompt. Incremental but complete.

2. **$SPACE expansion** — The infrastructure is ticker-agnostic (hooks take params, tables keyed by symbol). Start adding sector-wide coverage: RKLB, LUNR, MNTS, VORB, SPIR. New landing at /space. Reuse everything.

3. **Content + distribution** — The platform exists but nobody knows. Write the launch post. Build the X presence. Create the "why Short Gravity" narrative. Ship the Patreon tiers. Get users.

4. **New thread** — Is there a fourth user intent we're missing? Portfolio tracking? Alerts/notifications? Comparative analysis across companies? What compounds with the existing three?

5. **Polish + mobile** — 13 pages work but some are desktop-only. Mobile responsiveness, loading states, error handling, empty states. Make it bulletproof.

6. **API / programmatic access** — Full Spectrum tier includes API access but there's no developer-facing API docs or keys. Build the API product.

What would you prioritize? What's the one thing that would make the biggest difference right now — before we iterate based on real user feedback?

---

## GEMINI (turn 1) — Gemini 3 Pro Preview

This is the pivot point between a "project" and a "platform."

You have built a Ferrari engine (the graph, the workers, the brain), but you have currently installed it in a go-kart (a single-ticker dashboard).

The highest-leverage move is **Option 2: $SPACE Expansion**.

You must immediately prove the infrastructure is ticker-agnostic. Expanding coverage from just ASTS to a select basket (specifically **RKLB** and **LUNR**) creates the highest compound return for three reasons:

1.  **Market Cap of Attention:** You instantly triple your addressable audience. The RKLB (Rocket Lab) and LUNR (Intuitive Machines) retail communities are just as obsessive as the SpaceMob.
2.  **Value Proposition Shift:** It transforms the product from "An ASTS deep-dive tool" (niche, feels like a fan site) to "Sector Intelligence" (enterprise, investable software).
3.  **Technical Proof:** It forces you to clean up hardcoded assumptions *now* before they ossify. If the "Signal-to-Source" loop works for Rocket Lab filings without code changes, you have a SaaS product.

Here is the execution plan.

### The Strategy: "The Retail Trinity"
Don't try to boil the ocean with SPIR, MNTS, or VORB yet. Focus entirely on the "Retail Trinity": **ASTS, RKLB, LUNR.** These three dominate social volume and retail sentiment. They are the testbed.

#### Phase 1: The Data Clone (Days 1-7)
You stated the infrastructure is ticker-agnostic. Prove it.
*   **Ingest:** Clone the Github Action workflows for RKLB and LUNR.
    *   *SEC:* CIK mappings are easy.
    *   *Social:* specific lists/accounts for Rocket Lab/Beck and Intuitive Machines.
    *   *Patents:* Assign assignees.
*   **Brain:** Ensure vectors are tagged with metadata `{ symbol: 'RKLB' }`.
*   **Success Metric:** `/signals?symbol=RKLB` populates with real data without crashing.

#### Phase 2: Context Management (Days 8-14)
The UI currently implicitly assumes ASTS in too many places (likely the 3D globe, specific widget configurations, orbit paths).
*   **Global Context:** Introduce a global context provider (Zustand store) for `activeSymbol`.
*   **Navigation:** The Command Palette (Cmd+K) must allow switching contexts. `> Switch to RKLB`.
*   **The Globe:** This is the hardest part. If RKLB is selected, `/asts` (the terminal) needs to become `/terminal` and show Electron stats or Neutron launch sites, not BlueBirds. *Cut scope:* Keep the 3D globe focused on ASTS for now, but make the *data* pages (Signals, Horizon, Thesis) fully multi-ticker.

#### Phase 3: The "Sector" View (Days 15-21)
This is the money shot. You need a new page: `/sector` (or replace Landing).
*   **Comparative Velocity:** A chart or grid showing Signal Velocity of ASTS vs. RKLB vs. LUNR. Who is shipping? Who is filing?
*   **Cross-Pollination:** Allow `/thesis` to run queries across the sector. *"Compare the cash burn rate of ASTS and RKLB based on recent 10-Qs."*
*   **Why this wins:** This feature alone validates the "Short Gravity" name. It is gravity across the sector, not just one star.

### What to Ignore (Ruthless Prioritization)

*   **Kill Option 1 (Deepen Threads):** The "Frayed" edges of Horizon and Thesis are fine. Users will forgive a missing FCC deadline date. They will not forgive a "Space Platform" that only covers one stock.
*   **Kill Option 5 (Mobile Polish):** This is a pro-sumer research terminal. It is meant to be used on a monitor. Mobile just needs to not crash; it doesn't need to be perfect.
*   **Kill Option 3 (Marketing/Content):** Do not launch marketing until you have RKLB support. Launching as "The ASTS Dashboard" creates a tiny box you will struggle to break out of. Launching as "The Space Sector Intelligence Platform" (starting with ASTS/RKLB/LUNR) is a headline.

### The 90-Day Compound View

If you ship multi-ticker support in the next 3 weeks:
1.  **Month 1:** Soft launch to RKLB and LUNR subreddits/X communities. "I built this for ASTS, just turned it on for RKLB. What signals am I missing?" -> **Instant feedback loop.**
2.  **Month 2:** The "Compare" feature becomes the viral hook. Screenshots of Thesis comparing specific technical moats of the three companies circulate on X.
3.  **Month 3:** You introduce the paid tier. "Full Spectrum" access covers the whole sector.

**Recommendation:** Stop polishing the ASTS vertical. Build the RKLB horizontal. Go.
