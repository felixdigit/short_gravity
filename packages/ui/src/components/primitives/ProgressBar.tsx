import { cn } from '../../lib/utils'

type ProgressBarVariant = 'default' | 'warning' | 'success' | 'danger'

interface ProgressBarProps {
  value: number
  max?: number
  variant?: ProgressBarVariant
  size?: 'sm' | 'md'
  className?: string
  showLabel?: boolean
}

const variantStyles: Record<ProgressBarVariant, string> = {
  default: 'from-white/50 to-white/70',
  warning: 'from-amber-500/70 to-amber-400',
  success: 'from-green-500/70 to-green-400',
  danger: 'from-red-500/70 to-red-400',
}

const sizeStyles: Record<string, string> = {
  sm: 'h-1',
  md: 'h-1.5',
}

export function ProgressBar({
  value,
  max = 100,
  variant = 'default',
  size = 'md',
  className,
  showLabel = false,
}: ProgressBarProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100)

  return (
    <div className={cn('w-full', className)}>
      <div className={cn('bg-white/10 rounded-full overflow-hidden', sizeStyles[size])}>
        <div
          className={cn('h-full bg-gradient-to-r rounded-full transition-all duration-300', variantStyles[variant])}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <div className="text-[6px] text-white/40 mt-1 tabular-nums">{percentage.toFixed(0)}%</div>
      )}
    </div>
  )
}
