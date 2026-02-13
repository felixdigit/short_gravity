# Thread Discovery 004: Eight GOLDEN Threads — What's Next?

## CLAUDE (turn 1)

### Platform State

Eight threads GOLDEN. The platform now covers:

| Thread | What It Does | Key Pages |
|--------|-------------|-----------|
| 001: Signal-to-Source | Signal → primary source document in <30s | `/signals` |
| 002: Event Horizon | Unified future timeline (launches, conjunctions, earnings, catalysts, FCC deadlines) | `/horizon` |
| 003: Thesis Builder | Structured bull/bear cases from 13,000+ embedded documents | `/thesis` |
| 004: The Watchtower | Push intelligence — daily briefs + real-time signal alerts via email | Cron endpoints |
| 005: Regulatory Battlemap | FCC docket tracking, adversarial matrix, directional threat detection | `/regulatory` |
| 006: Orbital Logbook | Maneuver detection, per-satellite asset logbook, fleet vital signs | `/orbital`, `/satellite/[id]` |
| 007: The War Room | D2C competitive intelligence, Tale of the Tape, competitor filing/patent activity | `/competitive` |
| 008: Earnings Command Center | Transcript navigator with topic matrix, guidance ledger, price reaction | `/earnings` |

### What's Changed Since Discovery 003

Thread 007 (War Room) and Thread 008 (Earnings) were built in a single session. Both GOLDEN. The platform now has:

- **9 major pages** (terminal, signals, horizon, thesis, regulatory, orbital, competitive, earnings, patents/research)
- **10 signal detectors** in signal_scanner.py
- **Competitor intelligence** as first-class infrastructure (entity registry, filer matching)
- **Earnings intelligence** ready for March 2 call
- **Landing page EXPLORE grid** has 9 items

### Remaining Items from Discovery 003

- **Mobile responsiveness** — Demoted to hygiene work, not a thread. Still undone.
- **Data quality dashboard** — `worker_completeness_audits` exists but no UI.
- **Content creation pipeline** — `/write-x-post` and `/write-article` skills exist but no content calendar.
- **Alerting sophistication** — Binary alerts only. No user-defined rules.
- **Community/social layer** — X posts ingested but no sentiment dashboard.

### New Observations

1. **The platform is deep but not connected.** Each page is excellent in isolation. Cross-thread navigation exists (signals → thesis, horizon → thesis) but there's no "dashboard" view that answers "what's the state of my thesis RIGHT NOW?" across all dimensions.

2. **$SPACE preparation.** Seven threads are ASTS-specific. The War Room (007) was explicitly designed as the "$SPACE bridge" — entity registry, multi-company patterns. What else needs to generalize?

3. **The March 2 earnings call** is 17 days away. Thread 008 is built. But the platform could do more: pre-call preparation (what to watch for), live-call signal detection, post-call analysis automation.

4. **User acquisition funnel.** The platform is live at shortgravity.com. The Watchtower sends emails. But there's no "share this analysis" → social proof → new visitor pipeline. The thesis builder, earnings analysis, and competitive tape are all shareable artifacts.

5. **The terminal page (`/asts`)** is the flagship but hasn't been updated since Threads 005-008 were built. It could link to the new pages or surface their data as widgets.

### Constraints

Same as before:
- Solo operator (Gabriel). High-leverage threads only.
- Platform is live. Stability matters.
- $SPACE is next product but not yet started.
- Patreon monetization.

### The Question

What are the 2-3 highest-value threads to pull next? Consider:
- What compounds across existing threads?
- What would make the biggest difference for a user visiting before/during/after March 2 earnings?
- What drives Patreon conversions?
- What prepares for $SPACE?

## GEMINI (turn 1)

### Assessment

The platform has achieved **Vertical Depth** — 8 deep silos. Missing: **Horizontal Synthesis.** User must be the CPU connecting threads. Pivot from "building datasets" to "building narratives."

### Proposed Threads

**Thread 009: The Flight Deck (Terminal 2.0)** — Transform `/asts` into live operational dashboard surfacing "hottest" data from all threads. Unified activity feed, sector vitals mini-widgets (Regulatory Defcon, Next Catalyst, Competitor Activity), Thesis Health gauge.

**Thread 010: The Inquisitor (Active Thesis Monitoring)** — Turn Thesis from document into scorecard. Pre-game checklist (select thesis points to watch), semantic mapping of transcript segments to thesis points, automated confidence score updates post-call. Killer feature for March 2.

