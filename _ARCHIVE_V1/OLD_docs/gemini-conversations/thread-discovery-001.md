# Thread Discovery: What's Next After All GOLDEN?

## CLAUDE (turn 1)

### Context

All three threads are GOLDEN:
- **Thread 001 (Signal-to-Source, P0):** Signal → evidence → source document. All paths work: signal evidence, brain citations in chat, brain panel on /signals.
- **Thread 002 (Event Horizon, P1):** 7 event sources flow into `/horizon` (launches, conjunctions, FCC expirations, FCC docket deadlines, patents, earnings, catalysts). Earnings automated via Finnhub. Docket metadata captured.
- **Thread 003 (Thesis Builder, P2):** Structured FOR/AGAINST/SYNTHESIS from 13,000+ brain chunks. Persistence, sharing, evidence scoring all working.

Cross-thread wiring is live: Signal→Thesis, Signal→Horizon, Horizon→Thesis, widget links, command palette integration.

### Platform State

**What's built:**
- `/asts` — Immersive terminal with 3D globe, widget system, live satellite tracking
- `/signals` — Intelligence feed with price correlation, filtering, brain search
- `/horizon` — Event timeline from 7 data sources
- `/thesis` — Structured bull/bear case builder
- `/orbital` — Constellation health, orbital analysis, space weather
- `/satellite/[noradId]` — Per-satellite telemetry
- `/patents` — Patent portfolio browser
- `/research` — Brain-powered research with filing citations
- 22+ automated workers on GH Actions cron schedules
- Brain/RAG with 13,000+ embedded chunks, hybrid vector+keyword search, LLM reranking

**What's NOT built (known from CLAUDE.md):**
- `$SPACE Dashboard` — Sector-wide space investing intelligence. "Next release." No surface area yet.
- Counter-thesis mode in brain queries is tiered but the Patreon integration for Full Spectrum is basic (OAuth exists, ClearanceModal exists, but actual gating enforcement needs auditing)
- No mobile optimization
- No email digest/alerts
- No API access for Full Spectrum tier (mentioned in C6 tier table)

### The Question

All three user-journey threads are GOLDEN. Where does the platform go next?

Options I see:
1. **New threads for existing dark intents** — What user journeys exist that we haven't built for? (e.g., "Compare ASTS to competitors", "Alert me when X happens", "Show me the full patent portfolio analysis")
2. **Depth on existing threads** — Thread 003 GAP 6 (perf optimization), richer Horizon events, smarter signal detection
3. **$SPACE expansion** — Start building sector-wide coverage infrastructure
4. **Monetization hardening** — Audit tier gating, build Full Spectrum API access, Patreon webhook for real-time tier sync
5. **Distribution** — Email alerts, RSS feeds, embeddable widgets, social sharing

What does Gemini think the highest-leverage next move is? Not features — threads. What user intent is the platform failing to serve that would compound with what's already built?

## GEMINI (turn 1)

**Recommendation: Thread 004 — The Watchtower**

**User Intent:** "Don't make me stare at the screen. Tell me when the thesis changes."

The Spacemob Terminal is currently a Passive HUD — Bloomberg-grade, but requires the user to be the active agent. Real intelligence platforms intrude when it matters. If we move to $SPACE now, we just create more dashboards to manually check. Need a mechanism to scale "signal" before scaling "scope."

**Why it compounds:**
1. Signals (T001) become Triggers — push notifications on high-impact events
2. Horizon (T002) becomes Operations — T-minus briefings, new filing alerts
3. Thesis (T003) becomes Dynamic — thesis shift alerts when new evidence changes the picture

**Core Loop:** Configure → Monitor → Notify → React

**Key Components:**
- Notification Engine: unified dispatcher (Email via Resend, Discord Webhooks, Browser Push)
- User Preferences: "Notify me on: High Impact Signals, Horizon Events < 24h, Thesis Shifts"
- The Daily Brief: morning summary email synthesizing last 24h of worker collection

**Strategic Fit:** This is the necessary bridge to Full Spectrum paid tier. Users pay for "peace of mind" far more than "better charts." Also builds filtering infrastructure needed for $SPACE's 50+ companies.

**Verdict:** Build The Watchtower. Turn the platform from Pull to Push.

## CLAUDE (turn 2)

Agree with the diagnosis. The platform is pull-only — everything waits for the user to visit. The Watchtower is the right next thread.

But I want to scope this tightly. A "notification engine" with email, Discord, and browser push is three new integrations, user preferences UI, queue infrastructure, and template systems. That's a 3-week build, not a thread loop.

**My counter-proposal: Phase the Watchtower into 3 GAPs that each deliver standalone value:**

**GAP 1 — The Daily Brief (Email)**
- Single new worker: `daily_brief_worker.py` runs at 7 AM ET
- Queries last 24h: new signals, upcoming horizon events (next 7 days), new filings, price change
- Renders a simple HTML email via Resend (single API, $0 at low volume)
- Sends to subscribers (new `email_subscribers` table, or reuse `profiles` with email)
- No preferences UI needed yet — everyone gets the same brief
- **This alone is a product.** "Subscribe to the ASTS morning brief."

**GAP 2 — Alert Triggers**
- Extend the signal_scanner: when a new signal with severity >= 'high' is created, fire an alert
- Same Resend channel. Template: "{signal.title} — View on Spacemob Terminal"
- Threshold-based, not preference-based (yet). All subscribers get high-severity alerts.

**GAP 3 — Preferences + Tier Gating**
- User preferences: which categories, which severity threshold, frequency
- Full Spectrum gets real-time alerts; free tier gets daily brief only
- This is where it becomes a monetization lever

GAP 1 is the only one that matters right now. A daily email that actually contains intelligence — that's the hook. GAPs 2-3 build on it.

What's the email infrastructure look like? Do we have Resend, SendGrid, or any email service set up? Or is this net-new?

## GEMINI (turn 2)

**Approved: Thread 004 — The Watchtower.**

Architecture override: don't use Python worker for the email. The Short Gravity aesthetic (Tactical HUD, JetBrains Mono) is defined in Tailwind/React — replicating in Python HTML strings is brittle.

**The Stack:**
- **Service:** Resend (best DX, native Next.js integration)
- **Templating:** React Email (Tailwind + React components for email)
- **Execution:** Vercel Cron (triggers Next.js API route)

**GAP 1 — The Daily Brief spec:**

1. **Infrastructure:** Add `resend` + `@react-email/components`. Env: `RESEND_API_KEY`. Sender: `intelligence@shortgravity.com`.

2. **Data Pipeline:** API route `app/api/cron/daily-brief/route.ts` (cron-secured). Three parallel Supabase queries:
   - Signals: created_at > 24h ago, limit 5, order severity desc
   - Horizon: events in next 48h
   - Filings: count in last 24h

3. **Template (`emails/DailyBrief.tsx`):** React component. Header (logo + date), Intel Feed (top signals), Horizon (upcoming events), CTA ("Open Terminal" button). Black bg, white text, orange accents.

4. **Storage:** `subscribers` table (id, email, status, created_at). Seed with Gabriel's email.

5. **Execution:** Install → Design template → Wire API route → Test send → Vercel Cron.
