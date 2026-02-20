'use client'

import { cn } from '@/lib/utils'
import { useTerminalData } from '@/lib/providers/TerminalDataProvider'
import { useTerminalStore } from '@/lib/stores/terminal-store'
import { FM1_NORAD_ID } from '@/lib/data/satellites'
import type { WidgetManifest } from './types'

export const constellationMatrixManifest: WidgetManifest = {
  id: 'constellation-matrix',
  name: 'CONSTELLATION MATRIX',
  category: 'data',
  panelPreference: 'left',
  sizing: 'fixed',
  expandable: false,
  separator: false,
}

function formatAge(hoursOld: number | undefined | null): { text: string; stale: boolean } {
  if (hoursOld == null) return { text: '\u2014', stale: false }
  if (hoursOld < 1) return { text: `${Math.round(hoursOld * 60)}m`, stale: false }
  if (hoursOld < 24) return { text: `${hoursOld.toFixed(1)}h`, stale: false }
  return { text: `${(hoursOld / 24).toFixed(1)}d`, stale: true }
}

function formatBstar(bstar: number): { mantissa: string; exponent: string } {
  if (bstar === 0) return { mantissa: '0', exponent: '' }
  const exp = Math.floor(Math.log10(Math.abs(bstar)))
  const man = bstar / Math.pow(10, exp)
  return { mantissa: `${man.toFixed(1)}e`, exponent: `${exp}` }
}

export function ConstellationMatrix() {
  const ctx = useTerminalData()
  const store = useTerminalStore()

  const { satellites, perSatelliteFreshness, divergenceData } = ctx

  if (satellites.length === 0) {
    return (
      <div className="font-mono text-[11px] text-white/50 animate-pulse">
        ACQUIRING TELEMETRY...
      </div>
    )
  }

  return (
    <div className="font-mono">
      <div className="flex items-center text-[11px] tracking-widest text-white/50 uppercase mb-1.5">
        <span className="w-10">SAT</span>
        <span className="w-10 text-right">AGE</span>
        <span className="flex-1 text-right">ALT</span>
        <span className="w-14 text-right">PER</span>
        <span className="w-16 text-right">B*</span>
        <span className="w-7 text-right">SRC</span>
      </div>

      {satellites.map((sat) => {
        const freshness = perSatelliteFreshness[sat.noradId]
        const age = formatAge(freshness?.hoursOld)
        const bstar = formatBstar(sat.bstar)
        const divergence = divergenceData?.find(d => d.noradId === sat.noradId)
        const bstarDelta = divergence?.bstarDelta ?? 0
        const divergencePercent = Math.abs(bstarDelta) > 0.05 ? Math.round(Math.abs(bstarDelta) * 100) : null
        const isSelected = store.selectedSatellite === sat.noradId
        const isFM1 = sat.noradId === FM1_NORAD_ID

        return (
          <button
            key={sat.noradId}
            onClick={() => store.toggleSatelliteCard(sat.noradId)}
            className={cn(
              'flex items-center w-full text-[11px] py-[3px] transition-colors text-left',
              isSelected
                ? 'text-[var(--asts-orange)]'
                : 'text-white/70 hover:text-white/90'
            )}
          >
            <span className={cn('w-10 tabular-nums', isFM1 && !isSelected && 'text-white/90')}>
              {sat.name}
            </span>
            <span className={cn('w-10 text-right tabular-nums', age.stale ? 'text-[var(--asts-orange)]' : 'text-white/50')}>
              {age.text}
            </span>
            <span className="flex-1 text-right tabular-nums">{sat.altitude.toFixed(1)}</span>
            <span className="w-14 text-right tabular-nums text-white/50">
              {sat.periodMinutes ? sat.periodMinutes.toFixed(1) : '\u2014'}
            </span>
            <span className="w-16 text-right tabular-nums">
              <span>{bstar.mantissa}</span>
              <span className="text-white/50">{bstar.exponent}</span>
            </span>
            <span className={cn(
              'w-7 text-right tabular-nums text-[11px]',
              divergencePercent ? 'text-[var(--asts-orange)]' : 'text-white/50'
            )}>
              {divergencePercent ? `${divergencePercent}%` : '\u00b7'}
            </span>
          </button>
        )
      })}
    </div>
  )
}