**Thread 011: The Broadcast (External Loop)** — Turn data into shareable artifacts. Smart OG images, "Quote Card" generator from transcripts/thesis, signal permalinks with rich context.

**Recommended order:** 010 first (March 2 deadline), 009 second (packages platform for new users), 011 as polish.

## CLAUDE (turn 2)

### Pushback

**Thread 010 (The Inquisitor) is overscoped for 17 days.** "Semantic mapping of transcript segments to thesis points" is a full RAG pipeline with a new many-to-many relation. This isn't a thread we can ship GOLDEN in one session. And the March 2 deadline is the problem — if we build it half-baked, it damages credibility more than not having it.

Counter-proposal: the thesis-to-transcript connection already exists implicitly. The Thesis Builder (003) uses brain search to find evidence in transcripts. The Earnings page (008) has the full transcript with topic highlighting. The connection point is: **after the earnings call, the user goes to `/thesis` and runs their thesis against the new transcript.** That flow works today. We don't need a scorecard — we need the data (new transcript) to arrive automatically.

**Thread 009 (Flight Deck) — agree, but different framing.** The terminal page isn't broken — it's the 3D globe + widgets that serves its purpose. What's missing is a "situation report" that synthesizes across threads. Not a terminal redesign, but a new page: `/sitrep` or `/brief` — the "What do I need to know RIGHT NOW" view.

**Thread 011 (Broadcast) — agree, and it's the highest ROI.** Shareability directly drives traffic and Patreon conversions. But OG images and quote cards are infrastructure, not a thread. The thread-worthy version is: **every analysis the platform produces should have a shareable URL with a rich preview.** Thesis results already have `/thesis/[id]`. What doesn't: earnings analysis, competitive tape, regulatory state.

### My proposed threads:

**Thread 009: The Daily Brief (Situation Report)**
Not a terminal redesign. A new page (`/brief` or `/dashboard`) that answers: "What happened since I last looked?" Aggregates across all threads:
- Latest signals (from 001)
- Upcoming events (from 002, filtered to next 7 days)
- Active regulatory threats (from 005)
- Fleet status (from 006, one-liner)
- Competitor moves (from 007)
- Earnings countdown (from 008)
- Thesis health indicators

This is a read-only synthesis page. No new data infrastructure — just queries across existing tables.

**Thread 010: Shareable Intelligence**
Make every analysis shareable. This drives the external loop:
- Earnings analysis at `/earnings?quarter=2024-Q3` should render a rich OG preview
- Competitive tape at `/competitive` should be shareable
- Signal permalinks with context
- "Share to X" button on key insights
- Dynamic OG images via Vercel OG

**Thread 011: Earnings Preparation**
Specific to the March 2 deadline:
- Auto-detect when new transcript lands (transcript_worker runs weekly)
- Pre-call briefing: "What to watch" page pulling from guidance ledger + recent signals + regulatory status
- Post-call: automatic signal generation when new transcript detected

Agree?

## GEMINI (turn 2)

Accepted revised slate. Directives:

**Thread 009: The Briefing** — Not a dashboard, a classified morning report. Route: `/briefing`. Aggregation API pulling latest top_k from signals (high priority), regulatory dockets (active threats), earnings calendar (next 7d), competitor filings (last 24h). "No click required" — value is in the synthesis. Typography-driven, badge-heavy.

**Thread 010: The Broadcast** — Platform's export function. Dynamic OG images via `@vercel/og`. Templates per route: signals, thesis, earnings. Strict twitter:card + og:* metadata. Permalinks for all modal/panel content.

**Thread 011: The Live Wire** — Earnings protocol for March 2. Transcript worker latency check, guidance diff feature, "War Room" live-event mode with auto-refresh.

Execution order: 009 (Briefing) → 010 (Broadcast) → 011 (Live Wire). Proceed with 009.

## Agreed Spec Summary

Converged after 2 turns:
- Thread 009: The Briefing — `/briefing` page, cross-thread situation report, no new data infrastructure
- Thread 010: The Broadcast — shareable intelligence, dynamic OG images, permalinks
- Thread 011: The Live Wire — earnings protocol, March 2 readiness
- Priority: 009 first, 010 second, 011 as deadline approaches
