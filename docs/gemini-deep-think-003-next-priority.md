# Gemini Deep Think — Context Package

---

## Project: Short Gravity

Autonomous space sector intelligence platform. Solo-built by Gabriel. Live at shortgravity.com.

**Stack:** Next.js 14, TypeScript, Tailwind, Three.js, Python 3 workers, Supabase (PostgreSQL + pgvector), Vercel, GitHub Actions.

**Architecture:** Every feature = Worker → Supabase → API Route → UI Component. Workers run on cron schedules. UI reads live from database.

## Your role

Research and architecture analyst. Be opinionated. Pick ONE thing. Write a tight build spec, not a research paper.

## What shipped today (3 loops so far)

1. **Command Palette (Cmd+K)** — Global navigation/search. Portal overlay, keyboard nav, parallel search across static commands + brain API + satellites.

2. **Intelligence Feed (`/signals`)** — Dashboard with SGChart price+signal markers, category/severity filters, signal detail panel with metrics and evidence chain. Extended API with category/date/pagination.

3. **Landing page launch readiness** — $ASTS card now says "LIVE" with Enter Terminal link. Added EXPLORE nav section (Signals, Patents, Research, Orbital). Login link for returning users. $SPACE stays "COMING SOON".

## Current state

**Live pages:** `/` (landing), `/asts` (terminal), `/signals` (intelligence feed), `/orbital`, `/intel`, `/patents`, `/research`, `/compare`, `/satellite/[noradId]`

**Auth:** Magic link via email. Middleware gates all non-public routes behind auth in production. Free tier gets Haiku brain + basic widgets. Full Spectrum (Patreon) gets Sonnet, deeper search, more turns.

**What's still broken/missing (priority order):**
1. `/intel` page has a parallel signal system that duplicates `/signals` — should merge or redirect
2. No onboarding after first login — user lands on 3D globe terminal with zero guidance
3. Signal worker doesn't populate the new `category` column yet (migration 022 not run)
4. No pricing/upgrade path visible to free users (they don't know Full Spectrum exists)
5. `price_impact_24h` not computed yet
6. Mobile experience broken (3D globe)

## Question

What's the highest-leverage thing to build in the next ~1 hour loop? Consider:

- **Onboarding** — First-time user guidance after login (what is this? where do I go? what can I do?)
- **Pricing/upgrade flow** — Make Full Spectrum visible and desirable. Show what free users are missing.
- **Intel → Signals merge** — Eliminate the parallel signal system, redirect /intel to /signals or merge the computed signals
- **Signal worker category backfill** — Make the signal_scanner populate category + confidence fields so /signals shows real categorized data
- **Something else**

Constraints: Solo dev. 1-hour implementation budget. Impact over polish. What makes the biggest difference to a user who just landed from the new landing page?

**Deliverable:** Pick ONE. 2-3 sentence justification. Then a concrete build spec (files to create/modify, architecture) that a coding agent can implement immediately.
