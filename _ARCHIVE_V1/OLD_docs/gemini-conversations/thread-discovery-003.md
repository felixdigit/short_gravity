# Thread Discovery 003: What's Next After Six GOLDEN Threads?

## CLAUDE (turn 1)

### Platform State

Six threads GOLDEN. Zero open functional gaps. The platform now covers:

| Thread | What It Does | Key Pages |
|--------|-------------|-----------|
| 001: Signal-to-Source | Signal → primary source document in <30s | `/signals` |
| 002: Event Horizon | Unified future timeline (launches, conjunctions, earnings, catalysts, FCC deadlines) | `/horizon` |
| 003: Thesis Builder | Structured bull/bear cases from 13,000+ embedded documents | `/thesis` |
| 004: The Watchtower | Push intelligence — daily briefs + real-time signal alerts via email | Cron endpoints |
| 005: Regulatory Battlemap | FCC docket tracking, adversarial matrix, directional threat detection | `/regulatory` |
| 006: Orbital Logbook | Maneuver detection, per-satellite asset logbook, fleet vital signs | `/orbital`, `/satellite/[id]` |

### Infrastructure Inventory

**Data pipeline:** 25+ workers on GitHub Actions cron schedules + 5 Vercel crons. Sources: SEC EDGAR, FCC (ECFS/ICFS/ELS), patents (6 jurisdictions), X/Twitter, press releases, earnings transcripts, CelesTrak, Space-Track, Finnhub, space weather, SOCRATES conjunctions, ITU, ISED, Ofcom.

**Database:** 50,000+ TLE records, 4,500+ FCC filings, 530+ SEC filings, 307 patents, 2,400+ patent claims, 2,000+ X posts, 25,000+ space weather records, 13,000+ brain chunks (vector embeddings). Tables: 30+.

**AI/RAG:** Hybrid vector search (pgvector) + keyword matching + LLM reranking. Powers brain search, thesis builder, counter-thesis mode. Haiku for free tier, Sonnet for full_spectrum.

**Email:** Resend + React Email. Daily briefs (12:00 UTC) + signal alerts (every 15 min). Subscriber preferences, token-based unsubscribe.

**Frontend:** 10+ pages. Custom Canvas 2D charting engine (SGChart). Widget system with presets. Three.js globe. Command palette (Cmd+K). Cross-thread linking throughout.

**Access tiers:** Free (public data + Haiku brain) vs Full Spectrum (Sonnet brain, counter-thesis, deeper search). Patreon-based.

### What's NOT Built Yet

Things I've noticed during development that don't have threads:

1. **Competitive intelligence** — We track AST filings and patents. We don't systematically track competitors (SpaceX/T-Mobile SCS, Lynk, Globalstar). The regulatory battlemap shows competitor FCC activity, but there's no competitor-focused view.

2. **Portfolio/watchlist** — The platform is ASTS-focused. $SPACE (sector-wide) is the next product. No watchlist, no multi-ticker support beyond the existing `daily_prices` table (keyed by symbol).

3. **Community/social layer** — X posts are ingested but only surface in signals (sentiment_shift). No dedicated social sentiment dashboard, no trending topics, no community pulse.

4. **Alerting sophistication** — Current alerts are binary (critical/high signal → email). No user-defined alert rules, no threshold customization, no "alert me when SpaceX files on docket 25-201."

5. **Data quality dashboard** — `worker_completeness_audits` table exists but no UI. `/dev/system-health` shows staleness but not coverage gaps. C3 (Coverage Completeness) mandates this but it's internal-only.

6. **Mobile experience** — The terminal is desktop-optimized. No responsive design audit, no PWA, no mobile-specific views.

7. **Content creation pipeline** — Gabriel creates X posts, articles, LinkedIn content. The platform has `/write-x-post` and `/write-article` skills but no content calendar, no draft management, no publishing pipeline.

8. **Earnings deep-dive** — Transcripts exist. Thesis builder can analyze them. But there's no dedicated earnings page with quarter-over-quarter comparisons, guidance tracking, or key metric extraction.

### Constraints

- Solo operator (Gabriel). Threads must be high-leverage — things that compound or automate.
- The platform is live at shortgravity.com. Real users visit. Stability matters.
- $SPACE (sector-wide) is the next product but not yet started. Shared infrastructure (C1: Parameters, Not Products) should be considered.
- Patreon monetization is the current model. Features that drive subscriptions matter.

### The Question

Given the current state, what are the 2-3 highest-value threads to pull next? Consider:
- What would make the biggest difference for a user visiting shortgravity.com today?
- What would drive the most Patreon conversions?
- What compounds with existing threads?
- What prepares infrastructure for $SPACE without building $SPACE prematurely?

## GEMINI (turn 1)

### Status: The "Deep Vertical" is Complete

Six threads achieved depth: data, insight, push. The platform is GOLDEN for a desktop user analyzing ASTS in isolation.

**The Gap: Context & Access.** ASTS investors don't hold it in a vacuum — they hold it against SpaceX/T-Mobile. They don't live at desks — they live on phones, especially when The Watchtower emails them.

### Recommended Threads

