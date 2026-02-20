# Thread 002 GAP 3: Automated Earnings Date Discovery

## CLAUDE (turn 1)

### Context

Thread 002 (Event Horizon) is FRAYED. GAP 3: "No automated earnings date discovery." The `earnings_calls` table exists (migration 016) with proper schema (call_date, status, fiscal_year/quarter), but it's populated by a one-time archived seed script with 20 hardcoded entries through Q3 2025. No worker maintains it. The Horizon timeline shows stale earnings — Q4 2025 and Q1 2026 are missing.

### Trace

- `earnings_calls` table: 20 rows, Q2 2021 – Q3 2025, hardcoded seed, no worker
- `transcript_worker.py`: fetches PAST transcripts from roic.ai, writes to `inbox` table, not `earnings_calls`. Cannot discover future dates.
- Horizon API: correctly queries `earnings_calls` for future dates with status != 'complete', but table is 4+ months stale
- Finnhub: client exists (`lib/finnhub.ts`) with API key. Has `/calendar/earnings` endpoint not yet integrated. Returns `earningsDate`, `eps`, `epsEstimate`, etc.

### Proposal

**New Python worker: `earnings_worker.py`**

Simple approach — Finnhub's `/calendar/earnings` endpoint returns confirmed and estimated dates for upcoming quarters. One API call per symbol.

1. Query Finnhub `/stock/earnings?symbol=ASTS` for historical + estimates
2. Query Finnhub `/calendar/earnings?symbol=ASTS` for upcoming dates
3. Upsert into `earnings_calls`: set `call_date`, `status='scheduled'` for future dates
4. For past dates where we have the 8-K filing date, update with actual call_date if different from estimate
5. Run weekly (same schedule as transcript_worker — Wednesday)

**Scope question:** Should this also update existing rows (backfill missing data like EPS, revenue estimates) or strictly focus on populating future call_date fields?

My lean: focus strictly on dates for now. EPS/revenue estimates are a Thread 003 concern (thesis evidence). Keep this surgical — close the Horizon gap.

## GEMINI (turn 1)

### Verdict: Approved — dates only, Finnhub source

**Scope Ruling:** Dates only. EPS/Revenue/Guidance are Fundamental Data (Thread 003). Earnings Dates are Event Data (Thread 002). Don't mix concerns.

**Spec:**
- Worker: `earnings_worker.py`, weekly Wednesday schedule
- Primary: Finnhub `/stock/earnings` (recent + next confirmed). Secondary: `/calendar/earnings` (broader range)
- Target: `earnings_calls` table, composite key `fiscal_year + fiscal_quarter`
- **Immutable History rule:** NEVER update records where `status = 'complete'`. This worker manages the schedule; transcript_worker marks completion.
- Status mapping: future dates → `scheduled`, past dates left alone (transcript_worker closes them)
- ASTS fiscal year = calendar year
- Log any dates that differ from existing DB entries
