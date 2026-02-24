'use client'

import { useQuery } from '@tanstack/react-query'
import { getBatchTLEQueryKey } from './query-keys'

export interface TLEFreshness {
  oldestEpoch: string | null
  newestEpoch: string | null
  maxHoursOld: number | null
  minHoursOld: number | null
  avgHoursOld: number | null
}

interface SatelliteFreshness {
  tleEpoch: string
  updatedAt: string
  hoursOld: number
}

export interface PerSatelliteFreshness {
  source: string
  hoursOld: number
}

interface BatchTLEResponse {
  satellites: Array<{
    noradId: string
    tleSource?: string
    freshness: SatelliteFreshness
  }>
  count: number
  source: string
  lastUpdated: string
}

/**
 * Derives TLE freshness from the shared batch-tle React Query cache.
 * Does NOT make its own fetch — shares cache key with useMultipleSatellitePositions.
 */
export function useTLEFreshness(noradIds: string[]): {
  freshness: TLEFreshness | null
  perSatellite: Record<string, PerSatelliteFreshness>
  isLoading: boolean
} {
  const { data, isLoading } = useQuery({
    queryKey: getBatchTLEQueryKey(noradIds),
    queryFn: async (): Promise<BatchTLEResponse | null> => {
      if (noradIds.length === 0) return null
      const response = await fetch(`/api/satellites/batch-tle?noradIds=${noradIds.join(',')}`)
      if (!response.ok) throw new Error('Failed to fetch TLE data')
      return response.json()
    },
    staleTime: 30 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
    enabled: noradIds.length > 0,
  })

  const freshness = deriveFreshness(data)
  const perSatellite = derivePerSatellite(data)

  return { freshness, perSatellite, isLoading }
}

function deriveFreshness(data: BatchTLEResponse | null | undefined): TLEFreshness | null {
  if (!data?.satellites?.length) return null

  const validFreshness = data.satellites
    .map((sat) => sat.freshness)
    .filter((f): f is SatelliteFreshness =>
      f != null && typeof f.tleEpoch === 'string' && typeof f.hoursOld === 'number'
    )

  if (validFreshness.length === 0) return null

  const epochs = validFreshness.map((f) => new Date(f.tleEpoch).getTime())
  const hoursOldValues = validFreshness.map((f) => f.hoursOld)

  return {
    oldestEpoch: new Date(Math.min(...epochs)).toISOString(),
    newestEpoch: new Date(Math.max(...epochs)).toISOString(),
    maxHoursOld: Math.max(...hoursOldValues),
    minHoursOld: Math.min(...hoursOldValues),
    avgHoursOld: hoursOldValues.reduce((sum, val) => sum + val, 0) / hoursOldValues.length,
  }
}

function derivePerSatellite(data: BatchTLEResponse | null | undefined): Record<string, PerSatelliteFreshness> {
  if (!data?.satellites?.length) return {}

  const result: Record<string, PerSatelliteFreshness> = {}
  for (const sat of data.satellites) {
    if (sat.freshness?.hoursOld != null) {
      result[sat.noradId] = {
        source: sat.tleSource || 'unknown',
        hoursOld: sat.freshness.hoursOld,
      }
    }
  }
  return result
}
