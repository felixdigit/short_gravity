'use client'

import { create } from 'zustand'

interface FrameState {
  sidebarExpanded: boolean
  sidebarHovered: boolean
  activeSymbol: string
  setSidebarExpanded: (expanded: boolean) => void
  setSidebarHovered: (hovered: boolean) => void
  setActiveSymbol: (symbol: string) => void
}

export const useFrameStore = create<FrameState>((set) => ({
  sidebarExpanded: false,
  sidebarHovered: false,
  activeSymbol: 'ASTS',
  setSidebarExpanded: (expanded) => set({ sidebarExpanded: expanded }),
  setSidebarHovered: (hovered) => set({ sidebarHovered: hovered }),
  setActiveSymbol: (symbol) => set({ activeSymbol: symbol }),
}))
