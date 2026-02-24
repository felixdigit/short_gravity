'use client'

import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useRouter } from 'next/navigation'
import { useTerminalStore } from '@/lib/stores/terminal-store'
import { useCommandSearch } from './useCommandSearch'
import type { CommandCategory, CommandAction } from './types'

const CATEGORY_LABELS: Record<CommandCategory, string> = {
  navigation: 'NAVIGATE',
  preset: 'PRESETS',
  action: 'ACTIONS',
  search: 'DOCUMENTS',
  satellite: 'SATELLITES',
}

const CATEGORY_ORDER: CommandCategory[] = ['navigation', 'preset', 'action', 'search', 'satellite']

export function CommandPalette() {
  const [mounted, setMounted] = useState(false)
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const router = useRouter()

  const isOpen = useTerminalStore(s => s.commandPaletteOpen)
  const setOpen = useTerminalStore(s => s.setCommandPaletteOpen)
  const store = useTerminalStore

  const { staticResults, searchResults, satelliteResults, isSearching } = useCommandSearch(query, isOpen)

  useEffect(() => { setMounted(true) }, [])

  // All results merged in category order
  const allResults = useMemo(() => {
    const combined = [...staticResults, ...searchResults, ...satelliteResults]
    const grouped = new Map<CommandCategory, typeof combined>()
    for (const item of combined) {
      const list = grouped.get(item.category) || []
      list.push(item)
      grouped.set(item.category, list)
    }
    const ordered: typeof combined = []
    for (const cat of CATEGORY_ORDER) {
      const items = grouped.get(cat)
      if (items?.length) ordered.push(...items)
    }
    return ordered
  }, [staticResults, searchResults, satelliteResults])

  // Reset selection on query or results change
  useEffect(() => { setSelectedIndex(0) }, [query, allResults.length])

  // Reset query when opening
  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setSelectedIndex(0)
      setTimeout(() => inputRef.current?.focus(), 0)
    }
  }, [isOpen])

  // Global Cmd+K
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setOpen(!useTerminalStore.getState().commandPaletteOpen)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [setOpen])

  const executeAction = useCallback((action: CommandAction) => {
    const state = store.getState()
    switch (action.type) {
      case 'navigate':
        router.push(action.href)
        setOpen(false)
        break
      case 'preset':
        state.setActivePreset(action.presetId)
        setOpen(false)
        break
      case 'toggle':
        if (action.key === 'showOrbits') state.setShowOrbits(!state.showOrbits)
        else if (action.key === 'showCoverage') state.setShowCoverage(!state.showCoverage)
        else if (action.key === 'mode') state.setMode(state.mode === 'dense' ? 'minimal' : 'dense')
        // Don't close on toggles — allow rapid toggling
        break
      case 'open-brain':
        state.setBrainOpen(true)
        setOpen(false)
        break
      case 'select-satellite':
        router.push(`/satellite/${action.noradId}`)
        setOpen(false)
        break
      case 'external':
        window.open(action.url, '_blank')
        setOpen(false)
        break
    }
  }, [router, setOpen, store])

  // Keyboard nav inside palette
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault()
      setOpen(false)
      return
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex(i => Math.min(i + 1, allResults.length - 1))
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex(i => Math.max(i - 1, 0))
      return
    }
    if (e.key === 'Enter') {
      e.preventDefault()
      const item = allResults[selectedIndex]
      if (item) executeAction(item.action)
      return
    }
  }, [allResults, selectedIndex, executeAction, setOpen])

  // Scroll active item into view
  useEffect(() => {
    if (!listRef.current) return
    const active = listRef.current.querySelector('[data-active="true"]')
    active?.scrollIntoView({ block: 'nearest' })
  }, [selectedIndex])

  if (!mounted || !isOpen) return null

  // Build grouped display with category headers
  const rows: Array<{ type: 'header'; category: CommandCategory } | { type: 'item'; item: (typeof allResults)[number]; index: number }> = []
  let flatIndex = 0
  let lastCategory: CommandCategory | null = null
  for (const item of allResults) {
    if (item.category !== lastCategory) {
      rows.push({ type: 'header', category: item.category })
      lastCategory = item.category
    }
    rows.push({ type: 'item', item, index: flatIndex })
    flatIndex++
  }

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="command-palette-backdrop"
          className="fixed inset-0 z-[60] flex justify-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          onClick={() => setOpen(false)}
        >
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" />
          <motion.div
            className="relative w-full max-w-xl mt-[20vh] mx-4 h-fit"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.15 }}
            onClick={e => e.stopPropagation()}
            style={{ boxShadow: '0 0 80px rgba(0,0,0,0.8)' }}
          >
            <div className="bg-[#030305] border border-white/[0.06] overflow-hidden">
              {/* Input */}
              <div className="relative border-b border-white/[0.06]">
                <input
                  ref={inputRef}
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="TYPE A COMMAND..."
                  className="w-full bg-transparent px-4 py-3 font-mono text-[13px] text-white placeholder:text-white/20 focus:outline-none"
                  autoComplete="off"
                  spellCheck={false}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[8px] font-mono text-white/20 tracking-wider">
                  ESC
                </span>
              </div>

              {/* Results */}
              <div ref={listRef} className="max-h-[50vh] overflow-y-auto">
                {rows.map((row) => {
                  if (row.type === 'header') {
                    return (
                      <div key={`h-${row.category}`} className="px-4 pt-3 pb-1 flex items-center gap-2">
                        <span className="text-[8px] font-mono text-white/25 tracking-wider uppercase">
                          {CATEGORY_LABELS[row.category]}
                        </span>
                        {row.category === 'search' && isSearching && (
                          <span className="w-1 h-1 rounded-full bg-white/30 animate-pulse" />
                        )}
                      </div>
                    )
                  }

                  const { item, index } = row
                  const active = index === selectedIndex

                  return (
                    <div
                      key={item.id}
                      data-active={active}
                      className={`
                        px-4 py-2 flex items-center gap-3 cursor-pointer transition-colors
                        ${active ? 'bg-white/[0.04] border-l-2 border-[#FF6B35]' : 'border-l-2 border-transparent hover:bg-white/[0.02]'}
                      `}
                      onClick={() => executeAction(item.action)}
                      onMouseEnter={() => setSelectedIndex(index)}
                    >
                      {item.badge && (
                        <span className="text-[8px] font-mono text-white/30 tracking-wider w-8 shrink-0 text-center">
                          {item.badge}
                        </span>
                      )}
                      <div className="min-w-0 flex-1">
                        <div className="font-mono text-[12px] text-white/80 truncate">
                          {item.label}
                        </div>
                        {item.sublabel && (
                          <div className="font-mono text-[10px] text-white/25 truncate">
                            {item.sublabel}
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}

                {allResults.length === 0 && query.length > 0 && !isSearching && (
                  <div className="px-4 py-6 text-center font-mono text-[11px] text-white/20">
                    NO RESULTS
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  )
}
