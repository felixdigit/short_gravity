import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const revalidate = 3600  // 1hr cache — data changes daily at most

async function fetchCashHistory() {
  const supabase = getAnonClient()
  const { data, error } = await supabase
    .from('cash_position')
    .select('filing_date, filing_form, cash_and_equivalents, total_cash_restricted, available_liquidity, quarterly_burn, unit')
    .eq('symbol', 'ASTS')
    .order('filing_date', { ascending: true })

  if (error || !data) return []
  return data.map((row: any) => {
    const bestCash = row.available_liquidity || row.total_cash_restricted || row.cash_and_equivalents
    return {
      date: row.filing_date,
      form: row.filing_form,
      cash: bestCash,
      burn: row.quarterly_burn,
      unit: row.unit || 'thousands',
    }
  })
}

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 60 },
  handler: async (request) => {
    const supabase = getAnonClient()
    const { searchParams } = new URL(request.url)
    const wantHistory = searchParams.get('history') === 'true'

    if (wantHistory) {
      const history = await fetchCashHistory()
      return NextResponse.json({ history })
    }
    // Try cash_position table first (populated by worker)
    const { data: cached, error: cacheErr } = await supabase
      .from('cash_position')
      .select('*')
      .eq('symbol', 'ASTS')
      .order('filing_date', { ascending: false })
      .limit(1)

    if (!cacheErr && cached && cached.length > 0) {
      const row = cached[0] as any
      // Prefer available_liquidity (pro forma), fall back to total_cash_restricted, then cash_and_equivalents
      const bestCash = row.available_liquidity || row.total_cash_restricted || row.cash_and_equivalents
      const label = row.label || (row.available_liquidity ? 'PRO FORMA LIQUIDITY' : 'ON HAND')

      return NextResponse.json({
        cashOnHand: bestCash,
        unit: row.unit || 'thousands',
        quarterlyBurn: row.quarterly_burn,
        label,
        filingForm: row.filing_form,
        filingDate: row.filing_date,
        source: 'supabase',
      })
    }

    // Fallback: extract from filing content directly
    const { data: filings, error } = await supabase
      .from('filings')
      .select('form, filing_date, content_text')
      .in('form', ['10-Q', '10-K', '10-Q/A', '10-K/A'])
      .eq('status', 'completed')
      .order('filing_date', { ascending: false })
      .limit(3)

    if (error || !filings || filings.length === 0) {
      return NextResponse.json({ cashOnHand: null, unit: null, quarterlyBurn: null, label: null, filingForm: null, filingDate: null, source: null })
    }

    for (const filing of filings) {
      const content = (filing as any).content_text as string | null
      if (!content) continue

      // Extract total cash, cash equivalents and restricted cash from cash flow statement
      const totalMatch = content.match(/Cash, cash equivalents and restricted cash\s+\$\s*([\d,]+)/i)
      // Extract cash used in operating activities
      const burnMatch = content.match(/Cash used in operating activities\s*\(?\s*([\d,]+)/i)
      // Look for liquidity disclosure with ATM
      const liquidityMatch = content.match(/\$([\d,.]+)\s*(?:million|billion)\s+(?:of\s+)?cash(?:\s+and\s+cash\s+equivalents)?\s+on\s+hand/i)
      const atmMatch = content.match(/\$([\d,.]+)\s*(?:million|billion)\s+remaining.*?(?:ATM|at.the.market)/i)

      let bestCash: number | null = null
      let unit: string = 'thousands'
      let label = 'ON HAND'

      // Build liquidity number (cash on hand + ATM)
      if (liquidityMatch) {
        let cashM = parseFloat(liquidityMatch[1].replace(/,/g, ''))
        let atmM = 0
        if (atmMatch) {
          atmM = parseFloat(atmMatch[1].replace(/,/g, ''))
        }
        bestCash = (cashM + atmM) * 1000 // convert M to K
        label = atmM > 0 ? `CASH + $${Math.round(atmM)}M ATM` : 'CASH ON HAND'
      }

      // Fall back to total cash+restricted from cash flow statement
      if (!bestCash && totalMatch) {
        bestCash = parseInt(totalMatch[1].replace(/,/g, ''))
        label = 'CASH + RESTRICTED'
      }

      if (bestCash) {
        return NextResponse.json({
          cashOnHand: bestCash,
          unit,
          quarterlyBurn: burnMatch ? parseInt(burnMatch[1].replace(/,/g, '')) : null,
          label,
          filingForm: filing.form,
          filingDate: filing.filing_date,
          source: 'fallback',
        })
      }
    }

    return NextResponse.json({ cashOnHand: null, unit: null, quarterlyBurn: null, label: null, filingForm: null, filingDate: null, source: null })
  },
})
