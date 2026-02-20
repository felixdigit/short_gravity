import { cn } from '../../lib/utils'

type StatusDotVariant = 'nominal' | 'warning' | 'critical' | 'info' | 'accent'
type StatusDotSize = 'xs' | 'sm' | 'md'

interface StatusDotProps {
  variant?: StatusDotVariant
  size?: StatusDotSize
  pulse?: boolean
  className?: string
}

const variantStyles: Record<StatusDotVariant, string> = {
  nominal: 'bg-green-400',
  warning: 'bg-amber-400',
  critical: 'bg-red-400',
  info: 'bg-blue-400',
  accent: 'bg-amber-400',
}

const sizeStyles: Record<StatusDotSize, string> = {
  xs: 'w-1 h-1',
  sm: 'w-1.5 h-1.5',
  md: 'w-2 h-2',
}

export function StatusDot({
  variant = 'nominal',
  size = 'sm',
  pulse = false,
  className,
}: StatusDotProps) {
  return (
    <span
      className={cn(
        'rounded-full inline-block',
        variantStyles[variant],
        sizeStyles[size],
        pulse && 'animate-pulse',
        className
      )}
    />
  )
}
