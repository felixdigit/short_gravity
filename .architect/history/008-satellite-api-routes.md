TARGET: apps/web
---
MISSION:
Create the 6 satellite/telemetry API routes that the terminal HUD widgets need. These are the atomic data endpoints that power the globe, constellation matrix, environment strip, and FM1 monitor. Without these routes, TerminalDataProvider has nothing to fetch. After this mandate, all 6 routes return real Supabase data.

IMPORTANT IMPORT RULES:
- Supabase client: `import { getAnonClient } from '@shortgravity/database'`, then `const supabase = getAnonClient()`
- API wrapper: `import { createApiHandler } from '@/lib/api/handler'`
- Response: `import { NextResponse } from 'next/server'`
- Follow the EXACT pattern used in the existing `src/app/api/horizon/route.ts` and `src/app/api/widgets/regulatory/route.ts`

V1 REFERENCE FILES (read these for column names and query patterns, then rewrite imports):
- `../../_ARCHIVE_V1/short-gravity-web/app/api/satellites/batch-tle/route.ts`
- `../../_ARCHIVE_V1/short-gravity-web/app/api/satellites/freshness/route.ts`
- `../../_ARCHIVE_V1/short-gravity-web/app/api/satellites/divergence/route.ts`
- `../../_ARCHIVE_V1/short-gravity-web/app/api/satellites/[noradId]/drag-history/route.ts`

DIRECTIVES:

## Route 1: `/api/satellites/batch-tle`

1. Create `src/app/api/satellites/batch-tle/route.ts`.

2. This is the PRIMARY satellite data endpoint. It reads from the `satellites` Supabase table.

3. Accept query param: `noradIds` (comma-separated NORAD IDs). Validate they are numeric, max 20.

4. Query: `supabase.from('satellites').select('norad_id, name, tle_line0, tle_line1, tle_line2, tle_epoch, tle_source, inclination, ra_of_asc_node, bstar, eccentricity, mean_motion, mean_motion_dot, period_minutes, apoapsis_km, periapsis_km, updated_at, raw_gp').in('norad_id', noradIds)`

5. Transform each row to this response shape (parse numeric strings to numbers):
   ```ts
   {
     noradId: string,
     name: string,
     tleSource: string,
     tle: { line0: string, line1: string, line2: string, epoch: string },
     orbital: {
       inclination: number | null, raan: number | null, bstar: number | null,
       avgAltitude: number | null, eccentricity: number | null, meanMotion: number | null,
       meanMotionDot: number | null, periodMinutes: number | null,
       apoapsis: number | null, periapsis: number | null
     },
     freshness: { tleEpoch: string, updatedAt: string, hoursOld: number | null }
   }
   ```
   `avgAltitude` = `(apoapsis + periapsis) / 2`. `hoursOld` = server-calculated from `tle_epoch`.

6. Filter out satellites missing TLE lines (tle_line1 or tle_line2 null).

7. Return: `{ satellites: [...], errors?: Record<string, string>, count: number, source: 'supabase', lastUpdated: ISO string }`

8. Use `createApiHandler` with `rateLimit: { windowMs: 60_000, max: 30 }`. Set `export const dynamic = 'force-dynamic'`.

## Route 2: `/api/satellites/freshness`

9. Create `src/app/api/satellites/freshness/route.ts`.

10. Query the `satellite_freshness` Supabase VIEW: `supabase.from('satellite_freshness').select('norad_id, name, tle_epoch, hours_since_epoch, freshness_status')`.

11. If the view doesn't exist (error code `42P01`), fall back to querying the `satellites` table directly: select `norad_id, name, tle_epoch`, compute hours_since_epoch server-side, derive freshness_status (FRESH <6h, OK 6-12h, STALE 12-24h, CRITICAL >24h).

12. Return: `{ satellites: [{ noradId, name, tleEpoch, hoursOld, status }], count, lastChecked: ISO string }`

13. Set `export const revalidate = 300` (5min cache).

## Route 3: `/api/satellites/divergence`

14. Create `src/app/api/satellites/divergence/route.ts`.

15. Query the `source_divergence` Supabase VIEW: `supabase.from('source_divergence').select('norad_id, ct_bstar, st_bstar, bstar_delta, diverged, ct_epoch, st_epoch, epoch_gap_hours')`.

16. If the view doesn't exist (error code `42P01` or message contains `does not exist`), return `{ satellites: [], error: 'source_divergence view not created yet' }` gracefully.

