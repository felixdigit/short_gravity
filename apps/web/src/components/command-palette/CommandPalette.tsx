'use client'

import { useEffect } from 'react'
import { useTerminalStore } from '@/lib/stores/terminal-store'

/**
 * CommandPalette stub.
 * TODO: Migrate the full CommandPalette from archive (search, navigate, preset switching, satellite selection).
 * Currently provides the Cmd+K shortcut binding and a placeholder overlay.
 */
export function CommandPalette() {
  const { commandPaletteOpen, setCommandPaletteOpen } = useTerminalStore()

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setCommandPaletteOpen(!commandPaletteOpen)
      }
      if (e.key === 'Escape' && commandPaletteOpen) {
        setCommandPaletteOpen(false)
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [commandPaletteOpen, setCommandPaletteOpen])

  if (!commandPaletteOpen) return null

  return (
    <div
      className="fixed inset-0 z-[80] bg-black/60 backdrop-blur-sm flex items-start justify-center pt-[20vh]"
      onClick={() => setCommandPaletteOpen(false)}
    >
      <div
        className="bg-[var(--nebula-depth)] border border-white/10 rounded-lg w-full max-w-lg mx-4 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 px-4 py-3 border-b border-white/[0.06]">
          <span className="text-white/30 text-sm">&gt;</span>
          <input
            autoFocus
            type="text"
            placeholder="Search or type a command..."
            className="flex-1 bg-transparent text-[13px] text-white/80 font-mono placeholder:text-white/30 outline-none"
          />
        </div>
        <div className="px-4 py-6 text-center">
          <div className="text-[12px] text-white/30 font-mono">
            Command palette not yet wired.
          </div>
        </div>
      </div>
    </div>
  )
}
