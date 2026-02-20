'use client'

/**
 * DocumentViewer stub — placeholder for the activity feed document viewer.
 * TODO: Migrate from archive (modal that fetches and renders filing/post content).
 */
interface DocumentViewerProps {
  itemId: string | null
  onClose: () => void
}

export function DocumentViewer({ itemId, onClose }: DocumentViewerProps) {
  if (!itemId) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-[var(--nebula-depth)] border border-white/10 rounded-lg p-6 max-w-lg w-full mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <span className="text-[11px] text-white/50 tracking-wider font-mono">DOCUMENT</span>
          <button onClick={onClose} className="text-white/50 hover:text-white/70 text-sm">
            ESC
          </button>
        </div>
        <div className="text-[12px] text-white/60 font-mono">
          Document viewer not yet wired. Item ID: {itemId}
        </div>
      </div>
    </div>
  )
}
