'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

export interface ThesisSource {
  table: string
  id: string
  title: string
}

export interface Thesis {
  id: string
  session_id: string
  statement: string
  supporting_prose: string | null
  supporting_sources: ThesisSource[]
  contradicting_prose: string | null
  contradicting_sources: ThesisSource[]
  synthesis_prose: string | null
  synthesis_sources: ThesisSource[]
  status: 'generating' | 'complete' | 'failed'
  created_at: string
  updated_at: string
}

export interface ThesesResponse {
  data: Thesis[]
  count: number
}

export function useTheses(sessionId?: string) {
  return useQuery<ThesesResponse>({
    queryKey: ['theses', sessionId ?? 'all'],
    queryFn: async () => {
      const params = sessionId ? `?session_id=${sessionId}` : ''
      const res = await fetch(`/api/theses${params}`)
      if (!res.ok) throw new Error('Failed to fetch theses')
      return res.json()
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useCreateThesis() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (input: { session_id: string; statement: string }) => {
      const res = await fetch('/api/theses', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      })
      if (!res.ok) throw new Error('Failed to create thesis')
      return res.json()
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['theses'] }),
  })
}
