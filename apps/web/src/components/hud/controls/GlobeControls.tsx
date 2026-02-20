'use client'

import { cn } from '@/lib/utils'
import { useTerminalStore } from '@/lib/stores/terminal-store'

/**
 * GlobeControls — bottom-center pill-shaped control bar for the immersive terminal.
 */
export function GlobeControls() {
  const store = useTerminalStore()

  const toggles = [
    { label: store.mode === 'minimal' ? 'DENSE' : 'CLEAN', action: () => store.setMode(store.mode === 'minimal' ? 'dense' : 'minimal') },
    { label: 'ORBITS', active: store.showOrbits, action: () => store.setShowOrbits(!store.showOrbits) },
    { label: 'COVERAGE', active: store.showCoverage, action: () => store.setShowCoverage(!store.showCoverage) },
    { label: 'DOTS', active: store.useDotMarkers, action: () => store.setUseDotMarkers(!store.useDotMarkers) },
  ]

  return (
    <div className="flex items-center gap-0.5 bg-black/40 backdrop-blur-sm border border-white/[0.06] rounded-full px-1 py-0.5">
      {toggles.map((t) => (
        <button
          key={t.label}
          onClick={t.action}
          className={cn(
            'text-[11px] font-mono px-2.5 py-1 rounded-full transition-colors',
            t.active !== undefined
              ? t.active
                ? 'text-white/70 bg-white/[0.06]'
                : 'text-white/30 hover:text-white/50'
              : 'text-white/50 hover:text-white/70'
          )}
        >
          {t.label}
        </button>
      ))}

      <div className="w-px h-4 bg-white/[0.06] mx-0.5" />

      <button
        onClick={() => store.setBrainOpen(true)}
        className="text-[11px] font-mono px-2.5 py-1 rounded-full text-white/50 hover:text-white/70 transition-colors"
      >
        BRAIN
      </button>
    </div>
  )
}
