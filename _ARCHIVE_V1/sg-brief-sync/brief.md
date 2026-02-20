# Short Gravity — Latest Brief

**Last updated: Feb 10, 2026**

## One-Liner

Short Gravity is an independent space sector intelligence platform that cross-references satellite orbital data, SEC/FCC filings, patents, and market data to surface actionable insights for $ASTS investors.

## What We're Building

A "Bloomberg Terminal for space" — a real-time research instrument that tracks AST SpaceMobile's satellite constellation, regulatory filings, patent portfolio, and stock activity in one dense interface. The platform ingests data from 15+ sources via automated workers, embeds it into a unified vector search layer, and exposes it through an AI research assistant that can query across 13,000+ indexed records. The Terminal at shortgravity.com is live and open to the public, with a paid tier unlocking deeper AI analysis.

## Current Stage

Production. 21+ automated data pipelines running on cron schedules. 530 SEC filings, 4,500+ FCC filings, 307 patents across 7 jurisdictions, 50,000+ orbital records — all indexed and searchable. Live satellite tracking for 7 ASTS satellites including the 5 BlueBird production birds and the new BlueBird 6/FM1 (223 m² array, commissioning). Patreon-based monetization in development.

## Key Technical Work

- **Dual-source TLE pipeline** — CelesTrak supplemental GP (primary for position) + Space-Track radar (primary for BSTAR/drag), with automated health anomaly detection and source divergence tracking
- **RAG-powered research assistant** — hybrid vector + keyword search across all data sources, Claude synthesis with full citation chains (~$0.001/query)
- **International patent coverage** — claims data from USPTO, EPO, WIPO, JPO, KIPO, IP Australia, CIPO (2,482 claims mapped into 29 patent families)
- **International regulatory tracking** — ITU, ISED Canada, Ofcom UK scrapers alongside FCC ECFS/ICFS/ULS
- **Signal scanner** — automated cross-source anomaly detection running twice daily

## Recent Milestones

- Shipped production Terminal with 3D globe, live satellite positions via satellite.js/SGP4, and real-time stock overlay
- Built 6 international patent claims fetchers, covering all major filing jurisdictions
- Deployed FCC ECFS docket crawler tracking 6 SCS-related proceedings (including the primary D2D rulemaking 23-65 and AST's SCS modification 25-201)
- Consolidated TLE pipeline to single dual-source system with health monitoring
- Established full automation layer — every worker has a GitHub Actions workflow on schedule

## Talking Points for Public Content

- **The "why":** Public satellite data is free but fragmented across dozens of agencies and databases. Short Gravity stitches it together and makes it searchable. The alpha isn't in knowing where a satellite is — it's in cross-referencing orbital behavior changes with regulatory filings and patent activity to understand what a company is *doing*.
- **For non-aerospace audiences:** Think of it as building a financial research terminal for a sector that doesn't have one yet. Space is becoming investable infrastructure (cell towers in orbit), but the data tools haven't caught up. Short Gravity is closing that gap.
- **The technical angle:** Solo-built platform with 21+ automated data pipelines, AI-powered research across 13K+ records, and real-time orbital tracking — all running on Next.js, Python workers, and Supabase.
- **The market angle:** AST SpaceMobile is building direct-to-smartphone satellite connectivity — essentially cell towers in space. Short Gravity exists because this sector moves fast and the public data is scattered across SEC, FCC, international patent offices, and orbital databases.

## What's Next

- Patreon OAuth integration for paid tier gating (public AI vs. deep analysis)
- MCP server + custom GPT so external AI tools can query Short Gravity as a source of truth
- Patent figure coverage backfill (175 patents missing figures)
- XBRL reprocessing for 29 SEC filings after parser fix
- Community intelligence layer (Spacemob knowledge base — tracking X/Reddit voices with reliability scores)

## Brand & Visual Identity

**Aesthetic:** NASA mission control meets Bloomberg Terminal. Dark mode only.

| Token | Value | Usage |
|-------|-------|-------|
| Background | `#030305` (void black) | Page/panel background |
| Primary text | `#FFFFFF` | Key data, hero numbers |
| Secondary text | `#E5E7EB` | Supporting content |
| Muted text | `#71717A` | Timestamps, metadata |
| Accent | `#FF6B35` (ASTS orange) | Selection/active states ONLY — 5% of UI max |

**Typography:** JetBrains Mono throughout. Uppercase labels with wide tracking. Large values at 300 weight (light). No serif, no sans-serif mixing.

**Rules:** White is the hero color. Orange is surgical — never decorative. No soft shadows, no rounded consumer-app styling. Information density is a feature. Chart lines are white; only selection states get orange.