17. Transform: parse numeric strings to numbers. Return: `{ satellites: [{ noradId, ctBstar, stBstar, bstarDelta, diverged, ctEpoch, stEpoch, epochGapHours }] }`

18. Set `export const dynamic = 'force-dynamic'`.

## Route 4: `/api/satellites/[noradId]/drag-history`

19. Create `src/app/api/satellites/[noradId]/drag-history/route.ts`.

20. Read the V1 version at `../../_ARCHIVE_V1/short-gravity-web/app/api/satellites/[noradId]/drag-history/route.ts` for the exact query logic.

21. Accept query param: `days` (default 45, max 180). Extract `noradId` from route params.

22. Query `tle_history` table: filter by `norad_id`, `source = 'spacetrack'` (CRITICAL — never use CelesTrak for BSTAR/drag trends), order by `epoch` descending, limit to `days` worth of data. Select: `epoch, bstar, mean_motion, period_minutes, apoapsis_km, periapsis_km`.

23. Compute `avgAltitude` per row: `(apoapsis + periapsis) / 2`. Compute summary: initial vs latest BSTAR, percent change.

24. Return: `{ noradId, days, dataPoints: [{ epoch, bstar, avgAltitude, source }], summary: { initialBstar, latestBstar, bstarChangePercent } }`

25. Use `createApiHandler` with `rateLimit: { windowMs: 60_000, max: 30 }`.

## Route 5: `/api/space-weather`

26. Create `src/app/api/space-weather/route.ts`.

27. Accept query param: `days` (default 90, max 365).

28. Query `space_weather` table: `supabase.from('space_weather').select('date, kp_sum, ap_avg, f107_obs, f107_adj, f107_center81, sunspot_number, data_type').order('date', { ascending: false }).limit(days)`.

29. The existing `useSpaceWeather` hook expects this response shape:
    ```ts
    { days: number, count: number, data: SpaceWeatherDay[], lastUpdated: ISO string }
    ```
    Where SpaceWeatherDay = `{ date, kp_sum, ap_avg, f107_obs, f107_adj, f107_center81, sunspot_number, data_type }`.

30. Set `export const revalidate = 21600` (6h cache, matching the hook's staleTime).

## Route 6: `/api/conjunctions`

31. Create `src/app/api/conjunctions/route.ts`.

32. Accept query param: `days` (default 14, max 90). Fetch upcoming and recent conjunctions.

33. Query `conjunctions` table: `supabase.from('conjunctions').select('cdm_id, tca, min_range_km, collision_probability, sat1_name, sat2_name, sat1_norad, sat2_norad, created_at').gte('tca', cutoffDate).order('tca', { ascending: true }).limit(100)`. Where cutoffDate = `now - days`.

34. If some columns don't exist (the table may have slightly different column names), adapt gracefully. Check the V1 horizon route at `src/app/api/horizon/route.ts` which already queries this table for the confirmed column names.

35. Return: `{ data: [{ cdmId, tca, minRange, probability, sat1, sat2, sat1Norad, sat2Norad }], count, lastUpdated: ISO string }`

36. Set `export const revalidate = 900` (15min cache).

## Verification

37. Run `pnpm install` from the monorepo root. Verify exit 0.

38. Run `turbo run typecheck` from the monorepo root. Fix type errors in files you created. IGNORE type errors in files you did NOT touch.

39. Do NOT run `pnpm dev` or any persistent process.

CONTEXT FOR THE AGENT:
- You are working in `apps/web`. All new routes go under `src/app/api/`.
- Import Supabase client from `@shortgravity/database` — NEVER create a local supabase.ts file.
- `createApiHandler` is at `@/lib/api/handler`. See `src/app/api/horizon/route.ts` for the pattern.
- The `satellites` table columns include: norad_id, name, tle_line0, tle_line1, tle_line2, tle_epoch, tle_source, inclination, ra_of_asc_node, bstar, eccentricity, mean_motion, mean_motion_dot, period_minutes, apoapsis_km, periapsis_km, updated_at, raw_gp.
- The `space_weather` table columns include: date, kp_sum, ap_avg, f107_obs, f107_adj, f107_center81, sunspot_number, data_type.
- The `conjunctions` table columns (confirmed from horizon route): cdm_id, tca, min_range_km, collision_probability, sat1_name, sat2_name.
- Views (`satellite_freshness`, `source_divergence`) may or may not exist — always handle gracefully with fallbacks.
- BSTAR/drag queries MUST filter `source = 'spacetrack'`. Never use CelesTrak data for drag trend analysis (per the TLE Source Trust rules in the constitution).
