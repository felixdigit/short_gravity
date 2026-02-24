'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { filterCommands } from './commands'
import type { CommandItem } from './types'

const BADGE_MAP: Record<string, string> = {
  patent: 'PAT',
  patent_claim: 'PAT',
  filing: 'SEC',
  fcc_filing: 'FCC',
  press_release: 'PR',
  x_post: 'X',
  signal: 'SIG',
  earnings_transcript: 'CALL',
  glossary: 'TERM',
  cash_position: 'FIN',
  short_interest: 'FIN',
}

interface SearchResult {
  source: string
  id: string
  title: string
  snippet: string
}

interface SatelliteResult {
  noradId: string
  name: string
  altitude: number | null
}

export function useCommandSearch(query: string, isOpen: boolean) {
  const [staticResults, setStaticResults] = useState<CommandItem[]>([])
  const [searchResults, setSearchResults] = useState<CommandItem[]>([])
  const [satelliteResults, setSatelliteResults] = useState<CommandItem[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  const resetResults = useCallback(() => {
    setSearchResults([])
    setSatelliteResults([])
    setIsSearching(false)
  }, [])

  useEffect(() => {
    if (!isOpen) {
      setStaticResults(filterCommands(''))
      resetResults()
      return
    }

    // Static filtering is instant
    setStaticResults(filterCommands(query))

    // Cancel previous requests
    if (abortRef.current) abortRef.current.abort()
    if (timerRef.current) clearTimeout(timerRef.current)

    if (query.length < 2) {
      resetResults()
      return
    }

    setIsSearching(true)

    // Debounce API calls
    timerRef.current = setTimeout(() => {
      const controller = new AbortController()
      abortRef.current = controller

      const brainFetch = fetch(`/api/brain/search?q=${encodeURIComponent(query)}&limit=5`, {
        signal: controller.signal,
      })
        .then(r => r.ok ? r.json() : { results: [] })
        .then(data => {
          const items: CommandItem[] = (data.results || []).map((r: SearchResult) => ({
            id: `search-${r.source}-${r.id}`,
            category: 'search' as const,
            label: r.title,
            sublabel: r.snippet?.slice(0, 80),
            badge: BADGE_MAP[r.source] || r.source.toUpperCase(),
            action: { type: 'open-brain' as const, query },
          }))
          if (!controller.signal.aborted) setSearchResults(items)
        })
        .catch(() => {})

      const satFetch = fetch(`/api/satellites/search?name=${encodeURIComponent(query)}`, {
        signal: controller.signal,
      })
        .then(r => r.ok ? r.json() : { results: [] })
        .then(data => {
          const items: CommandItem[] = (data.results || []).slice(0, 5).map((s: SatelliteResult) => ({
            id: `sat-${s.noradId}`,
            category: 'satellite' as const,
            label: s.name,
            sublabel: s.altitude ? `ALT ${Math.round(s.altitude)} km` : undefined,
            badge: 'SAT',
            action: { type: 'select-satellite' as const, noradId: s.noradId },
          }))
          if (!controller.signal.aborted) setSatelliteResults(items)
        })
        .catch(() => {})

      Promise.allSettled([brainFetch, satFetch]).then(() => {
        if (!controller.signal.aborted) setIsSearching(false)
      })
    }, 150)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
      if (abortRef.current) abortRef.current.abort()
    }
  }, [query, isOpen, resetResults])

  return { staticResults, searchResults, satelliteResults, isSearching }
}
