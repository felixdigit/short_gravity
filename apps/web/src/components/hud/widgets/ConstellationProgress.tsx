'use client'

import { cn } from '@/lib/utils'
import { useTerminalData } from '@/lib/providers/TerminalDataProvider'
import type { WidgetManifest } from './types'

export const constellationProgressManifest: WidgetManifest = {
  id: 'constellation-progress',
  name: 'CONSTELLATION',
  category: 'data',
  panelPreference: 'left',
  sizing: 'fixed',
  expandable: false,
  separator: true,
}

interface ConstellationProgressProps {
  currentCount?: number
  className?: string
}

export function ConstellationProgress({ currentCount, className }: ConstellationProgressProps = {}) {
  const ctx = useTerminalData()
  const count = currentCount ?? ctx.satellites.length

  return (
    <div className={cn('font-mono flex items-center justify-between', className)}>
      <div>
        <div className="text-[28px] font-extralight text-white leading-none tabular-nums">
          {count > 0 ? count : <span className="inline-block w-8 h-7 animate-pulse bg-white/5 rounded" />}
        </div>
        <div className="text-[11px] text-white/50 mt-1">SATELLITES IN ORBIT</div>
      </div>
      <img
        src="/bluebird.webp"
        alt="BlueBird satellite"
        className="h-8 object-contain opacity-30"
      />
    </div>
  )
}
