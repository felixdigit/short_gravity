'use client'

import { useState, useMemo } from 'react'
import { cn } from '@/lib/utils'
import { Text, LoadingState } from '@shortgravity/ui'
import { DragChart } from './DragChart'
import { FocusPanel } from '@/components/ui/FocusPanel'
import { useFocusPanelContext } from '@shortgravity/ui'
import { useTerminalData } from '@/lib/providers/TerminalDataProvider'
import type { WidgetManifest } from './types'

export const fm1WatchManifest: WidgetManifest = {
  id: 'fm1-watch',
  name: 'FM1 WATCH',
  category: 'data',
  panelPreference: 'left',
  sizing: 'fixed',
  expandable: true,
  separator: true,
}

type SourceFilter = 'all' | 'celestrak' | 'spacetrack'

export function FM1WatchPanel() {
  const ctx = useTerminalData()
  const data = ctx.fm1 ?? null
  const dragHistory = ctx.dragHistory
  const isLoading = ctx.dragLoading

  const [sourceFilter, setSourceFilter] = useState<SourceFilter>('all')

  const fullTimeRange = useMemo(() => {
    if (!dragHistory?.dataPoints?.length) return undefined
    const times = dragHistory.dataPoints.map((d) => new Date(d.epoch).getTime())
    return { min: Math.min(...times), max: Math.max(...times) }
  }, [dragHistory])

  const dragChartData = useMemo(() => {
    if (!dragHistory?.dataPoints?.length) return []
    let points = dragHistory.dataPoints
    if (sourceFilter !== 'all') {
      points = points.filter((d) => d.source === sourceFilter)
    }
    if (points.length === 0) return []
    const step = Math.max(1, Math.floor(points.length / 30))
    return points
      .filter((_, i) => i % step === 0 || i === points.length - 1)
      .map((d) => ({
        epoch: d.epoch,
        bstar: d.bstar,
        altitude: d.avgAltitude ?? null,
        source: d.source,
      }))
  }, [dragHistory, sourceFilter])

  const { focusedPanelId } = useFocusPanelContext()
  const expanded = focusedPanelId === 'fm1-watch'
  const changePercent = dragHistory?.summary?.bstarChangePercent ?? 0

  if (!data && !isLoading) {
    return (
      <FocusPanel panelId="fm1-watch" collapsedPosition="inline" expandedSize={{ width: '50vw', height: '50vh' }} label="FM1 DRAG (B*) SINCE LAUNCH">
        <div className="w-full h-[120px] flex items-center justify-center">
          <LoadingState text="Waiting for FM1 TLE..." size="sm" />
        </div>
      </FocusPanel>
    )
  }

  return (
    <FocusPanel panelId="fm1-watch" collapsedPosition="inline" expandedSize={{ width: '50vw', height: '50vh' }} label="FM1 DRAG (B*) SINCE LAUNCH">
      <div className={cn('w-full h-full font-mono flex flex-col', expanded && 'p-4 pt-10')}>
        <div className="flex items-center justify-between shrink-0">
          {dragHistory?.summary && (
            <Text
              variant="primary"
              size="sm"
              tabular
              className={changePercent > 0 ? 'text-red-400/50' : 'text-green-400/50'}
              as="div"
            >
              {changePercent > 0 ? '\u2191' : '\u2193'}
              {Math.abs(changePercent).toFixed(1)}%
            </Text>
          )}
          <div className="flex gap-0.5">
            {(['all', 'celestrak', 'spacetrack'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setSourceFilter(f)}
                className={cn(
                  'text-[11px] font-mono px-1 py-0.5 rounded transition-colors',
                  sourceFilter === f
                    ? 'text-white/70 bg-white/[0.06]'
                    : 'text-white/50 hover:text-white/60'
                )}
              >
                {f === 'all' ? 'ALL' : f === 'celestrak' ? 'CT' : 'ST'}
              </button>
            ))}
          </div>
        </div>

        <div className={cn('mt-1', expanded ? 'flex-1 min-h-0' : 'h-[120px]')}>
          {isLoading ? (
            <LoadingState size="sm" />
          ) : dragChartData.length > 0 ? (
            <DragChart data={dragChartData} timeRange={fullTimeRange} />
          ) : (
            <LoadingState text="No data" size="sm" />
          )}
        </div>

        <div className="flex justify-between mt-1 text-[11px] shrink-0">
          <div>
            <span className="text-white/50">B* </span>
            <span className="text-white/70 tabular-nums">
              {dragHistory?.summary?.latestBstar?.toExponential(2) ?? '\u2014'}
            </span>
          </div>
          {dragHistory?.summary?.initialBstar && (
            <div>
              <span className="text-white/50">INIT </span>
              <span className="text-white/50 tabular-nums">
                {dragHistory.summary.initialBstar.toExponential(2)}
              </span>
            </div>
          )}
        </div>
      </div>
    </FocusPanel>
  )
}
