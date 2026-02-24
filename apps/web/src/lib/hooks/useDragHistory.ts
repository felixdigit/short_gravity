'use client'

import { useQuery } from '@tanstack/react-query'

export interface DragDataPoint {
  epoch: string
  bstar: number
  avgAltitude: number | null
  source: string
}

export interface DragHistoryResponse {
  noradId: string
  days: number
  dataPoints: DragDataPoint[]
  summary: {
    initialBstar: number | null
    latestBstar: number | null
    bstarChangePercent: number | null
  }
}

export function useDragHistory(noradId: string, days: number = 45) {
  return useQuery<DragHistoryResponse>({
    queryKey: ['drag-history', noradId, days],
    queryFn: async () => {
      const response = await fetch(
        `/api/satellites/${noradId}/drag-history?days=${days}`
      )
      if (!response.ok) throw new Error('Failed to fetch drag history')
      return response.json()
    },
    staleTime: 60 * 60 * 1000,
    refetchInterval: 60 * 60 * 1000,
    enabled: !!noradId,
  })
}
