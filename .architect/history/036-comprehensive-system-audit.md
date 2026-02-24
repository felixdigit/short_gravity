TARGET: apps/web
---

MISSION:
Comprehensive reliability and stability audit of the ENTIRE frontend system. Verify every API route against the database schema, every cron handler for correctness, every React hook for API contract alignment, and every data flow for end-to-end integrity. Fix every issue found. This is the final quality gate.

DIRECTIVES:

1. **API ROUTE AUDIT** — Read EVERY `route.ts` file under `src/app/api/`. For each route, check:

   a. **Table names** — Every Supabase table reference must match the schema. Known mismatches to hunt for:
      - `earnings_calls` → WRONG. Correct table: `earnings_transcripts`
      - `feed_seen` → may not exist as a standalone table
      - `waitlist` → verify it exists (mentioned in waitlist route)
      - `widget_cache` → verify it exists

   b. **Column names** — Every column reference must match. Known mismatches:
      - `applicant` → WRONG for `fcc_filings`. Correct column: likely `filer_name` or check the actual schema by reading the archive's `lib/supabase.ts` and checking what column names the FCC filing queries use.
      - `filed_date` → might be wrong. Check if the column is `filing_date` or `filed_at`.
      - `filing_system` CHECK constraint: only `'ICFS'`, `'ECFS'`, `'ELS'` are valid. Any route trying to filter by `filing_system='ISED'` or `filing_system='ITU'` will fail — international filings use `file_number` LIKE patterns instead.

   c. **Auth levels** — Cron routes must use `auth: 'cron'`. Admin routes must use `auth: 'admin'`. Public read routes can use `auth: 'none'`. No route should be completely unwrapped (all should use `createApiHandler`).

   d. **Error handling** — Every route must:
      - Return proper HTTP status codes (200, 400, 404, 500)
      - Not expose internal error details in responses
      - Handle null/empty query results gracefully (return `[]` or `null`, not crash)

   e. **Rate limiting** — Public-facing routes (brain query, search, waitlist) should have rate limiting configured.

   Document every issue found as you go.

2. **CRON ROUTE AUDIT** — Read every `route.ts` under `src/app/api/cron/`. For each:

   a. Verify `auth: 'cron'` is set.
   b. Verify all Supabase writes use `getServiceClient()` (service-role key), NOT the anon-key client.
   c. Verify idempotency — running the cron twice in the same period must not create duplicate records. Check for upsert patterns or dedup checks.
   d. Verify timeout safety — estimate how long each route takes. Vercel Pro plan allows up to 60s for API routes. Routes that process multiple items should have limits (e.g., max 5 filings per run for filings-sync).
   e. Verify graceful degradation — if an external API is down (CelesTrak, SEC, Resend), the route should log the error and return a partial success, not crash entirely.

3. **REACT HOOK AUDIT** — Read every file under `src/lib/hooks/`. For each hook:

   a. **URL match**: The `fetch()` URL must match an existing API route under `src/app/api/`.
      Known hooks to verify:
      - `useSatellitePosition.ts` — fetches `/api/satellites/batch-tle` and `/api/satellites/${noradId}`
      - `useDragHistory.ts` — fetches `/api/satellites/${noradId}/drag-history?days=${days}`
      - `useConjunctions.ts` — fetches `/api/conjunctions`
      - `useTLEFreshness.ts` — fetches `/api/satellites/batch-tle` (shares cache key)
      - `useDivergence.ts` — fetches divergence data
      - `useSpaceWeather.ts` — fetches `/api/space-weather`
      - `useBrainQuery.ts` — fetches `/api/brain/query`
      Verify EACH fetch URL has a corresponding route file.

   b. **Response type match**: The TypeScript interface in the hook must match what the API route actually returns. Check field names carefully — previous bugs included:
      - `sat1NoradId` vs `sat1Norad` (conjunction fields)
      - `startDate/endDate` vs `days` (drag history params)

   c. **React Query key uniqueness**: No two hooks should use the same query key for different data. Check `queryKey` arrays.

   d. **staleTime sanity**:
      - Real-time data (satellite positions): 10-30 seconds
      - Semi-static data (TLE freshness): 5-15 minutes
      - Static data (conjunctions, space weather): 15-60 minutes
      - Highly static data (drag history): 60 minutes
      Flag any staleTime that seems too aggressive or too lazy.

   e. **Shared cache keys**: `useSatellitePosition` and `useTLEFreshness` should share the same batch-tle query key. Verify their staleTime values match or are compatible.

4. **DATA PROVIDER AUDIT** — Read `src/lib/providers/TerminalDataProvider.tsx`:

   a. Verify ALL hooks are called with correct parameters.
   b. Verify data transformations preserve information (no silent data loss from incorrect mapping).
   c. Verify `useMemo` dependencies are complete — every variable used inside the memo callback must be in the dependency array.
   d. Verify the `filter((s) => s.altitude > 0)` doesn't incorrectly filter out satellites that are temporarily at 0 due to propagation delays.
   e. Verify `FM1_NORAD_ID` is correct and references an actual satellite.

5. **STORE AUDIT** — Read `src/lib/stores/terminal-store.ts`:

   a. Verify default values are sensible: `showOrbits: true`, `showCoverage: true`, `useDotMarkers: true`.
   b. Verify persist configuration only saves non-sensitive UI preferences.
   c. Verify all Zustand actions (toggleSatelliteCard, deselectSatellite, etc.) work correctly.
   d. Verify there are no stale references to removed features.

6. **GLOBE WIDGET AUDIT** — Read `src/components/dashboard/GlobeWidget.tsx`:

   a. Verify it imports `useTerminalStore` and forwards ALL display props to Globe3D: `showOrbits`, `showCoverage`, `useDotMarkers`, `selectedSatellite`, `onSelectSatellite`.
   b. Verify satellite data mapping is complete (noradId, name, latitude, longitude, altitude, inclination, tle).

7. **ENV VAR INVENTORY** — Compile a complete list of every environment variable referenced across ALL routes, crons, and lib files. Write to `src/ENV_VARS_REQUIRED.md`:

   ```
   # Required Environment Variables

   ## Supabase (all routes)
   - NEXT_PUBLIC_SUPABASE_URL
   - NEXT_PUBLIC_SUPABASE_ANON_KEY
   - SUPABASE_SERVICE_KEY

   ## Cron Authentication
   - CRON_SECRET

   ## External APIs
   - SPACE_TRACK_USERNAME
   - SPACE_TRACK_PASSWORD
   - OPENAI_API_KEY
   - ANTHROPIC_API_KEY
   - FINNHUB_API_KEY
   - ALPHA_VANTAGE_API_KEY

   ## Email
   - RESEND_API_KEY
   - RESEND_FROM_EMAIL
   - NEXT_PUBLIC_SITE_URL

   ## Social / Notifications
   - DISCORD_WEBHOOK_URL (optional)

   ## Feature flags
   - NEXT_PUBLIC_ENABLE_DEBUG_MODE
   ```
   Add any additional env vars found during the audit.

8. **FIX EVERY ISSUE FOUND** — For each problem discovered in steps 1-6:
   a. Edit the file directly to fix it.
   b. Add a comment above the fix if the change is non-obvious.
   c. Keep a running count of issues found and fixed.

9. Run `pnpm typecheck` as the FINAL verification. All type errors must be resolved.

10. Write a summary to `src/AUDIT_REPORT.md`:
    - Total files audited
    - Total issues found and fixed (with brief description of each)
    - Remaining concerns that require runtime verification (env vars, database state, external API availability)
    - Confidence level: HIGH / MEDIUM / LOW for each subsystem
