'use client'

import Link from 'next/link'
import { cn } from '@/lib/utils'
import { useQuery } from '@tanstack/react-query'
import type { WidgetManifest } from './types'

export const earningsLedgerManifest: WidgetManifest = {
  id: 'earnings-ledger',
  name: 'EARNINGS',
  category: 'data',
  panelPreference: 'right',
  sizing: 'fixed',
  expandable: false,
  separator: false,
}

interface EarningsSummary {
  quarter: string
  date: string | null
  time: string | null
  status: string | null
  daysUntil: number | null
  guidancePending: number
  guidanceMet: number
}

function useEarningsSummary() {
  return useQuery<EarningsSummary | null>({
    queryKey: ['earnings-summary'],
    queryFn: async () => {
      const res = await fetch('/api/earnings/context')
      if (!res.ok) return null
      const data = await res.json()
      const meta = data?.meta
      if (!meta) return null

      const date = meta.date ? new Date(meta.date) : null
      const daysUntil = date ? Math.ceil((date.getTime() - Date.now()) / 86400000) : null

      const guidance = data?.guidance
      const guidancePending = guidance?.active?.length || 0
      const guidanceMet = guidance?.resolved?.filter((g: { status: string }) => g.status === 'MET')?.length || 0

      return {
        quarter: meta.quarter,
        date: meta.date,
        time: meta.time,
        status: meta.status,
        daysUntil,
        guidancePending,
        guidanceMet,
      }
    },
    staleTime: 30 * 60 * 1000,
    refetchInterval: 30 * 60 * 1000,
  })
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '--'
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export function EarningsLedger() {
  const { data, isLoading } = useEarningsSummary()

  if (isLoading) {
    return (
      <div className="font-mono">
        <div className="text-[11px] text-white/50 tracking-wider mb-2">EARNINGS</div>
        <div className="h-12 animate-pulse bg-white/5 rounded" />
      </div>
    )
  }

  if (!data) {
    return (
      <div className="font-mono">
        <div className="text-[11px] text-white/50 tracking-wider mb-2">EARNINGS</div>
        <div className="text-[12px] text-white/50">NO DATA</div>
      </div>
    )
  }

  const showCountdown = data.daysUntil != null && data.daysUntil > 0 && data.daysUntil <= 30
  const isUpcoming = data.status === 'scheduled'

  return (
    <div className="font-mono">
      <div className="flex items-center justify-between mb-2">
        <Link href="/earnings" className="text-[11px] text-white/50 hover:text-white/70 tracking-wider transition-colors">
          EARNINGS
        </Link>
        <span className="text-[11px] text-white/50 tracking-wider">{data.quarter}</span>
      </div>

      {showCountdown ? (
        <div className="flex items-baseline gap-2 mb-2">
          <span className="text-[28px] font-extralight text-[var(--asts-orange)] tabular-nums leading-none">
            {data.daysUntil}
          </span>
          <span className="text-[12px] text-white/50 tracking-wider">DAYS</span>
        </div>
      ) : (
        <div className="text-[14px] font-light text-white tabular-nums leading-none mb-2">
          {formatDate(data.date)}
        </div>
      )}

      <div className="text-[11px] text-white/60">
        {isUpcoming ? (
          <span>{data.time ? `${data.time}` : 'Time TBD'}</span>
        ) : (
          <span>REPORTED</span>
        )}
      </div>

      {(data.guidancePending > 0 || data.guidanceMet > 0) && (
        <div className="flex items-center gap-4 mt-3">
          {data.guidanceMet > 0 && (
            <div>
              <div className="text-[14px] font-light text-green-400 leading-none tabular-nums">
                {data.guidanceMet}
              </div>
              <div className="text-[11px] text-white/50 mt-0.5">MET</div>
            </div>
          )}
          {data.guidancePending > 0 && (
            <div>
              <div className="text-[14px] font-light text-amber-400 leading-none tabular-nums">
                {data.guidancePending}
              </div>
              <div className="text-[11px] text-white/50 mt-0.5">PENDING</div>
            </div>
          )}
        </div>
      )}

      <Link
        href="/earnings"
        className="block mt-3 text-[11px] text-white/50 hover:text-white/70 tracking-wider transition-colors"
      >
        FULL REPORT &rarr;
      </Link>
    </div>
  )
}
