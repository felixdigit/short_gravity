import { useQuery } from '@tanstack/react-query'

export interface ShortInterestResponse {
  floatShortPct: number | null
  outstandingShortPct: number | null
  sharesShort: number | null
  sharesShortPrior: number | null
  shortChange: number | null
  daysToCover: number | null
  sharesOutstanding: number | null
  floatShares: number | null
  reportDate: string | null
  source: string
}

export function useShortInterest() {
  return useQuery<ShortInterestResponse>({
    queryKey: ['short-interest'],
    queryFn: async () => {
      const res = await fetch('/api/widgets/short-interest')
      if (!res.ok) throw new Error('Failed to fetch short interest')
      return res.json()
    },
    staleTime: 60 * 60 * 1000,
    refetchInterval: 60 * 60 * 1000,
  })
}

export interface ShortInterestHistoryPoint {
  date: string
  floatShortPct: number | null
  sharesShort: number | null
  daysToCover: number | null
}

export function useShortInterestHistory() {
  return useQuery<{ history: ShortInterestHistoryPoint[] }>({
    queryKey: ['short-interest-history'],
    queryFn: async () => {
      const res = await fetch('/api/widgets/short-interest?history=true')
      if (!res.ok) throw new Error('Failed to fetch short interest history')
      return res.json()
    },
    staleTime: 60 * 60 * 1000,
  })
}
