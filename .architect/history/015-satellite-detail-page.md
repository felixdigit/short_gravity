TARGET: apps/web
---
MISSION:
Build the per-satellite detail page at /satellite/[noradId] and the missing single-satellite API route.

DIRECTIVES:

## 1. Create the single-satellite API route

Create `src/app/api/satellites/[noradId]/route.ts`:

```ts
import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const dynamic = 'force-dynamic'

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 60 },
  handler: async (request, ctx) => {
    const supabase = getAnonClient()
    const { noradId } = await ctx!.params

    if (!/^\d+$/.test(noradId)) {
      return NextResponse.json({ error: 'Invalid NORAD ID' }, { status: 400 })
    }

    const { data, error } = await supabase
      .from('satellites')
      .select('norad_id, name, tle_line0, tle_line1, tle_line2, tle_epoch, tle_source, inclination, ra_of_asc_node, bstar, eccentricity, mean_motion, mean_motion_dot, period_minutes, apoapsis_km, periapsis_km, updated_at')
      .eq('norad_id', noradId)
      .single()

    if (error || !data) {
      return NextResponse.json(
        { error: `Satellite ${noradId} not found` },
        { status: 404 }
      )
    }

    const sf = (v: unknown): number | null => {
      if (v == null || v === '') return null
      const n = parseFloat(String(v))
      return isNaN(n) ? null : n
    }

    const apoapsis = sf(data.apoapsis_km)
    const periapsis = sf(data.periapsis_km)

    return NextResponse.json({
      noradId: data.norad_id,
      name: data.name,
      tle: data.tle_line1 && data.tle_line2 ? {
        line0: data.tle_line0 || `0 ${data.name}`,
        line1: data.tle_line1,
        line2: data.tle_line2,
        epoch: data.tle_epoch,
        bstar: sf(data.bstar),
      } : null,
      metadata: {
        orbit: {
          inclination: sf(data.inclination),
          raan: sf(data.ra_of_asc_node),
          eccentricity: sf(data.eccentricity),
          apogee: apoapsis,
          perigee: periapsis,
        },
      },
      freshness: {
        tleEpoch: data.tle_epoch,
        updatedAt: data.updated_at,
        hoursOld: data.tle_epoch
          ? (Date.now() - new Date(data.tle_epoch).getTime()) / (1000 * 60 * 60)
          : null,
        source: data.tle_source || 'unknown',
      },
    })
  },
})
```

IMPORTANT: This route's response shape must match what `useSatellitePosition` expects. Check `src/lib/hooks/useSatellitePosition.ts` — the single `useSatellitePosition(noradId)` hook fetches from `/api/satellites/${noradId}` and reads `data.tle.line1`, `data.tle.line2`, `data.tle.bstar`, `data.metadata.orbit.inclination`, `data.metadata.orbit.raan`, `data.metadata.orbit.eccentricity`, `data.metadata.orbit.apogee`, `data.metadata.orbit.perigee`. Ensure the response shape matches exactly.

## 2. Create the satellite detail page

Create `src/app/satellite/[noradId]/page.tsx`:

