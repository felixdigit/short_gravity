/**
 * API Route: Get stock quote
 * GET /api/stock/[symbol]
 *
 * Returns real-time stock price data from Finnhub
 */

import { NextResponse } from 'next/server'
import { getStockQuote } from '@/lib/finnhub'
import { createApiHandler } from '@/lib/api/handler'

export const dynamic = 'force-dynamic';

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 60 },
  handler: async (
    request,
    ctx
  ) => {
    const { symbol } = await ctx!.params

    if (!symbol) {
      return NextResponse.json(
        { error: 'Symbol parameter is required' },
        { status: 400 }
      )
    }

    const quote = await getStockQuote(symbol.toUpperCase())

    return NextResponse.json(quote)
  },
})
