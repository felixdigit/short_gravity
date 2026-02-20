import { useQuery } from '@tanstack/react-query'

export interface Signal {
  id: number
  signal_type: string
  severity: string
  category: string | null
  title: string
  description: string
  source_refs: Array<{ table: string; id: string; title: string; date: string }>
  metrics: Record<string, unknown>
  confidence_score: number | null
  price_impact_24h: number | null
  fingerprint: string
  detected_at: string
  expires_at: string
  created_at: string
}

export interface SignalsResponse {
  data: Signal[]
  count: number
}

export interface SignalFilters {
  severity?: string
  type?: string
  category?: string
  startDate?: string
  endDate?: string
  limit?: number
  offset?: number
}

export function useSignals(options?: SignalFilters) {
  const params = new URLSearchParams()
  if (options?.severity) params.set('severity', options.severity)
  if (options?.type) params.set('type', options.type)
  if (options?.category) params.set('category', options.category)
  if (options?.startDate) params.set('startDate', options.startDate)
  if (options?.endDate) params.set('endDate', options.endDate)
  if (options?.limit) params.set('limit', String(options.limit))
  if (options?.offset) params.set('offset', String(options.offset))

  return useQuery<SignalsResponse>({
    queryKey: ['signals', options],
    queryFn: async () => {
      const url = `/api/signals${params.toString() ? `?${params}` : ''}`
      const res = await fetch(url)
      if (!res.ok) throw new Error(`Failed to fetch signals: ${res.status}`)
      return res.json()
    },
    staleTime: 5 * 60 * 1000,
  })
}
