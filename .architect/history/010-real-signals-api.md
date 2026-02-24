TARGET: apps/web
---
MISSION:
Replace the mock signals API with real Supabase data. The `/api/signals` route currently imports `generateMockSignals()` from `@shortgravity/core` and returns 3 fake signals. The `signals` table in Supabase is populated twice daily by the signal_scanner worker and contains real cross-source anomaly detections. After this mandate, the SignalFeed widget shows real intelligence signals.

DIRECTIVES:

1. Read the current mock route at `src/app/api/signals/route.ts`. Understand the response shape it returns — the `useSignals` hook and `SignalFeed` widget depend on this exact shape.

2. REWRITE `src/app/api/signals/route.ts` to query the real `signals` Supabase table instead of calling `generateMockSignals()`.

3. Import pattern:
   ```ts
   import { NextRequest, NextResponse } from 'next/server'
   import { createApiHandler } from '@/lib/api/handler'
   import { getAnonClient } from '@shortgravity/database'
   ```

4. The `signals` table has these columns (query with `select`):
   - `id` (bigserial) — primary key
   - `signal_type` (text) — e.g., 'ORB-DEV', 'REG-UNU', 'FIN-ANOM'
   - `severity` (text) — 'critical', 'high', 'medium', 'low'
   - `category` (text, nullable) — grouping category
   - `title` (text) — human-readable title
   - `description` (text, nullable) — detailed description
   - `source_table` (text) — originating data table
   - `source_id` (text, nullable) — reference ID in source table
   - `entity_name` (text, nullable) — entity involved
   - `observed_value` (numeric, nullable)
   - `baseline_value` (numeric, nullable)
   - `z_score` (numeric, nullable)
   - `raw_data` (jsonb, nullable) — additional structured data
   - `fingerprint` (text, unique) — dedup key
   - `detected_at` (timestamptz)
   - `expires_at` (timestamptz, nullable)
   - `created_at` (timestamptz)

5. The response MUST match the existing shape that `useSignals` expects:
   ```ts
   interface SignalResponse {
     id: number
     signal_type: string
     severity: string
     category: string | null
     title: string
     description: string | null
     source_refs: Array<{ table: string; id: string; title: string; date: string }>
     metrics: Record<string, unknown>
     confidence_score: number | null
     price_impact_24h: number | null
     fingerprint: string
     detected_at: string
     expires_at: string
     created_at: string
   }
   ```

6. Map the Supabase columns to this response shape:
   - `source_refs`: Build from `source_table`, `source_id`, `entity_name`, `detected_at`
   - `metrics`: Build from `observed_value`, `baseline_value`, `z_score`, plus spread `raw_data`
   - `confidence_score`: Derive from z_score: `Math.min(Math.abs(z_score) / 10, 1)` (or null if no z_score)
   - `price_impact_24h`: null for now (future enhancement)

7. Support the existing query params (the current mock route already handles these):
   - `severity` — filter by severity level
   - `type` — filter by signal_type
   - `limit` — max results (default 50)
   - `offset` — pagination offset (default 0)

8. Query: order by `detected_at` descending (newest first). Filter out expired signals: `expires_at` is null OR `expires_at > now()`.

9. Return: `{ data: SignalResponse[], count: number }` — same shape as the current mock response.

10. Use `createApiHandler` with `rateLimit: { windowMs: 60_000, max: 60 }`. Set `export const revalidate = 300` (5min cache).

11. REMOVE the import of `generateMockSignals` from `@shortgravity/core`. The mock function is no longer needed by this route.

12. If the `signals` table is empty or the query returns no results, return `{ data: [], count: 0 }` — the widget already handles empty state gracefully.

## Verification

13. Run `turbo run typecheck` from the monorepo root. Fix type errors in the file you modified. IGNORE type errors in files you did NOT touch.

14. Do NOT run `pnpm dev` or any persistent process.

CONTEXT FOR THE AGENT:
- You are modifying ONE file: `src/app/api/signals/route.ts`.
- The `useSignals` hook at `src/lib/hooks/useSignals.ts` already fetches from this endpoint with the correct query params. Do NOT modify the hook.
- The `SignalFeed` widget already renders the signals. Do NOT modify the widget.
- The signal_scanner worker runs twice daily (13:00 + 21:00 UTC) and writes to the `signals` table with a unique `fingerprint` for dedup.
- If column names don't exactly match what's listed above, adapt gracefully. The critical ones are: id, signal_type, severity, title, fingerprint, detected_at, created_at.
- Do NOT remove `generateMockSignals` from `@shortgravity/core` — other code may reference it. Just remove the import from this route file.