```tsx
'use client'

import { use } from 'react'
import { Panel, Text, Stat, Muted, StatusDot } from '@shortgravity/ui'
import { useSatellitePosition } from '@/lib/hooks/useSatellitePosition'
import { useDragHistory } from '@/lib/hooks/useDragHistory'
import { getSatelliteInfo } from '@/lib/data/satellites'

export default function SatelliteDetailPage({
  params,
}: {
  params: Promise<{ noradId: string }>
}) {
  const { noradId } = use(params)
  const { position, orbital, tle, isLoading, error } = useSatellitePosition(noradId)
  const { data: dragData, isLoading: dragLoading } = useDragHistory(noradId, 45)
  const satInfo = getSatelliteInfo(noradId)

  return (
    <div className="min-h-screen bg-[#030305] text-white font-mono">
      <div className="max-w-4xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="mb-10">
          <div className="flex items-center gap-3 mb-1">
            <StatusDot status={position ? 'online' : isLoading ? 'inactive' : 'error'} />
            <h1 className="text-2xl font-light tracking-wider">
              {satInfo?.name ?? `NORAD ${noradId}`}
            </h1>
          </div>
          <div className="flex gap-4 text-xs text-white/30">
            <span>NORAD {noradId}</span>
            {satInfo?.type && <span>{satInfo.type}</span>}
            {satInfo?.fullName && <span>{satInfo.fullName}</span>}
            {satInfo?.launch && <span>LAUNCHED {satInfo.launch}</span>}
          </div>
        </div>

        {error && (
          <div className="border border-red-400/20 bg-red-400/5 rounded-lg p-4 mb-8 text-xs text-red-400">
            {error.message}
          </div>
        )}

        {/* === LIVE TELEMETRY === */}
        <section className="mb-12">
          <h2 className="text-xs text-white/40 tracking-widest mb-4">LIVE TELEMETRY</h2>
          {isLoading ? (
            <div className="text-xs text-white/20">Acquiring telemetry...</div>
          ) : position ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="border border-white/[0.06] rounded-lg p-4">
                <div className="text-[10px] text-white/30 mb-1">LATITUDE</div>
                <div className="text-xl font-light tabular-nums">
                  {position.latitude.toFixed(4)}°
                </div>
              </div>
              <div className="border border-white/[0.06] rounded-lg p-4">
                <div className="text-[10px] text-white/30 mb-1">LONGITUDE</div>
                <div className="text-xl font-light tabular-nums">
                  {position.longitude.toFixed(4)}°
                </div>
              </div>
              <div className="border border-white/[0.06] rounded-lg p-4">
                <div className="text-[10px] text-white/30 mb-1">ALTITUDE</div>
                <div className="text-xl font-light tabular-nums">
                  {position.altitude.toFixed(1)}
                  <span className="text-xs text-white/40 ml-1">km</span>
                </div>
              </div>
              <div className="border border-white/[0.06] rounded-lg p-4">
                <div className="text-[10px] text-white/30 mb-1">VELOCITY</div>
                <div className="text-xl font-light tabular-nums">
                  {position.velocity.toFixed(3)}
                  <span className="text-xs text-white/40 ml-1">km/s</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-xs text-white/20">No position data available</div>
          )}
        </section>

        {/* === ORBITAL PARAMETERS === */}
        <section className="mb-12">
          <h2 className="text-xs text-white/40 tracking-widest mb-4">ORBITAL PARAMETERS</h2>
          {orbital ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-8 gap-y-3">
              {[
                { label: 'INCLINATION', value: orbital.inclination?.toFixed(4), unit: '°' },
                { label: 'RAAN', value: orbital.raan?.toFixed(4), unit: '°' },
                { label: 'ECCENTRICITY', value: orbital.eccentricity?.toFixed(6), unit: '' },
                { label: 'B* DRAG', value: orbital.bstar?.toExponential(2), unit: '' },
                { label: 'AVG ALTITUDE', value: orbital.avgAltitude?.toFixed(1), unit: 'km' },
              ].map(({ label, value, unit }) => (
                <div key={label} className="flex justify-between border-b border-white/[0.03] py-2">
                  <span className="text-[11px] text-white/30">{label}</span>
                  <span className="text-[11px] text-white/60 tabular-nums">
                    {value ?? '—'}{value && unit ? ` ${unit}` : ''}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-white/20">No orbital data</div>
          )}
        </section>

        {/* === TLE DATA === */}
        {tle && (
          <section className="mb-12">
            <h2 className="text-xs text-white/40 tracking-widest mb-4">TLE</h2>
            <div className="bg-white/[0.02] border border-white/[0.06] rounded-lg p-4 font-mono text-[11px] text-white/50 leading-relaxed">
              <div>{tle.line1}</div>
              <div>{tle.line2}</div>
            </div>
          </section>
        )}

        {/* === DRAG HISTORY === */}
        <section className="mb-12">
          <h2 className="text-xs text-white/40 tracking-widest mb-4">DRAG HISTORY (45 DAYS)</h2>
          {dragLoading ? (
            <div className="text-xs text-white/20">Loading drag data...</div>
          ) : !dragData?.dataPoints?.length ? (
            <div className="text-xs text-white/20">No drag history available</div>
          ) : (
            <>
              {dragData.summary && (
                <div className="flex gap-8 mb-4">
                  <div>
                    <div className="text-[10px] text-white/30">INITIAL B*</div>
                    <div className="text-sm text-white/70 tabular-nums">
                      {dragData.summary.initialBstar?.toExponential(2) ?? '—'}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-white/30">LATEST B*</div>
                    <div className="text-sm text-white/70 tabular-nums">
                      {dragData.summary.latestBstar?.toExponential(2) ?? '—'}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-white/30">CHANGE</div>
                    <div className={`text-sm tabular-nums ${
                      (dragData.summary.bstarChangePercent ?? 0) > 0
                        ? 'text-red-400'
                        : 'text-emerald-400'
                    }`}>
                      {dragData.summary.bstarChangePercent != null
                        ? `${dragData.summary.bstarChangePercent > 0 ? '+' : ''}${dragData.summary.bstarChangePercent.toFixed(2)}%`
                        : '—'}
                    </div>
                  </div>
                </div>
              )}

              <div className="overflow-x-auto">
                <table className="w-full text-[11px]">
                  <thead>
                    <tr className="text-white/30 border-b border-white/[0.06]">
                      <th className="text-left py-2 pr-4">EPOCH</th>
                      <th className="text-right py-2 px-3">B*</th>
                      <th className="text-right py-2 pl-3">AVG ALT (km)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dragData.dataPoints.slice(-20).map((dp, i) => (
                      <tr key={i} className="border-b border-white/[0.03]">
                        <td className="text-white/50 py-1.5 pr-4">
                          {new Date(dp.epoch).toISOString().slice(0, 16).replace('T', ' ')}
                        </td>
                        <td className="text-right text-white/60 tabular-nums py-1.5 px-3">
                          {dp.bstar.toExponential(2)}
                        </td>
                        <td className="text-right text-white/60 tabular-nums py-1.5 pl-3">
                          {dp.avgAltitude?.toFixed(1) ?? '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>

        {/* Navigation */}
        <div className="mt-12 flex gap-6 justify-center text-[11px]">
          <a href="/orbital" className="text-white/30 hover:text-white/50 transition-colors">
            CONSTELLATION
          </a>
          <a href="/" className="text-white/30 hover:text-white/50 transition-colors">
            TERMINAL
          </a>
        </div>
      </div>
    </div>
  )
}
```

## 3. Important: Verify `useSatellitePosition` compatibility

Read `src/lib/hooks/useSatellitePosition.ts` — the single-satellite `useSatellitePosition(noradId)` hook. It fetches from `/api/satellites/${noradId}` and expects:
- `data.tle.line1` / `data.tle.line2` (for SGP4 propagation)
- `data.tle.bstar` (for orbital params)
- `data.metadata.orbit.inclination`, `.raan`, `.eccentricity`, `.apogee`, `.perigee`

Make sure the API route response matches this shape EXACTLY. The code in directive 1 is designed to match, but verify after implementation.

## 4. Handle Next.js async params

In Next.js 15+, `params` is a Promise. The page uses `use(params)` to unwrap it. If you get type errors, use `const { noradId } = await params` with the page as an async component, or check the Next.js version.

## 5. Run `npx tsc --noEmit` to verify
