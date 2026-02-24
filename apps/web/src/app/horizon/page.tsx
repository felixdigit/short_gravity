'use client'

import { useState } from 'react'
import { Muted } from '@shortgravity/ui'
import { useHorizon, type HorizonEvent } from '@/lib/hooks/useHorizon'

const EVENT_TYPES = ['launch', 'conjunction', 'regulatory', 'patent', 'earnings', 'catalyst'] as const

const TYPE_CONFIG: Record<string, { label: string; color: string; bg: string; border: string }> = {
  launch:      { label: 'LAUNCH',      color: 'text-emerald-400', bg: 'bg-emerald-400/10', border: 'border-emerald-400/30' },
  conjunction: { label: 'CONJUNCTION', color: 'text-red-400',     bg: 'bg-red-400/10',     border: 'border-red-400/30' },
  regulatory:  { label: 'REGULATORY',  color: 'text-blue-400',    bg: 'bg-blue-400/10',    border: 'border-blue-400/30' },
  patent:      { label: 'PATENT',      color: 'text-purple-400',  bg: 'bg-purple-400/10',  border: 'border-purple-400/30' },
  earnings:    { label: 'EARNINGS',    color: 'text-amber-400',   bg: 'bg-amber-400/10',   border: 'border-amber-400/30' },
  catalyst:    { label: 'CATALYST',    color: 'text-orange-400',  bg: 'bg-orange-400/10',  border: 'border-orange-400/30' },
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'text-red-400',
  high: 'text-red-400',
  medium: 'text-amber-400',
  low: 'text-white/50',
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function formatMonthKey(dateStr: string): string {
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function formatMonthLabel(key: string): string {
  const [year, month] = key.split('-')
  const months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
  return `${months[parseInt(month) - 1]} ${year}`
}

function groupByMonth(events: HorizonEvent[]): Map<string, HorizonEvent[]> {
  const groups = new Map<string, HorizonEvent[]>()
  for (const event of events) {
    const key = formatMonthKey(event.date)
    const group = groups.get(key)
    if (group) {
      group.push(event)
    } else {
      groups.set(key, [event])
    }
  }
  return groups
}

export default function HorizonPage() {
  const [activeTypes, setActiveTypes] = useState<Set<string>>(new Set())
  const { data, isLoading } = useHorizon(90)

  const events = data?.data ?? []
  const count = data?.count ?? 0

  const filtered = activeTypes.size === 0
    ? events
    : events.filter((e) => activeTypes.has(e.type))

  const grouped = groupByMonth(filtered)

  function toggleType(type: string) {
    setActiveTypes((prev) => {
      const next = new Set(prev)
      if (next.has(type)) {
        next.delete(type)
      } else {
        next.add(type)
      }
      return next
    })
  }

  return (
    <div className="min-h-screen bg-[#030305] text-white font-mono">
      <div className="max-w-5xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="flex items-baseline justify-between mb-8">
          <div>
            <h1 className="text-2xl font-light tracking-wider">EVENT HORIZON</h1>
            <Muted className="text-xs mt-1">
              Unified timeline — launches, conjunctions, regulatory, patents, earnings, catalysts
            </Muted>
          </div>
          <div className="text-right">
            <span className="text-3xl font-light tabular-nums">{count}</span>
            <Muted className="text-xs ml-2">EVENTS</Muted>
          </div>
        </div>

        {/* Type filter chips */}
        <div className="flex flex-wrap gap-1 mb-8">
          {EVENT_TYPES.map((type) => {
            const cfg = TYPE_CONFIG[type]
            const active = activeTypes.has(type)
            return (
              <button
                key={type}
                onClick={() => toggleType(type)}
                className={`text-[10px] px-2.5 py-1 rounded border transition-colors ${
                  active
                    ? `${cfg.border} ${cfg.bg} ${cfg.color}`
                    : 'border-white/[0.06] text-white/25 hover:text-white/40'
                }`}
              >
                {cfg.label}
              </button>
            )
          })}
        </div>

        {/* Timeline */}
        {isLoading ? (
          <div className="text-white/30 text-sm py-20 text-center">
            SCANNING HORIZON...
          </div>
        ) : filtered.length === 0 ? (
          <div className="border border-white/[0.06] rounded-lg p-12 text-center">
            <div className="text-white/30 text-sm mb-2">No events in window</div>
            <Muted className="text-xs">
              Showing next 90 days.
              {activeTypes.size > 0 && ' Try clearing filters.'}
            </Muted>
          </div>
        ) : (
          <div className="space-y-10">
            {Array.from(grouped.entries()).map(([monthKey, monthEvents]) => (
              <section key={monthKey}>
                <h2 className="text-xs text-white/40 tracking-widest mb-3 border-b border-white/[0.06] pb-2">
                  {formatMonthLabel(monthKey)}
                </h2>
                <div className="space-y-2">
                  {monthEvents.map((event) => {
                    const cfg = TYPE_CONFIG[event.type] ?? TYPE_CONFIG.catalyst
                    return (
                      <div
                        key={event.id}
                        className="border border-white/[0.06] rounded-lg px-4 py-3 hover:border-white/[0.12] transition-colors"
                      >
                        <div className="flex items-start gap-3">
                          {/* Type badge */}
                          <span
                            className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${cfg.color} ${cfg.bg} mt-0.5 shrink-0`}
                          >
                            {cfg.label}
                          </span>

                          <div className="flex-1 min-w-0">
                            {/* Date + severity */}
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-[10px] text-white/40 tabular-nums">
                                {formatDate(event.date)}
                              </span>
                              {event.estimated_period && (
                                <span className="text-[10px] text-white/20">
                                  ~{event.estimated_period}
                                </span>
                              )}
                              <span
                                className={`text-[10px] ml-auto ${SEVERITY_COLORS[event.severity] ?? 'text-white/30'}`}
                              >
                                {event.severity.toUpperCase()}
                              </span>
                            </div>

                            {/* Title */}
                            <div className="text-sm text-white/80 leading-snug">
                              {event.title}
                            </div>

                            {/* Subtitle */}
                            {event.subtitle && (
                              <div className="text-xs text-white/40 mt-1 line-clamp-2">
                                {event.subtitle}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </section>
            ))}
          </div>
        )}

        {/* Back links */}
        <div className="mt-12 flex justify-center gap-6">
          <a href="/" className="text-[11px] text-white/30 hover:text-white/50 transition-colors">
            BACK TO TERMINAL
          </a>
          <a href="/orbital" className="text-[11px] text-white/30 hover:text-white/50 transition-colors">
            ORBITAL INTELLIGENCE
          </a>
        </div>
      </div>
    </div>
  )
}
