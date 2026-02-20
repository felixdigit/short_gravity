'use client'

/**
 * BrainSearch overlay stub.
 * TODO: Migrate the full BrainSearch from the archive (streaming chat, conversation history, image paste).
 */
interface BrainSearchProps {
  open: boolean
  onClose: () => void
  onClear?: () => void
  messages?: unknown[]
  isStreaming?: boolean
  onAsk?: (query: string, image?: string) => void
  conversations?: unknown[]
  currentConversationId?: string | null
  onLoadConversation?: (id: string) => void
}

export function BrainSearch({ open, onClose }: BrainSearchProps) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-[60] bg-black/80 backdrop-blur-sm flex items-center justify-center">
      <div className="bg-[var(--nebula-depth)] border border-white/10 rounded-lg w-full max-w-2xl mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <span className="text-[11px] text-white/50 tracking-wider font-mono">BRAIN SEARCH</span>
          <button onClick={onClose} className="text-white/50 hover:text-white/70 text-sm font-mono">
            ESC
          </button>
        </div>
        <div className="text-[12px] text-white/40 font-mono text-center py-8">
          Brain search overlay not yet wired.
        </div>
      </div>
    </div>
  )
}
