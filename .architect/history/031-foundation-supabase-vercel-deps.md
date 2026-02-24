TARGET: apps/web
---

MISSION:
Establish the foundation layer required by all cron routes and server-side API routes — the Supabase service client (`getServiceClient`), Vercel cron schedule configuration, and email package dependencies. Nothing else can run until this is in place.

DIRECTIVES:

1. Copy the Supabase service client library from the V1 archive into the monorepo. The source file is at `../../_ARCHIVE_V1/short-gravity-web/lib/supabase.ts`. Copy it to `src/lib/supabase.ts`. This file exports:
   - `getServiceClient()` — creates a Supabase client with `SUPABASE_SERVICE_KEY` (service-role, full DB access). Required by ALL cron routes and server-side mutations.
   - `sanitizeSearchQuery()` — escapes SQL wildcards for safe `ilike` patterns.
   - `supabase` proxy — lazy-initialized anon-key client for read-only queries.
   - Data access helpers: `getFilingsFeed`, `getSatellitesByNoradIds`, `getTLEHistory`, `getSatelliteFreshness`, `getBstarTrends`, `searchGlossaryTerms`, `getGlossaryTerm`, `getGlossaryCitations`, `getGlossaryCategories`, `getGlossaryCount`.
   Keep the file exactly as-is — all `@/lib/` and `@supabase/supabase-js` imports are compatible with the monorepo.

2. AUDIT the copied `src/lib/supabase.ts`:
   - Verify `getServiceClient()` reads `NEXT_PUBLIC_SUPABASE_URL` and `SUPABASE_SERVICE_KEY` env vars.
   - Verify it throws clear errors if either is missing (never falls back to anon key).
   - Verify the singleton pattern (caches the client instance so we don't create new connections per request).
   - Verify all table names in data helpers match the schema: `filings`, `satellites`, `tle_history`, `satellite_freshness`, `bstar_trends`, `glossary_terms`, `glossary_citations`.

3. Create `vercel.json` in the `apps/web/` root directory (NOT the monorepo root — Vercel reads it from the project directory). Content:
```json
{
  "crons": [
    { "path": "/api/cron/tle-refresh", "schedule": "0 */4 * * *" },
    { "path": "/api/cron/check-feeds", "schedule": "*/15 * * * *" },
    { "path": "/api/cron/filings-sync", "schedule": "*/15 * * * *" },
    { "path": "/api/cron/daily-brief", "schedule": "0 12 * * *" },
    { "path": "/api/cron/signal-alerts", "schedule": "*/15 * * * *" }
  ]
}
```

4. Add email dependencies to `package.json`. Add these two packages to the `"dependencies"` section:
   - `"resend": "^6.9.2"`
   - `"@react-email/components": "^1.0.7"`
   Then run `cd ../.. && pnpm install` to install and update the lockfile.

5. Verify `src/lib/api/handler.ts` exists and is functional. Read it and confirm:
   - It exports `createApiHandler(config)` which wraps route handlers.
   - The `config.auth` option supports `'cron'` mode.
   - Cron auth checks `CRON_SECRET` env var against `x-vercel-cron-secret` header, `Authorization: Bearer` header, and QStash signature header.
   - It falls through to allow in `NODE_ENV === 'development'`.
   If this file is missing, copy from `../../_ARCHIVE_V1/short-gravity-web/lib/api/handler.ts`.

6. Verify `src/lib/rate-limit.ts` exists (imported by handler.ts). If missing, copy from `../../_ARCHIVE_V1/short-gravity-web/lib/rate-limit.ts`. Read and confirm it exports `rateLimit()` and `rateLimitResponse()`.

7. Check if there's an existing `src/lib/supabase.ts` that would conflict. If one already exists, merge the `getServiceClient()` function into it rather than overwriting. The critical exports are `getServiceClient` and `sanitizeSearchQuery`.

8. Run `pnpm typecheck` from `apps/web/` to verify zero type errors. Fix any issues.
