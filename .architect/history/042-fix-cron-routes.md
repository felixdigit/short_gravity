TARGET: apps/web
---

MISSION:
Fix all issues found in the Vercel cron route audit: tle-refresh fallback logging, filings-sync maxDuration, and add operational robustness to all 5 cron handlers.

DIRECTIVES:

1. Read `src/app/api/cron/tle-refresh/route.ts` fully.

   Fix the following:
   a. When Space-Track is unavailable and the handler falls back to CelesTrak for health detection, it currently logs misleadingly. Find the fallback code path and add an explicit log:
      ```typescript
      console.warn('[tle-refresh] Space-Track unavailable — falling back to CelesTrak for health detection (less reliable for BSTAR trends)')
      ```
   b. Verify that when Space-Track fails, the route still returns a partial success response (not a 500 error). It should return something like:
      ```json
      { "status": "partial", "celestrak": "ok", "spacetrack": "failed", "reason": "..." }
      ```
   c. Verify the Claude model ID if Haiku is used for any synthesis. Should be `claude-haiku-4-5-20251001`.

2. Read `src/app/api/cron/filings-sync/route.ts` fully.

   Fix: Change `maxDuration` from 300 to 60. Vercel Pro caps at 60 seconds — declaring 300 is misleading:
   ```typescript
   export const maxDuration = 60
   ```
   Also verify the batch size (max 5 filings per run) is sufficient to complete within 60 seconds given the 2-second per-filing rate limit (5 × 2s = 10s + network overhead = ~20-30s total, well within 60s).

3. Read `src/app/api/cron/check-feeds/route.ts` fully. Verify:
   a. No `feed_seen` table reference exists (should use inline dedup).
   b. OpenAI embedding calls have proper error handling — if OpenAI is down, the route should still save the press releases without embeddings.
   c. Discord webhook calls are wrapped in try/catch and are non-fatal.

4. Read `src/app/api/cron/daily-brief/route.ts` fully. Verify:
   a. `earnings_transcripts` is used (not `earnings_calls`) — confirm the fix is in place.
   b. All parallel queries have error handling — if one query fails (e.g., `catalysts` table is empty), the brief should still send with available data.
   c. Resend batch send handles partial failures — if some emails fail, it should log them and continue.
   d. The `RESEND_FROM_EMAIL` env var has a sensible default fallback.

5. Read `src/app/api/cron/signal-alerts/route.ts` fully. Verify:
   a. Per-signal error handling — if sending alerts for one signal fails, it should continue to the next signal.
   b. The `signal_alert_log` upsert uses the correct `onConflict` column.
   c. The 1-hour lookback window is correct and uses UTC timestamps.

6. For ALL 5 cron routes, verify they export the correct HTTP method:
   ```typescript
   export const GET = createApiHandler({ ... })
   // OR
   export const POST = createApiHandler({ ... })
   ```
   Vercel crons send GET requests by default. Verify each route handles GET.

7. For ALL 5 cron routes, verify they have `export const dynamic = 'force-dynamic'` to prevent Next.js from caching the response.

8. Run `pnpm typecheck` to verify all changes compile cleanly.
