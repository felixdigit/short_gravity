'use client'

import { useMemo } from 'react'
import { cn } from '@/lib/utils'
import { LoadingState } from '@shortgravity/ui'
import { FocusPanel } from '@/components/ui/FocusPanel'
import { useFocusPanelContext } from '@shortgravity/ui'
import { useTerminalData } from '@/lib/providers/TerminalDataProvider'
import { SGChart } from '@/lib/charts'
import type { TimeSeriesPoint, SeriesConfig, OverlayConfig } from '@/lib/charts'
import type { WidgetManifest } from './types'

export const fm1MonitorManifest: WidgetManifest = {
  id: 'fm1-monitor',
  name: 'FM1 MONITOR',
  category: 'data',
  panelPreference: 'left',
  sizing: 'fixed',
  expandable: true,
  separator: true,
}

export function FM1Monitor() {
  const ctx = useTerminalData()
  const { fm1, dragHistory, dragLoading } = ctx
  const { focusedPanelId } = useFocusPanelContext()
  const expanded = focusedPanelId === 'fm1-monitor'

  const chartData = useMemo(() => {
    if (!dragHistory?.dataPoints?.length) return { series: [] as SeriesConfig[], overlays: [] as OverlayConfig[] }

    const points = dragHistory.dataPoints
    const step = Math.max(1, Math.floor(points.length / 40))
    const sampled = points.filter((_, i) => i % step === 0 || i === points.length - 1)

    const bstarSeries: TimeSeriesPoint[] = sampled.map(d => ({
      time: new Date(d.epoch).getTime(),
      value: d.bstar,
    }))

    const hasAlt = sampled.some(d => d.avgAltitude != null)
    const altSeries: TimeSeriesPoint[] = hasAlt
      ? sampled.filter(d => d.avgAltitude != null).map(d => ({
          time: new Date(d.epoch).getTime(),
          value: d.avgAltitude!,
        }))
      : []

    const series: SeriesConfig[] = [
      { id: 'bstar', type: 'line', data: bstarSeries, strokeWidth: 1 },
    ]

    if (altSeries.length > 0) {
      series.push({
        id: 'altitude',
        type: 'line',
        data: altSeries,
        axis: 'y2',
        opacity: 0.4,
        strokeWidth: 0.75,
      })
    }

    const overlays: OverlayConfig[] = [{ type: 'trend', seriesId: 'bstar' }]

    return { series, overlays }
  }, [dragHistory])

  const changePercent = dragHistory?.summary?.bstarChangePercent ?? 0
  const hasAlt = chartData.series.length > 1

  return (
    <FocusPanel
      panelId="fm1-monitor"
      collapsedPosition="inline"
      expandedSize={{ width: '55vw', height: '50vh' }}
      screenshotFilename="fm1-monitor"
      label="FM1 MONITOR"
    >
      <div className={cn('w-full font-mono', expanded && 'h-full flex flex-col p-4 pt-10')}>
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2 text-[11px]">
            <span className="text-white/70 tracking-wider">B* & ALT</span>
            {dragHistory?.summary && (
              <span className={cn(
                'tabular-nums',
                changePercent > 0 ? 'text-red-400/60' : 'text-green-400/60'
              )}>
                {changePercent > 0 ? '\u25b2' : '\u25bc'}{Math.abs(changePercent).toFixed(1)}%
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 text-[11px] text-white/50">
            <span>&mdash;&mdash; B*</span>
            {hasAlt && <span className="text-white/50">&mdash;&mdash; Alt</span>}
          </div>
        </div>

        <div className={cn(expanded ? 'flex-1 min-h-0' : 'h-[100px]')}>
          {dragLoading ? (
            <LoadingState size="sm" />
          ) : chartData.series.length > 0 ? (
            <SGChart
              className="w-full h-full"
              series={chartData.series}
              overlays={chartData.overlays}
              axes={{
                x: 'time',
                y: { format: (v: number) => v.toExponential(1), label: 'B*' },
                y2: hasAlt ? { format: (v: number) => v.toFixed(0), label: 'km' } : undefined,
              }}
              padding={{ top: 12, right: hasAlt ? 36 : 12, bottom: 20, left: 44 }}
              animate={false}
            />
          ) : (
            <div className="h-full flex items-center justify-center">
              <span className="text-[11px] text-white/50">NO DRAG DATA</span>
            </div>
          )}
        </div>

        {fm1 && (
          <div className="flex items-center gap-3 mt-1.5 text-[11px]">
            <span>
              <span className="text-white/50">INC </span>
              <span className="text-white/70 tabular-nums">{fm1.inclination.toFixed(1)}&deg;</span>
            </span>
            <span>
              <span className="text-white/50">ECC </span>
              <span className="text-white/70 tabular-nums">{fm1.eccentricity?.toFixed(4) ?? '\u2014'}</span>
            </span>
            <span>
              <span className="text-white/50">PER </span>
              <span className="text-white/70 tabular-nums">{fm1.periodMinutes ? `${fm1.periodMinutes.toFixed(1)}m` : '\u2014'}</span>
            </span>
          </div>
        )}
      </div>
    </FocusPanel>
  )
}
