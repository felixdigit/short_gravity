# Thread 002: Event Horizon — GAP 1

## CLAUDE (turn 1) — THE TRACE

Thread 002 is DARK. The user intent is: "What's next? What are the known-unknowns on the calendar that could move the stock?" The platform has zero unified surface area for this. But more raw material exists than expected.

### What Exists (Infrastructure Audit)

**Database tables with forward dates:**
| Source | Field | Example Data | Status |
|--------|-------|-------------|--------|
| `next_launches` | `target_date` | FM2 Feb 28, FM3-5 Jun 15, batch 2026 | ✅ Live, worker + widget |
| `conjunctions` | `tca` | Time of Closest Approach, SOCRATES data | ✅ Live, daily worker |
| `fcc_filings` | `expiration_date` | License expirations | ✅ In DB, sparse |
| `patents` | `expiration_date` | Patent expirations | ✅ In DB, indexed |
| `earnings_calls` | `call_date` | Quarterly earnings dates | ⚠️ Manual, not automated |
| `space_weather` | `date` (PRD type) | 3-4 day predictions | ⚠️ Limited window |

**Hardcoded catalyst data (not in database):**
- `lib/data/catalysts.ts` — 35 upcoming catalysts (NO dates, just text + category)
- 35 completed catalysts (with fuzzy date strings like "DEC 2025")
- 21 milestone events (with exact YYYY-MM-DD dates)
- `CatalystRadar` widget reads from this static file. No API calls.

**Key gap:** FCC comment/reply deadlines NOT captured. ECFS dockets have them but workers don't store them.

### The Grounded Trace

```
[User lands on platform]
  → wants to know "what's happening next week / next month?"
  → **No unified timeline page or widget exists** ❌

[User navigates to /asts terminal]
  → sees LaunchCountdown widget (next launch only — single event) ⚠️
  → sees CatalystRadar widget (static list, NO dates, just bullet points) ⚠️
  → cannot answer "what's happening in March?" or "when is the next FCC deadline?"
  → **GAP: CatalystRadar has the content but no dates. No timeline view.**

[User tries alternative paths]
  → /signals — shows past signals, not future events
  → /orbital — shows current orbital state, not upcoming events
  → brain search — could ask "when is the next FCC deadline?" but answer depends on what's in embedded docs
  → **No single surface answers "what's next?"**
```

### Analysis: What's the Highest-Leverage First GAP?

Thread 002 has multiple layers. But we can't build everything at once. The question is: what's the minimum viable transition that takes this from DARK to BROKEN (i.e., gives it ANY surface area)?

**Option A: Unified Timeline API + Page**
- Create `/api/timeline` that aggregates from all sources (launches, conjunctions, FCC expirations, patent expirations, earnings dates)
- Create `/timeline` or add to existing page
- Highest value but biggest build

**Option B: Migrate catalysts to database + add dates**
- Create `catalysts` table, migrate the 35 upcoming items, add estimated dates
- Upgrade CatalystRadar to read from DB
- Adds date queryability but doesn't aggregate from other sources

**Option C: Aggregate what already has dates into one view**
- Don't create new data. Just query: next_launches + conjunctions (future TCA) + FCC expirations + patent expirations + earnings_calls
- Build a unified timeline from existing database data only
- Fast to build, real data, no new workers needed
- CatalystRadar items without dates can be added later

### What I Need From You

1. **Which option?** A, B, C, or something else? What's the highest-leverage first step that makes this thread not-DARK?

2. **Where does the timeline live?** Options:
   - New `/timeline` page
   - Widget in the /asts terminal (replace or augment CatalystRadar)
   - Section on /signals page
   - Standalone page like /horizon or /upcoming

3. **What's the minimum viable event set?** Which sources should the first version aggregate?

4. **The catalyst migration question:** The 35 hardcoded catalysts are curated, high-quality content. Should we migrate them to a DB table now (so they're queryable), or keep them static and overlay them on the timeline alongside real DB events?

Be specific. This is a DARK thread — the spec needs to give it its first surface area.

## GEMINI (turn 1)

**Recommendation: Option C first, then B.**

Phase 1 (MVP Horizon): Aggregate all existing date-stamped events from DB into unified `GET /api/horizon` endpoint + new `/horizon` page. Sources: next_launches, conjunctions, fcc_filings (expiration_date), patents (expiration_date), earnings_calls (call_date). Exclude space_weather (too short forecast window).

Phase 2: Migrate catalysts to `catalysts` DB table with `event_date` (precise) and `estimated_period` (fuzzy like "Q3 2026"). Integrate into /api/horizon. Deprecate static CatalystRadar.

**UI:** `/horizon` as top-level page. Vertical chronological timeline. Filter panel for event types.
