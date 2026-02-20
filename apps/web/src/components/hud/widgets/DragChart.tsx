'use client'

import { cn } from '@/lib/utils'

/**
 * DragChart stub — placeholder for the B-star / altitude dual chart.
 * TODO: Migrate the full DragChart from the archive.
 */
interface DragChartProps {
  data: Array<{
    epoch: string
    bstar: number
    altitude: number | null
    source?: string
  }>
  timeRange?: { min: number; max: number }
  className?: string
}

export function DragChart({ data, className }: DragChartProps) {
  if (!data.length) {
    return (
      <div className={cn('flex items-center justify-center h-full text-[11px] text-white/50', className)}>
        NO DRAG DATA
      </div>
    )
  }

  // Simple SVG sparkline of B* values
  const values = data.map(d => d.bstar)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1

  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * 100
    const y = 100 - ((v - min) / range) * 80 - 10
    return `${x},${y}`
  }).join(' ')

  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className={cn('w-full h-full', className)}>
      <polyline
        points={points}
        fill="none"
        stroke="rgba(255,255,255,0.4)"
        strokeWidth="0.5"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  )
}
