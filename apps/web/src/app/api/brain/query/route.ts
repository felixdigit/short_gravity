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
    interface BrainChunk {
      content: string
      source_table: string
      source_id: string
      metadata?: Record<string, unknown>
    }

    const context = (chunks as BrainChunk[])
      .map((chunk, i) => {
        const source = chunk.source_table || 'unknown'
        const title = (chunk.metadata as Record<string, string>)?.title || chunk.source_id
        return `[${i + 1}] (${source}) ${title}\n${chunk.content}`
      })
      .join('\n\n---\n\n')

    const sources = (chunks as BrainChunk[]).map((chunk) => ({
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
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify({ type: 'sources', sources })}\n\n`)
          )

          for await (const event of stream) {
            if (
              event.type === 'content_block_delta' &&
              event.delta.type === 'text_delta'
            ) {
              controller.enqueue(
                encoder.encode(
                  `data: ${JSON.stringify({ type: 'text', content: event.delta.text })}\n\n`
                )
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
