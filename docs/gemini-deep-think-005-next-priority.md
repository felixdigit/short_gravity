# Gemini Deep Think — Context Package 005

---

## Project: Short Gravity

Autonomous space sector intelligence platform. Solo-built by Gabriel. Live at shortgravity.com.

**Stack:** Next.js 14, TypeScript, Tailwind, Three.js, Python 3 workers, Supabase (PostgreSQL + pgvector), Vercel, GitHub Actions.

**Architecture:** Every feature = Worker → Supabase → API Route → UI Component. Workers run on cron schedules. UI reads live from database.

## Your role

Research and architecture analyst. Be opinionated. Pick ONE thing. Write a tight build spec, not a research paper.

## What shipped today (5 loops so far)

1. **Command Palette (Cmd+K)** — Global navigation/search. Portal overlay, keyboard nav, parallel search across static commands + brain API + satellites.

2. **Intelligence Feed (`/signals`)** — Dashboard with SGChart price+signal markers, category/severity filters, signal detail panel with metrics and evidence chain.

3. **Landing page launch readiness** — $ASTS card now says "LIVE" with Enter Terminal link. Added EXPLORE nav section. Login link for returning users.

4. **First-time onboarding** — "Mission Briefing" modal on first terminal visit. HUD-style, explains Globe/Widgets/Brain/Cmd+K. localStorage-gated.

5. **Intel → Signals merge** — Deleted duplicate `/intel` page. Permanent redirect to `/signals`. Enhanced signal_scanner.py to v2 with `category` + `confidence_score` auto-population, 2 new detectors (patent↔regulatory cross-refs, earnings language shifts). Added Brain/RAG search panel to `/signals`. All nav links updated.

## Current state

**Live pages:** `/` (landing), `/asts` (terminal), `/signals` (unified intelligence feed with brain search), `/orbital`, `/patents`, `/research`, `/compare`, `/satellite/[noradId]`

**Auth:** Magic link via email. Middleware gates non-public routes in production. Free tier gets Haiku brain + basic widgets. Full Spectrum (Patreon) gets Sonnet, deeper search, more turns.

**Signal scanner v2:** 8 detectors (sentiment_shift, filing_cluster, fcc_status_change, cross_source, short_interest_spike, new_content, patent_regulatory_crossref, earnings_language_shift). All signals auto-categorized (regulatory/market/community/corporate/ip) with confidence scores.

## What's still missing (priority order)

1. **No pricing/upgrade flow** — Free users don't know Full Spectrum exists. No upsell anywhere. No way to see what they're missing. Patreon integration exists but is invisible.
2. **Migration 022 not run** — `category`, `confidence_score`, `price_impact_24h` columns not yet added to production signals table.
3. **price_impact_24h** not computed yet in worker.
4. **Mobile experience broken** (3D globe doesn't work on mobile).
5. **No email notification system** — Users can sign up for $SPACE notifications but there's no way to alert them when signals fire or new content drops.
6. **No social proof / activity indicators** — No way to see how many people use the platform, no recent activity feed on landing page.

## Question

What's the highest-leverage thing to build in the next ~1 hour loop? Consider:

- **Pricing/upgrade CTA** — Make Full Spectrum visible. Show free users what they're missing. Subtle upgrade prompts in brain search (when hitting limits), signals detail, and terminal. Link to Patreon.
- **Mobile fallback** — Detect mobile, show a static dashboard instead of the 3D globe. Even a simple responsive layout with key stats + links would be better than a broken page.
- **Email alerts** — When a high-severity signal fires, email subscribed users. Uses the existing email signup list.
- **Something else entirely**

Constraints: Solo dev. 1-hour implementation budget. Impact over polish. What makes the biggest difference to converting a visitor into a returning user?

**Deliverable:** Pick ONE. 2-3 sentence justification. Then a concrete build spec (files to create/modify, architecture) that a coding agent can implement immediately.
