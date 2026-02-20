interface CrosshairProps {
  x: number
  y: number
  size?: number
  gap?: number
  opacity?: number
}

export function Crosshair({ x, y, size = 5, gap = 1.5, opacity = 0.8 }: CrosshairProps) {
  return (
    <g>
      <line x1={x - size} y1={y} x2={x - gap} y2={y} stroke="white" strokeWidth="0.75" opacity={opacity} />
      <line x1={x + gap} y1={y} x2={x + size} y2={y} stroke="white" strokeWidth="0.75" opacity={opacity} />
      <line x1={x} y1={y - size} x2={x} y2={y - gap} stroke="white" strokeWidth="0.75" opacity={opacity} />
      <line x1={x} y1={y + gap} x2={x} y2={y + size} stroke="white" strokeWidth="0.75" opacity={opacity} />
    </g>
  )
}
