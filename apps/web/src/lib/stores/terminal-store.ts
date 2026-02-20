'use client'

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Mode = 'minimal' | 'dense'

interface TerminalStore {
  mode: Mode
  showOrbits: boolean
  showCoverage: boolean
  useDotMarkers: boolean
  selectedSatellite: string | null
  showSatelliteCard: boolean
  brainOpen: boolean
  commandPaletteOpen: boolean
  clearanceModalOpen: boolean
  activePreset: string

  setMode: (mode: Mode) => void
  setShowOrbits: (show: boolean) => void
  setShowCoverage: (show: boolean) => void
  setUseDotMarkers: (useDots: boolean) => void
  selectSatellite: (noradId: string) => void
  deselectSatellite: () => void
  toggleSatelliteCard: (noradId: string) => void
  setBrainOpen: (open: boolean) => void
  setCommandPaletteOpen: (open: boolean) => void
  setClearanceModalOpen: (open: boolean) => void
  setActivePreset: (presetId: string) => void
}

export const useTerminalStore = create<TerminalStore>()(
  persist(
    (set, get) => ({
      mode: 'dense',
      showOrbits: true,
      showCoverage: true,
      useDotMarkers: true,
      selectedSatellite: null,
      showSatelliteCard: false,
      brainOpen: false,
      commandPaletteOpen: false,
      clearanceModalOpen: false,
      activePreset: 'default',

      setMode: (mode) => set({ mode }),
      setShowOrbits: (show) => set({ showOrbits: show }),
      setShowCoverage: (show) => set({ showCoverage: show }),
      setUseDotMarkers: (useDots) => set({ useDotMarkers: useDots }),
      selectSatellite: (noradId) => set({ selectedSatellite: noradId, showSatelliteCard: true }),
      deselectSatellite: () => set({ selectedSatellite: null, showSatelliteCard: false }),
      toggleSatelliteCard: (noradId) => {
        const state = get()
        if (noradId === state.selectedSatellite) {
          set({ showSatelliteCard: !state.showSatelliteCard })
        } else {
          set({ selectedSatellite: noradId, showSatelliteCard: true })
        }
      },
      setBrainOpen: (open) => set({ brainOpen: open }),
      setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
      setClearanceModalOpen: (open) => set({ clearanceModalOpen: open }),
      setActivePreset: (presetId) => set({ activePreset: presetId }),
    }),
    {
      name: 'sg-terminal',
      partialize: (state) => ({
        activePreset: state.activePreset,
        mode: state.mode,
      }),
    }
  )
)
