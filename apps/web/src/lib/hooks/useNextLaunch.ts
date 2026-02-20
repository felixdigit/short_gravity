import { useQuery } from '@tanstack/react-query'

export interface NextLaunchData {
  mission: string
  provider: string | null
  site: string | null
  targetDate: string | null
  status: string
  satelliteCount: number | null
  notes: string | null
}

export interface NextLaunchResponse {
  launch: NextLaunchData | null
}

export function useNextLaunch() {
  return useQuery<NextLaunchResponse>({
    queryKey: ['next-launch'],
    queryFn: async () => {
      const res = await fetch('/api/widgets/next-launch')
      if (!res.ok) throw new Error('Failed to fetch next launch')
      return res.json()
    },
    staleTime: 60 * 60 * 1000,
    refetchInterval: 60 * 60 * 1000,
  })
}
