'use client'

import { useQuery } from '@tanstack/react-query'
import { Muted } from '@shortgravity/ui'

interface BriefingData {
  generated: string
  sections: {
    signals: {
      count: number
      items: Array<{
        id: number
        signal_type: string
        severity: string
        title: string
        detected_at: string
      }>
      critical: number
    }
    filings: {
      count: number
      items: Array<{
        id: string
        form: string
        title: string
        filing_date: string
      }>
    }
    constellation: {
      count: number
      satellites: Array<{
        name: string
        noradId: string
        tleAge: string
        bstar: number | null
      }>
    }
    spaceWeather: {
      date: string
      f107_obs: number
      kp_sum: number
      ap_avg: number
      sunspot_number: number
    } | null
    market: {
      latestPrice: { date: string; close: number; volume: number } | null
      previousPrice: { date: string; close: number; volume: number } | null
    }
  }
}

function useBriefing() {
  return useQuery<BriefingData>({
    queryKey: ['briefing'],
    queryFn: async () => {
      const res = await fetch('/api/briefing')
      if (!res.ok) throw new Error('Failed to fetch briefing')
      return res.json()
    },
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: true,
  })
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'text-red-400',
  high: 'text-red-400',
  medium: 'text-amber-400',
  low: 'text-white/50',
}

