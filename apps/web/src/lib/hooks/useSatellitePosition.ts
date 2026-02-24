'use client'

import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import * as satellite from 'satellite.js'
import { getBatchTLEQueryKey } from './query-keys'

export interface SatellitePosition {
  latitude: number
  longitude: number
  altitude: number
  velocity: number
  timestamp: Date
}

export interface OrbitalParameters {
  avgAltitude: number | null
  inclination: number
  raan: number
  bstar: number
  eccentricity: number
  periodMinutes?: number | null
  apoapsis?: number | null
  periapsis?: number | null
}

export interface TLEData {
  line1: string
  line2: string
}

export interface SatellitePositionState {
  position: SatellitePosition | null
  orbital: OrbitalParameters | null
  tle: TLEData | null
  isLoading: boolean
  error: Error | null
}

function propagateTLE(tle1: string, tle2: string, date: Date): SatellitePosition {
  const satrec = satellite.twoline2satrec(tle1, tle2)
  const positionAndVelocity = satellite.propagate(satrec, date)

  if (!positionAndVelocity || typeof positionAndVelocity.position === 'boolean') {
    throw new Error('Failed to propagate satellite position')
  }

  const positionEci = positionAndVelocity.position
  const velocityEci = positionAndVelocity.velocity

  if (!positionEci || typeof positionEci === 'boolean') {
    throw new Error('Invalid satellite position')
  }

  const gmst = satellite.gstime(date)
  const positionGd = satellite.eciToGeodetic(positionEci, gmst)

  let velocityMagnitude = 0
  if (velocityEci && typeof velocityEci !== 'boolean') {
    velocityMagnitude = Math.sqrt(
      velocityEci.x * velocityEci.x +
      velocityEci.y * velocityEci.y +
      velocityEci.z * velocityEci.z
    )
  }

  return {
    latitude: satellite.degreesLat(positionGd.latitude),
    longitude: satellite.degreesLong(positionGd.longitude),
    altitude: positionGd.height,
    velocity: velocityMagnitude,
    timestamp: date,
  }
}

export function useSatellitePosition(
  noradId: string,
  updateInterval: number = 5000
): SatellitePositionState {
  const [position, setPosition] = useState<SatellitePosition | null>(null)
  const [error, setError] = useState<Error | null>(null)

  const { data: satelliteData, isLoading } = useQuery({
    queryKey: ['satellite', noradId],
    queryFn: async () => {
      const response = await fetch(`/api/satellites/${noradId}`)
      if (!response.ok) {
        throw new Error(`Failed to fetch satellite: ${response.statusText}`)
      }
      return response.json()
    },
    staleTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
  })

  useEffect(() => {
    if (!satelliteData?.tle) return

    const updatePosition = () => {
      try {
        const now = new Date()
        const newPosition = propagateTLE(satelliteData.tle.line1, satelliteData.tle.line2, now)
        setPosition(newPosition)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Unknown error'))
      }
    }

    updatePosition()
    const interval = setInterval(updatePosition, updateInterval)
    return () => clearInterval(interval)
  }, [satelliteData, updateInterval])

  const orbital: OrbitalParameters | null = satelliteData ? {
    avgAltitude: satelliteData.metadata?.orbit?.apogee && satelliteData.metadata?.orbit?.perigee
      ? (satelliteData.metadata.orbit.apogee + satelliteData.metadata.orbit.perigee) / 2
      : null,
    inclination: satelliteData.metadata?.orbit?.inclination ?? 0,
    raan: satelliteData.metadata?.orbit?.raan ?? 0,
    bstar: satelliteData.tle?.bstar ?? 0,
    eccentricity: satelliteData.metadata?.orbit?.eccentricity ?? 0,
  } : null

  const tle: TLEData | null = satelliteData?.tle
    ? { line1: satelliteData.tle.line1, line2: satelliteData.tle.line2 }
    : null

  return { position, orbital, tle, isLoading, error }
}

export function useMultipleSatellitePositions(
  noradIds: string[],
  updateInterval: number = 5000
): Record<string, SatellitePositionState> {
  const [positions, setPositions] = useState<Record<string, SatellitePositionState>>(() => {
    const initial: Record<string, SatellitePositionState> = {}
    noradIds.forEach((id) => {
      initial[id] = { position: null, orbital: null, tle: null, isLoading: true, error: null }
    })
    return initial
  })

  const satelliteQueries = useQuery({
    queryKey: getBatchTLEQueryKey(noradIds),
    queryFn: async () => {
      if (noradIds.length === 0) return { satellites: [], errors: {} }
      const response = await fetch(`/api/satellites/batch-tle?noradIds=${noradIds.join(',')}`)
      if (!response.ok) throw new Error(`Failed to fetch batch TLE: ${response.statusText}`)
      return response.json()
    },
    staleTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
    enabled: noradIds.length > 0,
  })

  const noradIdsKey = noradIds.join(',')

  useEffect(() => {
    if (satelliteQueries.isLoading || !satelliteQueries.data) return

    const updateAllPositions = () => {
      const newPositions: Record<string, SatellitePositionState> = {}
      const { satellites, errors } = satelliteQueries.data

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      satellites.forEach((sat: any) => {
        const { noradId, tle, orbital } = sat

        if (!tle) {
          newPositions[noradId] = {
            position: null, orbital: null, tle: null, isLoading: false,
            error: new Error('No TLE data available'),
          }
          return
        }

        try {
          const now = new Date()
          const position = propagateTLE(tle.line1, tle.line2, now)
          newPositions[noradId] = {
            position, orbital: orbital || null,
            tle: { line1: tle.line1, line2: tle.line2 },
            isLoading: false, error: null,
          }
        } catch (err) {
          newPositions[noradId] = {
            position: null, orbital: orbital || null,
            tle: { line1: tle.line1, line2: tle.line2 },
            isLoading: false,
            error: err instanceof Error ? err : new Error('Failed to propagate position'),
          }
        }
      })

      if (errors) {
        Object.entries(errors).forEach(([noradId, errorMsg]) => {
          newPositions[noradId] = {
            position: null, orbital: null, tle: null, isLoading: false,
            error: new Error(errorMsg as string),
          }
        })
      }

      setPositions(newPositions)
    }

    updateAllPositions()
    const interval = setInterval(updateAllPositions, updateInterval)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [satelliteQueries.data, satelliteQueries.isLoading, updateInterval, noradIdsKey])

  return positions
}
