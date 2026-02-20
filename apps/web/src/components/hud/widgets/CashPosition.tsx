'use client'

import { useMemo } from 'react'
import { cn } from '@/lib/utils'
import { useCashPosition, useCashHistory } from '@/lib/hooks/useCashPosition'
import { SGChart } from '@/lib/charts'
import type { TimeSeriesPoint, SeriesConfig } from '@/lib/charts'
import type { WidgetManifest } from './types'

export const cashPositionManifest: WidgetManifest = {
  id: 'cash-position',
  name: 'CASH POSITION',
  category: 'data',
  panelPreference: 'right',
  sizing: 'fixed',
  expandable: false,
  separator: false,
}

function formatCash(value: number, unit: string | null): string {
  if (unit === 'billions') return `$${value.toFixed(1)}B`
  if (unit === 'millions') {
    if (value >= 1000) return `$${(value / 1000).toFixed(1)}B`
    return `$${Math.round(value)}M`
  }
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}B`
  if (value >= 1_000) return `$${Math.round(value / 1_000)}M`
  return `$${Math.round(value)}K`
}

function formatBurn(value: number, unit: string | null): string {
  if (unit === 'millions') return `$${Math.round(value)}M`
  if (value >= 1_000) return `$${Math.round(value / 1_000)}M`
  return `$${Math.round(value)}K`
}

function getQuarter(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00')
  const month = d.getMonth()
  if (month >= 2 && month <= 4) return '4'
  if (month >= 5 && month <= 7) return '1'
  if (month >= 8 && month <= 10) return '3'
  return '2'
}

export function CashPosition() {
  const { data, isLoading } = useCashPosition()
  const { data: historyData } = useCashHistory()

  const sparkline = useMemo(() => {
    if (!historyData?.history?.length) return null
    const points: TimeSeriesPoint[] = historyData.history
      .filter(h => h.cash != null)
      .map((h, i) => ({
        time: i,
        value: h.unit === 'millions' ? h.cash! : h.cash! / 1000,
      }))
    return points.length >= 2 ? points : null
  }, [historyData])

  if (isLoading) {
    return (
      <div className="font-mono">
        <div className="text-[11px] text-white/50 tracking-wider mb-2">CASH POSITION</div>
        <div className="h-12 animate-pulse bg-white/5 rounded" />
      </div>
    )
  }

  const cashDisplay = data?.cashOnHand != null ? formatCash(data.cashOnHand, data.unit) : '--'
  const burnDisplay = data?.quarterlyBurn != null ? formatBurn(data.quarterlyBurn, data.unit) : null
  const runwayQ = data?.quarterlyBurn && data?.cashOnHand ? Math.floor(data.cashOnHand / data.quarterlyBurn) : null

  const series: SeriesConfig[] = sparkline ? [{
    id: 'cash',
    type: 'area',
    data: sparkline,
    color: 'rgba(34,197,94,0.4)',
    strokeWidth: 0.75,
    fillOpacity: 0.06,
  }] : []

  return (
    <div className="font-mono">
      <div className="mb-2">
        <span className="text-[11px] text-white/50 tracking-wider">CASH POSITION</span>
      </div>

      <div className="text-[28px] font-extralight text-white leading-none tabular-nums">
        {cashDisplay}
      </div>
      <div className="text-[11px] text-white/50 mt-1">
        {data?.label || 'ON HAND'}
        {data?.filingForm && data?.filingDate && (
          <span className="text-white/40">
            {' \u00b7 as per '}{data.filingForm === '10-Q' || data.filingForm === '10-K' ? 'Q' + getQuarter(data.filingDate) + ' Call' : data.filingForm}
          </span>
        )}
      </div>

      {sparkline && (
        <div className="h-[40px] mt-2">
          <SGChart
            series={series}
            axes={{ x: 'index', y: { format: (v: number) => `$${v.toFixed(0)}M`, ticks: 2 } }}
            padding={{ top: 4, right: 4, bottom: 12, left: 32 }}
            animate={false}
          />
        </div>
      )}

      <div className="flex items-center gap-4 mt-3">
        {burnDisplay && (
          <div>
            <div className="text-[14px] font-light text-white leading-none tabular-nums">{burnDisplay}</div>
            <div className="text-[11px] text-white/50 mt-0.5">QTR BURN</div>
          </div>
        )}
        {runwayQ != null && (
          <div>
            <div className="text-[14px] font-light text-white leading-none tabular-nums">{runwayQ}Q</div>
            <div className="text-[11px] text-white/50 mt-0.5">RUNWAY</div>
          </div>
        )}
      </div>
    </div>
  )
}
