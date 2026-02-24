/**
 * Finnhub API Client
 *
 * Provides access to real-time stock market data from Finnhub API
 * Free tier: 60 API calls/minute, 15-minute delayed data
 * Documentation: https://finnhub.io/docs/api
 */

const FINNHUB_BASE_URL = 'https://finnhub.io/api/v1'

export interface FinnhubQuote {
  c: number  // Current price
  h: number  // High price of the day
  l: number  // Low price of the day
  o: number  // Open price of the day
  pc: number // Previous close price
  d: number  // Change
  dp: number // Percent change
  t: number  // Timestamp
}

export interface StockQuote {
  symbol: string
  currentPrice: number
  open: number
  high: number
  low: number
  previousClose: number
  change: number
  changePercent: number
  timestamp: number
}

/**
 * Fetch real-time stock quote for a given symbol
 * @param symbol - Stock ticker symbol (e.g., 'ASTS', 'AAPL')
 * @returns Stock quote data
 */
export async function getStockQuote(symbol: string): Promise<StockQuote> {
  const apiKey = process.env.FINNHUB_API_KEY!
  const url = `${FINNHUB_BASE_URL}/quote?symbol=${symbol}&token=${apiKey}`

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
      // Cache for 15 seconds to avoid hitting rate limits
      next: { revalidate: 15 }
    })

    if (!response.ok) {
      throw new Error(`Finnhub API error: ${response.status} ${response.statusText}`)
    }

    const data: FinnhubQuote = await response.json()

    // Transform to our internal format
    return {
      symbol,
      currentPrice: data.c,
      open: data.o,
      high: data.h,
      low: data.l,
      previousClose: data.pc,
      change: data.d,
      changePercent: data.dp,
      timestamp: data.t * 1000, // Convert to milliseconds
    }
  } catch (error) {
    console.error('Error fetching stock quote from Finnhub:', error)
    throw error
  }
}

/**
 * Fetch stock quotes for multiple symbols
 * @param symbols - Array of stock ticker symbols
 * @returns Array of stock quote data
 */
export async function getMultipleStockQuotes(symbols: string[]): Promise<StockQuote[]> {
  const promises = symbols.map(symbol => getStockQuote(symbol))
  return Promise.all(promises)
}

export interface BasicFinancials {
  metric: Record<string, number | string | null>
  series: Record<string, unknown>
}

/**
 * Fetch company basic financials / key metrics from Finnhub
 * Free tier includes: 52WeekHigh/Low, beta, marketCap, sharesOutstanding, etc.
 * May include shortInterest fields depending on tier.
 */
export async function getBasicFinancials(symbol: string): Promise<BasicFinancials> {
  const apiKey = process.env.FINNHUB_API_KEY!
  const url = `${FINNHUB_BASE_URL}/stock/metric?symbol=${symbol}&metric=all&token=${apiKey}`

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
      next: { revalidate: 3600 },
    })

    if (!response.ok) {
      throw new Error(`Finnhub API error: ${response.status} ${response.statusText}`)
    }

    return response.json()
  } catch (error) {
    console.error('Error fetching basic financials from Finnhub:', error)
    throw error
  }
}
