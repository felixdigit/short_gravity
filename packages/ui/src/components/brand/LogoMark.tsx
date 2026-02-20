interface LogoMarkProps {
  size?: number
  className?: string
}

export function LogoMark({ size = 48, className }: LogoMarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      className={className}
    >
      {/* Planet / body */}
      <circle cx="24" cy="24" r="4" fill="white" fillOpacity="0.15" />
      <circle cx="24" cy="24" r="4" stroke="white" strokeOpacity="0.3" strokeWidth="0.5" />

      {/* Orbit ring */}
      <ellipse
        cx="24"
        cy="24"
        rx="18"
        ry="7"
        transform="rotate(-30 24 24)"
        stroke="white"
        strokeOpacity="0.15"
        strokeWidth="0.5"
      />

      {/* Satellite dot on orbit */}
      <circle cx="38" cy="13.5" r="1.5" fill="white" fillOpacity="0.9" />
    </svg>
  )
}
