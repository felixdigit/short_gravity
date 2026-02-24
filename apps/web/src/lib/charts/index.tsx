'use client'

import { useState, useMemo, useCallback, useRef, type ComponentType } from 'react'

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

const DEFAULT_COLORS = [
  'rgba(255,255,255,0.6)',
  '#FF6B35',
  'rgba(34,197,94,0.6)',
  'rgba(59,130,246,0.6)',
  'rgba(168,85,247,0.6)',
]

function defaultFormat(v: number): string {
  if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (Math.abs(v) >= 1_000) return `${(v / 1_000).toFixed(1)}K`
  if (Math.abs(v) < 0.01 && v !== 0) return v.toExponential(1)
  if (Number.isInteger(v)) return v.toString()
  return v.toFixed(1)
}

function formatTime(ts: number): string {
  const d = new Date(ts)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function niceRange(min: number, max: number): { min: number; max: number } {
  if (min === max) {
    const pad = Math.abs(min) * 0.1 || 1
    return { min: min - pad, max: max + pad }
  }
  const padding = (max - min) * 0.05
  return { min: min - padding, max: max + padding }
}

function linearTicks(min: number, max: number, count: number): number[] {
  if (count <= 1) return [(min + max) / 2]
  const step = (max - min) / (count - 1)
  return Array.from({ length: count }, (_, i) => min + i * step)
}

function linearRegression(points: Array<{ x: number; y: number }>): { slope: number; intercept: number } {
  const n = points.length
  if (n < 2) return { slope: 0, intercept: points[0]?.y ?? 0 }
  let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0
  for (const p of points) {
    sumX += p.x
    sumY += p.y
    sumXY += p.x * p.y
    sumXX += p.x * p.x
  }
  const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX)
  const intercept = (sumY - slope * sumX) / n
  return { slope, intercept }
}

