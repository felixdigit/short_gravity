import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const revalidate = 3600

async function fetchFromSupabase() {
  const supabase = getAnonClient()
  const { data, error } = await supabase
    .from('short_interest')
    .select('*')
    .eq('symbol', 'ASTS')
    .order('report_date', { ascending: false })
    .limit(1)

  if (error || !data || data.length === 0) return null

  const row = data[0] as any

  // Calculate change from prior month
  let shortChange: number | null = null
  if (row.shares_short && row.shares_short_prior) {
    shortChange = row.shares_short - row.shares_short_prior
  }

  return {
    floatShortPct: row.short_pct_float,
    outstandingShortPct: row.short_pct_outstanding,
    sharesShort: row.shares_short,
    sharesShortPrior: row.shares_short_prior,
    shortChange,
    daysToCover: row.short_ratio,
    sharesOutstanding: row.shares_outstanding,
    floatShares: row.float_shares,
    reportDate: row.report_date,
    source: 'supabase',
  }
}

async function fetchHistory() {
  const supabase = getAnonClient()
  const { data, error } = await supabase
    .from('short_interest')
    .select('report_date, short_pct_float, shares_short, short_ratio')
    .eq('symbol', 'ASTS')
    .order('report_date', { ascending: true })

  if (error || !data) return []
  return data.map((row: any) => ({
    date: row.report_date,
    floatShortPct: row.short_pct_float,
    sharesShort: row.shares_short,
    daysToCover: row.short_ratio,
  }))
}

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 60 },
  handler: async (request) => {
    const { searchParams } = new URL(request.url)
    const wantHistory = searchParams.get('history') === 'true'

    if (wantHistory) {
      const history = await fetchHistory()
      return NextResponse.json({ history })
    }

    // Fetch from Supabase (populated by GitHub Actions worker)
    const dbResult = await fetchFromSupabase()
    if (dbResult) {
      return NextResponse.json(dbResult)
    }

    return NextResponse.json({
      floatShortPct: null,
      outstandingShortPct: null,
      sharesShort: null,
      sharesShortPrior: null,
      shortChange: null,
      daysToCover: null,
      sharesOutstanding: null,
      floatShares: null,
      reportDate: null,
      source: null,
    })
  },
})
