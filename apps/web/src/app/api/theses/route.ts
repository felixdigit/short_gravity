import { NextRequest, NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const dynamic = 'force-dynamic'

const THESIS_COLUMNS =
  'id, session_id, statement, supporting_prose, supporting_sources, contradicting_prose, contradicting_sources, synthesis_prose, synthesis_sources, status, created_at, updated_at'

/**
 * GET /api/theses
 *
 * List theses, optionally filtered by session_id.
 */
export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 30 },
  handler: async (req: NextRequest) => {
    const params = req.nextUrl.searchParams
    const sessionId = params.get('session_id')
    const limit = Number(params.get('limit') ?? 20)
    const offset = Number(params.get('offset') ?? 0)

    const supabase = getAnonClient()

    let query = supabase
      .from('theses')
      .select(THESIS_COLUMNS, { count: 'exact' })
      .order('created_at', { ascending: false })

    if (sessionId) query = query.eq('session_id', sessionId)

    query = query.range(offset, offset + limit - 1)

    const { data, count, error } = await query

    if (error) {
      console.error('[/api/theses] Supabase error:', error.message)
      return NextResponse.json({ data: [], count: 0 }, { status: 500 })
    }

    return NextResponse.json({ data: data ?? [], count: count ?? 0 })
  },
})

/**
 * POST /api/theses
 *
 * Create a new thesis. Requires session_id and statement.
 * The thesis is created with status='generating'; a separate process
 * fills in the supporting/contradicting/synthesis analysis.
 */
export const POST = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 10 },
  handler: async (request: NextRequest) => {
    const body = await request.json()
    const { session_id, statement } = body

    if (!session_id || !statement) {
      return NextResponse.json(
        { error: 'session_id and statement are required' },
        { status: 400 },
      )
    }

    if (typeof statement !== 'string' || statement.trim().length === 0) {
      return NextResponse.json(
        { error: 'statement must be a non-empty string' },
        { status: 400 },
      )
    }

    const supabase = getAnonClient()
    const { data, error } = await supabase
      .from('theses')
      .insert({ session_id, statement: statement.trim() })
      .select(THESIS_COLUMNS)
      .single()

    if (error) {
      console.error('[/api/theses] Insert error:', error.message)
      return NextResponse.json({ error: 'Failed to create thesis' }, { status: 500 })
    }

    return NextResponse.json({ thesis: data })
  },
})