export function SGChart({ series, axes, overlays, padding, className }: SGChartProps) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null)
  const svgRef = useRef<SVGSVGElement>(null)

  const pad = {
    top: padding?.top ?? 12,
    right: padding?.right ?? 12,
    bottom: padding?.bottom ?? 24,
    left: padding?.left ?? 40,
  }

  const W = 400
  const H = 200
  const cw = W - pad.left - pad.right
  const ch = H - pad.top - pad.bottom

  const xMode = axes?.x ?? 'index'
  const yAxisCfg = axes?.y
  const y2AxisCfg = axes?.y2
  const yFormat = yAxisCfg?.format ?? defaultFormat
  const y2Format = y2AxisCfg?.format ?? defaultFormat
  const yTickCount = yAxisCfg?.ticks ?? 4
  const y2TickCount = y2AxisCfg?.ticks ?? 4

  // Separate series by axis
  const ySeries = useMemo(() => series.filter(s => !s.axis || s.axis === 'y'), [series])
  const y2Series = useMemo(() => series.filter(s => s.axis === 'y2'), [series])

  // Compute ranges
  const { yRange, y2Range, xRange, maxPoints } = useMemo(() => {
    let yMin = Infinity, yMax = -Infinity
    let y2Min = Infinity, y2Max = -Infinity
    let xMin = Infinity, xMax = -Infinity
    let maxPts = 0

    for (const s of ySeries) {
      for (const p of s.data) {
        if (p.value < yMin) yMin = p.value
        if (p.value > yMax) yMax = p.value
        const xVal = xMode === 'time' ? p.time : 0
        if (xVal < xMin) xMin = xVal
        if (xVal > xMax) xMax = xVal
      }
      if (s.data.length > maxPts) maxPts = s.data.length
    }

    for (const s of y2Series) {
      for (const p of s.data) {
        if (p.value < y2Min) y2Min = p.value
        if (p.value > y2Max) y2Max = p.value
        const xVal = xMode === 'time' ? p.time : 0
        if (xVal < xMin) xMin = xVal
        if (xVal > xMax) xMax = xVal
      }
      if (s.data.length > maxPts) maxPts = s.data.length
    }

    if (xMode === 'index') {
      xMin = 0
      xMax = maxPts - 1
    }

    return {
      yRange: yMin <= yMax ? niceRange(yMin, yMax) : { min: 0, max: 1 },
      y2Range: y2Min <= y2Max ? niceRange(y2Min, y2Max) : { min: 0, max: 1 },
      xRange: xMin <= xMax ? { min: xMin, max: xMax } : { min: 0, max: 1 },
      maxPoints: maxPts,
    }
  }, [ySeries, y2Series, xMode])

  const toSvg = useCallback((xVal: number, yVal: number, axis: 'y' | 'y2' = 'y') => {
    const xPct = xRange.max > xRange.min ? (xVal - xRange.min) / (xRange.max - xRange.min) : 0.5
    const range = axis === 'y' ? yRange : y2Range
    const yPct = range.max > range.min ? (yVal - range.min) / (range.max - range.min) : 0.5
    return {
      x: pad.left + xPct * cw,
      y: pad.top + ch - yPct * ch,
    }
  }, [xRange, yRange, y2Range, pad, cw, ch])

  if (!series.length || series.every(s => s.data.length < 2)) {
    return <div className={className || 'w-full h-full'} />
  }

  // Build paths for each series
  const seriesPaths = series.map((s, si) => {
    const axis = s.axis ?? 'y'
    const color = s.color ?? DEFAULT_COLORS[si % DEFAULT_COLORS.length]
    const sw = s.strokeWidth ?? 1
    const opacity = s.opacity ?? 1

    const pathPoints = s.data.map((p, i) => {
      const xVal = xMode === 'time' ? p.time : i
      const { x, y } = toSvg(xVal, p.value, axis)
      return { x, y }
    })

    const linePath = pathPoints.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ')

    let areaPath = ''
    if (s.type === 'area' && pathPoints.length > 0) {
      const baseline = pad.top + ch
      areaPath = linePath +
        ` L${pathPoints[pathPoints.length - 1].x},${baseline}` +
        ` L${pathPoints[0].x},${baseline} Z`
    }

    return { id: s.id, color, sw, opacity, linePath, areaPath, fillOpacity: s.fillOpacity ?? 0.1, pathPoints }
  })

  // Overlay (trend lines)
  const overlayPaths = (overlays ?? []).map(ov => {
    const s = series.find(s => s.id === ov.seriesId)
    if (!s || s.data.length < 2 || ov.type !== 'trend') return null
    const axis = s.axis ?? 'y'
    const regrPoints = s.data.map((p, i) => ({
      x: xMode === 'time' ? p.time : i,
      y: p.value,
    }))
    const { slope, intercept } = linearRegression(regrPoints)
    const xStart = regrPoints[0].x
    const xEnd = regrPoints[regrPoints.length - 1].x
    const p1 = toSvg(xStart, slope * xStart + intercept, axis)
    const p2 = toSvg(xEnd, slope * xEnd + intercept, axis)
    return { d: `M${p1.x},${p1.y} L${p2.x},${p2.y}`, color: 'rgba(255,255,255,0.15)' }
  }).filter(Boolean)

  // Y ticks
  const yTicks = linearTicks(yRange.min, yRange.max, yTickCount)
  const y2Ticks = y2Series.length > 0 ? linearTicks(y2Range.min, y2Range.max, y2TickCount) : []

  // X labels
  const xLabelCount = Math.min(maxPoints, 5)
  const xLabels = xLabelCount > 1
    ? Array.from({ length: xLabelCount }, (_, i) => {
        const pct = i / (xLabelCount - 1)
        const xVal = xRange.min + pct * (xRange.max - xRange.min)
        const label = xMode === 'time' ? formatTime(xVal) : Math.round(xVal).toString()
        const svgX = pad.left + pct * cw
        return { svgX, label }
      })
    : []

  // Hover
  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const svg = svgRef.current
    if (!svg || !maxPoints) return
    const rect = svg.getBoundingClientRect()
    const mouseX = ((e.clientX - rect.left) / rect.width) * W
    if (mouseX < pad.left || mouseX > pad.left + cw) {
      setHoverIdx(null)
      return
    }
    const pct = (mouseX - pad.left) / cw
    const idx = Math.round(pct * (maxPoints - 1))
    setHoverIdx(Math.max(0, Math.min(maxPoints - 1, idx)))
  }

  // Hover crosshair x position
  const hoverX = hoverIdx != null
    ? pad.left + (maxPoints > 1 ? (hoverIdx / (maxPoints - 1)) * cw : cw / 2)
    : null

  // Hover values for each series
  const hoverValues = hoverIdx != null
    ? series.map(s => {
        const p = s.data[hoverIdx]
        if (!p) return null
        const axis = s.axis ?? 'y'
        const fmt = axis === 'y2' ? y2Format : yFormat
        return { name: s.id, value: fmt(p.value), color: s.color ?? DEFAULT_COLORS[0] }
      }).filter(Boolean)
    : []

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${W} ${H}`}
      className={className || 'w-full h-full'}
      preserveAspectRatio="xMidYMid meet"
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setHoverIdx(null)}
    >
      {/* Grid lines */}
      {yTicks.map((v, i) => {
        const { y } = toSvg(0, v, 'y')
        return (
          <line
            key={`g-${i}`}
            x1={pad.left} y1={y} x2={pad.left + cw} y2={y}
            stroke="white" strokeOpacity={0.04} strokeWidth={0.5}
          />
        )
      })}

      {/* Y axis labels */}
      {yTicks.map((v, i) => {
        const { y } = toSvg(0, v, 'y')
        return (
          <text
            key={`yl-${i}`}
            x={pad.left - 3} y={y + 3}
            textAnchor="end"
            fill="white" fillOpacity={0.4}
            fontSize={7} fontFamily="monospace"
          >
            {yFormat(v)}
          </text>
        )
      })}

      {/* Y axis label text */}
      {yAxisCfg?.label && (
        <text
          x={6} y={pad.top + ch / 2}
          textAnchor="middle"
          fill="white" fillOpacity={0.3}
          fontSize={7} fontFamily="monospace"
          transform={`rotate(-90, 6, ${pad.top + ch / 2})`}
        >
          {yAxisCfg.label}
        </text>
      )}

      {/* Y2 axis labels */}
      {y2Ticks.map((v, i) => {
        const { y } = toSvg(0, v, 'y2')
        return (
          <text
            key={`y2l-${i}`}
            x={pad.left + cw + 3} y={y + 3}
            textAnchor="start"
            fill="white" fillOpacity={0.3}
            fontSize={7} fontFamily="monospace"
          >
            {y2Format(v)}
          </text>
        )
      })}

      {/* Y2 axis label text */}
      {y2AxisCfg?.label && (
        <text
          x={W - 6} y={pad.top + ch / 2}
          textAnchor="middle"
          fill="white" fillOpacity={0.3}
          fontSize={7} fontFamily="monospace"
          transform={`rotate(90, ${W - 6}, ${pad.top + ch / 2})`}
        >
          {y2AxisCfg.label}
        </text>
      )}

      {/* X axis labels */}
      {xLabels.map(({ svgX, label }, i) => (
        <text
          key={`xl-${i}`}
          x={svgX} y={H - pad.bottom + 12}
          textAnchor="middle"
          fill="white" fillOpacity={0.35}
          fontSize={7} fontFamily="monospace"
        >
          {label}
        </text>
      ))}

      {/* Overlay trend lines */}
      {overlayPaths.map((ov, i) => ov && (
        <line
          key={`ov-${i}`}
          x1={parseFloat(ov.d.split(' ')[0].slice(1).split(',')[0])}
          y1={parseFloat(ov.d.split(' ')[0].slice(1).split(',')[1])}
          x2={parseFloat(ov.d.split(' ')[1].slice(1).split(',')[0])}
          y2={parseFloat(ov.d.split(' ')[1].slice(1).split(',')[1])}
          stroke={ov.color}
          strokeWidth={0.75}
          strokeDasharray="4,3"
        />
      ))}

      {/* Series */}
      {seriesPaths.map((sp) => (
        <g key={sp.id} opacity={sp.opacity}>
          {sp.areaPath && (
            <path d={sp.areaPath} fill={sp.color} opacity={sp.fillOpacity} />
          )}
          <path d={sp.linePath} fill="none" stroke={sp.color} strokeWidth={sp.sw} />
        </g>
      ))}

      {/* Hover crosshair */}
      {hoverX != null && (
        <>
          <line
            x1={hoverX} y1={pad.top}
            x2={hoverX} y2={pad.top + ch}
            stroke="white" strokeOpacity={0.15} strokeWidth={0.5}
            strokeDasharray="2,2"
          />
          {/* Hover dots */}
          {seriesPaths.map((sp, si) => {
            if (hoverIdx == null || hoverIdx >= sp.pathPoints.length) return null
            const pt = sp.pathPoints[hoverIdx]
            return (
              <circle
                key={`hd-${si}`}
                cx={pt.x} cy={pt.y} r={2.5}
                fill={sp.color} opacity={1}
              />
            )
          })}
          {/* Hover tooltip */}
          {hoverValues.length > 0 && (
            <g>
              <rect
                x={hoverX > W / 2 ? hoverX - 80 : hoverX + 6}
                y={pad.top + 2}
                width={74}
                height={8 + hoverValues.length * 11}
                rx={2}
                fill="black" fillOpacity={0.85}
                stroke="white" strokeOpacity={0.1} strokeWidth={0.5}
              />
              {hoverValues.map((hv, i) => hv && (
                <text
                  key={`ht-${i}`}
                  x={(hoverX > W / 2 ? hoverX - 74 : hoverX + 12)}
                  y={pad.top + 12 + i * 11}
                  fill="white" fillOpacity={0.7}
                  fontSize={7} fontFamily="monospace"
                >
                  <tspan fill={hv.color}>{'\u25CF'} </tspan>
                  {hv.name}: {hv.value}
                </text>
              ))}
            </g>
          )}
        </>
      )}

      {/* Legend (if multiple series) */}
      {series.length > 1 && (
        <g>
          {series.map((s, i) => {
            const color = s.color ?? DEFAULT_COLORS[i % DEFAULT_COLORS.length]
            const lx = pad.left + i * 60
            return (
              <g key={`leg-${i}`}>
                <line
                  x1={lx} y1={4} x2={lx + 10} y2={4}
                  stroke={color} strokeWidth={1.5}
                />
                <text
                  x={lx + 13} y={6}
                  fill="white" fillOpacity={0.5}
                  fontSize={7} fontFamily="monospace"
                >
                  {s.id}
                </text>
              </g>
            )
          })}
        </g>
      )}
    </svg>
  )
}
