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
