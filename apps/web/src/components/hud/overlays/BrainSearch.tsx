'use client'

import { useState, useRef, useEffect } from 'react'
import { useBrainQuery } from '@/lib/hooks/useBrainQuery'

interface BrainSearchProps {
  open: boolean
  onClose: () => void
}

export function BrainSearch({ open, onClose }: BrainSearchProps) {
  const [input, setInput] = useState('')
  const { messages, isStreaming, error, ask, clear } = useBrainQuery()
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to bottom on new content
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  // Focus input when opened
  useEffect(() => {
    if (open && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [open])

  // Close on Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) onClose()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [open, onClose])

  if (!open) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim() && !isStreaming) {
      ask(input.trim())
      setInput('')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col bg-[#0a0f14]/95 border border-white/[0.08] rounded-xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.06]">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-white/50 tracking-wider">BRAIN</span>
            <span className="text-[10px] text-white/20">13K+ documents</span>
          </div>
          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <button
                onClick={clear}
                className="text-[10px] font-mono text-white/30 hover:text-white/50 transition-colors px-2 py-1"
              >
                CLEAR
              </button>
            )}
            <button
              onClick={onClose}
              className="text-white/30 hover:text-white/50 transition-colors text-lg leading-none"
            >
              &times;
            </button>
          </div>
        </div>

        {/* Messages */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-5 py-4 space-y-4 min-h-[200px] max-h-[55vh]"
        >
          {messages.length === 0 && (
            <div className="text-center py-12">
              <div className="text-white/20 text-sm mb-2">Ask anything about AST SpaceMobile</div>
              <div className="text-white/10 text-xs">
                SEC filings, FCC dockets, patents, earnings calls, X posts, press releases
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={msg.role === 'user' ? 'flex justify-end' : ''}>
              {msg.role === 'user' ? (
                <div className="bg-white/[0.06] border border-white/[0.08] rounded-lg px-4 py-2 max-w-[80%]">
                  <div className="text-sm text-white/80">{msg.content}</div>
                </div>
              ) : (
                <div className="space-y-2">
                  {/* Sources */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-2">
                      {msg.sources.map((src, j) => (
                        <span
                          key={j}
                          className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-white/[0.04] border border-white/[0.06] text-white/30"
                          title={src.snippet}
                        >
                          [{j + 1}] {src.table}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Answer text */}
                  <div className="text-sm text-white/70 leading-relaxed whitespace-pre-wrap">
                    {msg.content}
                    {isStreaming && i === messages.length - 1 && (
                      <span className="inline-block w-1.5 h-4 bg-white/40 ml-0.5 animate-pulse" />
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}

          {error && (
            <div className="text-xs text-red-400/70 bg-red-400/5 border border-red-400/10 rounded-lg px-3 py-2">
              {error}
            </div>
          )}
        </div>

        {/* Input */}
        <form onSubmit={handleSubmit} className="px-5 py-3 border-t border-white/[0.06]">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about filings, patents, regulatory status..."
              disabled={isStreaming}
              className="flex-1 bg-white/[0.04] border border-white/[0.08] rounded-lg px-4 py-2.5 text-sm text-white/80 placeholder:text-white/20 focus:outline-none focus:border-white/[0.15] font-mono disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isStreaming || !input.trim()}
              className="px-4 py-2.5 bg-white/[0.06] border border-white/[0.08] rounded-lg text-xs font-mono text-white/50 hover:text-white/70 hover:bg-white/[0.08] transition-colors disabled:opacity-30"
            >
              {isStreaming ? '...' : 'ASK'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
