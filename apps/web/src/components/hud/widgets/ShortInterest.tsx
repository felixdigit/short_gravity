'use client'

import { useMemo } from 'react'
import { cn } from '@/lib/utils'
import { useShortInterest, useShortInterestHistory } from '@/lib/hooks/useShortInterest'
import { SGChart } from '@/lib/charts'
import type { TimeSeriesPoint, SeriesConfig } from '@/lib/charts'
import type { WidgetManifest } from './types'

export const shortInterestManifest: WidgetManifest = {
  id: 'short-interest',
  name: 'SHORT INTEREST',
  category: 'data',
  panelPreference: 'right',
  sizing: 'fixed',
  expandable: false,
  separator: false,
}

function formatShares(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`
  return n.toString()
}

function formatReportDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export function ShortInterest() {
  const { data, isLoading } = useShortInterest()
  const { data: historyData } = useShortInterestHistory()

  const sparkline = useMemo(() => {
    if (!historyData?.history?.length) return null
    const points: TimeSeriesPoint[] = historyData.history
      .filter(h => h.floatShortPct != null)
      .map((h, i) => ({ time: i, value: h.floatShortPct! }))
    return points.length >= 2 ? points : null
  }, [historyData])

  if (isLoading) {
    return (
      <div className="font-mono">
        <div className="text-[11px] text-white/50 tracking-wider mb-2">SHORT INTEREST</div>
        <div className="h-12 animate-pulse bg-white/5 rounded" />
      </div>
    )
  }

  const floatShorted = data?.floatShortPct

  if (!data || floatShorted == null) {
    return (
      <div className="font-mono">
        <div className="text-[11px] text-white/50 tracking-wider mb-2">SHORT INTEREST</div>
        <div className="text-[24px] font-extralight text-white/30 leading-none">--</div>
      </div>
    )
  }

  const changeDir = data.shortChange != null && data.shortChange > 0 ? '+' : ''
  const changeStr = data.shortChange != null ? `${changeDir}${formatShares(data.shortChange)}` : null

  const series: SeriesConfig[] = sparkline ? [{
    id: 'si',
    type: 'area',
    data: sparkline,
    color: 'rgba(255,255,255,0.35)',
    strokeWidth: 0.75,
    fillOpacity: 0.04,
  }] : []

  return (
    <div className="font-mono">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] text-white/50 tracking-wider">SHORT INTEREST</span>
        {data.reportDate && (
          <span className="text-[11px] text-white/50">
            {formatReportDate(data.reportDate).toUpperCase()}
          </span>
        )}
      </div>

      <div className="text-[28px] font-extralight text-white leading-none tabular-nums">
        {floatShorted.toFixed(1)}%
      </div>
      <div className="text-[11px] text-white/50 mt-1">FLOAT SHORTED</div>

      {sparkline && (
        <div className="h-[40px] mt-2">
          <SGChart
            series={series}
            axes={{ x: 'index', y: { format: (v: number) => `${v.toFixed(0)}%`, ticks: 2 } }}
            padding={{ top: 4, right: 4, bottom: 12, left: 28 }}
            animate={false}
          />
        </div>
      )}

      <div className="flex items-center gap-4 mt-3">
        {data.daysToCover != null && (
          <div>
            <div className="text-[14px] font-light text-white leading-none tabular-nums">
              {data.daysToCover.toFixed(1)}d
            </div>
            <div className="text-[11px] text-white/50 mt-0.5">TO COVER</div>
          </div>
        )}
        {data.sharesShort != null && (
          <div>
            <div className="text-[14px] font-light text-white leading-none tabular-nums">
              {formatShares(data.sharesShort)}
            </div>
            <div className="text-[11px] text-white/50 mt-0.5">
              SHARES{changeStr ? ` (${changeStr})` : ''}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
