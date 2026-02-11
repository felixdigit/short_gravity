# Short Gravity — Insights

Compounding knowledge from building. These inform architecture and product decisions.

---

## Satellite Tracking

### TLE is the public interface (2026-02-01)
- A TLE (Two-Line Element) is not a position — it's a mathematical model of an orbit at a specific moment
- Space-Track TLEs + SGP4 propagation = ~1km accuracy, degrades over time
- Accuracy: <1km at 0-6hrs, 1-5km at 6-24hrs, garbage after a week
- Good enough for visualization and monitoring, not for collision avoidance
- "Real-time" is an illusion — TLEs update every 8-12 hours from Space-Track
- satellite.js recalculates position client-side every 500ms using the same static TLE

### The alpha is in metadata patterns (2026-02-01)
Position accuracy isn't the edge. Pattern recognition is:
- **B* drag history** — detecting orbital decay or maneuvers before anyone else
- **TLE epoch gaps** — if Space-Track stops updating a satellite, something's wrong
- **Cross-referencing** — SEC filings + FCC applications + launch manifests reveal intent
- The position on the globe is just visualization. The alpha is in the metadata.

### Alternatives to TLE (2026-02-01)
| Method | Accuracy | Access |
|--------|----------|--------|
| TLE + SGP4 | ~1 km | Public (Space-Track) |
| Ephemeris (SP3) | ~1-10 m | Limited |
| Operator telemetry | Exact | Private (ASTS has this) |
| Commercial tracking (LeoLabs) | ~10 m | $10K+/month |

For our use case, TLE is correct. It's what NASA Eyes, Celestrak, N2YO all use.

---

## Data Architecture

### Space-Track caching strategy (2026-02-01)
- Current: In-memory cache (60 min) — fragile, loses data on restart
- Better: Persist TLEs to Supabase, refresh every 4-6 hours via worker
- The `tle_history` and `satellites` tables exist in schema but aren't used yet
- API routes should read from Supabase first, fallback to Space-Track on miss

---

## UI/Design

### Tactical HUD aesthetic (2026-02-01)
- White is the hero — let it pop against true black
- Orange is surgical — selection/active states ONLY (5% of UI)
- No decorative color, no cyan overuse
- Source of truth: `globals.css` CSS variables, not markdown docs

---

## Product

### What Short Gravity actually is (2026-02-01)
A **targeting system** for space sector intelligence, not just a satellite tracker:
- Real-time constellation monitoring (7 ASTS satellites)
- Orbital health via B* drag coefficient trends
- Cross-referenced with SEC filings, stock data, FCC applications
- The terminal is Bloomberg for space — dense, precise, actionable

---

## RAG Archive (2026-02-04)

### Scale and composition
- **4,000+ searchable records** across 4 tables
- SEC filings: 530 (full document text + AI summaries)
- FCC filings: 666 (structured metadata + AI summaries)
- Patents: 307 (29 families, 7 jurisdictions)
- Patent claims: 2,482+ individual claim texts
- This is the foundation for the Brain — all queryable via Supabase full-text search

### XBRL bug in filing worker (2026-02-04)
- **29 high-signal filings (10-Q, 10-K) store XBRL metadata instead of readable text**
- Root cause: `filing_worker.py` HTML parser doesn't handle iXBRL format
- iXBRL embeds hidden XBRL data in `<div style="display:none">` — parser extracts it as text
- **Summaries still work** (Claude generates from content before storage) — full-text search is broken
- Fix: Strip `display:none` divs and `<ix:header>` sections before tag removal
- 29 filings need reprocessing after fix deployed

---

## Patent Intelligence (2026-02-05)

### ASTS patent portfolio mapped
- **307 patents**: 133 granted, 174 pending across 7 jurisdictions
- US dominates (164), then KR (31), EP (31), JP (30), WO (21), AU (18), CA (10)
- 29 patent families — each family filed across multiple countries
- **Key tech categories**: LEO deployable structures (40+), MIMO/beamforming (25+), satellite-cellular direct (20+), fractionated satellites (15+), phased array (15+)

### Data quality gaps identified
- Titles: ~60% populated (many "[no title]" entries)
- Abstracts: 17% — needs backfill
- Figure URLs: 35% — Gabriel wants 100% ("We want a source of truth")
- AI summaries: 0% — not generated yet
- Claims: 72% of patents have claims (75 patents missing)

### Patent worker pipeline (2026-02-05)
- Unified `patent_worker_v2.py` — 5-stage pipeline (discover → claims → enrich → cleanup → report)
- Sources: PatentsView API (US), EPO OPS (international), Google Patents scraping (titles/abstracts/figures)
- Deployed on GitHub Actions daily cron (6 AM UTC, 60 min timeout)
- Google Patents scraping via Playwright is the bottleneck — timeouts on KR/JP pages

---

## Brain Architecture (2026-02-06)

### Unified AI research interface designed
- Single `/api/brain/query` endpoint searches ALL data sources in parallel
- RAG pipeline: search → rank/dedupe → Claude Haiku synthesizes with citations
- Cost: ~$0.001 per query (Haiku for search, Sonnet only for complex synthesis)
- Context window managed: limit to ~50K tokens per query

### External distribution strategy
- **MCP Server**: Publish as Claude tool — other Claude users can query ASTS data directly
- **Custom GPT**: OpenAI action pointing to our API
- **Public API**: Rate-limited free tier for developers
- Goal: become THE source of truth for ASTS data, not just for us

### Spacemob Knowledge Base schema designed
- Full schema for community intelligence: `voices`, `posts`, `events`, `alpha`, `entities`
- Tracks X accounts + Reddit users with reliability scores
- `alpha` table for extracted insights with confidence levels and validation status
- `events` table for curated timeline (the digital museum)
- Storage estimate: ~150-250 MB, well within Supabase free tier

---

## Skills System (2026-02-07)

### Atomic skill architecture
- 6 skills built: `research-filings`, `run-filing-worker`, `satellite-data`, `write-article`, `write-x-post`, `nano-banana`
- Skills are **atomic capabilities, not pipelines** — each does one thing
- Orchestration happens in conversation: invoke one, use output, invoke next
- Skills cannot call other skills — this is by design
- Gabriel's workflow: research → write → visualize (chain skills conversationally)