function timeAgo(dateStr: string): string {
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000)
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export default function BriefingPage() {
  const { data, isLoading } = useBriefing()

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#030305] text-white font-mono">
        <div className="max-w-5xl mx-auto px-6 py-12">
          <h1 className="text-2xl font-light tracking-wider mb-8">THE BRIEFING</h1>
          <div className="text-white/30 text-sm py-20 text-center">COMPILING INTELLIGENCE...</div>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-[#030305] text-white font-mono">
        <div className="max-w-5xl mx-auto px-6 py-12">
          <h1 className="text-2xl font-light tracking-wider mb-8">THE BRIEFING</h1>
          <div className="border border-white/[0.06] rounded-lg p-12 text-center">
            <div className="text-white/30 text-sm mb-2">Briefing unavailable</div>
            <Muted className="text-xs">Could not compile intelligence data.</Muted>
          </div>
        </div>
      </div>
    )
  }

  const { sections } = data
  const priceChange =
    sections.market.latestPrice && sections.market.previousPrice
      ? sections.market.latestPrice.close - sections.market.previousPrice.close
      : null
  const pricePct =
    priceChange != null && sections.market.previousPrice
      ? (priceChange / sections.market.previousPrice.close) * 100
      : null

  return (
    <div className="min-h-screen bg-[#030305] text-white font-mono">
      <div className="max-w-5xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="flex items-baseline justify-between mb-8">
          <div>
            <h1 className="text-2xl font-light tracking-wider">THE BRIEFING</h1>
            <Muted className="text-xs mt-1">
              Daily intelligence summary — generated{' '}
              {new Date(data.generated).toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                timeZoneName: 'short',
              })}
            </Muted>
          </div>
          <div className="text-right">
            <span className="text-[10px] text-white/30 tracking-wider">
              {new Date(data.generated).toLocaleDateString('en-US', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              }).toUpperCase()}
            </span>
          </div>
        </div>

        {/* SITUATION — Signals */}
        <div className="border border-white/[0.06] rounded-lg px-4 py-4 mb-4">
          <div className="text-[11px] text-white/50 tracking-wider mb-3">SITUATION</div>
          <div className="flex items-baseline gap-4 mb-3">
            <span className="text-3xl font-light tabular-nums">{sections.signals.count}</span>
            <Muted className="text-xs">ACTIVE SIGNALS (24H)</Muted>
            {sections.signals.critical > 0 && (
              <span className="text-red-400 text-xs tabular-nums">
                {sections.signals.critical} CRITICAL/HIGH
              </span>
            )}
          </div>
          {sections.signals.items.length > 0 ? (
            <div className="space-y-1.5">
              {sections.signals.items.map((s) => (
                <div key={s.id} className="flex items-center gap-2 text-xs">
                  <span
                    className={`text-[9px] font-bold px-1.5 py-0.5 rounded bg-white/[0.04] ${
                      SEVERITY_COLORS[s.severity] ?? 'text-white/50'
                    }`}
                  >
                    {s.severity.toUpperCase()}
                  </span>
                  <span className="text-white/70 truncate flex-1">{s.title}</span>
                  <span className="text-white/20 text-[10px] shrink-0">
                    {timeAgo(s.detected_at)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <Muted className="text-xs">No signals detected in the last 24 hours.</Muted>
          )}
        </div>

        {/* MARKET */}
        <div className="border border-white/[0.06] rounded-lg px-4 py-4 mb-4">
          <div className="text-[11px] text-white/50 tracking-wider mb-3">MARKET</div>
          {sections.market.latestPrice ? (
            <div className="flex items-baseline gap-6">
              <div>
                <span className="text-[10px] text-white/40 mr-2">ASTS</span>
                <span className="text-2xl font-light tabular-nums">
                  ${sections.market.latestPrice.close.toFixed(2)}
                </span>
              </div>
              {priceChange != null && pricePct != null && (
                <div className={priceChange >= 0 ? 'text-green-400' : 'text-red-400'}>
                  <span className="text-sm tabular-nums">
                    {priceChange >= 0 ? '+' : ''}
                    {priceChange.toFixed(2)}
                  </span>
                  <span className="text-[10px] ml-1 tabular-nums">
                    ({pricePct >= 0 ? '+' : ''}
                    {pricePct.toFixed(2)}%)
                  </span>
                </div>
              )}
              <div className="ml-auto text-right">
                <div className="text-[10px] text-white/30">VOLUME</div>
                <div className="text-sm text-white/60 tabular-nums">
                  {(sections.market.latestPrice.volume / 1_000_000).toFixed(1)}M
                </div>
              </div>
            </div>
          ) : (
            <Muted className="text-xs">No market data available.</Muted>
          )}
        </div>

        {/* CONSTELLATION */}
        <div className="border border-white/[0.06] rounded-lg px-4 py-4 mb-4">
          <div className="flex items-baseline justify-between mb-3">
            <div className="text-[11px] text-white/50 tracking-wider">CONSTELLATION</div>
            <Muted className="text-[10px]">{sections.constellation.count} TRACKED</Muted>
          </div>
          {sections.constellation.satellites.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-[10px] text-white/30 border-b border-white/[0.06]">
                    <th className="text-left py-1.5 font-normal">SATELLITE</th>
                    <th className="text-left py-1.5 font-normal">NORAD</th>
                    <th className="text-right py-1.5 font-normal">TLE AGE</th>
                    <th className="text-right py-1.5 font-normal">B*</th>
                  </tr>
                </thead>
                <tbody>
                  {sections.constellation.satellites.map((sat) => {
                    const ageHours = parseFloat(sat.tleAge)
                    const ageColor =
                      isNaN(ageHours) || ageHours > 48
                        ? 'text-red-400'
                        : ageHours > 24
                          ? 'text-amber-400'
                          : 'text-white/60'
                    return (
                      <tr
                        key={sat.noradId}
                        className="border-b border-white/[0.03] last:border-0"
                      >
                        <td className="py-1.5 text-white/70">{sat.name}</td>
                        <td className="py-1.5 text-white/40 tabular-nums">{sat.noradId}</td>
                        <td className={`py-1.5 text-right tabular-nums ${ageColor}`}>
                          {sat.tleAge}
                        </td>
                        <td className="py-1.5 text-right text-white/40 tabular-nums">
                          {sat.bstar != null ? Number(sat.bstar).toExponential(2) : '—'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <Muted className="text-xs">No satellite data available.</Muted>
          )}
        </div>

        {/* FILINGS */}
        <div className="border border-white/[0.06] rounded-lg px-4 py-4 mb-4">
          <div className="flex items-baseline justify-between mb-3">
            <div className="text-[11px] text-white/50 tracking-wider">FILINGS (7D)</div>
            <Muted className="text-[10px]">{sections.filings.count} RECENT</Muted>
          </div>
          {sections.filings.items.length > 0 ? (
            <div className="space-y-2">
              {sections.filings.items.map((f) => (
                <div key={f.id} className="flex items-start gap-3">
                  <span className="text-[10px] text-[#FF6B35] bg-[#FF6B35]/10 px-1.5 py-0.5 rounded shrink-0">
                    {f.form}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs text-white/70 truncate">{f.title}</div>
                    <div className="text-[10px] text-white/25 mt-0.5">
                      {formatDate(f.filing_date)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <Muted className="text-xs">No SEC filings in the last 7 days.</Muted>
          )}
        </div>

        {/* SPACE WEATHER */}
        <div className="border border-white/[0.06] rounded-lg px-4 py-4 mb-4">
          <div className="text-[11px] text-white/50 tracking-wider mb-3">SPACE WEATHER</div>
          {sections.spaceWeather ? (
            <div className="flex gap-8">
              <div>
                <div className="text-[10px] text-white/30 mb-1">F10.7 FLUX</div>
                <div className="text-lg font-light tabular-nums">
                  {sections.spaceWeather.f107_obs}
                </div>
                <div className="text-[9px] text-white/20">SFU</div>
              </div>
              <div>
                <div className="text-[10px] text-white/30 mb-1">Kp SUM</div>
                <div className="text-lg font-light tabular-nums">
                  {sections.spaceWeather.kp_sum}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-white/30 mb-1">Ap AVG</div>
                <div className="text-lg font-light tabular-nums">
                  {sections.spaceWeather.ap_avg}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-white/30 mb-1">SUNSPOTS</div>
                <div className="text-lg font-light tabular-nums">
                  {sections.spaceWeather.sunspot_number}
                </div>
              </div>
              <div className="ml-auto text-right">
                <div className="text-[10px] text-white/30 mb-1">DATE</div>
                <div className="text-xs text-white/40">
                  {formatDate(sections.spaceWeather.date)}
                </div>
              </div>
            </div>
          ) : (
            <Muted className="text-xs">No space weather data available.</Muted>
          )}
        </div>

        {/* Footer */}
        <div className="mt-12 flex justify-center gap-6">
          <a
            href="/"
            className="text-[11px] text-white/30 hover:text-white/50 transition-colors"
          >
            BACK TO TERMINAL
          </a>
          <a
            href="/signals"
            className="text-[11px] text-white/30 hover:text-white/50 transition-colors"
          >
            SIGNALS
          </a>
          <a
            href="/orbital"
            className="text-[11px] text-white/30 hover:text-white/50 transition-colors"
          >
            ORBITAL
          </a>
        </div>
      </div>
    </div>
  )
}
