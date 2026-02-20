'use client'

import { useState, useEffect, useMemo } from 'react'
import Link from 'next/link'
import { cn } from '@/lib/utils'
import { useNextLaunch } from '@/lib/hooks/useNextLaunch'
import { useQuery } from '@tanstack/react-query'
import type { WidgetManifest } from './types'

export const nextEventManifest: WidgetManifest = {
  id: 'next-event',
  name: 'NEXT EVENT',
  category: 'data',
  panelPreference: 'right',
  sizing: 'fixed',
  expandable: false,
  separator: false,
}

interface HorizonEvent {
  id: string
  date: string
  type: string
  title: string
  subtitle: string | null
  severity: string
}

function useNextHorizonEvent() {
  return useQuery<HorizonEvent | null>({
    queryKey: ['next-horizon-event'],
    queryFn: async () => {
      const res = await fetch('/api/horizon?days=90&limit=5')
      if (!res.ok) return null
      const data = await res.json()
      const events: HorizonEvent[] = data?.events || []
      return events.find(e => e.type !== 'launch') || events[0] || null
    },
    staleTime: 30 * 60 * 1000,
    refetchInterval: 30 * 60 * 1000,
  })
}

const EVENT_TYPE_LABELS: Record<string, string> = {
  launch: 'LAUNCH',
  earnings: 'EARNINGS',
  regulatory: 'REGULATORY',
  catalyst: 'CATALYST',
  conjunction: 'CONJUNCTION',
  patent: 'PATENT',
}

const EVENT_TYPE_COLORS: Record<string, string> = {
  launch: 'text-red-400',
  earnings: 'text-[var(--asts-orange)]',
  regulatory: 'text-blue-400',
  catalyst: 'text-purple-400',
  conjunction: 'text-yellow-400',
  patent: 'text-white/60',
}

export function NextEvent() {
  const { data: launchData, isLoading: launchLoading } = useNextLaunch()
  const { data: horizonEvent, isLoading: horizonLoading } = useNextHorizonEvent()
  const [countdown, setCountdown] = useState({ d: 0, h: 0, m: 0, s: 0 })

  const activeEvent = useMemo(() => {
    const launch = launchData?.launch
    const launchDate = launch?.targetDate ? new Date(launch.targetDate) : null
    const launchDays = launchDate ? Math.ceil((launchDate.getTime() - Date.now()) / 86400000) : Infinity

    if (launch && launchDays <= 14 && launchDays > 0) {
      return {
        type: 'launch' as const,
        title: launch.mission,
        subtitle: [launch.provider, launch.site].filter(Boolean).join(' \u00b7 ') || null,
        date: launch.targetDate!,
        status: launch.status || 'SCHEDULED',
        link: '/horizon?type=launch',
      }
    }

    if (horizonEvent) {
      return {
        type: horizonEvent.type,
        title: horizonEvent.title,
        subtitle: horizonEvent.subtitle,
        date: horizonEvent.date,
        status: horizonEvent.severity?.toUpperCase() || '',
        link: '/horizon',
      }
    }

    return null
  }, [launchData, horizonEvent])

  const targetTime = useMemo(() => {
    if (!activeEvent?.date) return null
    return new Date(activeEvent.date).getTime()
  }, [activeEvent?.date])

  useEffect(() => {
    if (!targetTime) return

    const update = () => {
      const diff = Math.max(0, targetTime - Date.now())
      const d = Math.floor(diff / (1000 * 60 * 60 * 24))
      const h = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
      const m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
      const s = Math.floor((diff % (1000 * 60)) / 1000)
      setCountdown({ d, h, m, s })
    }

    update()
    const interval = setInterval(update, 1000)
    return () => clearInterval(interval)
  }, [targetTime])

  if (launchLoading && horizonLoading) {
    return (
      <div className="font-mono">
        <div className="text-[11px] text-white/50 tracking-wider mb-2">NEXT EVENT</div>
        <div className="h-16 animate-pulse bg-white/5 rounded" />
      </div>
    )
  }

  if (!activeEvent) {
    return (
      <div className="font-mono">
        <div className="text-[11px] text-white/50 tracking-wider mb-2">NEXT EVENT</div>
        <div className="text-[12px] text-white/50">NO UPCOMING EVENTS</div>
      </div>
    )
  }

  const pad = (n: number) => String(n).padStart(2, '0')
  const typeLabel = EVENT_TYPE_LABELS[activeEvent.type] || activeEvent.type.toUpperCase()
  const typeColor = EVENT_TYPE_COLORS[activeEvent.type] || 'text-white/60'

  return (
    <div className="font-mono">
      <div className="flex items-center justify-between mb-2">
        <Link href={activeEvent.link} className="text-[11px] text-white/50 hover:text-white/70 tracking-wider transition-colors">
          NEXT EVENT
        </Link>
        <span className={cn('text-[11px] tracking-wider', typeColor)}>
          {typeLabel}
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
        <div className="text-[12px] text-white/70 leading-snug line-clamp-1">
          {activeEvent.title}
        </div>
        {activeEvent.subtitle && (
          <div className="text-[11px] text-white/50 mt-0.5">{activeEvent.subtitle}</div>
        )}
      </div>
    </div>
  )
}
