/**
 * Chart system stub.
 * TODO: Migrate the SGChart implementation from the archive.
 * This provides the type signatures and a placeholder component.
 */

'use client'

import { type ComponentType } from 'react'

export interface TimeSeriesPoint {
  time: number
  value: number
}

export interface SeriesConfig {
  id: string
  type: 'line' | 'area'
  data: TimeSeriesPoint[]
  color?: string
  strokeWidth?: number
  fillOpacity?: number
  opacity?: number
  axis?: 'y' | 'y2'
}

export interface AxisConfig {
  format?: (v: number) => string
  label?: string
  ticks?: number
}

export interface OverlayConfig {
  type: 'trend' | 'baseline'
  seriesId: string
}

export interface SGChartProps {
  series: SeriesConfig[]
  axes?: {
    x?: 'time' | 'index'
    y?: AxisConfig
    y2?: AxisConfig
  }
  overlays?: OverlayConfig[]
  padding?: { top?: number; right?: number; bottom?: number; left?: number }
  animate?: boolean
  className?: string
}

/** Placeholder chart — renders a simple SVG sparkline from the first series */
export function SGChart({ series, className }: SGChartProps) {
  const data = series[0]?.data
  if (!data || data.length < 2) {
    return <div className={className} />
  }

  const values = data.map(d => d.value)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1

  const points = data.map((d, i) => {
    const x = (i / (data.length - 1)) * 100
    const y = 100 - ((d.value - min) / range) * 80 - 10
    return `${x},${y}`
  }).join(' ')

  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className={className || 'w-full h-full'}>
      <polyline
        points={points}
        fill="none"
        stroke="rgba(255,255,255,0.3)"
        strokeWidth="0.5"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  )
}
