interface ValueReadoutProps {
  x: number
  y: number
  children: React.ReactNode
  anchor?: 'start' | 'middle' | 'end'
  opacity?: number
  fontSize?: number
}

export function ValueReadout({ x, y, children, anchor = 'end', opacity = 0.7, fontSize = 14 }: ValueReadoutProps) {
  return (
    <text
      x={x} y={y}
      textAnchor={anchor}
      fill="white" fillOpacity={opacity}
      fontSize={fontSize} fontWeight="300"
    >
      {children}
    </text>
  )
}
