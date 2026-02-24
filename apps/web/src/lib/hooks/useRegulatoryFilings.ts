import { useQuery } from '@tanstack/react-query'

export interface RegulatoryFiling {
  id: string
  filing_system: string
  file_number: string
  title: string | null
  filing_type: string | null
  application_status: string | null
  applicant: string | null
  docket: string | null
  filed_date: string | null
  call_sign: string | null
  created_at: string
}

export interface RegulatoryFilingsResponse {
  filings: RegulatoryFiling[]
  count: number
}

export function useRegulatoryFilings(system?: string) {
  const params = new URLSearchParams()
  if (system) params.set('system', system)
  params.set('limit', '100')

  return useQuery<RegulatoryFilingsResponse>({
    queryKey: ['regulatory-filings', system || 'all'],
    queryFn: async () => {
      const res = await fetch(`/api/regulatory/filings?${params}`)
      if (!res.ok) throw new Error('Failed to fetch regulatory filings')
      return res.json()
    },
    staleTime: 15 * 60 * 1000,
    refetchInterval: 15 * 60 * 1000,
  })
}
