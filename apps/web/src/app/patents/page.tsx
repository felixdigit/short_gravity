'use client'

import { useState, useMemo } from 'react'
import { Muted, StatusDot } from '@shortgravity/ui'
import { usePatents, type Patent } from '@/lib/hooks/usePatents'

const STATUS_FILTERS = ['ALL', 'GRANTED', 'PENDING', 'ABANDONED'] as const
type StatusFilter = (typeof STATUS_FILTERS)[number]

const STATUS_VARIANT: Record<string, 'nominal' | 'warning' | 'critical' | 'info'> = {
  granted: 'nominal',
  pending: 'warning',
  abandoned: 'critical',
  expired: 'critical',
  unknown: 'info',
}

function statusVariant(status: string | null): 'nominal' | 'warning' | 'critical' | 'info' {
  if (!status) return 'info'
  return STATUS_VARIANT[status.toLowerCase()] ?? 'info'
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—'
  const d = new Date(dateStr + 'T00:00:00')
  return d
    .toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
    .toUpperCase()
}

function truncate(str: string | null | undefined, max: number): string {
  if (!str) return '—'
  return str.length > max ? str.slice(0, max) + '...' : str
}

const PAGE_SIZE = 50

export default function PatentsPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL')
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [page, setPage] = useState(0)

  // Debounce search input
  const debounceRef = useMemo(() => {
    let timer: ReturnType<typeof setTimeout>
    return (value: string) => {
      clearTimeout(timer)
      timer = setTimeout(() => {
        setDebouncedSearch(value)
        setPage(0)
      }, 300)
    }
  }, [])

  const { data, isLoading } = usePatents({
    q: debouncedSearch || undefined,
    status: statusFilter === 'ALL' ? undefined : statusFilter.toLowerCase(),
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  })

  const patents = data?.patents ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="min-h-screen bg-[#030305] text-white font-mono">
      <div className="max-w-6xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="flex items-baseline justify-between mb-8">
          <div>
            <h1 className="text-2xl font-light tracking-wider">PATENT PORTFOLIO</h1>
            <Muted className="text-xs mt-1">
              AST SpaceMobile patent filings across all jurisdictions
            </Muted>
          </div>
          <div className="text-right">
            <span className="text-3xl font-light tabular-nums">{total}</span>
            <Muted className="text-xs ml-2">PATENTS</Muted>
          </div>
        </div>

        {/* Search */}
        <div className="mb-6">
          <input
            type="text"
            placeholder="Search patents by title, abstract, or number..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              debounceRef(e.target.value)
            }}
            className="w-full bg-black/30 border border-white/[0.06] rounded-lg px-4 py-2.5 text-[12px] text-white/80 placeholder-white/20 focus:outline-none focus:border-white/20 transition-colors"
          />
        </div>

        {/* Status filter chips */}
        <div className="flex gap-1 mb-8">
          {STATUS_FILTERS.map((s) => (
            <button
              key={s}
              onClick={() => {
                setStatusFilter(s)
                setPage(0)
              }}
              className={`text-[11px] px-3 py-1.5 rounded-full border transition-colors ${
                statusFilter === s
                  ? 'border-white/20 bg-white/[0.06] text-white/80'
                  : 'border-white/[0.06] text-white/30 hover:text-white/50'
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Patent list */}
        {isLoading ? (
          <div className="text-white/30 text-sm py-20 text-center">LOADING PATENTS...</div>
        ) : patents.length === 0 ? (
          <div className="border border-white/[0.06] rounded-lg p-12 text-center">
            <div className="text-white/30 text-sm mb-2">No patents found</div>
            <Muted className="text-xs">
              {debouncedSearch || statusFilter !== 'ALL'
                ? 'Try clearing filters.'
                : 'No patent data available.'}
            </Muted>
          </div>
        ) : (
          <>
            {/* Table header */}
            <div className="hidden md:grid grid-cols-[130px_1fr_90px_90px_80px_60px] gap-3 px-4 pb-2 border-b border-white/[0.06]">
              <span className="text-[10px] text-white/30 tracking-wider">PATENT #</span>
              <span className="text-[10px] text-white/30 tracking-wider">TITLE</span>
              <span className="text-[10px] text-white/30 tracking-wider">STATUS</span>
              <span className="text-[10px] text-white/30 tracking-wider">FILED</span>
              <span className="text-[10px] text-white/30 tracking-wider">JURIS</span>
              <span className="text-[10px] text-white/30 tracking-wider">CLAIMS</span>
            </div>

            {/* Patent rows */}
            <div className="space-y-0">
              {patents.map((patent) => (
                <PatentRow key={patent.id} patent={patent} />
              ))}
            </div>
          </>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-4 mt-8">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="text-[11px] px-3 py-1.5 rounded border border-white/[0.06] text-white/40 hover:text-white/60 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              PREV
            </button>
            <span className="text-[11px] text-white/40 tabular-nums">
              {page + 1} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="text-[11px] px-3 py-1.5 rounded border border-white/[0.06] text-white/40 hover:text-white/60 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              NEXT
            </button>
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

function PatentRow({ patent }: { patent: Patent }) {
  return (
    <div className="md:grid md:grid-cols-[130px_1fr_90px_90px_80px_60px] gap-3 px-4 py-3 border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
      {/* Patent number */}
      <span className="text-[11px] text-white/60 tabular-nums truncate" title={patent.patent_number}>
        {patent.patent_number}
      </span>

      {/* Title + abstract */}
      <div className="min-w-0">
        <div className="text-[12px] text-white/70 leading-snug" title={patent.title || undefined}>
          {truncate(patent.title, 80)}
        </div>
        {patent.abstract && (
          <div className="text-[10px] text-white/30 leading-snug mt-0.5 line-clamp-2">
            {patent.abstract}
          </div>
        )}
      </div>

      {/* Status */}
      <span className="flex items-center gap-1.5">
        <StatusDot variant={statusVariant(patent.status)} size="xs" />
        <span className="text-[10px] text-white/50 capitalize">{patent.status || '—'}</span>
      </span>

      {/* Filing date */}
      <span className="text-[11px] text-white/40 tabular-nums">
        {formatDate(patent.filing_date)}
      </span>

      {/* Jurisdiction */}
      <span className="text-[10px] text-white/40">{patent.jurisdiction || '—'}</span>

      {/* Claims count */}
      <span className="text-[11px] text-white/40 tabular-nums text-right">
        {patent.claims_count ?? '—'}
      </span>
    </div>
  )
}
