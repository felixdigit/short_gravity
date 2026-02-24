'use client'

import { useQuery } from '@tanstack/react-query'

export interface Patent {
  id: string
  patent_number: string
  title: string | null
  abstract?: string | null
  status: string
  filing_date?: string | null
  grant_date?: string | null
  expiration_date?: string | null
  jurisdiction?: string | null
  applicant?: string | null
  claims_count?: number | null
  created_at: string
}

export interface PatentsResponse {
  patents: Patent[]
  total: number
}

export interface PatentFilters {
  q?: string
  status?: string
  jurisdiction?: string
  limit?: number
  offset?: number
}

export function usePatents(filters: PatentFilters = {}) {
  const params = new URLSearchParams()
  if (filters.q) params.set('q', filters.q)
  if (filters.status) params.set('status', filters.status)
  if (filters.jurisdiction) params.set('jurisdiction', filters.jurisdiction)
  if (filters.limit) params.set('limit', String(filters.limit))
  if (filters.offset) params.set('offset', String(filters.offset))

  return useQuery<PatentsResponse>({
    queryKey: ['patents', filters],
    queryFn: async () => {
      const res = await fetch(`/api/patents?${params}`)
      if (!res.ok) throw new Error('Failed to fetch patents')
      return res.json()
    },
    staleTime: 15 * 60 * 1000,
  })
}
