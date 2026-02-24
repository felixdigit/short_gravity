'use client'

import { useQuery } from '@tanstack/react-query'

export interface HorizonEvent {
  id: string
  date: string
  type: 'launch' | 'conjunction' | 'regulatory' | 'patent' | 'earnings' | 'catalyst'
  title: string
  subtitle: string | null
  severity: 'critical' | 'high' | 'medium' | 'low'
  source_table: string
  source_ref: string | null
  estimated_period?: string
}

interface HorizonResponse {
  data: HorizonEvent[]
  count: number
  horizon: { from: string; to: string; days: number }
}

export function useHorizon(days: number = 90) {
  return useQuery<HorizonResponse>({
    queryKey: ['horizon', days],
    queryFn: async () => {
      const res = await fetch(`/api/horizon?days=${days}`)
      if (!res.ok) throw new Error('Failed to fetch horizon')
      return res.json()
    },
    staleTime: 15 * 60 * 1000,
  })
}
