import { useQuery } from '@tanstack/react-query'

interface ConstellationStats {
  boxscore: {
    us: { orbitalPayloads: number; orbitalDebris: number; orbitalTotal: number; decayedTotal: number } | null
    global: Array<{ country: string; orbitalTotal: number; payloads: number }>
  }
  recentAstsSatellites: Array<{ noradId: string; name: string; launchDate: string; objectType: string }>
  lastUpdated: string
}

export function useConstellationStats() {
  return useQuery<ConstellationStats>({
    queryKey: ['constellation', 'stats'],
    queryFn: async () => {
      const response = await fetch('/api/constellation/stats')
      if (!response.ok) throw new Error('Failed to fetch constellation stats')
      return response.json()
    },
    staleTime: 24 * 60 * 60 * 1000,
    refetchInterval: 24 * 60 * 60 * 1000,
  })
}
