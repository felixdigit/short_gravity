'use client'

import { useState } from 'react'
import { Muted } from '@shortgravity/ui'
import { useSignals } from '@/lib/hooks/useSignals'

const SEVERITY_FILTERS = ['all', 'critical', 'high', 'medium', 'low'] as const

const TYPE_LABELS: Record<string, string> = {
  sentiment_shift: 'SENTIMENT',
  filing_cluster: 'FILINGS',
  fcc_status_change: 'FCC',
  cross_source: 'CROSS-SRC',
  short_interest_spike: 'SHORT INT',
  patent_regulatory_crossref: 'PATENT',
  earnings_language_shift: 'EARNINGS',
  regulatory_threat: 'REG THREAT',
  regulatory_defense: 'REG DEFENSE',
  competitor_docket_activity: 'COMPETITOR',
  competitor_fcc_grant: 'COMP FCC',
  competitor_patent_grant: 'COMP PATENT',
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'text-red-400',
  high: 'text-red-400',
  medium: 'text-amber-400',
  low: 'text-white/50',
}

function timeAgo(dateStr: string): string {
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000)
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export default function SignalsPage() {
  const [severity, setSeverity] = useState<string>('all')
  const [selectedType, setSelectedType] = useState<string>('')

  const { data, isLoading } = useSignals({
    severity: severity === 'all' ? undefined : severity,
    type: selectedType || undefined,
    limit: 50,
  })

  const signals = data?.data ?? []
  const total = data?.count ?? 0

  return (
    <div className="min-h-screen bg-[#030305] text-white font-mono">
      <div className="max-w-5xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="flex items-baseline justify-between mb-8">
          <div>
            <h1 className="text-2xl font-light tracking-wider">SIGNALS</h1>
            <Muted className="text-xs mt-1">
              Cross-source anomaly detection — scanner runs twice daily
            </Muted>
          </div>
          <div className="text-right">
            <span className="text-3xl font-light tabular-nums">{total}</span>
            <Muted className="text-xs ml-2">ACTIVE</Muted>
          </div>
        </div>

        {/* Severity filter chips */}
        <div className="flex gap-1 mb-4">
          {SEVERITY_FILTERS.map((s) => (
            <button
              key={s}
              onClick={() => setSeverity(s)}
              className={`text-[11px] px-3 py-1.5 rounded-full border transition-colors ${
                severity === s
                  ? 'border-white/20 bg-white/[0.06] text-white/80'
                  : 'border-white/[0.06] text-white/30 hover:text-white/50'
              }`}
            >
              {s.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Type filter chips */}
        <div className="flex flex-wrap gap-1 mb-8">
          {Object.entries(TYPE_LABELS).map(([type, label]) => (
            <button
              key={type}
              onClick={() => setSelectedType(selectedType === type ? '' : type)}
              className={`text-[10px] px-2 py-1 rounded border transition-colors ${
                selectedType === type
                  ? 'border-[#FF6B35]/40 bg-[#FF6B35]/10 text-[#FF6B35]'
                  : 'border-white/[0.06] text-white/25 hover:text-white/40'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Signal list */}
        {isLoading ? (
          <div className="text-white/30 text-sm py-20 text-center">
            SCANNING...
          </div>
        ) : signals.length === 0 ? (
          <div className="border border-white/[0.06] rounded-lg p-12 text-center">
            <div className="text-white/30 text-sm mb-2">No active signals</div>
            <Muted className="text-xs">
              Signal scanner runs twice daily at 13:00 and 21:00 UTC.
              {severity !== 'all' && ' Try clearing filters.'}
            </Muted>
          </div>
        ) : (
          <div className="space-y-2">
            {signals.map((signal) => (
              <div
                key={signal.id ?? signal.fingerprint}
                className="border border-white/[0.06] rounded-lg px-4 py-3 hover:border-white/[0.12] transition-colors"
              >
                <div className="flex items-start gap-3">
                  {/* Severity badge */}
                  <span
                    className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      SEVERITY_COLORS[signal.severity] ?? 'text-white/50'
                    } bg-white/[0.04] mt-0.5`}
                  >
                    {signal.severity?.toUpperCase()}
                  </span>

                  <div className="flex-1 min-w-0">
                    {/* Type + time */}
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] text-white/40">
                        {TYPE_LABELS[signal.signal_type] ?? signal.signal_type?.toUpperCase()}
                      </span>
                      {signal.detected_at && (
                        <span className="text-[10px] text-white/20">
                          {timeAgo(signal.detected_at)}
                        </span>
                      )}
                      {signal.category && (
                        <span className="text-[10px] text-white/15 ml-auto">
                          {signal.category.toUpperCase()}
                        </span>
                      )}
                    </div>

                    {/* Title */}
                    <div className="text-sm text-white/80 leading-snug">
                      {signal.title}
                    </div>

                    {/* Description */}
                    {signal.description && (
                      <div className="text-xs text-white/40 mt-1 line-clamp-2">
                        {signal.description}
                      </div>
                    )}

                    {/* Metrics */}
                    {signal.metrics && (signal.metrics.observed_value != null || signal.metrics.z_score != null) && (
                      <div className="flex gap-4 mt-2 text-[10px] text-white/30">
                        {signal.metrics.observed_value != null && (
                          <span>OBS: {Number(signal.metrics.observed_value).toFixed(2)}</span>
                        )}
                        {signal.metrics.baseline_value != null && (
                          <span>BASE: {Number(signal.metrics.baseline_value).toFixed(2)}</span>
                        )}
                        {signal.metrics.z_score != null && (
                          <span>Z: {Number(signal.metrics.z_score).toFixed(1)}</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Back link */}
        <div className="mt-12 text-center">
          <a href="/" className="text-[11px] text-white/30 hover:text-white/50 transition-colors">
            BACK TO TERMINAL
          </a>
        </div>
      </div>
    </div>
  )
}
