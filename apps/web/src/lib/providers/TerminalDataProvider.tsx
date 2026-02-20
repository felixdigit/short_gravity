'use client'

import { createContext, useContext, type ReactNode } from 'react'

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
  periodMinutes?: number
  eccentricity?: number
  apoapsis?: number
  periapsis?: number
}

export interface PerSatelliteFreshness {
  source: string
  hoursOld: number
}

export interface DivergenceEntry {
  noradId: string
  bstarDelta: number
  diverged: boolean
}

export interface SpaceWeatherEntry {
  date: string
  kp_sum: number | null
  ap_avg: number | null
  f107_obs: number | null
  f107_adj: number | null
  sunspot_number: number | null
}

export interface ConjunctionEntry {
  tca: string
  minRange: number
  probability: number
  sat1: string
  sat2: string
}

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
  tleFreshness: { maxHoursOld: number | null; minHoursOld: number | null } | null
  perSatelliteFreshness: Record<string, PerSatelliteFreshness>
  divergenceData: DivergenceEntry[]
  spaceWeather: SpaceWeatherEntry[]
  conjunctions: ConjunctionEntry[]
  fm1: TerminalSatellite | null
  dragHistory: DragHistoryData | null
  dragLoading: boolean
  terminalContext: string
}

const TerminalDataContext = createContext<TerminalDataContextType>({
  satellites: [],
  tleFreshness: null,
  perSatelliteFreshness: {},
  divergenceData: [],
  spaceWeather: [],
  conjunctions: [],
  fm1: null,
  dragHistory: null,
  dragLoading: false,
  terminalContext: '',
})

export function useTerminalData() {
  return useContext(TerminalDataContext)
}

/**
 * TODO: Wire this provider to real data fetching.
 * Currently provides the context shape so widgets compile.
 * The real implementation should fetch from API routes and propagate via SGP4.
 */
export function TerminalDataProvider({ children }: { children: ReactNode }) {
  const value: TerminalDataContextType = {
    satellites: [],
    tleFreshness: null,
    perSatelliteFreshness: {},
    divergenceData: [],
    spaceWeather: [],
    conjunctions: [],
    fm1: null,
    dragHistory: null,
    dragLoading: false,
    terminalContext: '',
  }

  return (
    <TerminalDataContext.Provider value={value}>
      {children}
    </TerminalDataContext.Provider>
  )
}
