TARGET: apps/web
---
MISSION:
Wire the Brain search system — API route for RAG query, useBrainQuery hook with streaming, and replace the BrainSearch stub with a functional component.

DIRECTIVES:

## 1. Check dependencies

Run: `npx next info` or check `package.json` for `@anthropic-ai/sdk` and `openai`.

If `@anthropic-ai/sdk` is NOT in dependencies, add it:
```bash
cd /Users/gabriel/Desktop/short_gravity && pnpm add @anthropic-ai/sdk openai --filter @shortgravity/web
```

If the package names differ in the workspace, check the package.json `name` field in `apps/web/package.json` and use the correct filter.

## 2. Create the Brain query API route

Create `src/app/api/brain/query/route.ts`:

The pipeline is:
1. Receive POST with `{ query: string }`
2. Embed the query using OpenAI `text-embedding-3-small` (1536 dimensions)
3. Call Supabase RPC `brain_search` to find relevant chunks
4. Build a context prompt from the top chunks
5. Call Claude API to synthesize an answer
6. Stream the response back

```ts
import { NextRequest } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getServiceClient } from '@shortgravity/database'
import Anthropic from '@anthropic-ai/sdk'
import OpenAI from 'openai'

export const dynamic = 'force-dynamic'
export const maxDuration = 30

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY! })
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY! })

export const POST = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 10 },
  handler: async (request: NextRequest) => {
    const body = await request.json()
    const { query } = body

    if (!query || typeof query !== 'string' || query.trim().length === 0) {
      return Response.json({ error: 'Query is required' }, { status: 400 })
    }

    if (query.length > 2000) {
      return Response.json({ error: 'Query too long (max 2000 chars)' }, { status: 400 })
    }

    // Step 1: Embed query
    const embeddingResponse = await openai.embeddings.create({
      model: 'text-embedding-3-small',
      input: query.trim(),
    })
    const queryEmbedding = embeddingResponse.data[0].embedding

    // Step 2: Search brain chunks via Supabase RPC
    const supabase = getServiceClient()
    const { data: chunks, error: searchError } = await supabase.rpc('brain_search', {
      query_embedding: queryEmbedding,
      match_count: 8,
    })

    if (searchError) {
      console.error('Brain search error:', searchError)
      return Response.json({ error: 'Search failed' }, { status: 500 })
    }

    if (!chunks || chunks.length === 0) {
      return Response.json({
        answer: 'No relevant documents found for this query.',
        sources: [],
      })
    }

    // Step 3: Build context from chunks
    const context = chunks
      .map((chunk: { content: string; source_table: string; source_id: string; metadata?: Record<string, unknown> }, i: number) => {
        const source = chunk.source_table || 'unknown'
        const title = (chunk.metadata as Record<string, string>)?.title || chunk.source_id
        return `[${i + 1}] (${source}) ${title}\n${chunk.content}`
      })
      .join('\n\n---\n\n')

    const sources = chunks.map((chunk: { source_table: string; source_id: string; content: string; metadata?: Record<string, unknown> }) => ({
      table: chunk.source_table,
      id: chunk.source_id,
      title: (chunk.metadata as Record<string, string>)?.title || chunk.source_id,
      snippet: chunk.content?.slice(0, 200),
    }))

    // Step 4: Stream Claude response
    const stream = anthropic.messages.stream({
      model: 'claude-sonnet-4-5-20250514',
      max_tokens: 1500,
      system: `You are a research analyst for Short Gravity, an intelligence platform tracking AST SpaceMobile ($ASTS). Answer questions using ONLY the provided context documents. Be concise and cite sources by their number [1], [2], etc. If the context doesn't contain enough information, say so clearly.`,
      messages: [
        {
          role: 'user',
          content: `Context documents:\n\n${context}\n\n---\n\nQuestion: ${query}`,
        },
      ],
    })

    // Return as SSE stream
    const encoder = new TextEncoder()
    const readable = new ReadableStream({
      async start(controller) {
        try {
          // Send sources first
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify({ type: 'sources', sources })}\n\n`)
          )

          for await (const event of stream) {
            if (event.type === 'content_block_delta' && event.delta.type === 'text_delta') {
              controller.enqueue(
                encoder.encode(`data: ${JSON.stringify({ type: 'text', content: event.delta.text })}\n\n`)
              )
            }
          }

          controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'done' })}\n\n`))
          controller.close()
        } catch (err) {
          const errorMsg = err instanceof Error ? err.message : 'Stream error'
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify({ type: 'error', error: errorMsg })}\n\n`)
          )
          controller.close()
        }
      },
    })

    return new Response(readable, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      },
    })
  },
})
```