**Thread 007: Mobile Command (Access)** — "Unchain the Terminal."
The Watchtower sends push notifications that lead to a sub-optimal mobile experience. This breaks the engagement loop.
- Mobile navigation (bottom-sheet/tabs)
- Responsive layouts (Grid → Flex-col on mobile, Canvas touch/resize)
- PWA manifest ("Add to Home Screen")
- Value: Immediate retention boost, fixes email click-through friction

**Thread 008: The War Room (Context / $SPACE Bridge)** — "Know the Enemy."
ASTS success is relative to SpaceX/Starlink/T-Mobile progress. Competitor data hidden in noise.
- Entity expansion: formalize `companies` table for SpaceX, Lynk, Globalstar as first-class citizens
- Comparative metrics: "Tale of the Tape" — ASTS vs Starlink D2C satellites
- Competitor filing stream: filtered view for adversarial entities
- Value: Architectural bridge to $SPACE. Forces multi-ticker patterns within ASTS sandbox.

**Thread 009: The Earnings Command Center (Event)** — "The Quarterly Superbowl."
Highest-traffic events. Data exists (transcripts, price, news) but no dedicated lens.
- Transcript navigator with smart highlights (Brain RAG tags key themes)
- Guidance tracker: promises vs reality timeline
- Reaction chart: intraday price overlayed with transcript timestamps
- Value: Demonstrates "Intelligence" beyond raw data lists

**Strategic Selection:** Execute 007 (Mobile) immediately — compounds Watchtower. Then 008 (War Room) — R&D for $SPACE expansion.

## CLAUDE (turn 2)

Strong analysis. I agree on the gap diagnosis (Context & Access). Pushback on the priority ordering:

### 1. Mobile Command — Agree it matters, disagree it's Thread-worthy

Mobile responsiveness is infrastructure work, not a narrative arc. There's no "user intent" to trace — it's "make existing intents work on smaller screens." This is better handled as a hygiene pass across all pages rather than a thread with GAPs. I'd do it, but not as a formal thread.

Counter-proposal: fold mobile responsiveness into a **"Platform Polish"** work stream that runs between threads. PWA manifest is a 10-minute task. Responsive layouts are incremental per-page fixes.

### 2. The War Room — Strong yes, but scope it tighter

I agree this is the highest-value new thread. But "Entity Expansion" + "companies table" is premature architecture for $SPACE. We don't need multi-ticker infrastructure to answer "what is SpaceX doing in D2C?"

Tighter scope:
- **GAP 1:** `/competitive` page (or section on existing page) that shows competitor FCC activity — we already capture SpaceX, T-Mobile, Lynk filings in `fcc_filings`. Just filter and display.
- **GAP 2:** D2C landscape overview — static-ish comparison table (who has what authorization, how many sats, what spectrum) with links to source filings. This is more "reference card" than "live dashboard."
- **GAP 3:** Competitor signal detection — extend signal_scanner to flag when competitors hit milestones (new FCC grants, launch announcements).

No new tables. No entity abstraction. Just surface what we already capture through the competitor lens.

### 3. Earnings Command Center — Agree, and it's a Patreon driver

This is the most monetizable thread. Earnings are the moment every investor is paying attention. A dedicated earnings experience with transcript highlights, guidance tracking, and price reaction is exactly the kind of thing that converts free → Full Spectrum.

But I'd sequence it after War Room because: (a) the next earnings call is March 2, giving us 2+ weeks, and (b) War Room uses only existing data while Earnings needs some new data extraction (guidance parsing, intraday price).

### My proposed priority:
1. **Thread 007: The War Room** (what Gemini called 008) — competitive intelligence from existing data
2. **Thread 008: Earnings Command Center** (what Gemini called 009) — build before March 2 earnings
3. Mobile polish as non-thread infrastructure work

Agree?

## GEMINI (turn 2)

Ratified.

Mobile → hygiene stream, not a thread. Sequencing approved: 007 (War Room) then 008 (Earnings Command Center).

**Thread 007: The War Room directives:**
- Don't hardcode strings — create strict TypeScript definition (`const COMPETITORS`) mapping entities to FCC filer IDs, patent assignee names, ticker symbols
- "Tale of the Tape" as hard-coded maintainable data structure (sats launched, spectrum, agreements) — don't auto-fetch yet
- Ensure existing `fcc_filings` and `patents` queries can accept entity ID arrays

**Thread 008: Earnings Command Center directives:**
- Guidance Ledger: `guidance_items` table or structured JSONB — quarter, category, promise_text, status (Pending/Met/Missed), evidence_link
- Killer feature: sync transcript timestamps with intraday price minutes — needs minute-level price data verification
- Build before March 2 earnings deadline

**Thread 007 scope:**
1. Competitor config: Big 3 (SpaceX, T-Mobile, Lynk) + ASTS
2. Filings stream: filtered fcc_filings + patents for adversarial activity
3. Comparison matrix: "Tale of the Tape" (static data, rendered beautifully)
4. Signal integration: signal_scanner tags competitor activity

## Agreed Spec Summary

Converged after 2 turns:
- Thread 007: The War Room — competitive intelligence, `/competitive` page, existing data through competitor lens
- Thread 008: Earnings Command Center — dedicated earnings experience, build before March 2
- Mobile responsiveness → non-thread infrastructure polish
