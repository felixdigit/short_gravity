'use client'

import { type ReactNode, useEffect, useCallback } from 'react'
import { cn } from '@/lib/utils'
import { useFocusPanelContext } from '@shortgravity/ui'
import { AnimatePresence, motion } from 'framer-motion'

interface FocusPanelProps {
  panelId: string
  collapsedPosition?: 'inline' | 'fixed'
  expandedSize?: { width: string; height: string }
  screenshotFilename?: string
  label?: string
  children: ReactNode
  className?: string
}

export function FocusPanel({
  panelId,
  expandedSize,
  label,
  children,
  className,
}: FocusPanelProps) {
  const { focusedPanelId, requestFocus, releaseFocus } = useFocusPanelContext()
  const expanded = focusedPanelId === panelId

  const handleExpand = useCallback(() => {
    requestFocus(panelId)
  }, [panelId, requestFocus])

  const handleCollapse = useCallback(() => {
    releaseFocus(panelId)
  }, [panelId, releaseFocus])

  // Close on Escape
  useEffect(() => {
    if (!expanded) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleCollapse()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [expanded, handleCollapse])

  return (
    <>
      {/* Collapsed / inline view */}
      <div className={cn('relative w-full group', className)}>
        {children}

        {/* Expand button — only when not expanded and expandedSize is set */}
        {!expanded && expandedSize && (
          <button
            onClick={handleExpand}
            className="absolute top-1 right-1 text-[9px] font-mono text-white/30 hover:text-white/60
                       tracking-wider px-1.5 py-0.5 rounded bg-white/[0.03] hover:bg-white/[0.08]
                       transition-colors opacity-0 group-hover:opacity-100"
          >
            EXPAND
          </button>
        )}
      </div>

      {/* Expanded overlay */}
      <AnimatePresence>
        {expanded && expandedSize && (
          <>
            {/* Backdrop */}
            <motion.div
              key={`backdrop-${panelId}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="fixed inset-0 z-[90] bg-black/70"
              onClick={handleCollapse}
            />

            {/* Expanded panel */}
            <motion.div
              key={`panel-${panelId}`}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              className="fixed z-[100] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
              style={{
                width: expandedSize.width,
                height: expandedSize.height,
                maxWidth: '90vw',
                maxHeight: '90vh',
              }}
            >
              <div className="w-full h-full rounded border border-white/[0.08] bg-[#0a0a0c] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between px-3 py-2 border-b border-white/[0.06] shrink-0">
                  {label && (
                    <span className="text-[11px] font-mono text-white/50 tracking-wider">
                      {label}
                    </span>
                  )}
                  <button
                    onClick={handleCollapse}
                    className="text-[11px] font-mono text-white/40 hover:text-white/70
                               tracking-wider px-2 py-0.5 rounded hover:bg-white/[0.06] transition-colors ml-auto"
                  >
                    CLOSE
                  </button>
                </div>

                {/* Content */}
                <div className="flex-1 min-h-0 overflow-auto p-1">
                  {children}
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
