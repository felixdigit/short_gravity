'use client'

import { cn } from '@/lib/utils'
import { useTerminalData } from '@/lib/providers/TerminalDataProvider'
import type { WidgetManifest } from './types'

export const environmentStripManifest: WidgetManifest = {
  id: 'environment-strip',
  name: 'ENVIRONMENT',
  category: 'data',
  panelPreference: 'left',
  sizing: 'fixed',
  expandable: false,
  separator: true,
}

export function EnvironmentStrip() {
  const ctx = useTerminalData()
  const { spaceWeather, conjunctions } = ctx

  const latest = spaceWeather?.[0]
  const prev = spaceWeather?.[1]

  const f107 = latest?.f107_obs ?? latest?.f107_adj
  const f107Prev = prev?.f107_obs ?? prev?.f107_adj
  const f107Trend = f107 != null && f107Prev != null ? (f107 > f107Prev ? '\u25b2' : f107 < f107Prev ? '\u25bc' : '\u00b7') : ''

  const ap = latest?.ap_avg
  const apPrev = prev?.ap_avg
  const apTrend = ap != null && apPrev != null ? (ap > apPrev ? '\u25b2' : ap < apPrev ? '\u25bc' : '\u00b7') : ''

  const kp = latest?.kp_sum != null ? (latest.kp_sum / 80).toFixed(1) : null

  const now = new Date()
  const activeCdm = conjunctions?.filter(c => new Date(c.tca) > now).length ?? 0

  if (!latest) {
    return (
      <div className="font-mono text-[11px] text-white/50 tracking-wider">
        ENV: LOADING...
      </div>
    )
  }

  return (
    <div className="font-mono flex items-center gap-3 text-[11px]">
      <span className="text-white/70 tracking-wider">ENV</span>

      <span className="tabular-nums">
        <span className="text-white/50">F10.7 </span>
        <span className="text-white/70">{f107 != null ? Math.round(f107) : '\u2014'}</span>
        <span className={cn(
          'ml-0.5',
          f107Trend === '\u25b2' ? 'text-red-400/50' : f107Trend === '\u25bc' ? 'text-green-400/50' : 'text-white/50'
        )}>{f107Trend}</span>
      </span>

      <span className="tabular-nums">
        <span className="text-white/50">Ap </span>
        <span className="text-white/70">{ap != null ? Math.round(ap) : '\u2014'}</span>
        <span className={cn(
          'ml-0.5',
          apTrend === '\u25b2' ? 'text-red-400/50' : apTrend === '\u25bc' ? 'text-green-400/50' : 'text-white/50'
        )}>{apTrend}</span>
      </span>

      <span className="tabular-nums">
        <span className="text-white/50">Kp </span>
        <span className="text-white/70">{kp ?? '\u2014'}</span>
      </span>

      <span className="tabular-nums">
        <span className="text-white/50">CDM </span>
        <span className={cn(activeCdm > 0 ? 'text-red-400/80' : 'text-white/70')}>{activeCdm}</span>
      </span>
    </div>
  )
}
