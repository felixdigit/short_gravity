import { useQuery } from '@tanstack/react-query'

export interface CashPositionResponse {
  cashOnHand: number | null
  unit: 'thousands' | 'millions' | 'billions' | null
  quarterlyBurn: number | null
  label: string | null
  filingForm: string
  filingDate: string
  source: string | null
}

export function useCashPosition() {
  return useQuery<CashPositionResponse>({
    queryKey: ['cash-position'],
    queryFn: async () => {
      const res = await fetch('/api/widgets/cash-position')
      if (!res.ok) throw new Error('Failed to fetch cash position')
      return res.json()
    },
    staleTime: 24 * 60 * 60 * 1000,
    refetchInterval: 60 * 60 * 1000,
  })
}

export interface CashHistoryPoint {
  date: string
  form: string
  cash: number | null
  burn: number | null
  unit: string
}

export function useCashHistory() {
  return useQuery<{ history: CashHistoryPoint[] }>({
    queryKey: ['cash-history'],
    queryFn: async () => {
      const res = await fetch('/api/widgets/cash-position?history=true')
      if (!res.ok) throw new Error('Failed to fetch cash history')
      return res.json()
    },
    staleTime: 24 * 60 * 60 * 1000,
  })
}
