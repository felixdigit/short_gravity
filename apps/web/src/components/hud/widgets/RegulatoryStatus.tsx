'use client'

import Link from 'next/link'
import { cn } from '@/lib/utils'
import { useRegulatoryStatus } from '@/lib/hooks/useRegulatoryStatus'
import type { WidgetManifest } from './types'

export const regulatoryStatusManifest: WidgetManifest = {
  id: 'regulatory-status',
  name: 'REGULATORY',
  category: 'data',
  panelPreference: 'either',
  sizing: 'fixed',
  expandable: false,
  separator: false,
}

const colorStyles: Record<string, string> = {
  green: 'text-green-400',
  yellow: 'text-yellow-400',
  blue: 'text-blue-400',
  red: 'text-red-400',
  white: 'text-white/60',
}

const dotStyles: Record<string, string> = {
  green: 'bg-green-400',
  yellow: 'bg-yellow-400',
  blue: 'bg-blue-400',
  red: 'bg-red-400',
  white: 'bg-white/60',
}

export function RegulatoryStatus() {
  const { data, isLoading } = useRegulatoryStatus()

  if (isLoading) {
    return (
      <div className="font-mono">
        <div className="text-[11px] text-white/50 tracking-wider mb-2">REGULATORY</div>
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
      <Link href="/regulatory" className="text-[11px] text-white/50 hover:text-white/70 tracking-wider transition-colors block mb-3">
        REGULATORY
      </Link>

      <div className="space-y-2.5">
        {items.map((item, i) => (
          <div key={i} className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <div className={cn('w-2 h-2 rounded-full flex-shrink-0', dotStyles[item.color] || 'bg-white/50')} />
              <span className="text-[12px] text-white/70">{item.label}</span>
            </div>
            <span className={cn('text-[11px] tabular-nums', colorStyles[item.color] || 'text-white/60')}>
              {item.value}
            </span>
          </div>
        ))}
        {items.length === 0 && (
          <div className="text-[12px] text-white/50">NO DATA</div>
        )}
      </div>

      <Link
        href="/regulatory"
        className="block mt-3 text-[11px] text-white/50 hover:text-white/70 tracking-wider transition-colors"
      >
        VIEW DETAILS &rarr;
      </Link>
    </div>
  )
}
