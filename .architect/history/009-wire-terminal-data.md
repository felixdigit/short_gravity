TARGET: apps/web
---
MISSION:
Replace the stub TerminalDataProvider with a real implementation that fetches satellite telemetry from the API routes created in mandate 008. This is the highest-impact single change — it transforms the terminal from a dead skeleton into a living intelligence display. After this mandate, the globe shows 7 real satellites with orbits, the constellation matrix shows live data, and the environment strip shows space weather.

V1 REFERENCE FILES (read these for the proven patterns, then adapt imports):
- `../../_ARCHIVE_V1/short-gravity-web/lib/providers/TerminalDataProvider.tsx` (THE GOLD STANDARD — read this first)
- `../../_ARCHIVE_V1/short-gravity-web/lib/hooks/useSatellitePosition.ts` (client-side SGP4 propagation)
- `../../_ARCHIVE_V1/short-gravity-web/lib/hooks/useTLEFreshness.ts` (freshness derivation from batch-tle cache)
- `../../_ARCHIVE_V1/short-gravity-web/lib/hooks/useDivergence.ts` (source divergence)
- `../../_ARCHIVE_V1/short-gravity-web/lib/hooks/useDragHistory.ts` (BSTAR drag history)
- `../../_ARCHIVE_V1/short-gravity-web/lib/hooks/useSpaceWeather.ts` (space weather — if it exists)
- `../../_ARCHIVE_V1/short-gravity-web/lib/hooks/query-keys.ts` (shared query keys)

DIRECTIVES:

## PHASE 1: Create the satellite position hook (the core engine)

1. Read `../../_ARCHIVE_V1/short-gravity-web/lib/hooks/useSatellitePosition.ts` in full.

2. Create `src/lib/hooks/useSatellitePosition.ts`. This is the most important hook — it:
   - Fetches TLE data from `/api/satellites/batch-tle?noradIds=...`
   - Uses `satellite.js` to propagate real-time positions CLIENT-SIDE
   - Runs on a configurable interval (default ~500ms) using `setInterval` + `satellite.js` SGP4
   - Returns a `Record<noradId, SatellitePositionState>` with position, orbital params, and raw TLE lines

3. The hook must export these types (match the V1 exactly):
   ```ts
   export interface SatellitePosition {
     latitude: number; longitude: number; altitude: number; velocity: number; timestamp: Date;
   }
   export interface OrbitalParameters {
     avgAltitude: number | null; inclination: number; raan: number; bstar: number; eccentricity: number;
   }
   export interface TLEData { line1: string; line2: string; }
   export interface SatellitePositionState {
     position: SatellitePosition | null; orbital: OrbitalParameters | null;
     tle: TLEData | null; isLoading: boolean; error: Error | null;
   }
   ```

4. Export both `useSatellitePosition(noradId, intervalMs)` and `useMultipleSatellitePositions(noradIds, intervalMs)`.

5. `satellite.js` is already a dependency of `@shortgravity/core`. Add it to `apps/web/package.json` as well:
   ```
   pnpm add satellite.js
   ```

6. Also create `src/lib/hooks/query-keys.ts` to centralize query keys:
   ```ts
   export const getBatchTLEQueryKey = (noradIds: string[]) => ['batch-tle', ...noradIds.sort()]
   ```

## PHASE 2: Create the supporting hooks

7. Create `src/lib/hooks/useTLEFreshness.ts`. Copy the V1 version, adapting:
   - Remove the `import { getBatchTLEQueryKey } from './query-keys'` and use local import: `import { getBatchTLEQueryKey } from './query-keys'`
   - This hook reads from the SAME React Query cache as useSatellitePosition (shared query key on batch-tle). It does NOT make its own fetch — it derives freshness from the cached batch-tle response.
   - Export: `TLEFreshness`, `PerSatelliteFreshness`, and the `useTLEFreshness(noradIds)` hook.

8. Create `src/lib/hooks/useDivergence.ts`. Copy from V1:
   - Fetches from `/api/satellites/divergence`
   - Export: `DivergenceData` interface and `useDivergence()` hook
   - staleTime: 5min, gcTime: 30min

9. Create `src/lib/hooks/useDragHistory.ts`. Read the V1 version and adapt:
   - Fetches from `/api/satellites/${noradId}/drag-history?days=${days}`
   - Export: `DragHistoryResponse` and `useDragHistory(noradId, days)` hook
   - The response shape must match what TerminalDataProvider expects: `{ dataPoints, summary }`

