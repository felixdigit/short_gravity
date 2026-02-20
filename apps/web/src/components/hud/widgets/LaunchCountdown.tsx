'use client'

import { useState, useEffect, useMemo } from 'react'
import Link from 'next/link'
import { cn } from '@/lib/utils'
import { useNextLaunch } from '@/lib/hooks/useNextLaunch'
import type { WidgetManifest } from './types'

export const launchCountdownManifest: WidgetManifest = {
  id: 'launch-countdown',
  name: 'LAUNCH COUNTDOWN',
  category: 'data',
  panelPreference: 'right',
  sizing: 'fixed',
  expandable: false,
  separator: false,
}

function statusColor(status: string): string {
  const s = status.toUpperCase()
  if (s === 'GO' || s === 'SCHEDULED') return 'text-white/70'
  if (s === 'HOLD' || s === 'SCRUBBED') return 'text-white/50'
  return 'text-white/50'
}

export function LaunchCountdown() {
  const { data, isLoading } = useNextLaunch()
  const [countdown, setCountdown] = useState({ d: 0, h: 0, m: 0, s: 0 })

  const launch = data?.launch
  const targetDate = launch?.targetDate ? new Date(launch.targetDate) : null
  const targetTime = useMemo(() => targetDate?.getTime() ?? null, [targetDate?.toISOString()])

  useEffect(() => {
    if (!targetTime) return

    const updateCountdown = () => {
      const diff = targetTime - Date.now()
      if (diff <= 0) {
        setCountdown({ d: 0, h: 0, m: 0, s: 0 })
        return
      }
      const d = Math.floor(diff / (1000 * 60 * 60 * 24))
      const h = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
      const m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
      const s = Math.floor((diff % (1000 * 60)) / 1000)
      setCountdown({ d, h, m, s })
    }

    updateCountdown()
    const interval = setInterval(updateCountdown, 1000)
    return () => clearInterval(interval)
  }, [targetTime])

  if (isLoading) {
    return (
      <div className="font-mono">
        <div className="text-[11px] text-white/50 tracking-wider mb-2">NEXT LAUNCH</div>
        <div className="h-16 animate-pulse bg-white/5 rounded" />
      </div>
    )
  }

  if (!launch) {
    return (
      <div className="font-mono">
        <div className="text-[11px] text-white/50 tracking-wider mb-2">NEXT LAUNCH</div>
        <div className="text-[12px] text-white/50">NO LAUNCHES SCHEDULED</div>
      </div>
    )
  }

  const status = launch.status || 'SCHEDULED'
  const pad = (n: number) => String(n).padStart(2, '0')

  return (
    <div className="font-mono">
      <div className="flex items-center justify-between mb-2">
        <Link href="/horizon?type=launch" className="text-[11px] text-white/50 hover:text-white/70 tracking-wider transition-colors">NEXT LAUNCH</Link>
        <span className={cn('text-[11px] tracking-wider', statusColor(status))}>
          {status}
        </span>
      </div>

      <div className="flex items-baseline gap-2">
        <span className="text-[28px] font-extralight text-white tabular-nums leading-none">
          T-{countdown.d}
        </span>
        <span className="text-[14px] font-light text-white/50 tabular-nums leading-none">
          {pad(countdown.h)}:{pad(countdown.m)}:{pad(countdown.s)}
        </span>
      </div>

      <div className="mt-2">
        <div className="text-[12px] text-white/70 leading-snug">
          {launch.mission}
          {targetDate && (
            <span className="text-white/50">
              {' \u00b7 '}{targetDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            </span>
          )}
        </div>
        {(launch.site || launch.provider) && (
          <div className="text-[11px] text-white/50 mt-0.5">
            {[launch.provider, launch.site].filter(Boolean).join(' \u00b7 ')}
          </div>
        )}
      </div>
    </div>
  )
}
