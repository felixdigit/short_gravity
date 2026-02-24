import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const revalidate = 300

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 30 },
  handler: async (request) => {
    const supabase = getAnonClient()
    const params = request.nextUrl.searchParams
    const q = params.get('q') || ''
    const status = params.get('status') || ''
    const jurisdiction = params.get('jurisdiction') || ''
    const limit = Math.min(parseInt(params.get('limit') || '50'), 200)
    const offset = parseInt(params.get('offset') || '0')

    let query = supabase
      .from('patents')
      .select(
        'id, patent_number, title, abstract, status, filing_date, grant_date, expiration_date, jurisdiction, applicant, claims_count, created_at',
        { count: 'exact' },
      )
      .order('filing_date', { ascending: false, nullsFirst: false })

    if (q.trim()) {
      query = query.or(
        `title.ilike.%${q}%,abstract.ilike.%${q}%,patent_number.ilike.%${q}%`,
      )
    }

    if (status) {
      query = query.eq('status', status)
    }

    if (jurisdiction) {
      query = query.eq('jurisdiction', jurisdiction)
    }

    query = query.range(offset, offset + limit - 1)

    const { data, error, count } = await query
    if (error) throw error

    return NextResponse.json({
      patents: data || [],
      total: count ?? data?.length ?? 0,
    })
  },
})
