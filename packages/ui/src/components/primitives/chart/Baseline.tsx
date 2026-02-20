interface BaselineProps {
  x1: number
  x2: number
  y: number
  opacity?: number
}

export function Baseline({ x1, x2, y, opacity = 0.06 }: BaselineProps) {
  return (
    <line
      x1={x1} y1={y}
      x2={x2} y2={y}
      stroke="white" strokeOpacity={opacity} strokeWidth="0.5"
    />
  )
}
