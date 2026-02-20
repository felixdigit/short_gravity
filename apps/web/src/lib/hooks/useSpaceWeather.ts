'use client'

import { useQuery, type UseQueryResult } from '@tanstack/react-query'

export interface SpaceWeatherDay {
  date: string
  kp_sum: number | null
  ap_avg: number | null
  f107_obs: number | null
  f107_adj: number | null
  f107_center81: number | null
  sunspot_number: number | null
  data_type: string | null
}

export interface SpaceWeatherResponse {
  days: number
  count: number
  data: SpaceWeatherDay[]
  lastUpdated: string
}

export function useSpaceWeather(days: number = 90): UseQueryResult<SpaceWeatherResponse> {
  return useQuery({
    queryKey: ['space-weather', days],
    queryFn: async () => {
      const res = await fetch(`/api/space-weather?days=${days}`)
      if (!res.ok) throw new Error('Failed to fetch space weather')
      return res.json()
    },
    staleTime: 6 * 60 * 60 * 1000,
    refetchOnWindowFocus: false,
  })
}
