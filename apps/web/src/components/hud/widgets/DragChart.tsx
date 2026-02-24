'use client'

import { useState, useMemo, useCallback, useRef } from 'react'
import { cn } from '@/lib/utils'

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

const PAD = { top: 16, right: 12, bottom: 32, left: 52 }
const PAD_ALT_RIGHT = 44
const CHART_COLOR = '#FF6B35'
const ALT_COLOR = 'rgba(255,255,255,0.35)'

function formatDate(epoch: string): string {
  const d = new Date(epoch)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function formatBstar(v: number): string {
  return v.toExponential(2)
}

function niceTicksBstar(min: number, max: number, count: number): number[] {
  if (min === max) return [min]
  const step = (max - min) / (count - 1)
  return Array.from({ length: count }, (_, i) => min + i * step)
}

export function DragChart({ data, className }: DragChartProps) {
  const [activeIdx, setActiveIdx] = useState<number | null>(null)
  const svgRef = useRef<SVGSVGElement>(null)

  const hasAlt = useMemo(() => data.some(d => d.altitude != null), [data])
  const rightPad = hasAlt ? PAD_ALT_RIGHT : PAD.right

  const bounds = useMemo(() => {
    if (!data.length) return null
    const bstars = data.map(d => d.bstar)
    const bMin = Math.min(...bstars)
    const bMax = Math.max(...bstars)
    const alts = data.filter(d => d.altitude != null).map(d => d.altitude!)
    const aMin = alts.length ? Math.min(...alts) : 0
    const aMax = alts.length ? Math.max(...alts) : 0
    return { bMin, bMax, aMin, aMax }
  }, [data])

  const mapPoint = useCallback((i: number, width: number, height: number) => {
    if (!bounds || !data.length) return { x: 0, yBstar: 0, yAlt: 0 }
    const cw = width - PAD.left - rightPad
    const ch = height - PAD.top - PAD.bottom
    const x = PAD.left + (data.length > 1 ? (i / (data.length - 1)) * cw : cw / 2)
    const bRange = bounds.bMax - bounds.bMin || 1
    const yBstar = PAD.top + ch - ((data[i].bstar - bounds.bMin) / bRange) * ch
    const aRange = bounds.aMax - bounds.aMin || 1
    const yAlt = data[i].altitude != null
      ? PAD.top + ch - ((data[i].altitude! - bounds.aMin) / aRange) * ch
      : 0
    return { x, yBstar, yAlt }
  }, [bounds, data, rightPad])

  if (!data.length) {
    return (
      <div className={cn('flex items-center justify-center h-full text-[11px] text-white/50', className)}>
        NO DRAG DATA
      </div>
    )
  }

  const W = 400
  const H = 200
  const cw = W - PAD.left - rightPad
  const ch = H - PAD.top - PAD.bottom

  // Build B* path
  const bstarPath = data.map((_, i) => {
    const { x, yBstar } = mapPoint(i, W, H)
    return `${i === 0 ? 'M' : 'L'}${x},${yBstar}`
  }).join(' ')

  // Build altitude path
  const altPath = hasAlt
    ? data.filter(d => d.altitude != null).map((_, fi) => {
        const origIdx = data.findIndex((d, j) => {
          let count = 0
          for (let k = 0; k <= j; k++) { if (data[k].altitude != null) count++ }
          return count - 1 === fi
        })
        // Simpler: just iterate and count
        let realIdx = -1
        let seen = 0
        for (let k = 0; k < data.length; k++) {
          if (data[k].altitude != null) {
            if (seen === fi) { realIdx = k; break }
            seen++
          }
        }
        if (realIdx < 0) return ''
        const { x, yAlt } = mapPoint(realIdx, W, H)
        return `${fi === 0 ? 'M' : 'L'}${x},${yAlt}`
      }).join(' ')
    : ''

  // Y axis ticks (B*)
  const yTicks = bounds ? niceTicksBstar(bounds.bMin, bounds.bMax, 4) : []
  // Y2 axis ticks (altitude)
  const y2Ticks = hasAlt && bounds
    ? niceTicksBstar(bounds.aMin, bounds.aMax, 4)
    : []

  // X axis labels (pick ~5 evenly spaced)
  const xLabelCount = Math.min(data.length, 5)
  const xLabels = Array.from({ length: xLabelCount }, (_, i) => {
    const idx = xLabelCount > 1
      ? Math.round((i / (xLabelCount - 1)) * (data.length - 1))
      : 0
    return { idx, label: formatDate(data[idx].epoch) }
  })

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const svg = svgRef.current
    if (!svg) return
    const rect = svg.getBoundingClientRect()
    const mouseX = ((e.clientX - rect.left) / rect.width) * W
    const chartLeft = PAD.left
    const chartRight = W - rightPad
    if (mouseX < chartLeft || mouseX > chartRight) {
      setActiveIdx(null)
      return
    }
    const pct = (mouseX - chartLeft) / (chartRight - chartLeft)
    const idx = Math.round(pct * (data.length - 1))
    setActiveIdx(Math.max(0, Math.min(data.length - 1, idx)))
  }

  const activePoint = activeIdx != null ? data[activeIdx] : null
  const activePos = activeIdx != null ? mapPoint(activeIdx, W, H) : null

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${W} ${H}`}
      className={cn('w-full h-full', className)}
      preserveAspectRatio="xMidYMid meet"
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setActiveIdx(null)}
    >
      {/* Grid lines */}
      {yTicks.map((v, i) => {
        const bRange = (bounds?.bMax ?? 0) - (bounds?.bMin ?? 0) || 1
        const y = PAD.top + ch - ((v - (bounds?.bMin ?? 0)) / bRange) * ch
        return (
          <line
            key={`grid-${i}`}
            x1={PAD.left} y1={y} x2={W - rightPad} y2={y}
            stroke="white" strokeOpacity={0.05} strokeWidth={0.5}
          />
        )
      })}

      {/* Y axis labels (B*) */}
      {yTicks.map((v, i) => {
        const bRange = (bounds?.bMax ?? 0) - (bounds?.bMin ?? 0) || 1
        const y = PAD.top + ch - ((v - (bounds?.bMin ?? 0)) / bRange) * ch
        return (
          <text
            key={`yl-${i}`}
            x={PAD.left - 4} y={y + 3}
            textAnchor="end"
            fill="white" fillOpacity={0.4}
            fontSize={8} fontFamily="monospace"
          >
            {formatBstar(v)}
          </text>
        )
      })}

      {/* Y2 axis labels (altitude) */}
      {hasAlt && y2Ticks.map((v, i) => {
        const aRange = (bounds?.aMax ?? 0) - (bounds?.aMin ?? 0) || 1
        const y = PAD.top + ch - ((v - (bounds?.aMin ?? 0)) / aRange) * ch
        return (
          <text
            key={`y2l-${i}`}
            x={W - rightPad + 4} y={y + 3}
            textAnchor="start"
            fill="white" fillOpacity={0.3}
            fontSize={8} fontFamily="monospace"
          >
            {v.toFixed(0)}km
          </text>
        )
      })}

      {/* X axis labels */}
      {xLabels.map(({ idx, label }) => {
        const { x } = mapPoint(idx, W, H)
        return (
          <text
            key={`xl-${idx}`}
            x={x} y={H - PAD.bottom + 14}
            textAnchor="middle"
            fill="white" fillOpacity={0.4}
            fontSize={8} fontFamily="monospace"
          >
            {label}
          </text>
        )
      })}

      {/* Altitude line */}
      {hasAlt && altPath && (
        <path d={altPath} fill="none" stroke={ALT_COLOR} strokeWidth={1} />
      )}

      {/* B* line */}
      <path d={bstarPath} fill="none" stroke={CHART_COLOR} strokeWidth={1.5} />

      {/* Data point circles */}
      {data.map((_, i) => {
        const { x, yBstar } = mapPoint(i, W, H)
        return (
          <circle
            key={`pt-${i}`}
            cx={x} cy={yBstar} r={activeIdx === i ? 3 : 1.5}
            fill={CHART_COLOR}
            opacity={activeIdx === i ? 1 : 0.6}
          />
        )
      })}

      {/* Hover crosshair + tooltip */}
      {activeIdx != null && activePos && activePoint && (
        <>
          <line
            x1={activePos.x} y1={PAD.top}
            x2={activePos.x} y2={PAD.top + ch}
            stroke="white" strokeOpacity={0.2} strokeWidth={0.5}
            strokeDasharray="2,2"
          />
          {/* Tooltip background */}
          <rect
            x={activePos.x + (activePos.x > W / 2 ? -130 : 8)}
            y={Math.max(PAD.top, activePos.yBstar - 32)}
            width={122} height={activePoint.altitude != null ? 42 : 28}
            rx={2}
            fill="black" fillOpacity={0.85}
            stroke="white" strokeOpacity={0.15} strokeWidth={0.5}
          />
          {/* Tooltip text */}
          <text
            x={activePos.x + (activePos.x > W / 2 ? -124 : 14)}
            y={Math.max(PAD.top, activePos.yBstar - 32) + 12}
            fill="white" fillOpacity={0.8}
            fontSize={8} fontFamily="monospace"
          >
            {formatDate(activePoint.epoch)} · B*: {formatBstar(activePoint.bstar)}
          </text>
          {activePoint.altitude != null && (
            <text
              x={activePos.x + (activePos.x > W / 2 ? -124 : 14)}
              y={Math.max(PAD.top, activePos.yBstar - 32) + 24}
              fill="white" fillOpacity={0.5}
              fontSize={8} fontFamily="monospace"
            >
              Alt: {activePoint.altitude.toFixed(1)} km
            </text>
          )}
          {activePoint.source && (
            <text
              x={activePos.x + (activePos.x > W / 2 ? -124 : 14)}
              y={Math.max(PAD.top, activePos.yBstar - 32) + (activePoint.altitude != null ? 36 : 24)}
              fill="white" fillOpacity={0.3}
              fontSize={7} fontFamily="monospace"
            >
              src: {activePoint.source}
            </text>
          )}
        </>
      )}
    </svg>
  )
}
