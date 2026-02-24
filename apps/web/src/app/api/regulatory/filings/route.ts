import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const revalidate = 900

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 30 },
  handler: async (request) => {
    const supabase = getAnonClient()
    const system = request.nextUrl.searchParams.get('system') // ICFS, ECFS, ELS
    const limit = Math.min(
      parseInt(request.nextUrl.searchParams.get('limit') || '50'),
      200
    )
    const offset = parseInt(request.nextUrl.searchParams.get('offset') || '0')

    let query = supabase
      .from('fcc_filings')
      .select(
        'id, filing_system, file_number, title, filing_type, application_status, applicant, docket, filed_date, call_sign, created_at',
        { count: 'exact' }
      )
      .order('filed_date', { ascending: false, nullsFirst: false })
      .range(offset, offset + limit - 1)

    if (system) {
      query = query.eq('filing_system', system)
    }

    const { data, error, count } = await query
    if (error) throw error

    return NextResponse.json({
      filings: data || [],
      count: count ?? data?.length ?? 0,
    })
  },
})
