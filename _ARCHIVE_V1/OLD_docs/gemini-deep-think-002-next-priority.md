# Gemini Deep Think — Context Package

---

## Project: Short Gravity

Autonomous space sector intelligence platform. Solo-built by Gabriel. Live at shortgravity.com.

**Stack:** Next.js 14, TypeScript, Tailwind, Three.js, Python 3 workers, Supabase (PostgreSQL + pgvector), Vercel, GitHub Actions.

**Architecture:** Every feature = Worker → Supabase → API Route → UI Component. Workers run on cron schedules. UI reads live from database. No mock data. No placeholders.

## Your role

You are the research and architecture analyst. Be opinionated. Recommend one path. Write spec sections, not code. Your output drives a coding agent (Claude) that implements everything.

## Context: What just shipped

In the last session we built two features:

1. **Command Palette (Cmd+K)** — Global navigation/search across all routes, brain search, satellite search, layout presets, toggles. Works on every page.

2. **Intelligence Feed (`/signals`)** — Dashboard page YOU designed in round 1. Built: SGChart with ASTS price + signal markers (color-coded by severity), category/severity filter controls, scrollable signal feed, detail panel with metrics/evidence/confidence. Extended the API with category/date/pagination filters. DB migration ready for 3 new columns (category, confidence_score, price_impact_24h).

## Current platform state

**Pages that exist and work:**
- `/` — Landing page (says "LAUNCHING SOON", gated behind email signup)
- `/asts` — Immersive terminal with 3D globe, widgets, brain search
- `/signals` — NEW: Intelligence feed dashboard (just built)
- `/orbital` — Constellation health, space weather, drag analysis
- `/intel` — Cross-reference analysis, filing impact, sentiment (has parallel signal system — needs merging with /signals)
- `/patents` — Patent explorer with database/gallery/stats views
- `/research` — Brain-powered filing search
- `/compare` — Side-by-side satellite comparison
- `/satellite/[noradId]` — Per-satellite detail pages

**Data sources (all autonomous, cron-scheduled):**
- 530 SEC filings, 4,500+ FCC filings, 307 patents, 100+ press releases
- 2,000+ X posts, ~200 signals, 13,000+ brain chunks
- 7 satellites tracked, 50,000+ TLE records, 25,000+ space weather records
- Daily prices, short interest, earnings transcripts

**What's NOT done from your Phase 3-4 spec:**
- Port intel page ephemeral signals into signal_scanner.py
- Compute price_impact_24h in the worker
- Tier gating on /signals page
- Hover-highlighting between chart and feed (chart markers highlight, but bidirectional hover not wired)

**Bigger gaps identified in our audit:**
- Landing page says "LAUNCHING SOON" but product is live and functional
- No onboarding for new users after login
- No pricing page or clear upgrade path to Full Spectrum
- /intel page has a parallel signal system that should merge into /signals
- Mobile experience likely broken (3D globe, fixed positioning)

## Question

We're iterating toward a complete, shippable platform. Each loop: Gemini specs, Claude builds, commit, repeat.

**What should the next loop build?** Consider:

1. **Signal worker upgrades** (Phase 3-4 from your spec) — port ephemeral signals, compute price_impact_24h, finish the intelligence feed
2. **Launch readiness** — fix the landing page, add onboarding, create a pricing/upgrade flow
3. **Intel page merge** — unify /intel into /signals, eliminate the parallel signal system
4. **Something else entirely** — maybe there's a higher-leverage move I'm not seeing

Constraints:
- Solo dev. Each loop should be completable in ~1 hour of Claude implementation time.
- Impact over polish. What moves the needle most toward "this is a product people would pay for"?
- The platform already HAS the data. The gap is presentation and the "wow" factor.

**Deliverable:** Pick ONE thing. Explain why in 2-3 sentences. Then provide a concrete spec (files to create, files to modify, architecture) that Claude can implement immediately. Keep it tight — this isn't a research paper, it's a build order.
