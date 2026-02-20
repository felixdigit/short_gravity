interface HairlinePathProps {
  d: string
  opacity?: number
  strokeWidth?: number
}

export function HairlinePath({ d, opacity = 0.5, strokeWidth = 0.75 }: HairlinePathProps) {
  return (
    <path d={d} fill="none" stroke="white" strokeWidth={strokeWidth} opacity={opacity} />
  )
}
