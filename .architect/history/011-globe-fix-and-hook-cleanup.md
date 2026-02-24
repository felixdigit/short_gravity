TARGET: apps/web
---
MISSION:
Fix 6 bugs from the 008–010 mandate run. The globe shows Earth but no satellites because GlobeWidget does not forward display props from the terminal store to Globe3D. Four hooks have interface/parameter mismatches with their API routes.

DIRECTIVES:

## 1. GlobeWidget — wire terminal store props (CRITICAL)

File: `src/components/dashboard/GlobeWidget.tsx`

The GlobeWidget currently only passes `satellites` to Globe3D. The terminal store holds `showOrbits`, `showCoverage`, `useDotMarkers`, `selectedSatellite` — but none of these reach Globe3D, so all default to `false` and satellites are invisible.

Fix: Import `useTerminalStore` from `@/lib/stores/terminal-store` and forward all display props.

The component should become:

```tsx
"use client";

import dynamic from "next/dynamic";
import type { SatelliteData } from "@shortgravity/ui";
import { useTerminalData } from "@/lib/providers/TerminalDataProvider";
import { useTerminalStore } from "@/lib/stores/terminal-store";

const Globe3D = dynamic(
  () =>
    import("@shortgravity/ui/components/earth/Globe3D").then((mod) => ({
      default: mod.Globe3D,
    })),
  { ssr: false }
);

export function GlobeWidget({ className }: { className?: string }) {
  const { satellites } = useTerminalData();
  const store = useTerminalStore();

  const globeSatellites: SatelliteData[] = satellites.map((s) => ({
    noradId: s.noradId,
    name: s.name,
    latitude: s.latitude,
    longitude: s.longitude,
    altitude: s.altitude,
    inclination: s.inclination,
    raan: undefined,
    tle: s.tle,
  }));

  return (
    <Globe3D
      className={className}
      satellites={globeSatellites}
      selectedSatellite={store.selectedSatellite ?? undefined}
      onSelectSatellite={(noradId) =>
        noradId
          ? store.toggleSatelliteCard(noradId)
          : store.deselectSatellite()
      }
      showOrbits={store.showOrbits}
      showCoverage={store.showCoverage}
      useDotMarkers={store.useDotMarkers}
    />
  );
}
```

## 2. useDragHistory — fix parameter mismatch

File: `src/lib/hooks/useDragHistory.ts`

The hook sends `?startDate=${startDate}&endDate=${endDate}` but the API route (`/api/satellites/[noradId]/drag-history`) reads `?days=`. Fix the hook to send `?days=${days}`.

Also trim the interfaces to match the actual API response shape. The API returns:
```json
{
  "noradId": "67232",
  "days": 45,
  "dataPoints": [{ "epoch": "...", "bstar": 0.00012, "avgAltitude": 735.2, "source": "spacetrack" }],
  "summary": { "initialBstar": 0.00012, "latestBstar": 0.00013, "bstarChangePercent": 8.33 }
}
```

Replace the entire file with:

```ts
'use client'

import { useQuery } from '@tanstack/react-query'

export interface DragDataPoint {
  epoch: string
  bstar: number
  avgAltitude: number | null
  source: string
}

export interface DragHistoryResponse {
  noradId: string
  days: number
  dataPoints: DragDataPoint[]
  summary: {
    initialBstar: number | null
    latestBstar: number | null
    bstarChangePercent: number | null
  }
}

export function useDragHistory(noradId: string, days: number = 45) {
  return useQuery<DragHistoryResponse>({
    queryKey: ['drag-history', noradId, days],
    queryFn: async () => {
      const response = await fetch(
        `/api/satellites/${noradId}/drag-history?days=${days}`
      )
      if (!response.ok) throw new Error('Failed to fetch drag history')
      return response.json()
    },
    staleTime: 60 * 60 * 1000,
    refetchInterval: 60 * 60 * 1000,
    enabled: !!noradId,
  })
}
```

## 3. useConjunctions — fix field name mismatch

File: `src/lib/hooks/useConjunctions.ts`

The interface has `sat1NoradId`/`sat2NoradId` but the API returns `sat1Norad`/`sat2Norad`. Also, `relativeSpeed` and `source` are declared but the API does not return them.

Replace the `ConjunctionEvent` interface:

```ts
export interface ConjunctionEvent {
  cdmId: string
  tca: string
  minRange: number | null
  probability: number | null
  sat1: string
  sat2: string
  sat1Norad: string | null
  sat2Norad: string | null
}
```

Remove the `relativeSpeed` and `source` fields entirely.

## 4. Conjunctions route — add norad_id filter

File: `src/app/api/conjunctions/route.ts`

The hook sends `?norad_id=` but the route never reads it. Add the filter.

After the `cutoffDate` calculation (after line 15), add:

```ts
const noradId = request.nextUrl.searchParams.get('norad_id')
```

Then modify the query. If `noradId` is provided, add an `.or()` filter:

```ts
let query = supabase
  .from('conjunctions')
  .select('cdm_id, tca, min_range_km, collision_probability, sat1_name, sat2_name, sat1_norad, sat2_norad, created_at')
  .gte('tca', cutoffDate)

if (noradId) {
  query = query.or(`sat1_norad.eq.${noradId},sat2_norad.eq.${noradId}`)
}

const { data, error } = await query
  .order('tca', { ascending: true })
  .limit(100)
```

## 5. useTLEFreshness — align staleTime with shared cache

File: `src/lib/hooks/useTLEFreshness.ts`

This hook shares the same React Query cache key (`getBatchTLEQueryKey`) as `useMultipleSatellitePositions`, but uses `staleTime: 5 * 60 * 1000` (5min) while the position hook uses `staleTime: 30 * 60 * 1000` (30min). The shorter staleTime wins, causing unnecessary refetches every 5 minutes.

Change line 53 from:
```ts
    staleTime: 5 * 60 * 1000,
```
to:
```ts
    staleTime: 30 * 60 * 1000,
```

And change line 55 from:
```ts
    refetchOnWindowFocus: true,
```
to:
```ts
    refetchOnWindowFocus: false,
```

This aligns both hooks on the same cache behavior.

## 6. TerminalDataProvider — update DragHistoryData to match trimmed interface

File: `src/lib/providers/TerminalDataProvider.tsx`

After trimming `DragHistoryResponse` in directive 2, verify the `DragHistoryData` interface and `dragHistory` memo in the provider still compile. The existing `DragHistoryData` interface (lines 44-56) uses `dataPoints[].epoch`, `.bstar`, `.avgAltitude`, `.source` and `summary.initialBstar`, `.latestBstar`, `.bstarChangePercent` — these all match the trimmed API response, so no changes should be needed here. Just confirm `tsc --noEmit` passes.

## VERIFICATION

Run `npx tsc --noEmit` from the `apps/web` directory. All changes must type-check clean.
