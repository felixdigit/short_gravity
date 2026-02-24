TARGET: apps/web
---
MISSION:
Build the /research page — a standalone brain search interface for querying the 13K+ document corpus. The /api/brain/query endpoint already exists (created in mandate 016).

DIRECTIVES:

## 1. Create the /research page

Create `src/app/research/page.tsx`:

This is a full-page version of the Brain search modal — dedicated to deep research queries with more room for results and source exploration.

```tsx
'use client'

import { useState, useRef, useEffect } from 'react'
import { Muted } from '@shortgravity/ui'
import { useBrainQuery } from '@/lib/hooks/useBrainQuery'

export default function ResearchPage() {
  const [input, setInput] = useState('')
  const { messages, isStreaming, error, ask, clear } = useBrainQuery()
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim() && !isStreaming) {
      ask(input.trim())
      setInput('')
    }
  }

  // Source type labels
  const SOURCE_LABELS: Record<string, string> = {
    filings: 'SEC',
    fcc_filings: 'FCC',
    patents: 'PAT',
    press_releases: 'PR',
    x_posts: 'X',
    earnings_transcripts: 'CALL',
    inbox: 'NEWS',
    glossary_terms: 'TERM',
  }

  return (
    <div className="min-h-screen bg-[#030305] text-white font-mono flex flex-col">
      {/* Header */}
      <div className="border-b border-white/[0.06] px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-lg font-light tracking-wider">RESEARCH</h1>
            <Muted className="text-[10px]">13K+ documents — SEC filings, FCC dockets, patents, earnings, X posts</Muted>
          </div>
          <div className="flex gap-3">
            {messages.length > 0 && (
              <button
                onClick={clear}
                className="text-[10px] text-white/30 hover:text-white/50 border border-white/[0.06] px-3 py-1.5 rounded transition-colors"
              >
                CLEAR
              </button>
            )}
            <a href="/" className="text-[10px] text-white/30 hover:text-white/50 border border-white/[0.06] px-3 py-1.5 rounded transition-colors">
              TERMINAL
            </a>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
          {messages.length === 0 && (
            <div className="text-center py-20">
              <div className="text-white/15 text-sm mb-4">Ask anything about AST SpaceMobile</div>
              <div className="flex flex-wrap justify-center gap-2">
                {[
                  'What is the current FCC licensing status?',
                  'Summarize the latest earnings call',
                  'What patents cover the phased array design?',
                  'What are the key regulatory risks?',
                ].map((q) => (
                  <button
                    key={q}
                    onClick={() => { setInput(q); inputRef.current?.focus() }}
                    className="text-[11px] text-white/25 border border-white/[0.06] px-3 py-1.5 rounded-full hover:text-white/40 hover:border-white/[0.12] transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i}>
              {msg.role === 'user' ? (
                <div className="flex justify-end mb-2">
                  <div className="bg-white/[0.06] border border-white/[0.08] rounded-lg px-5 py-3 max-w-[75%]">
                    <div className="text-sm text-white/80">{msg.content}</div>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  {/* Sources */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {msg.sources.map((src, j) => (
                        <span
                          key={j}
                          className="text-[9px] font-mono px-2 py-1 rounded bg-white/[0.04] border border-white/[0.06] text-white/35"
                          title={src.snippet}
                        >
                          [{j + 1}] {SOURCE_LABELS[src.table] || src.table?.toUpperCase()}
                          {src.title && ` · ${src.title.slice(0, 40)}`}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Answer */}
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
            <div className="text-xs text-red-400/70 bg-red-400/5 border border-red-400/10 rounded-lg px-4 py-3">
              {error}
            </div>
          )}
        </div>
      </div>

      {/* Input bar */}
      <div className="border-t border-white/[0.06] px-6 py-4">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto flex gap-3">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Search filings, patents, earnings calls, regulatory documents..."
            disabled={isStreaming}
            className="flex-1 bg-white/[0.04] border border-white/[0.08] rounded-lg px-5 py-3 text-sm text-white/80 placeholder:text-white/20 focus:outline-none focus:border-white/[0.15] font-mono disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isStreaming || !input.trim()}
            className="px-6 py-3 bg-white/[0.06] border border-white/[0.08] rounded-lg text-xs font-mono text-white/50 hover:text-white/70 transition-colors disabled:opacity-30"
          >
            {isStreaming ? 'THINKING...' : 'ASK'}
          </button>
        </form>
      </div>
    </div>
  )
}
```

IMPORTANT: Check if `useBrainQuery` hook exists at `src/lib/hooks/useBrainQuery.ts` (created in mandate 016). If it doesn't exist yet, create it — see mandate 016 for the implementation. The hook provides: `{ messages, isStreaming, error, ask, clear }`.

## 2. Run `npx tsc --noEmit`
