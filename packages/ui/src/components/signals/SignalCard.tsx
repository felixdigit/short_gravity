import { cn } from '../../lib/utils'
import type { Signal } from '../../types'

const SEVERITY_COLORS: Record<string, { dot: string; badge: string }> = {
  critical: { dot: 'bg-[#EF4444]', badge: 'text-[#EF4444]' },
  high: { dot: 'bg-[#EF4444]', badge: 'text-[#EF4444]' },
  medium: { dot: 'bg-[#EAB308]', badge: 'text-[#EAB308]' },
  low: { dot: 'bg-white/30', badge: 'text-white/40' },
}

const CATEGORY_LABELS: Record<string, string> = {
  regulatory: 'REG',
  market: 'MKT',
  community: 'COMM',
  corporate: 'CORP',
  ip: 'IP',
  operations: 'OPS',
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const hours = Math.floor(diff / 3600000)
  if (hours < 1) return `${Math.floor(diff / 60000)}m`
  if (hours < 24) return `${hours}h`
  const days = Math.floor(hours / 24)
  return `${days}d`
}

interface SignalCardProps {
  signal: Signal
  isSelected: boolean
  isHighlighted: boolean
  onClick: () => void
  onMouseEnter: () => void
  onMouseLeave: () => void
}

export function SignalCard({ signal, isSelected, isHighlighted, onClick, onMouseEnter, onMouseLeave }: SignalCardProps) {
  const severity = SEVERITY_COLORS[signal.severity] || SEVERITY_COLORS.low
  const categoryLabel = CATEGORY_LABELS[signal.category || ''] || signal.signal_type.toUpperCase().slice(0, 4)

  return (
    <button
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      className={cn(
        'w-full text-left px-4 py-3 border-b border-white/[0.03] transition-colors',
        'border-l-2',
        isSelected
          ? 'bg-white/[0.04] border-l-[#FF6B35]'
          : isHighlighted
            ? 'bg-white/[0.02] border-l-white/10'
            : 'border-l-transparent hover:bg-white/[0.02]'
      )}
    >
      <div className="flex items-start gap-3">
        <div className={cn('w-1.5 h-1.5 rounded-full mt-1.5 shrink-0', severity.dot)} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={cn('text-[7px] tracking-[0.15em] font-mono', severity.badge)}>
              {signal.severity.toUpperCase()}
            </span>
            <span className="text-[7px] text-white/20 tracking-[0.1em] font-mono">
              {categoryLabel}
            </span>
            {signal.price_impact_24h != null && (
              <span className={cn(
                'text-[7px] font-mono tabular-nums',
                signal.price_impact_24h >= 0 ? 'text-[#22C55E]/60' : 'text-[#EF4444]/60'
              )}>
                {signal.price_impact_24h >= 0 ? '+' : ''}{signal.price_impact_24h.toFixed(1)}%
              </span>
            )}
            <span className="text-[7px] text-white/15 font-mono ml-auto shrink-0">
              {timeAgo(signal.detected_at)}
            </span>
          </div>
          <div className="font-mono text-[10px] text-white/70 leading-tight">{signal.title}</div>
          {signal.description && (
            <div className="font-mono text-[9px] text-white/25 leading-snug mt-1 line-clamp-1">
              {signal.description}
            </div>
          )}
        </div>
      </div>
    </button>
  )
}
