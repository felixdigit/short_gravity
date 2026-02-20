import { useQuery } from '@tanstack/react-query'

export interface RegulatoryItem {
  label: string
  value: string
  color: 'green' | 'yellow' | 'blue' | 'red' | 'white'
}

export interface RegulatoryResponse {
  items: RegulatoryItem[]
}

export function useRegulatoryStatus() {
  return useQuery<RegulatoryResponse>({
    queryKey: ['regulatory-status'],
    queryFn: async () => {
      const res = await fetch('/api/widgets/regulatory')
      if (!res.ok) throw new Error('Failed to fetch regulatory status')
      return res.json()
    },
    staleTime: 60 * 60 * 1000,
    refetchInterval: 60 * 60 * 1000,
  })
}
