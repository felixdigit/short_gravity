'use client'

import { useState } from 'react'
import { Muted, StatusDot } from '@shortgravity/ui'
import { useRegulatoryStatus } from '@/lib/hooks/useRegulatoryStatus'
import { useRegulatoryFilings, type RegulatoryFiling } from '@/lib/hooks/useRegulatoryFilings'

const SYSTEM_FILTERS = ['ALL', 'ICFS', 'ECFS', 'ELS'] as const
type SystemFilter = (typeof SYSTEM_FILTERS)[number]

const STATUS_VARIANT: Record<string, 'nominal' | 'warning' | 'critical' | 'info'> = {
  'Action Taken Public Notice': 'nominal',
  'Action Complete': 'nominal',
  'Granted': 'nominal',
  'Pending': 'warning',
  'Accepted for Filing': 'warning',
  'On Hold': 'warning',
  'Denied': 'critical',
  'Dismissed': 'critical',
  'Returned': 'critical',
}

function statusVariant(status: string | null): 'nominal' | 'warning' | 'critical' | 'info' {
  if (!status) return 'info'
  return STATUS_VARIANT[status] ?? 'info'
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }).toUpperCase()
}

function truncate(str: string | null, max: number): string {
  if (!str) return '—'
  return str.length > max ? str.slice(0, max) + '...' : str
}

export default function RegulatoryPage() {
  const [system, setSystem] = useState<SystemFilter>('ALL')
  const { data: summaryData, isLoading: summaryLoading } = useRegulatoryStatus()
  const { data: filingsData, isLoading: filingsLoading } = useRegulatoryFilings(
    system === 'ALL' ? undefined : system
  )

  const summaryItems = summaryData?.items || []
  const filings = filingsData?.filings || []
  const totalFilings = filingsData?.count ?? 0

  return (
    <div className="min-h-screen bg-[#030305] text-white font-mono">
      <div className="max-w-6xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="flex items-baseline justify-between mb-8">
          <div>
            <h1 className="text-2xl font-light tracking-wider">REGULATORY BATTLEMAP</h1>
            <Muted className="text-xs mt-1">
              FCC satellite licenses, earth stations, ICFS applications, and docket activity
            </Muted>
          </div>
          <div className="text-right">
            <span className="text-3xl font-light tabular-nums">{totalFilings}</span>
            <Muted className="text-xs ml-2">FILINGS</Muted>
          </div>
        </div>

        {/* Summary stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
          {summaryLoading ? (
            [1, 2, 3, 4].map((i) => (
              <div key={i} className="border border-white/[0.06] rounded-lg p-4">
                <div className="h-4 animate-pulse bg-white/5 rounded mb-2" />
                <div className="h-6 animate-pulse bg-white/5 rounded" />
              </div>
            ))
          ) : (
            summaryItems.map((item, i) => (
              <div key={i} className="border border-white/[0.06] rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <StatusDot variant={item.color === 'green' ? 'nominal' : item.color === 'yellow' ? 'warning' : item.color === 'blue' ? 'info' : item.color === 'red' ? 'critical' : 'nominal'} size="sm" />
                  <span className="text-[10px] text-white/50 tracking-wider">{item.label}</span>
                </div>
                <div className="text-sm text-white/80 tabular-nums">{item.value}</div>
              </div>
            ))
          )}
        </div>

        {/* System filter tabs */}
        <div className="flex gap-1 mb-8">
          {SYSTEM_FILTERS.map((s) => (
            <button
              key={s}
              onClick={() => setSystem(s)}
              className={`text-[11px] px-3 py-1.5 rounded-full border transition-colors ${
                system === s
                  ? 'border-white/20 bg-white/[0.06] text-white/80'
                  : 'border-white/[0.06] text-white/30 hover:text-white/50'
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Filing list */}
        {filingsLoading ? (
          <div className="text-white/30 text-sm py-20 text-center">
            LOADING FILINGS...
          </div>
        ) : filings.length === 0 ? (
          <div className="border border-white/[0.06] rounded-lg p-12 text-center">
            <div className="text-white/30 text-sm mb-2">No filings found</div>
            <Muted className="text-xs">
              {system !== 'ALL' ? 'Try clearing the filter.' : 'No FCC filings available.'}
            </Muted>
          </div>
        ) : (
          <>
            {/* Table header */}
            <div className="hidden md:grid grid-cols-[90px_60px_140px_1fr_130px_120px] gap-3 px-4 pb-2 border-b border-white/[0.06]">
              <span className="text-[10px] text-white/30 tracking-wider">DATE</span>
              <span className="text-[10px] text-white/30 tracking-wider">SYS</span>
              <span className="text-[10px] text-white/30 tracking-wider">FILE NUMBER</span>
              <span className="text-[10px] text-white/30 tracking-wider">TITLE</span>
              <span className="text-[10px] text-white/30 tracking-wider">STATUS</span>
              <span className="text-[10px] text-white/30 tracking-wider">APPLICANT</span>
            </div>

            {/* Filing rows */}
            <div className="space-y-0">
              {filings.map((filing: RegulatoryFiling) => (
                <FilingRow key={filing.id} filing={filing} />
              ))}
            </div>
          </>
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

function FilingRow({ filing }: { filing: RegulatoryFiling }) {
  return (
    <div className="md:grid md:grid-cols-[90px_60px_140px_1fr_130px_120px] gap-3 px-4 py-3 border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
      {/* Date */}
      <span className="text-[11px] text-white/40 tabular-nums">
        {formatDate(filing.filed_date)}
      </span>

      {/* System badge */}
      <span className="text-[10px] text-white/50">
        {filing.filing_system}
      </span>

      {/* File number */}
      <span className="text-[11px] text-white/60 truncate" title={filing.file_number}>
        {filing.file_number}
      </span>

      {/* Title */}
      <span className="text-[12px] text-white/70 leading-snug" title={filing.title || undefined}>
        {truncate(filing.title, 80)}
      </span>

      {/* Status */}
      <span className="flex items-center gap-1.5">
        <StatusDot variant={statusVariant(filing.application_status)} size="xs" />
        <span className="text-[10px] text-white/50 truncate">
          {filing.application_status || '—'}
        </span>
      </span>

      {/* Applicant */}
      <span className="text-[10px] text-white/40 truncate" title={filing.applicant || undefined}>
        {truncate(filing.applicant, 20)}
      </span>
    </div>
  )
}
