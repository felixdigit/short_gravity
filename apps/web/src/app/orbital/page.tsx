'use client'

import { Suspense } from 'react'
import { TerminalDataProvider, useTerminalData } from '@/lib/providers/TerminalDataProvider'
import { StatusDot } from '@shortgravity/ui'
import { SATELLITES_ORDERED } from '@/lib/data/satellites'

function OrbitalContent() {
  const {
    satellites,
    perSatelliteFreshness,
    tleFreshness,
    spaceWeather,
    divergenceData,
    dragHistory,
    dragLoading,
    conjunctions,
  } = useTerminalData()

  return (
    <div className="min-h-screen bg-[#030305] text-white font-mono">
      <div className="max-w-6xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="mb-10">
          <h1 className="text-2xl font-light tracking-wider">ORBITAL INTELLIGENCE</h1>
          <p className="text-xs text-white/30 mt-1">
            Constellation health, atmospheric drag, space weather
          </p>
        </div>

        {/* === CONSTELLATION HEALTH === */}
        <section className="mb-12">
          <h2 className="text-xs text-white/40 tracking-widest mb-4">CONSTELLATION HEALTH</h2>

          {tleFreshness && (
            <div className="flex gap-6 mb-4 text-xs text-white/40">
              <span>OLDEST TLE: {tleFreshness.maxHoursOld?.toFixed(1)}h</span>
              <span>FRESHEST: {tleFreshness.minHoursOld?.toFixed(1)}h</span>
            </div>
          )}

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {SATELLITES_ORDERED.map(({ id, name, type }) => {
              const sat = satellites.find(s => s.noradId === id)
              const freshness = perSatelliteFreshness[id]
              const hoursOld = freshness?.hoursOld ?? null

              const variant: 'nominal' | 'warning' | 'critical' | 'info' =
                hoursOld == null ? 'info'
                : hoursOld < 12 ? 'nominal'
                : hoursOld < 24 ? 'warning'
                : 'critical'

              return (
                <a
                  key={id}
                  href={`/satellite/${id}`}
                  className="border border-white/[0.06] rounded-lg p-3 hover:border-white/[0.15] transition-colors"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <StatusDot variant={variant} />
                    <span className="text-sm text-white/80">{name}</span>
                    <span className="text-[10px] text-white/20 ml-auto">{type}</span>
                  </div>
                  {sat ? (
                    <div className="space-y-1 text-[11px]">
                      <div className="flex justify-between">
                        <span className="text-white/30">ALT</span>
                        <span className="text-white/60 tabular-nums">{sat.altitude.toFixed(1)} km</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-white/30">B*</span>
                        <span className="text-white/60 tabular-nums">{sat.bstar.toExponential(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-white/30">TLE AGE</span>
                        <span className="text-white/60 tabular-nums">
                          {hoursOld != null ? `${hoursOld.toFixed(1)}h` : '—'}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="text-[11px] text-white/20">No telemetry</div>
                  )}
                </a>
              )
            })}
          </div>
        </section>

        {/* === SPACE WEATHER === */}
        <section className="mb-12">
          <h2 className="text-xs text-white/40 tracking-widest mb-4">SPACE WEATHER</h2>
          {spaceWeather.length === 0 ? (
            <div className="text-xs text-white/20">No space weather data</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-[11px]">
                <thead>
                  <tr className="text-white/30 border-b border-white/[0.06]">
                    <th className="text-left py-2 pr-4">DATE</th>
                    <th className="text-right py-2 px-3">F10.7</th>
                    <th className="text-right py-2 px-3">Kp</th>
                    <th className="text-right py-2 px-3">Ap</th>
                    <th className="text-right py-2 pl-3">SUNSPOT</th>
                  </tr>
                </thead>
                <tbody>
                  {spaceWeather.slice(0, 14).map((day, i) => (
                    <tr key={i} className="border-b border-white/[0.03]">
                      <td className="text-white/50 py-1.5 pr-4">{day.date}</td>
                      <td className="text-right text-white/60 tabular-nums py-1.5 px-3">
                        {day.f107_obs ?? '—'}
                      </td>
                      <td className="text-right text-white/60 tabular-nums py-1.5 px-3">
                        {day.kp_sum ?? '—'}
                      </td>
                      <td className="text-right text-white/60 tabular-nums py-1.5 px-3">
                        {day.ap_avg ?? '—'}
                      </td>
                      <td className="text-right text-white/60 tabular-nums py-1.5 pl-3">
                        {day.sunspot_number ?? '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* === SOURCE DIVERGENCE === */}
        <section className="mb-12">
          <h2 className="text-xs text-white/40 tracking-widest mb-4">SOURCE DIVERGENCE</h2>
          <p className="text-[10px] text-white/20 mb-3">
            CelesTrak vs Space-Track BSTAR comparison — delta &gt; 0.0001 flags divergence
          </p>
          {divergenceData.length === 0 ? (
            <div className="text-xs text-white/20">No divergence data</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-[11px]">
                <thead>
                  <tr className="text-white/30 border-b border-white/[0.06]">
                    <th className="text-left py-2 pr-4">SATELLITE</th>
                    <th className="text-right py-2 px-3">CT B*</th>
                    <th className="text-right py-2 px-3">ST B*</th>
                    <th className="text-right py-2 px-3">DELTA</th>
                    <th className="text-right py-2 pl-3">FLAG</th>
                  </tr>
                </thead>
                <tbody>
                  {divergenceData.map((row, i) => (
                    <tr key={i} className="border-b border-white/[0.03]">
                      <td className="text-white/50 py-1.5 pr-4">{row.noradId}</td>
                      <td className="text-right text-white/60 tabular-nums py-1.5 px-3">
                        {row.ctBstar?.toExponential(2) ?? '—'}
                      </td>
                      <td className="text-right text-white/60 tabular-nums py-1.5 px-3">
                        {row.stBstar?.toExponential(2) ?? '—'}
                      </td>
                      <td className="text-right text-white/60 tabular-nums py-1.5 px-3">
                        {row.bstarDelta.toExponential(2)}
                      </td>
                      <td className={`text-right py-1.5 pl-3 ${row.diverged ? 'text-amber-400' : 'text-white/20'}`}>
                        {row.diverged ? 'DIVERGED' : 'OK'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* === FM1 DRAG TRENDS === */}
        <section className="mb-12">
          <h2 className="text-xs text-white/40 tracking-widest mb-4">FM1 DRAG HISTORY</h2>
          {dragLoading ? (
            <div className="text-xs text-white/20">Loading drag data...</div>
          ) : !dragHistory?.dataPoints?.length ? (
            <div className="text-xs text-white/20">No drag history available</div>
          ) : (
            <>
              {/* Summary stats */}
              {dragHistory.summary && (
                <div className="flex gap-8 mb-4">
                  <div>
                    <div className="text-[10px] text-white/30">INITIAL B*</div>
                    <div className="text-sm text-white/70 tabular-nums">
                      {dragHistory.summary.initialBstar?.toExponential(2) ?? '—'}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-white/30">LATEST B*</div>
                    <div className="text-sm text-white/70 tabular-nums">
                      {dragHistory.summary.latestBstar?.toExponential(2) ?? '—'}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-white/30">CHANGE</div>
                    <div className={`text-sm tabular-nums ${
                      (dragHistory.summary.bstarChangePercent ?? 0) > 0
                        ? 'text-red-400'
                        : 'text-emerald-400'
                    }`}>
                      {dragHistory.summary.bstarChangePercent != null
                        ? `${dragHistory.summary.bstarChangePercent > 0 ? '+' : ''}${dragHistory.summary.bstarChangePercent.toFixed(2)}%`
                        : '—'}
                    </div>
                  </div>
                </div>
              )}

              {/* Data table (last 20 points) */}
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
                    {dragHistory.dataPoints.slice(-20).map((dp, i) => (
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

        {/* === CONJUNCTIONS === */}
        <section className="mb-12">
          <h2 className="text-xs text-white/40 tracking-widest mb-4">CONJUNCTIONS</h2>
          {conjunctions.length === 0 ? (
            <div className="text-xs text-white/20">No conjunction events in window</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-[11px]">
                <thead>
                  <tr className="text-white/30 border-b border-white/[0.06]">
                    <th className="text-left py-2 pr-4">TCA</th>
                    <th className="text-left py-2 px-3">SAT 1</th>
                    <th className="text-left py-2 px-3">SAT 2</th>
                    <th className="text-right py-2 px-3">MIN RANGE (km)</th>
                    <th className="text-right py-2 pl-3">PROBABILITY</th>
                  </tr>
                </thead>
                <tbody>
                  {conjunctions.map((c, i) => (
                    <tr key={i} className="border-b border-white/[0.03]">
                      <td className="text-white/50 py-1.5 pr-4">
                        {new Date(c.tca).toISOString().slice(0, 16).replace('T', ' ')}
                      </td>
                      <td className="text-white/60 py-1.5 px-3">{c.sat1}</td>
                      <td className="text-white/60 py-1.5 px-3">{c.sat2}</td>
                      <td className="text-right text-white/60 tabular-nums py-1.5 px-3">
                        {c.minRange != null ? c.minRange.toFixed(1) : '—'}
                      </td>
                      <td className={`text-right tabular-nums py-1.5 pl-3 ${
                        c.probability != null && c.probability > 0.001
                          ? 'text-red-400'
                          : 'text-white/40'
                      }`}>
                        {c.probability != null ? c.probability.toExponential(2) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Back link */}
        <div className="mt-12 text-center">
          <a href="/" className="text-[11px] text-white/30 hover:text-white/50 transition-colors">
            BACK TO TERMINAL
          </a>
        </div>
      </div>
    </div>
  )
}

export default function OrbitalPage() {
  return (
    <TerminalDataProvider>
      <Suspense>
        <OrbitalContent />
      </Suspense>
    </TerminalDataProvider>
  )
}
