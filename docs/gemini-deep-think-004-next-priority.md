# Gemini Deep Think — Context Package 004

---

## Project: Short Gravity

Autonomous space sector intelligence platform. Solo-built by Gabriel. Live at shortgravity.com.

**Stack:** Next.js 14, TypeScript, Tailwind, Three.js, Python 3 workers, Supabase (PostgreSQL + pgvector), Vercel, GitHub Actions.

**Architecture:** Every feature = Worker → Supabase → API Route → UI Component. Workers run on cron schedules. UI reads live from database.

## Your role

Research and architecture analyst. Be opinionated. Pick ONE thing. Write a tight build spec, not a research paper.

## What shipped today (4 loops so far)

1. **Command Palette (Cmd+K)** — Global navigation/search. Portal overlay, keyboard nav, parallel search across static commands + brain API + satellites.

2. **Intelligence Feed (`/signals`)** — Dashboard with SGChart price+signal markers, category/severity filters, signal detail panel with metrics and evidence chain. Extended API with category/date/pagination.

3. **Landing page launch readiness** — $ASTS card now says "LIVE" with Enter Terminal link. Added EXPLORE nav section (Signals, Patents, Research, Orbital). Login link for returning users. $SPACE stays "COMING SOON".

4. **First-time onboarding** — "Mission Briefing" modal on first terminal visit. HUD-style, explains Globe/Widgets/Brain/Cmd+K. localStorage-gated, shows once.

## Current state

**Live pages:** `/` (landing), `/asts` (terminal), `/signals` (intelligence feed), `/orbital`, `/intel`, `/patents`, `/research`, `/compare`, `/satellite/[noradId]`

**Auth:** Magic link via email. Middleware gates all non-public routes behind auth in production. Free tier gets Haiku brain + basic widgets. Full Spectrum (Patreon) gets Sonnet, deeper search, more turns.

## The duplication problem (detailed audit)

Two parallel signal systems exist and don't talk to each other:

### System A: `/signals` page (database-driven)
- **Source:** `signals` table populated by `signal_scanner.py` worker (runs twice daily)
- **6 detectors:** sentiment_shift, filing_cluster, fcc_status_change, cross_source, short_interest_spike, new_content
- **Schema:** signal_type, severity, title, description, source_refs JSONB, metrics JSONB, fingerprint (dedup), detected_at, expires_at
- **New columns (migration 022, not yet run):** category, confidence_score, price_impact_24h
- **UI:** SGChart with price+markers, feed with category/severity filters, detail panel

### System B: `/intel` page (client-side computed)
- **Source:** 4 widget API endpoints, computed on page load
- **4 signal types:** crossref (patent↔regulatory), language (earnings diffs), velocity (filing clusters), impact (filing market effects)
- **Brain integration:** Full RAG search panel with suggested queries
- **Unique value:** Cross-source semantic analysis, filing impact on price, community sentiment timeline, voice scoring
- **Problem:** Signals computed in-memory only, never stored, no dedup, stale on every load

### What each system has that the other doesn't

| Capability | `/signals` | `/intel` |
|-----------|-----------|---------|
| Database persistence | YES | NO |
| Worker-powered freshness | YES | NO |
| Deduplication | YES (fingerprint) | NO |
| Category/severity filtering | YES | NO |
| Cross-source semantic analysis | NO | YES |
| Patent↔regulatory cross-refs | NO | YES |
| Earnings language diffs | NO | YES |
| Brain/RAG integration | NO | YES |
| Filing impact on price | NO | YES |
| Community sentiment | NO | YES (via widgets) |

## What's still broken/missing (priority order)

1. **Intel ↔ Signals duplication** — Two signal pages computing different things, confusing UX
2. **No pricing/upgrade flow** — Free users don't know Full Spectrum exists. No upsell anywhere.
3. **Signal worker doesn't populate category** — migration 022 not run, signal_scanner.py doesn't set category/confidence
4. **price_impact_24h** not computed yet
5. **Mobile experience broken** (3D globe)

## Question

What's the highest-leverage thing to build in the next ~1 hour loop? Consider:

- **Intel → Signals merge** — Redirect /intel to /signals. Port the unique value (cross-refs, filing impact, brain integration) into the /signals page or into signal_scanner.py. Eliminate the parallel system.
- **Pricing/upgrade flow** — Make Full Spectrum visible and desirable. Show what free users are missing. Upgrade CTA in brain search, signals detail, and terminal. Patreon integration already exists.
- **Signal worker upgrade** — Make signal_scanner populate category + confidence. Add new detector types (patent_crossref, earnings_diff) ported from /intel. Run migration 022.
- **Something else**

Constraints: Solo dev. 1-hour implementation budget. Impact over polish. What moves the platform closest to "complete" from a new user's perspective?

**Deliverable:** Pick ONE. 2-3 sentence justification. Then a concrete build spec (files to create/modify, architecture) that a coding agent can implement immediately.