10. Create `src/lib/hooks/useConjunctions.ts`:
    - Fetches from `/api/conjunctions?days=14`
    - Export: `ConjunctionEvent` interface (`{ cdmId, tca, minRange, probability, sat1, sat2 }`) and `useConjunctions()` hook
    - staleTime: 15min

11. Check if `src/lib/hooks/useSpaceWeather.ts` already exists. If it does, verify it fetches from `/api/space-weather?days=N` and the response shape matches `SpaceWeatherResponse`. If it doesn't exist, create it following the V1 pattern.

## PHASE 3: Wire the TerminalDataProvider

12. Read the current stub at `src/lib/providers/TerminalDataProvider.tsx`.

13. REWRITE IT completely based on the V1 version (`../../_ARCHIVE_V1/short-gravity-web/lib/providers/TerminalDataProvider.tsx`). The V1 version is the gold standard — follow its exact data flow:
    ```
    useMultipleSatellitePositions(NORAD_IDS, 500) → real-time positions
    useDragHistory(FM1_NORAD_ID, 45) → FM1 drag trends
    useTLEFreshness(NORAD_IDS) → TLE age per satellite
    useDivergence() → CelesTrak vs Space-Track BSTAR deltas
    useSpaceWeather(7) → latest space weather
    useConjunctions() → active conjunction warnings
    ```

14. PRESERVE the existing `TerminalDataContextType` interface and `useTerminalData()` export — widgets already depend on these. If the V1 version has additional fields (like `mapTracks` or `terminalContext`), ADD them to the context type. Do NOT remove existing fields.

15. Import constants from `@/lib/data/satellites`:
    ```ts
    import { SATELLITES_ORDERED, NORAD_IDS, FM1_NORAD_ID } from '@/lib/data/satellites'
    ```

16. The `satellites` array must be built by mapping `SATELLITES_ORDERED` and merging with position data from `useMultipleSatellitePositions`. Filter out satellites with `altitude <= 0` (failed propagation).

17. FM1 is extracted as: `satellites.find(s => s.noradId === FM1_NORAD_ID)`.

## PHASE 4: Wire GlobeWidget

18. Update `src/components/dashboard/GlobeWidget.tsx`:
    - Import `useTerminalData` from `@/lib/providers/TerminalDataProvider`
    - Get `satellites` from the context
    - Map `TerminalSatellite[]` to `SatelliteData[]` (the type Globe3D expects from `@shortgravity/ui`):
      ```ts
      const globeSatellites: SatelliteData[] = satellites.map(s => ({
        noradId: s.noradId,
        name: s.name,
        latitude: s.latitude,
        longitude: s.longitude,
        altitude: s.altitude,
        inclination: s.inclination,
        raan: /* from orbital data if available */ undefined,
        tle: /* from satellite position state if available */ undefined,
      }))
      ```
    - Pass `satellites={globeSatellites}` to `<Globe3D>`.
    - Also wire `selectedSatellite` and `onSelectSatellite` from the terminal store if they exist.

19. Update the hooks barrel export. If `src/lib/hooks/index.ts` exists, add the new hooks. If not, that's fine — individual imports work.

## PHASE 5: Verify

20. Run `pnpm install` from the monorepo root (for satellite.js). Verify exit 0.

21. Run `turbo run typecheck` from the monorepo root. Fix type errors in files you created or modified. IGNORE type errors in files you did NOT touch.

22. Do NOT run `pnpm dev` or any persistent process.

CONTEXT FOR THE AGENT:
- You are working in `apps/web`. All new files go under `src/lib/hooks/` or `src/lib/providers/`.
- `@tanstack/react-query` is already installed — use `useQuery` for all data fetching.
- `satellite.js` provides SGP4 propagation. Key functions: `twoline2satrec`, `propagate`, `gstime`, `eciToGeodetic`, `degreesLat`, `degreesLong`.
- The 7 ASTS satellites and their NORAD IDs are defined in `src/lib/data/satellites.ts`. Import from there — do NOT hardcode NORAD IDs.
- FM1 (NORAD 67232) is the newest Block 2 satellite — it gets special treatment (dedicated drag history tracking).
- The current stub TerminalDataProvider already has the correct context type shape. Widgets like ConstellationMatrix, EnvironmentStrip, FM1Monitor already consume `useTerminalData()`. Your job is to fill the empty arrays with real data.
- The V1 TerminalDataProvider is 137 lines. The new one should be similar in size — it's mostly hook composition and memoization.
- ALL hooks must have `'use client'` at the top.
- Do NOT modify widget components. Do NOT modify Globe3D. Do NOT modify any files in `packages/`.
