'use client'

import Link from 'next/link'
import { cn } from '@/lib/utils'
import { useSignals, type Signal } from '@/lib/hooks/useSignals'
import type { WidgetManifest } from './types'

export const signalFeedManifest: WidgetManifest = {
  id: 'signal-feed',
  name: 'SIGNALS',
  category: 'data',
  panelPreference: 'either',
  sizing: 'flexible',
  expandable: false,
  separator: false,
}

const SEVERITY_STYLES: Record<string, { dot: string; text: string }> = {
  high: { dot: 'bg-[#EF4444]', text: 'text-[#EF4444]' },
  medium: { dot: 'bg-[#EAB308]', text: 'text-[#EAB308]' },
  low: { dot: 'bg-white/50', text: 'text-white/50' },
}

const TYPE_LABELS: Record<string, string> = {
  sentiment_shift: 'SENTIMENT',
  filing_cluster: 'FILINGS',
  fcc_status_change: 'FCC',
  cross_source: 'CROSS-SRC',
  short_interest_spike: 'SHORT INT',
  patent_deployment: 'PATENT',
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const hours = Math.floor(diff / 3600000)
  if (hours < 1) return `${Math.floor(diff / 60000)}m ago`
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function SignalRow({ signal }: { signal: Signal }) {
  const style = SEVERITY_STYLES[signal.severity] || SEVERITY_STYLES.low
  const typeLabel = TYPE_LABELS[signal.signal_type] || signal.signal_type.toUpperCase()

  return (
    <div className="py-2.5 border-b border-white/[0.03] last:border-0 group hover:bg-white/[0.02] transition-colors px-1">
      <div className="flex items-start gap-2.5">
        <div className={cn('w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0', style.dot)} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={cn('text-[11px] tracking-[0.15em] uppercase px-1 py-0.5 rounded', style.text,
              signal.severity === 'high' ? 'bg-red-500/10' : signal.severity === 'medium' ? 'bg-amber-500/10' : 'bg-white/[0.03]'
            )}>
              {signal.severity.toUpperCase()}
            </span>
            <span className="text-[11px] text-white/50 tracking-[0.1em]">{typeLabel}</span>
            <span className="text-[11px] text-white/50 ml-auto flex-shrink-0">{timeAgo(signal.detected_at)}</span>
          </div>
          <div className="text-[12px] text-white/70 leading-snug">{signal.title}</div>
          {signal.description && (
            <div className="text-[11px] text-white/50 leading-relaxed mt-1 line-clamp-2">{signal.description}</div>
          )}
        </div>
      </div>
    </div>
  )
}

export function SignalFeed({ limit = 5 }: { limit?: number }) {
  const { data, isLoading } = useSignals({ limit })

  if (isLoading) {
    return (
      <div className="font-mono">
        <div className="text-[11px] text-white/50 tracking-wider mb-2">SIGNALS</div>
        <div className="space-y-2">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-10 animate-pulse bg-white/5 rounded" />
          ))}
        </div>
      </div>
    )
  }

  const signals = data?.data || []
  const highCount = signals.filter(s => s.severity === 'high').length

  return (
    <div className="font-mono">
      <div className="flex items-center justify-between mb-2">
        <Link href="/signals" className="text-[11px] text-white/50 hover:text-white/70 tracking-wider transition-colors">SIGNALS</Link>
        <div className="flex items-center gap-2">
          {highCount > 0 && (
            <span className="text-[11px] text-[#EF4444] tabular-nums">{highCount} HIGH</span>
          )}
          <span className="text-[11px] text-white/50 tabular-nums">{signals.length} TOTAL</span>
        </div>
      </div>

      {signals.length === 0 ? (
        <div className="text-[12px] text-white/50 py-4 text-center">No active signals</div>
      ) : (
        <div className="max-h-[400px] overflow-y-auto">
          {signals.map(signal => (
            <SignalRow key={signal.id} signal={signal} />
          ))}
        </div>
      )}

      <Link
        href="/signals"
        className="block mt-2 text-[11px] text-white/50 hover:text-white/70 tracking-wider transition-colors"
      >
        VIEW ALL &rarr;
      </Link>
    </div>
  )
}
