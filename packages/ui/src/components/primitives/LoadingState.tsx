import { cn } from '../../lib/utils'

interface LoadingStateProps {
  text?: string
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

const sizeStyles: Record<string, { container: string; text: string }> = {
  sm: { container: 'h-8', text: 'text-[7px]' },
  md: { container: 'h-14', text: 'text-[8px]' },
  lg: { container: 'h-20', text: 'text-[9px]' },
}

export function LoadingState({ text = 'Loading...', className, size = 'md' }: LoadingStateProps) {
  const styles = sizeStyles[size]

  return (
    <div
      className={cn(
        'flex items-center justify-center font-mono',
        styles.container,
        className
      )}
    >
      <span className={cn('text-white/40 animate-pulse', styles.text)}>{text}</span>
    </div>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn('bg-white/5 animate-pulse rounded', className)} />
  )
}
