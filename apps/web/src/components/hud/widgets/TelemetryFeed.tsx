'use client'

import { cn } from '@/lib/utils'
import { useTerminalData } from '@/lib/providers/TerminalDataProvider'
import { useTerminalStore } from '@/lib/stores/terminal-store'
import { FM1_NORAD_ID } from '@/lib/data/satellites'
import type { WidgetManifest } from './types'

export const telemetryFeedManifest: WidgetManifest = {
  id: 'telemetry-feed',
  name: 'TELEMETRY FEED',
  category: 'data',
  panelPreference: 'left',
  sizing: 'fixed',
  expandable: false,
  separator: false,
}

interface TelemetryFeedProps {
  className?: string
}

export function TelemetryFeed({ className }: TelemetryFeedProps = {}) {
  const ctx = useTerminalData()
  const store = useTerminalStore()

  const satellites = ctx.satellites
  const selected = store.selectedSatellite
  const onSelect = (id: string) => store.toggleSatelliteCard(id)
  const tleFreshness = ctx.tleFreshness

  const formatTLEAge = (hours: number) => {
    if (hours < 1) return `${Math.round(hours * 60)}m`
    if (hours < 24) return `${Math.round(hours)}h`
    return `${(hours / 24).toFixed(1)}d`
  }

  return (
    <div className={cn('font-mono', className)}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-white/70 tracking-wider">TELEMETRY FEED</span>
          {tleFreshness?.minHoursOld != null && (
            <span className="text-[11px] tabular-nums text-white/50">
              TLE {formatTLEAge(tleFreshness.minHoursOld)}
            </span>
          )}
        </div>
        <span className="text-[11px] text-white/50 tracking-wider">Celestrak</span>
      </div>

      <div className="flex text-[11px] text-white/50 pb-1 border-b border-white/[0.03]">
        <div className="flex-[3] min-w-0">ID</div>
        <div className="flex-[2] min-w-0 text-right">ALT</div>
        <div className="flex-[3] min-w-0 text-right">LAT</div>
        <div className="flex-[4] min-w-0 text-right">LON</div>
        <div className="flex-[2] min-w-0 text-right">V</div>
      </div>

      <div className="space-y-0">
        {(!satellites || satellites.length === 0) && (
          <div className="py-1">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="flex py-0.5 gap-1">
                <div className="flex-[3] h-3 animate-pulse bg-white/5 rounded" />
                <div className="flex-[2] h-3 animate-pulse bg-white/5 rounded" />
                <div className="flex-[3] h-3 animate-pulse bg-white/5 rounded" />
                <div className="flex-[4] h-3 animate-pulse bg-white/5 rounded" />
                <div className="flex-[2] h-3 animate-pulse bg-white/5 rounded" />
              </div>
            ))}
          </div>
        )}
        {satellites.map((sat) => {
          const isSelected = sat.noradId === selected
          const isHighlight = sat.noradId === FM1_NORAD_ID

          return (
            <div
              key={sat.noradId}
              onClick={() => onSelect(sat.noradId)}
              className={cn(
                'flex py-0.5 cursor-pointer transition-colors text-[11px]',
                isSelected
                  ? 'text-[var(--asts-orange)]'
                  : isHighlight
                    ? 'text-white/70'
                    : 'text-white/50 hover:text-white/70'
              )}
            >
              <div className="flex-[3] min-w-0 text-[11px]">{sat.name}</div>
              <div className="flex-[2] min-w-0 text-right tabular-nums">{sat.altitude.toFixed(0)}</div>
              <div className="flex-[3] min-w-0 text-right tabular-nums">{sat.latitude.toFixed(1)}&deg;</div>
              <div className="flex-[4] min-w-0 text-right tabular-nums">{sat.longitude.toFixed(1)}&deg;</div>
              <div className="flex-[2] min-w-0 text-right tabular-nums opacity-70">{sat.velocity.toFixed(2)}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
