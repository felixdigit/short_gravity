'use client'

import { useTerminalStore } from '@/lib/stores/terminal-store'

/**
 * ClearanceModal stub.
 * TODO: Migrate the full ClearanceModal from archive (tier comparison, Patreon CTA, framer-motion).
 */
export function ClearanceModal() {
  const { clearanceModalOpen, setClearanceModalOpen } = useTerminalStore()

  if (!clearanceModalOpen) return null

  return (
    <div className="fixed inset-0 z-[70] bg-black/80 backdrop-blur-sm flex items-center justify-center">
      <div className="bg-[var(--nebula-depth)] border border-white/10 rounded-lg w-full max-w-md mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <span className="text-[11px] text-white/50 tracking-wider font-mono">CLEARANCE LEVEL</span>
          <button onClick={() => setClearanceModalOpen(false)} className="text-white/50 hover:text-white/70 text-sm font-mono">
            ESC
          </button>
        </div>
        <div className="text-[12px] text-white/40 font-mono text-center py-8">
          Clearance modal not yet wired.
        </div>
      </div>
    </div>
  )
}
