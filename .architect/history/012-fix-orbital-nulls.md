TARGET: apps/web
---
MISSION:
Wire the 3 null orbital fields (periodMinutes, apoapsis, periapsis) in TerminalDataProvider from the batch-tle API response. Currently hardcoded to null despite the API returning real values.

DIRECTIVES:

1. Open `src/lib/providers/TerminalDataProvider.tsx`.

2. In the `satellites` useMemo (the `.map()` inside around line 100-118), change these three lines:

FROM:
```ts
          periodMinutes: null,
          apoapsis: null,
          periapsis: null,
```

TO:
```ts
          periodMinutes: s?.orbital?.periodMinutes ?? null,
          apoapsis: s?.orbital?.apoapsis ?? null,
          periapsis: s?.orbital?.periapsis ?? null,
```

The variable `s` is `positions[id]` which comes from `useMultipleSatellitePositions`. Its shape is `SatellitePositionState` which has `orbital: OrbitalParameters | null`. The batch-tle API returns `orbital.periodMinutes`, `orbital.apoapsis`, and `orbital.periapsis` — these values are already in the React Query cache but never read.

3. Check that `OrbitalParameters` in `src/lib/hooks/useSatellitePosition.ts` does NOT already have `periodMinutes`, `apoapsis`, or `periapsis` fields. If missing, add them:

```ts
export interface OrbitalParameters {
  avgAltitude: number | null
  inclination: number
  raan: number
  bstar: number
  eccentricity: number
  periodMinutes?: number | null
  apoapsis?: number | null
  periapsis?: number | null
}
```

4. In the same file (`useSatellitePosition.ts`), in the `useMultipleSatellitePositions` function, check the orbital mapping inside the `satellites.forEach` callback. The batch-tle API returns `orbital` as an object. The code currently does `orbital: orbital || null`. Verify that the orbital object from the API includes periodMinutes, apoapsis, periapsis — it does (check the batch-tle route at `src/app/api/satellites/batch-tle/route.ts` lines 86-89 which return `periodMinutes`, `apoapsis`, `periapsis`).

5. Run `npx tsc --noEmit` to verify.
