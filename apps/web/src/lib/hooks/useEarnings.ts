'use client'

import { useQuery } from '@tanstack/react-query'

export interface EarningsMeta {
  quarter: string
  date: string | null
  time: string | null
  status: string | null
  fiscal_year: number
  fiscal_quarter: number
}

export interface EarningsQuarter {
  quarter: string
  date: string | null
  status: string | null
  fiscal_year: number
  fiscal_quarter: number
}

export interface EarningsTranscript {
  title: string
  date: string | null
  text: string | null
  summary: string | null
  wordCount: number
}

export interface TopicEntry {
  topic: string
  label: string
  counts: Record<string, number>
  currentCount: number
}

export interface PriceReaction {
  preClose: number | null
  earningsClose: number
  postClose: number | null
  deltaPct: number | null
  volumeSpikeFactor: number | null
  window: Array<{
    date: string
    close: number
    volume: number
    isEarningsDate: boolean
  }>
}

export interface GuidanceItem {
  id: string
  quarter_promised: string
  quarter_due: string
  category: string
  promise_text: string
  outcome_text?: string
  status: string
  source_url?: string
}

export interface EarningsResponse {
  meta: EarningsMeta
  quarters: EarningsQuarter[]
  transcript: EarningsTranscript | null
  topicMatrix: TopicEntry[]
  transcriptQuarters: string[]
  priceReaction: PriceReaction | null
  guidance: {
    active: GuidanceItem[]
    resolved: GuidanceItem[]
    all: GuidanceItem[]
  }
  lastUpdated: string
}

export function useEarnings(quarter?: string) {
  return useQuery<EarningsResponse>({
    queryKey: ['earnings', quarter ?? 'latest'],
    queryFn: async () => {
      const params = quarter ? `?quarter=${quarter}` : ''
      const res = await fetch(`/api/earnings/context${params}`)
      if (!res.ok) throw new Error('Failed to fetch earnings')
      return res.json()
    },
    staleTime: 30 * 60 * 1000,
  })
}
