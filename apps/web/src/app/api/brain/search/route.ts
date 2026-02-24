import { NextRequest } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getServiceClient } from '@shortgravity/database'
import OpenAI from 'openai'

export const dynamic = 'force-dynamic'

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY! })

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 30 },
  handler: async (request: NextRequest) => {
    const q = request.nextUrl.searchParams.get('q')
    const limit = Math.min(parseInt(request.nextUrl.searchParams.get('limit') || '5'), 20)

    if (!q || q.trim().length < 2) {
      return Response.json({ results: [] })
    }

    const embedding = await openai.embeddings.create({
      model: 'text-embedding-3-small',
      input: q.trim(),
    })

    const queryEmbedding = embedding.data[0].embedding

    const supabase = getServiceClient()
    const { data: chunks, error } = await supabase.rpc('brain_search', {
      query_embedding: queryEmbedding,
      match_count: limit,
    })

    if (error) {
      console.error('Brain search error:', error)
      return Response.json({ results: [] })
    }

    interface BrainChunk {
      id: string
      source_table: string
      source_id: string
      content: string
      metadata?: Record<string, string>
    }

    const results = ((chunks as BrainChunk[]) || []).map((chunk) => ({
      id: chunk.id,
      source: chunk.source_table,
      sourceId: chunk.source_id,
      title: chunk.metadata?.title || String(chunk.source_id),
      snippet: String(chunk.content || '').slice(0, 150),
      date: chunk.metadata?.date || null,
    }))

    return Response.json({ results })
  },
})
