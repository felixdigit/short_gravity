'use client'

import { useEffect } from 'react'
import { useTerminalStore } from '@/lib/stores/terminal-store'

export function ClearanceModal() {
  const { clearanceModalOpen, setClearanceModalOpen } = useTerminalStore()

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && clearanceModalOpen) setClearanceModalOpen(false)
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [clearanceModalOpen, setClearanceModalOpen])

  if (!clearanceModalOpen) return null

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => setClearanceModalOpen(false)}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 bg-[#0a0f14]/95 border border-white/[0.08] rounded-xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
          <h2 className="text-sm font-mono text-white/70 tracking-wider">CLEARANCE LEVEL</h2>
          <button
            onClick={() => setClearanceModalOpen(false)}
            className="text-white/30 hover:text-white/50 transition-colors text-lg"
          >
            &times;
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-6 space-y-6">
          {/* Current tier */}
          <div className="text-center">
            <div className="text-[10px] text-white/30 tracking-widest mb-1">CURRENT TIER</div>
            <div className="text-lg font-mono text-white/60">FREE</div>
          </div>

          {/* Tier comparison */}
          <div className="grid grid-cols-2 gap-4">
            <div className="border border-white/[0.06] rounded-lg p-4">
              <div className="text-[11px] font-mono text-white/40 mb-3">FREE</div>
              <ul className="space-y-2 text-[11px] text-white/50">
                <li>Live constellation tracking</li>
                <li>Public filings feed</li>
                <li>Basic orbital data</li>
                <li>Signal feed (delayed)</li>
              </ul>
            </div>
            <div className="border border-[#FF6B35]/20 rounded-lg p-4 bg-[#FF6B35]/[0.03]">
              <div className="text-[11px] font-mono text-[#FF6B35] mb-3">FULL SPECTRUM</div>
              <ul className="space-y-2 text-[11px] text-white/70">
                <li>Everything in Free</li>
                <li>Brain AI search (13K+ docs)</li>
                <li>Real-time signal alerts</li>
                <li>Daily intelligence briefing</li>
                <li>Drag analysis &amp; alerts</li>
                <li>Source divergence tracking</li>
              </ul>
            </div>
          </div>

          {/* CTAs */}
          <div className="space-y-3">
            <a
              href="https://www.patreon.com/shortgravity"
              target="_blank"
              rel="noopener noreferrer"
              className="block w-full text-center py-3 bg-[#FF6B35]/10 border border-[#FF6B35]/30 rounded-lg text-sm font-mono text-[#FF6B35] hover:bg-[#FF6B35]/20 transition-colors"
            >
              UPGRADE ON PATREON
            </a>
            {process.env.NEXT_PUBLIC_DISCORD_INVITE_URL && (
              <a
                href={process.env.NEXT_PUBLIC_DISCORD_INVITE_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="block w-full text-center py-2.5 border border-white/[0.06] rounded-lg text-[11px] font-mono text-white/40 hover:text-white/60 transition-colors"
              >
                JOIN DISCORD
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
