TARGET: .
---
MISSION:
Migrate the 7 API routes that the `/asts` HUD is actively calling (currently returning 404) from the V1 archive into `apps/web`. These are the data endpoints that power the terminal widgets. After this mandate, the HUD widgets receive real data from Supabase instead of empty 404s.

IMPORTANT IMPORT REWRITE RULES:
- V1 uses `import { supabase } from '@/lib/supabase'` → Replace with `import { getAnonClient } from '@shortgravity/database'`, then `const supabase = getAnonClient()`
- V1 uses `import { getServiceClient } from '@/lib/supabase'` → Replace with `import { getServiceClient } from '@shortgravity/database'`
- V1 uses `import { serverEnv } from '@/lib/env'` → Replace with direct `process.env.VARIABLE_NAME` access
- V1 uses `@/lib/anything-else` → Check if it exists in V1's `lib/` dir, copy and adapt if small, or simplify if complex

DIRECTIVES:

## PHASE 1: Supporting Libraries

1. Copy `_ARCHIVE_V1/short-gravity-web/lib/finnhub.ts` to `apps/web/src/lib/finnhub.ts`.
   - Rewrite: replace `import { serverEnv } from '@/lib/env'` with direct env access
   - Change `serverEnv.finnhub.apiKey()` → `process.env.FINNHUB_API_KEY!`
   - All other code stays the same (fetch wrapper, type definitions)

## PHASE 2: Widget Routes (Simple Supabase Queries)

2. Copy `_ARCHIVE_V1/short-gravity-web/app/api/widgets/regulatory/route.ts` to `apps/web/src/app/api/widgets/regulatory/route.ts`.
   - Rewrite Supabase imports per the rules above
   - Queries: `fcc_filings` table

3. Copy `_ARCHIVE_V1/short-gravity-web/app/api/widgets/short-interest/route.ts` to `apps/web/src/app/api/widgets/short-interest/route.ts`.
   - Rewrite Supabase imports
   - REMOVE any Python subprocess/yfinance fallback code — keep only the Supabase query path. We do not run Python subprocesses in Vercel.
   - Queries: `short_interest` table

4. Copy `_ARCHIVE_V1/short-gravity-web/app/api/widgets/cash-position/route.ts` to `apps/web/src/app/api/widgets/cash-position/route.ts`.
   - Rewrite Supabase imports
   - REMOVE any Python subprocess fallback code — keep only the Supabase query paths
   - Queries: `cash_position` table, `filings` table (fallback)

5. Copy `_ARCHIVE_V1/short-gravity-web/app/api/widgets/next-launch/route.ts` to `apps/web/src/app/api/widgets/next-launch/route.ts`.
   - This route uses direct REST API fetch with env vars — keep as-is or convert to `getAnonClient()` from `@shortgravity/database`
   - Queries: `next_launches` table

## PHASE 3: Data Routes (More Complex)

6. Copy `_ARCHIVE_V1/short-gravity-web/app/api/stock/[symbol]/route.ts` to `apps/web/src/app/api/stock/[symbol]/route.ts`.
   - Rewrite: `@/lib/finnhub` → `@/lib/finnhub` (same path alias, since we copied finnhub.ts to apps/web/src/lib/ in step 1)
   - Also copy `_ARCHIVE_V1/short-gravity-web/app/api/stock/[symbol]/candles/route.ts` to the matching path if it exists — it's a related endpoint

7. Copy `_ARCHIVE_V1/short-gravity-web/app/api/earnings/context/route.ts` to `apps/web/src/app/api/earnings/context/route.ts`.
   - Rewrite: `getServiceClient` import from `@shortgravity/database`
   - Check for any other `@/` imports and resolve them. If it imports helpers that are too complex to port, simplify the route to return the data it CAN return without those helpers. Comment out sections that need missing dependencies with a `// TODO: migrate helper` note.
   - Queries: `earnings_calls`, `inbox`, `daily_prices` tables

8. Copy `_ARCHIVE_V1/short-gravity-web/app/api/horizon/route.ts` to `apps/web/src/app/api/horizon/route.ts`.
   - Rewrite Supabase imports
   - Queries: `next_launches`, `conjunctions`, `fcc_filings`, `patents`, `earnings_calls`, `fcc_dockets`, `catalysts` tables
   - This route has many parallel queries — preserve the `Promise.all` pattern

## PHASE 4: Verify

9. Run `pnpm install` from the monorepo root (in case any new deps are needed). Verify exit 0.

10. Run `turbo run typecheck` from the monorepo root. Capture full output.
    - Fix type errors in files you created/modified.
    - IGNORE type errors in files you did NOT touch.
    - Common issues: missing type imports, Supabase client method signatures differing between versions.

11. Do NOT run `pnpm dev` or any persistent process.

CONTEXT FOR THE AGENT:
- The V1 archive is at `_ARCHIVE_V1/short-gravity-web/`. Routes are in `app/api/` (no `src/` prefix in V1). New routes go in `apps/web/src/app/api/`.
- `apps/web` already depends on `@shortgravity/database` (workspace:*).
- `@shortgravity/database` exports `getServiceClient()` and `getAnonClient()` from its index. These are singleton Supabase clients.
- `apps/web` uses the `@/` path alias mapped to `./src/*` (see `apps/web/tsconfig.json`).
- The existing `apps/web/src/app/api/signals/route.ts` uses mock data — do NOT modify it in this mandate.
- V1 routes may import from `@/lib/supabase-helpers`, `@/lib/satellite-coverage`, `@/types/`, etc. — check each import. If the needed module is small and self-contained, copy it to `apps/web/src/lib/`. If it's already in `@shortgravity/core` (like `satellite-coverage`), import from there. If it's complex, simplify or stub.
- Env vars used by these routes: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `FINNHUB_API_KEY`. These should already be in `.env.local`.
- Do NOT create `apps/web/src/lib/supabase.ts` — use `@shortgravity/database` directly. That IS the Supabase client layer.
