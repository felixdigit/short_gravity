'use client'

import { useState } from 'react'
import { Muted } from '@shortgravity/ui'
import { useEarnings } from '@/lib/hooks/useEarnings'
import { useStockPrice } from '@/lib/hooks/useStockPrice'

const STATUS_COLORS: Record<string, string> = {
  MET: 'text-green-400 border-green-400/20 bg-green-400/5',
  MISSED: 'text-red-400 border-red-400/20 bg-red-400/5',
  DELAYED: 'text-amber-400 border-amber-400/20 bg-amber-400/5',
  PENDING: 'text-white/40 border-white/10 bg-white/[0.02]',
  DROPPED: 'text-white/20 border-white/5 bg-white/[0.01]',
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '--'
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export default function EarningsPage() {
  const [selectedQuarter, setSelectedQuarter] = useState<string | undefined>()
  const [expandedTranscript, setExpandedTranscript] = useState(false)

  const { data, isLoading } = useEarnings(selectedQuarter)
  const { data: stock } = useStockPrice('ASTS')

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#030305] text-white font-mono">
        <div className="max-w-5xl mx-auto px-6 py-12">
          <h1 className="text-2xl font-light tracking-wider mb-8">EARNINGS</h1>
          <div className="text-white/30 text-sm py-20 text-center">LOADING...</div>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-[#030305] text-white font-mono">
        <div className="max-w-5xl mx-auto px-6 py-12">
          <h1 className="text-2xl font-light tracking-wider mb-8">EARNINGS</h1>
          <div className="border border-white/[0.06] rounded-lg p-12 text-center">
            <div className="text-white/30 text-sm mb-2">No earnings data available</div>
            <Muted className="text-xs">Transcript data is populated by the earnings worker.</Muted>
          </div>
          <div className="mt-12 text-center">
            <a href="/" className="text-[11px] text-white/30 hover:text-white/50 transition-colors">
              BACK TO TERMINAL
            </a>
          </div>
        </div>
      </div>
    )
  }

  const { meta, quarters, transcript, topicMatrix, priceReaction, guidance } = data

  return (
    <div className="min-h-screen bg-[#030305] text-white font-mono">
      <div className="max-w-5xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="flex items-baseline justify-between mb-8">
          <div>
            <h1 className="text-2xl font-light tracking-wider">EARNINGS</h1>
            <Muted className="text-xs mt-1">
              ASTS earnings call transcripts, topic analysis, and guidance tracking
            </Muted>
          </div>
          <div className="text-right">
            <span className="text-3xl font-light tabular-nums">{quarters.length}</span>
            <Muted className="text-xs ml-2">QUARTERS</Muted>
          </div>
        </div>

        {/* Stock context bar */}
        {stock && (
          <div className="flex items-center gap-6 border border-white/[0.06] rounded-lg px-4 py-3 mb-6">
            <div>
              <span className="text-[10px] text-white/40 mr-2">ASTS</span>
              <span className="text-lg font-light tabular-nums">
                ${stock.currentPrice.toFixed(2)}
              </span>
            </div>
            <div className={stock.change >= 0 ? 'text-green-400' : 'text-red-400'}>
              <span className="text-sm tabular-nums">
                {stock.change >= 0 ? '+' : ''}
                {stock.change.toFixed(2)}
              </span>
              <span className="text-[10px] ml-1 tabular-nums">
                ({stock.changePercent >= 0 ? '+' : ''}
                {stock.changePercent.toFixed(2)}%)
              </span>
            </div>
          </div>
        )}

        {/* Quarter selector */}
        <div className="flex flex-wrap gap-1 mb-8">
          {quarters.map((q) => {
            const isSelected = q.quarter === (selectedQuarter ?? meta.quarter)
            return (
              <button
                key={q.quarter}
                onClick={() => setSelectedQuarter(q.quarter)}
                className={`text-[11px] px-3 py-1.5 rounded-full border transition-colors ${
                  isSelected
                    ? 'border-white/20 bg-white/[0.06] text-white/80'
                    : 'border-white/[0.06] text-white/30 hover:text-white/50'
                }`}
              >
                {q.quarter}
                {q.status === 'scheduled' && (
                  <span className="ml-1 text-[9px] text-amber-400/60">SCHED</span>
                )}
              </button>
            )
          })}
        </div>

        {/* Selected quarter meta */}
        <div className="border border-white/[0.06] rounded-lg px-4 py-4 mb-6">
          <div className="flex items-baseline justify-between mb-3">
            <span className="text-lg font-light tracking-wider">{meta.quarter}</span>
            <span className="text-[11px] text-white/40">
              {meta.status === 'scheduled' ? 'SCHEDULED' : 'REPORTED'}
            </span>
          </div>
          <div className="flex gap-6 text-[12px] text-white/50">
            <span>DATE: {formatDate(meta.date)}</span>
            {meta.time && <span>TIME: {meta.time}</span>}
          </div>
        </div>

        {/* Price reaction */}
        {priceReaction && (
          <div className="border border-white/[0.06] rounded-lg px-4 py-4 mb-6">
            <div className="text-[11px] text-white/50 tracking-wider mb-3">PRICE REACTION</div>
            <div className="flex gap-6">
              {priceReaction.preClose != null && (
                <div>
                  <div className="text-[10px] text-white/30 mb-1">PRE</div>
                  <div className="text-sm tabular-nums">${priceReaction.preClose.toFixed(2)}</div>
                </div>
              )}
              <div>
                <div className="text-[10px] text-white/30 mb-1">CLOSE</div>
                <div className="text-sm tabular-nums">${priceReaction.earningsClose.toFixed(2)}</div>
              </div>
              {priceReaction.postClose != null && (
                <div>
                  <div className="text-[10px] text-white/30 mb-1">POST</div>
                  <div className="text-sm tabular-nums">${priceReaction.postClose.toFixed(2)}</div>
                </div>
              )}
              {priceReaction.deltaPct != null && (
                <div>
                  <div className="text-[10px] text-white/30 mb-1">DELTA</div>
                  <div
                    className={`text-sm tabular-nums ${
                      priceReaction.deltaPct >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}
                  >
                    {priceReaction.deltaPct >= 0 ? '+' : ''}
                    {priceReaction.deltaPct}%
                  </div>
                </div>
              )}
              {priceReaction.volumeSpikeFactor != null && (
                <div>
                  <div className="text-[10px] text-white/30 mb-1">VOL SPIKE</div>
                  <div className="text-sm tabular-nums">{priceReaction.volumeSpikeFactor}x</div>
                </div>
              )}
            </div>
            {/* Mini price window */}
            {priceReaction.window.length > 0 && (
              <div className="flex gap-2 mt-3">
                {priceReaction.window.map((d) => (
                  <div
                    key={d.date}
                    className={`text-[10px] tabular-nums px-2 py-1 rounded ${
                      d.isEarningsDate
                        ? 'bg-[#FF6B35]/10 text-[#FF6B35]'
                        : 'bg-white/[0.02] text-white/40'
                    }`}
                  >
                    <div>{d.date.slice(5)}</div>
                    <div>${d.close.toFixed(2)}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Transcript */}
        {transcript ? (
          <div className="border border-white/[0.06] rounded-lg px-4 py-4 mb-6">
            <div className="flex items-center justify-between mb-3">
              <div className="text-[11px] text-white/50 tracking-wider">TRANSCRIPT</div>
              <Muted className="text-[10px]">{transcript.wordCount.toLocaleString()} words</Muted>
            </div>
            {transcript.title && (
              <div className="text-sm text-white/70 mb-2">{transcript.title}</div>
            )}
            {transcript.summary && (
              <div className="text-xs text-white/50 leading-relaxed mb-3">{transcript.summary}</div>
            )}
            {transcript.text && (
              <>
                <button
                  onClick={() => setExpandedTranscript(!expandedTranscript)}
                  className="text-[11px] text-[#FF6B35]/70 hover:text-[#FF6B35] transition-colors mb-2"
                >
                  {expandedTranscript ? 'COLLAPSE' : 'EXPAND FULL TRANSCRIPT'}
                </button>
                {expandedTranscript && (
                  <div className="text-xs text-white/40 leading-relaxed whitespace-pre-wrap max-h-[60vh] overflow-y-auto border-t border-white/[0.06] pt-3 mt-2">
                    {transcript.text}
                  </div>
                )}
              </>
            )}
          </div>
        ) : (
          <div className="border border-white/[0.06] rounded-lg px-4 py-4 mb-6">
            <div className="text-[11px] text-white/50 tracking-wider mb-2">TRANSCRIPT</div>
            <Muted className="text-xs">
              {meta.status === 'scheduled'
                ? 'Transcript will be available after the earnings call.'
                : 'No transcript available for this quarter.'}
            </Muted>
          </div>
        )}

        {/* Topic matrix */}
        {topicMatrix.length > 0 && topicMatrix.some((t) => t.currentCount > 0) && (
          <div className="border border-white/[0.06] rounded-lg px-4 py-4 mb-6">
            <div className="text-[11px] text-white/50 tracking-wider mb-3">
              TOPIC ANALYSIS — {meta.quarter}
            </div>
            <div className="space-y-1">
              {topicMatrix
                .filter((t) => t.currentCount > 0)
                .sort((a, b) => b.currentCount - a.currentCount)
                .map((t) => (
                  <div key={t.topic} className="flex items-center gap-3">
                    <span className="text-[11px] text-white/50 w-28 shrink-0">{t.label}</span>
                    <div className="flex-1 h-3 bg-white/[0.03] rounded overflow-hidden">
                      <div
                        className="h-full bg-[#FF6B35]/30 rounded"
                        style={{
                          width: `${Math.min(100, (t.currentCount / Math.max(...topicMatrix.map((m) => m.currentCount), 1)) * 100)}%`,
                        }}
                      />
                    </div>
                    <span className="text-[11px] text-white/40 tabular-nums w-6 text-right">
                      {t.currentCount}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Guidance tracker */}
        {(guidance.active.length > 0 || guidance.resolved.length > 0) && (
          <div className="border border-white/[0.06] rounded-lg px-4 py-4 mb-6">
            <div className="flex items-baseline justify-between mb-3">
              <span className="text-[11px] text-white/50 tracking-wider">GUIDANCE TRACKER</span>
              <div className="flex gap-3 text-[10px]">
                {guidance.resolved.filter((g) => g.status === 'MET').length > 0 && (
                  <span className="text-green-400">
                    {guidance.resolved.filter((g) => g.status === 'MET').length} MET
                  </span>
                )}
                {guidance.active.length > 0 && (
                  <span className="text-amber-400">{guidance.active.length} PENDING</span>
                )}
              </div>
            </div>
            <div className="space-y-2">
              {[...guidance.active, ...guidance.resolved].map((g) => (
                <div
                  key={g.id}
                  className="flex items-start gap-3 border border-white/[0.04] rounded px-3 py-2"
                >
                  <span
                    className={`text-[9px] font-bold px-1.5 py-0.5 rounded border shrink-0 mt-0.5 ${
                      STATUS_COLORS[g.status] ?? STATUS_COLORS.PENDING
                    }`}
                  >
                    {g.status}
                  </span>
                  <div className="min-w-0">
                    <div className="text-xs text-white/70 leading-snug">{g.promise_text}</div>
                    {g.outcome_text && (
                      <div className="text-[11px] text-white/40 mt-1">{g.outcome_text}</div>
                    )}
                    <div className="flex gap-3 mt-1 text-[10px] text-white/25">
                      <span>{g.category}</span>
                      <span>DUE {g.quarter_due}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Back link */}
        <div className="mt-12 flex justify-center gap-6">
          <a
            href="/"
            className="text-[11px] text-white/30 hover:text-white/50 transition-colors"
          >
            BACK TO TERMINAL
          </a>
          <a
            href="/signals"
            className="text-[11px] text-white/30 hover:text-white/50 transition-colors"
          >
            SIGNALS
          </a>
        </div>
      </div>
    </div>
  )
}
