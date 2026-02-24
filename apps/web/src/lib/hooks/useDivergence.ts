'use client'

import { useQuery } from '@tanstack/react-query'

export interface DivergenceData {
  noradId: string
  ctBstar: number | null
  stBstar: number | null
  bstarDelta: number
  diverged: boolean
  ctEpoch: string | null
  stEpoch: string | null
}

interface DivergenceResponse {
  satellites: DivergenceData[]
  error?: string
}

export function useDivergence() {
  return useQuery<DivergenceData[]>({
    queryKey: ['source-divergence'],
    queryFn: async () => {
      const response = await fetch('/api/satellites/divergence')
      if (!response.ok) throw new Error('Failed to fetch divergence data')
      const data: DivergenceResponse = await response.json()
      return data.satellites
    },
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchOnWindowFocus: true,
  })
}
