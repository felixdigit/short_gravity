interface GhostTrendProps {
  x1: number
  y1: number
  x2: number
  y2: number
  opacity?: number
}

export function GhostTrend({ x1, y1, x2, y2, opacity = 0.15 }: GhostTrendProps) {
  return (
    <line
      x1={x1} y1={y1}
      x2={x2} y2={y2}
      stroke="white" strokeWidth="0.5" strokeDasharray="4,3" opacity={opacity}
    />
  )
}
