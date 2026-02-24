'use client'

import { useQuery } from '@tanstack/react-query'

export interface ConjunctionEvent {
  cdmId: string
  tca: string
  minRange: number | null
  probability: number | null
  sat1: string
  sat2: string
  sat1Norad: string | null
  sat2Norad: string | null
}

interface ConjunctionsResponse {
  data: ConjunctionEvent[]
  count: number
}

export function useConjunctions(noradId?: string) {
  const params = new URLSearchParams()
  if (noradId) params.set('norad_id', noradId)

  return useQuery<ConjunctionsResponse>({
    queryKey: ['conjunctions', noradId || 'all'],
    queryFn: async () => {
      const url = `/api/conjunctions${params.toString() ? `?${params}` : ''}`
      const res = await fetch(url)
      if (!res.ok) throw new Error(`Failed to fetch conjunctions: ${res.status}`)
      return res.json()
    },
    staleTime: 15 * 60 * 1000,
  })
}
