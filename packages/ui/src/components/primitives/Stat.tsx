import { cn } from '../../lib/utils'

type StatVariant = 'default' | 'positive' | 'negative' | 'warning' | 'accent'
type StatSize = 'sm' | 'md' | 'lg' | 'xl'

interface StatProps {
  value: string | number
  label?: string
  sublabel?: string
  delta?: {
    value: string | number
    direction?: 'up' | 'down'
  }
  variant?: StatVariant
  size?: StatSize
  className?: string
}

const variantStyles: Record<StatVariant, string> = {
  default: 'text-white',
  positive: 'text-green-400',
  negative: 'text-red-400',
  warning: 'text-amber-400',
  accent: 'text-amber-400',
}

const sizeStyles: Record<StatSize, { value: string; label: string; delta: string }> = {
  sm: {
    value: 'text-[14px] font-light',
    label: 'text-[7px]',
    delta: 'text-[6px]',
  },
  md: {
    value: 'text-[20px] font-light',
    label: 'text-[8px]',
    delta: 'text-[7px]',
  },
  lg: {
    value: 'text-[28px] font-extralight',
    label: 'text-[8px]',
    delta: 'text-[7px]',
  },
  xl: {
    value: 'text-[32px] font-extralight',
    label: 'text-[8px]',
    delta: 'text-[7px]',
  },
}

export function Stat({
  value,
  label,
  sublabel,
  delta,
  variant = 'default',
  size = 'lg',
  className,
}: StatProps) {
  const styles = sizeStyles[size]

  return (
    <div className={cn('font-mono', className)}>
      <div className="flex items-end gap-3">
        <div
          className={cn(
            'leading-none tabular-nums',
            styles.value,
            variantStyles[variant]
          )}
        >
          {value}
        </div>
        {label && (
          <div className="pb-0.5">
            <div className={cn('text-white/60', styles.label)}>{label}</div>
            {sublabel && (
              <div className={cn('text-white/40', styles.delta)}>{sublabel}</div>
            )}
          </div>
        )}
      </div>
      {delta && (
        <div
          className={cn(
            'mt-1 tabular-nums',
            styles.delta,
            delta.direction === 'up' ? 'text-red-400/80' : delta.direction === 'down' ? 'text-green-400/80' : 'text-white/50'
          )}
        >
          {delta.direction === 'up' && '\u2191'}
          {delta.direction === 'down' && '\u2193'}
          {delta.value}
        </div>
      )}
    </div>
  )
}
