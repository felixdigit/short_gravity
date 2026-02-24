'use client'

import { useQuery } from '@tanstack/react-query'
import { Muted } from '@shortgravity/ui'

interface Competitor {
  company: string
  ticker: string | null
  approach: string
  constellation: string
  spectrum: string
  status: string
  highlight: boolean
}

interface CompetitorSignal {
  id: number
  signal_type: string
  severity: string
  title: string
  detected_at: string
}

interface CompetitiveResponse {
  competitors: Competitor[]
  recentActivity: CompetitorSignal[]
}

const TYPE_BADGES: Record<string, string> = {
  competitor_docket_activity: 'COMP DOCKET',
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

const COLUMNS = ['APPROACH', 'CONSTELLATION', 'SPECTRUM', 'STATUS'] as const

export default function CompetitivePage() {
  const { data, isLoading } = useQuery<CompetitiveResponse>({
    queryKey: ['competitive'],
    queryFn: async () => {
      const res = await fetch('/api/competitive')
      if (!res.ok) throw new Error('Failed to fetch competitive data')
      return res.json()
    },
    staleTime: 15 * 60 * 1000,
  })

  const competitors = data?.competitors ?? []
  const activity = data?.recentActivity ?? []

  return (
    <div className="min-h-screen bg-[#030305] text-white font-mono">
      <div className="max-w-6xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="flex items-baseline justify-between mb-8">
          <div>
            <h1 className="text-2xl font-light tracking-wider">WAR ROOM</h1>
            <Muted className="text-xs mt-1">
              D2C satellite competitive landscape — AST SpaceMobile vs field
            </Muted>
          </div>
          <div className="text-right">
            <span className="text-3xl font-light tabular-nums">{competitors.length}</span>
            <Muted className="text-xs ml-2">PLAYERS</Muted>
          </div>
        </div>

        {isLoading ? (
          <div className="text-white/30 text-sm py-20 text-center">LOADING...</div>
        ) : (
          <>
            {/* Comparison table */}
            <div className="border border-white/[0.06] rounded-lg overflow-hidden mb-8">
              {/* Table header */}
              <div className="grid grid-cols-[160px_1fr_1fr_1fr_140px] border-b border-white/[0.06]">
                <div className="px-4 py-3 text-[10px] text-white/30 tracking-wider">COMPANY</div>
                {COLUMNS.map((col) => (
                  <div key={col} className="px-4 py-3 text-[10px] text-white/30 tracking-wider">
                    {col}
                  </div>
                ))}
              </div>

              {/* Rows */}
              {competitors.map((c) => (
                <div
                  key={c.company}
                  className={`grid grid-cols-[160px_1fr_1fr_1fr_140px] border-b border-white/[0.04] last:border-b-0 ${
                    c.highlight
                      ? 'bg-[#FF6B35]/[0.03] border-l-2 border-l-[#FF6B35]/30'
                      : 'hover:bg-white/[0.02]'
                  }`}
                >
                  <div className="px-4 py-3">
                    <div className={`text-xs ${c.highlight ? 'text-[#FF6B35]' : 'text-white/80'}`}>
                      {c.company}
                    </div>
                    {c.ticker && (
                      <div className="text-[10px] text-white/25 mt-0.5">{c.ticker}</div>
                    )}
                  </div>
                  <div className="px-4 py-3 text-xs text-white/60 leading-snug">{c.approach}</div>
                  <div className="px-4 py-3 text-xs text-white/60 leading-snug">
                    {c.constellation}
                  </div>
                  <div className="px-4 py-3 text-xs text-white/60 leading-snug">{c.spectrum}</div>
                  <div className="px-4 py-3">
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded border ${
                        c.highlight
                          ? 'border-[#FF6B35]/20 text-[#FF6B35]/80 bg-[#FF6B35]/5'
                          : 'border-white/10 text-white/40 bg-white/[0.02]'
                      }`}
                    >
                      {c.status.toUpperCase()}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* Key differentiator callout */}
            <div className="border border-[#FF6B35]/10 rounded-lg px-5 py-4 mb-8 bg-[#FF6B35]/[0.02]">
              <div className="text-[11px] text-[#FF6B35]/60 tracking-wider mb-3">
                KEY DIFFERENTIATOR
              </div>
              <div className="space-y-2 text-xs text-white/60 leading-relaxed">
                <p>
                  <span className="text-white/80">Massive phased arrays.</span> AST deploys the
                  largest-ever commercial phased array antennas (64–225m²), enabling broadband data
                  speeds to unmodified phones. Competitors use small satellite approaches limited to
                  SMS/text or emergency SOS.
                </p>
                <p>
                  <span className="text-white/80">Broadband vs SMS.</span> AST targets full voice +
                  data (5–10 Mbps per beam), while SpaceX/T-Mobile is text-only, Lynk is SMS-only,
                  and Apple/Globalstar is emergency-only. No competitor has demonstrated broadband
                  D2C with unmodified handsets.
                </p>
              </div>
            </div>

            {/* Recent competitor activity */}
            <div className="border border-white/[0.06] rounded-lg px-4 py-4 mb-6">
              <div className="text-[11px] text-white/50 tracking-wider mb-3">
                RECENT COMPETITOR ACTIVITY
              </div>
              {activity.length === 0 ? (
                <Muted className="text-xs">
                  No recent competitor signals detected. Scanner runs twice daily.
                </Muted>
              ) : (
                <div className="space-y-2">
                  {activity.map((signal) => (
                    <div
                      key={signal.id}
                      className="flex items-start gap-3 border border-white/[0.04] rounded px-3 py-2"
                    >
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.5 rounded bg-white/[0.04] mt-0.5 shrink-0 ${
                          SEVERITY_COLORS[signal.severity] ?? 'text-white/50'
                        }`}
                      >
                        {signal.severity?.toUpperCase()}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-[10px] text-white/40">
                            {TYPE_BADGES[signal.signal_type] ?? signal.signal_type?.toUpperCase()}
                          </span>
                          {signal.detected_at && (
                            <span className="text-[10px] text-white/20">
                              {timeAgo(signal.detected_at)}
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-white/80 leading-snug">{signal.title}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {/* Back links */}
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
