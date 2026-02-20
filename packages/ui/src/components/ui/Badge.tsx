import { cn } from '../../lib/utils'
import type { SignalSeverity } from '../../types'

interface BadgeProps {
  severity?: SignalSeverity
  children: React.ReactNode
  className?: string
}

const severityStyles: Record<SignalSeverity, string> = {
  critical: 'bg-red-500/10 text-red-400 border-red-500/20',
  high: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  medium: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  low: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
}

export function Badge({ severity, children, className }: BadgeProps) {
  return (
    <span className={cn(
      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border',
      severity ? severityStyles[severity] : 'bg-white/10 text-white/60 border-white/20',
      className
    )}>
      {children}
    </span>
  )
}