IMPORTANT: The `createApiHandler` wrapper may not support returning a raw `Response` (it might expect `NextResponse`). If it causes issues, bypass it and write a plain route handler:

```ts
export async function POST(request: NextRequest) {
  // ... same logic without createApiHandler wrapper
}
```

Also check the RPC function signature. The Supabase RPC `brain_search` may have different parameter names. Check the database or try:
```ts
supabase.rpc('brain_search', {
  query_embedding: queryEmbedding,
  match_count: 8,
  filter_sources: null, // or omit
})
```

## 3. Create the useBrainQuery hook

Create `src/lib/hooks/useBrainQuery.ts`:

```ts
'use client'

import { useState, useCallback, useRef } from 'react'

interface BrainSource {
  table: string
  id: string
  title: string
  snippet: string
}

interface BrainMessage {
  role: 'user' | 'assistant'
  content: string
  sources?: BrainSource[]
}

export function useBrainQuery() {
  const [messages, setMessages] = useState<BrainMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const ask = useCallback(async (query: string) => {
    if (!query.trim() || isStreaming) return

    setError(null)
    setMessages(prev => [...prev, { role: 'user', content: query }])
    setIsStreaming(true)

    // Add placeholder assistant message
    setMessages(prev => [...prev, { role: 'assistant', content: '', sources: [] }])

    try {
      abortRef.current = new AbortController()

      const response = await fetch('/api/brain/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
        signal: abortRef.current.signal,
      })

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.error || `Request failed: ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response stream')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const jsonStr = line.slice(6).trim()
          if (!jsonStr) continue

          try {
            const event = JSON.parse(jsonStr)

            if (event.type === 'sources') {
              setMessages(prev => {
                const updated = [...prev]
                const last = updated[updated.length - 1]
                if (last?.role === 'assistant') {
                  updated[updated.length - 1] = { ...last, sources: event.sources }
                }
                return updated
              })
            } else if (event.type === 'text') {
              setMessages(prev => {
                const updated = [...prev]
                const last = updated[updated.length - 1]
                if (last?.role === 'assistant') {
                  updated[updated.length - 1] = {
                    ...last,
                    content: last.content + event.content,
                  }
                }
                return updated
              })
            } else if (event.type === 'error') {
              setError(event.error)
            }
          } catch {
            // Skip malformed JSON
          }
        }
      }
    } catch (err) {
      if (err instanceof Error && err.name !== 'AbortError') {
        setError(err.message)
      }
    } finally {
      setIsStreaming(false)
      abortRef.current = null
    }
  }, [isStreaming])

  const clear = useCallback(() => {
    if (abortRef.current) abortRef.current.abort()
    setMessages([])
    setError(null)
    setIsStreaming(false)
  }, [])

  return { messages, isStreaming, error, ask, clear }
}
```

## 4. Rewrite BrainSearch component

Replace the stub in `src/components/hud/overlays/BrainSearch.tsx` with a functional implementation:

```tsx
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
```

## 5. Verify BrainSearch props match usage

Check `src/app/(immersive)/asts/page.tsx` to see how BrainSearch is used. It should be:
```tsx
<BrainSearch open={store.brainOpen} onClose={() => store.setBrainOpen(false)} />
```

The new component accepts `{ open, onClose }` — make sure these match. If the existing usage passes additional props (like `messages`, `isStreaming`, `onAsk`), remove those from the caller since the component now manages its own state via `useBrainQuery`.

## 6. Run `npx tsc --noEmit`

If the Anthropic SDK types cause issues (e.g., streaming event types), use `as any` sparingly on the stream events. The streaming API shape may vary by SDK version. Test the type-check and fix any issues.

If `getServiceClient` doesn't exist in `@shortgravity/database`, use `getAnonClient` instead. The brain_search RPC should be accessible with anon key if RLS is configured with public SELECT on brain_chunks.
