interface CornerBracketsProps {
  x0: number
  y0: number
  x1: number
  y1: number
  arm?: number
  opacity?: number
}

export function CornerBrackets({ x0, y0, x1, y1, arm = 6, opacity = 0.08 }: CornerBracketsProps) {
  return (
    <g>
      <path d={`M${x0},${y0 + arm} L${x0},${y0} L${x0 + arm},${y0}`} fill="none" stroke="white" strokeOpacity={opacity} strokeWidth="0.5" />
      <path d={`M${x1 - arm},${y0} L${x1},${y0} L${x1},${y0 + arm}`} fill="none" stroke="white" strokeOpacity={opacity} strokeWidth="0.5" />
      <path d={`M${x0},${y1 - arm} L${x0},${y1} L${x0 + arm},${y1}`} fill="none" stroke="white" strokeOpacity={opacity} strokeWidth="0.5" />
      <path d={`M${x1 - arm},${y1} L${x1},${y1} L${x1},${y1 - arm}`} fill="none" stroke="white" strokeOpacity={opacity} strokeWidth="0.5" />
    </g>
  )
}
