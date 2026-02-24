'use client'

import { createContext, useContext, useMemo, type ReactNode } from 'react'
import { useMultipleSatellitePositions } from '@/lib/hooks/useSatellitePosition'
import { useDragHistory } from '@/lib/hooks/useDragHistory'
import { useTLEFreshness, type TLEFreshness, type PerSatelliteFreshness } from '@/lib/hooks/useTLEFreshness'
import { useDivergence, type DivergenceData } from '@/lib/hooks/useDivergence'
import { useSpaceWeather, type SpaceWeatherDay } from '@/lib/hooks/useSpaceWeather'
import { useConjunctions, type ConjunctionEvent } from '@/lib/hooks/useConjunctions'
import { SATELLITES_ORDERED, NORAD_IDS, FM1_NORAD_ID } from '@/lib/data/satellites'

// Shared satellite shape used by widgets
export interface TerminalSatellite {
  noradId: string
  name: string
  type: string
  latitude: number
  longitude: number
  altitude: number
  velocity: number
  inclination: number
  bstar: number
  eccentricity: number
  periodMinutes: number | null
  apoapsis: number | null
  periapsis: number | null
  tle?: { line1: string; line2: string }
}

export interface MapSatellite {
  noradId: string
  name: string
  currentPosition: { latitude: number; longitude: number }
  inclination: number
  altitude: number
  tle?: { line1: string; line2: string }
}

export { type PerSatelliteFreshness } from '@/lib/hooks/useTLEFreshness'
export { type DivergenceData as DivergenceEntry } from '@/lib/hooks/useDivergence'
export { type SpaceWeatherDay as SpaceWeatherEntry } from '@/lib/hooks/useSpaceWeather'
export { type ConjunctionEvent as ConjunctionEntry } from '@/lib/hooks/useConjunctions'

export interface DragHistoryData {
  dataPoints?: Array<{
    epoch: string
    bstar: number
    avgAltitude?: number | null
    source?: string
  }>
  summary?: {
    initialBstar: number | null
    latestBstar: number | null
    bstarChangePercent: number | null
  }
}

export interface TerminalDataContextType {
  satellites: TerminalSatellite[]
  fm1: TerminalSatellite | null
  mapTracks: MapSatellite[]
  terminalContext: string
  tleFreshness: { maxHoursOld: number | null; minHoursOld: number | null } | null
  perSatelliteFreshness: Record<string, PerSatelliteFreshness>
  divergenceData: DivergenceData[]
  dragHistory: DragHistoryData | null
  dragLoading: boolean
  spaceWeather: SpaceWeatherDay[]
  conjunctions: ConjunctionEvent[]
}

const TerminalDataContext = createContext<TerminalDataContextType>({
  satellites: [],
  fm1: null,
  mapTracks: [],
  terminalContext: '',
  tleFreshness: null,
  perSatelliteFreshness: {},
  divergenceData: [],
  dragHistory: null,
  dragLoading: false,
  spaceWeather: [],
  conjunctions: [],
})

export function useTerminalData() {
  return useContext(TerminalDataContext)
}

export function TerminalDataProvider({ children }: { children: ReactNode }) {
  const positions = useMultipleSatellitePositions(NORAD_IDS, 500)
  const { data: dragData, isLoading: dragLoading } = useDragHistory(FM1_NORAD_ID, 45)
  const { freshness: tleFreshnessData, perSatellite: perSatelliteFreshness } = useTLEFreshness(NORAD_IDS)
  const { data: divergenceData } = useDivergence()
  const { data: spaceWeatherData } = useSpaceWeather(7)
  const { data: conjunctionsData } = useConjunctions()

  const satellites = useMemo(
    () =>
      SATELLITES_ORDERED.map(({ id, name, type }) => {
        const s = positions[id]
        return {
          noradId: id,
          name,
          type,
          latitude: s?.position?.latitude ?? 0,
          longitude: s?.position?.longitude ?? 0,
          altitude: s?.position?.altitude ?? 0,
          velocity: s?.position?.velocity ?? 0,
          inclination: s?.orbital?.inclination ?? 0,
          bstar: s?.orbital?.bstar ?? 0,
          eccentricity: s?.orbital?.eccentricity ?? 0,
          periodMinutes: s?.orbital?.periodMinutes ?? null,
          apoapsis: s?.orbital?.apoapsis ?? null,
          periapsis: s?.orbital?.periapsis ?? null,
          tle: s?.tle ?? undefined,
        }
      }).filter((s) => s.altitude > 0),
    [positions]
  )

  const fm1 = satellites.find((s) => s.noradId === FM1_NORAD_ID) ?? null

  const mapTracks = useMemo(
    () =>
      satellites.map((s) => ({
        noradId: s.noradId,
        name: s.name,
        currentPosition: { latitude: s.latitude, longitude: s.longitude },
        inclination: s.inclination,
        altitude: s.altitude,
        tle: s.tle,
      })),
    [satellites]
  )

  const terminalContext = useMemo(() => {
    if (satellites.length === 0) return ''
    const lines = satellites.map(s =>
      `${s.name} (NORAD ${s.noradId}): ${s.latitude.toFixed(2)}°N ${s.longitude.toFixed(2)}°E, alt ${s.altitude.toFixed(1)}km, vel ${s.velocity.toFixed(2)}km/s, inc ${s.inclination.toFixed(1)}°, B* ${s.bstar.toExponential(2)}`
    )
    return `Live satellite positions (${new Date().toISOString()}):\n${lines.join('\n')}`
  }, [satellites])

  const dragHistory: DragHistoryData | null = useMemo(() => {
    if (!dragData) return null
    return {
      dataPoints: dragData.dataPoints?.map(dp => ({
        epoch: dp.epoch,
        bstar: dp.bstar,
        avgAltitude: dp.avgAltitude,
        source: dp.source,
      })),
      summary: dragData.summary ? {
        initialBstar: dragData.summary.initialBstar,
        latestBstar: dragData.summary.latestBstar,
        bstarChangePercent: dragData.summary.bstarChangePercent,
      } : undefined,
    }
  }, [dragData])

  const value = useMemo<TerminalDataContextType>(
    () => ({
      satellites,
      fm1,
      mapTracks,
      terminalContext,
      tleFreshness: tleFreshnessData ? {
        maxHoursOld: tleFreshnessData.maxHoursOld,
        minHoursOld: tleFreshnessData.minHoursOld,
      } : null,
      perSatelliteFreshness: perSatelliteFreshness ?? {},
      divergenceData: divergenceData ?? [],
      dragHistory,
      dragLoading,
      spaceWeather: spaceWeatherData?.data ?? [],
      conjunctions: conjunctionsData?.data ?? [],
    }),
    [satellites, fm1, mapTracks, terminalContext, tleFreshnessData, perSatelliteFreshness, divergenceData, dragHistory, dragLoading, spaceWeatherData, conjunctionsData]
  )

  return (
    <TerminalDataContext.Provider value={value}>
      {children}
    </TerminalDataContext.Provider>
  )
}
