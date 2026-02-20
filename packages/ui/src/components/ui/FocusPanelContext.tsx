'use client'

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

interface FocusPanelContextType {
  focusedPanelId: string | null
  setFocusedPanel: (id: string | null) => void
  requestFocus: (id: string) => void
  releaseFocus: (id: string) => void
}

const FocusPanelContext = createContext<FocusPanelContextType | null>(null)

export function FocusPanelProvider({ children }: { children: ReactNode }) {
  const [focusedPanelId, setFocusedPanelId] = useState<string | null>(null)

  const setFocusedPanel = useCallback((id: string | null) => {
    setFocusedPanelId(id)
  }, [])

  const requestFocus = useCallback((id: string) => {
    setFocusedPanelId(id)
  }, [])

  const releaseFocus = useCallback((id: string) => {
    setFocusedPanelId(current => current === id ? null : current)
  }, [])

  return (
    <FocusPanelContext.Provider value={{ focusedPanelId, setFocusedPanel, requestFocus, releaseFocus }}>
      {children}
    </FocusPanelContext.Provider>
  )
}

export function useFocusPanelContext() {
  const context = useContext(FocusPanelContext)
  if (!context) {
    throw new Error('useFocusPanelContext must be used within a FocusPanelProvider')
  }
  return context
}
