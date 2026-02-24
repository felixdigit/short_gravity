TARGET: apps/web
---

MISSION:
Migrate the three core (non-email) Vercel cron route handlers from the V1 archive. These are the data ingestion backbone: TLE satellite tracking (dual-source CelesTrak + Space-Track), SEC/press release feed monitoring, and SEC EDGAR filing sync.

DIRECTIVES:

1. Create directory `src/app/api/cron/tle-refresh/` and copy the route handler from `../../_ARCHIVE_V1/short-gravity-web/app/api/cron/tle-refresh/route.ts` into it as `route.ts`.

   AUDIT the copied file thoroughly:
   a. Verify it imports `createApiHandler` from `@/lib/api/handler` and `getServiceClient` from `@/lib/supabase` — both must exist (created in mandate 031).
   b. Verify it uses `auth: 'cron'` in the handler config.
   c. Verify Supabase table names: `satellites` (upsert), `tle_history` (insert), `signals` (insert for anomalies).
   d. Verify `tle_history` unique constraint columns: `norad_id`, `epoch`, `source`.
   e. Verify Space-Track credentials come from `process.env.SPACE_TRACK_USERNAME` and `process.env.SPACE_TRACK_PASSWORD`.
   f. Verify CelesTrak endpoints use HTTPS URLs (e.g., `https://celestrak.org/NORAD/elements/supplemental/...`).
   g. Verify source tagging: CelesTrak data tagged `source: 'celestrak'`, Space-Track tagged `source: 'spacetrack'`.
   h. Verify health anomaly detection uses Space-Track data ONLY (per SOURCE-AWARE MANDATE in architecture docs).
   i. Verify maneuver detection uses CelesTrak data ONLY.
   j. If the route imports any lib files that don't exist (e.g., `@/lib/space-track`, `@/lib/celestrak`), check if those files exist in `src/lib/`. If not, copy them from the archive at `../../_ARCHIVE_V1/short-gravity-web/lib/`. Common candidates: `space-track.ts`, `celestrak.ts`.

2. Create directory `src/app/api/cron/check-feeds/` and copy from `../../_ARCHIVE_V1/short-gravity-web/app/api/cron/check-feeds/route.ts`.

   AUDIT:
   a. Verify table names: `press_releases` (upsert), `brain_chunks` (insert for inline embeddings).
   b. Check if it references a `feed_seen` table for deduplication. If this table doesn't exist in the schema, the route needs a fallback — either create inline dedup logic using `press_releases` existing records, or use a SHA-256 content hash check against existing rows.
   c. Verify OpenAI embedding integration uses `text-embedding-3-small` model with 1536 dimensions.
   d. Verify the `openai` package is available (it is — already in package.json).
   e. Verify Discord webhook notification is OPTIONAL — the route must NOT crash if `DISCORD_WEBHOOK_URL` is not set. Wrap Discord calls in try/catch or guard with `if (process.env.DISCORD_WEBHOOK_URL)`.
   f. Verify RSS/Atom parsing works with regex (no external XML parser dependency).
   g. Env vars needed: `OPENAI_API_KEY` (required for embedding), `DISCORD_WEBHOOK_URL` (optional).

3. Create directory `src/app/api/cron/filings-sync/` and copy from `../../_ARCHIVE_V1/short-gravity-web/app/api/cron/filings-sync/route.ts`.

   AUDIT:
   a. Verify table name: `filings` with columns `accession_number`, `form`, `filing_date`, `content_text`, `status`, `url`, `file_size`, `items`, `report_date`.
   b. Verify SEC CIK for ASTS is `0001780312`.
   c. Verify rate limiting: 2-second delay between individual filing fetches.
   d. Verify max 5 filings per cron run (Vercel function timeout safety — default 10s, Pro plan up to 60s).
   e. Verify filing status lifecycle: creates with `status: 'pending'`, updates to `'processing'`, then `'completed'` or `'failed'`.
   f. Verify SEC EDGAR User-Agent header is set (SEC requires identifying user agent).
   g. Verify deduplication: checks existing `accession_number` values before inserting.
   h. No external package dependencies beyond stdlib fetch.

4. For ALL three routes, verify error handling:
   - Each route should catch top-level errors and return proper JSON responses with status codes.
   - Database errors should not expose internal details to the response.
   - Network failures (CelesTrak down, SEC timeout) should be logged but not crash the handler.
   - Each route should return a summary JSON on success (e.g., `{ updated: N, errors: [] }`).

5. Run `pnpm typecheck` to verify all three routes compile without errors.

6. If any typecheck errors occur due to missing lib imports, trace the import chain. Common missing files to check for and copy from archive:
   - `src/lib/celestrak.ts` (CelesTrak API wrapper with 6h cache)
   - `src/lib/space-track.ts` (Space-Track API wrapper with auth)
   - `src/lib/finnhub.ts` (might be imported indirectly)
   Copy only what's needed. Fix any remaining type errors.
