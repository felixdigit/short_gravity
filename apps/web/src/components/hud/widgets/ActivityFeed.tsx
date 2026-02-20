'use client'

import { useState } from 'react'
import { cn } from '@/lib/utils'
import { useActivityFeed, type FeedItem } from '@/lib/hooks/useActivityFeed'
import { DocumentViewer } from './DocumentViewer'
import type { WidgetManifest } from './types'

export const activityFeedManifest: WidgetManifest = {
  id: 'activity-feed',
  name: 'ACTIVITY FEED',
  category: 'data',
  panelPreference: 'right',
  sizing: 'flexible',
  expandable: false,
  separator: true,
}

const TYPE_STYLES: Record<string, { label: string; color: string; bg: string }> = {
  sec: { label: 'SEC', color: 'text-white/50', bg: 'bg-white/[0.04]' },
  fcc: { label: 'FCC', color: 'text-white/50', bg: 'bg-white/[0.04]' },
  pr: { label: 'PR', color: 'text-white/50', bg: 'bg-white/[0.03]' },
  call: { label: 'CALL', color: 'text-white/50', bg: 'bg-white/[0.03]' },
  x: { label: 'X', color: 'text-white/50', bg: 'bg-white/[0.03]' },
  signal: { label: 'SIG', color: 'text-[#FF6B35]/70', bg: 'bg-[#FF6B35]/[0.06]' },
}

function timeAgo(dateStr: string): string {
  const date = new Date(dateStr + (dateStr.includes('T') ? '' : 'T00:00:00'))
  if (isNaN(date.getTime())) return ''
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  if (days < 0) return 'upcoming'
  if (days < 1) return 'today'
  if (days < 7) return `${days}d`
  if (days < 30) return `${Math.floor(days / 7)}w`
  if (days < 365) return `${Math.floor(days / 30)}mo`
  return `${Math.floor(days / 365)}y`
}

function FeedRow({ item, onSelect }: { item: FeedItem; onSelect: (id: string) => void }) {
  const style = TYPE_STYLES[item.type] || { label: '?', color: 'text-white/50', bg: 'bg-white/[0.03]' }
  const ago = timeAgo(item.date)

  return (
    <button
      onClick={() => onSelect(item.id)}
      className="w-full text-left flex items-start gap-2.5 py-2 group cursor-pointer hover:bg-white/[0.03] -mx-1 px-1 rounded transition-colors"
    >
      <span className={cn('text-[10px] px-1 py-0.5 rounded flex-shrink-0 font-mono tracking-wider mt-0.5', style.color, style.bg)}>
        {style.label}
      </span>
      <span className="text-[10px] text-white/50 leading-snug flex-1 line-clamp-2 group-hover:text-white/70 transition-colors">
        {item.title}
      </span>
      <span className="text-[10px] text-white/50 flex-shrink-0 tabular-nums mt-0.5">
        {ago}
      </span>
    </button>
  )
}

export function ActivityFeed() {
  const { data, isLoading } = useActivityFeed()
  const [viewingId, setViewingId] = useState<string | null>(null)

  if (isLoading) {
    return (
      <div className="font-mono">
        <div className="text-[11px] text-white/70 tracking-wider mb-2">LATEST DEVELOPMENTS</div>
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-4 animate-pulse bg-white/5 rounded" />
          ))}
        </div>
      </div>
    )
  }

  const items = data?.items || []

  return (
    <div className="font-mono">
      <div className="text-[11px] text-white/70 tracking-wider mb-2">LATEST DEVELOPMENTS</div>

      <div className="space-y-0 overflow-hidden">
        {items.length === 0 ? (
          <div className="text-[11px] text-white/50">NO RECENT DEVELOPMENTS</div>
        ) : (
          items.map((item) => <FeedRow key={item.id} item={item} onSelect={setViewingId} />)
        )}
      </div>

      <DocumentViewer itemId={viewingId} onClose={() => setViewingId(null)} />
    </div>
  )
}
