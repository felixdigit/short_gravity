import { useQuery } from '@tanstack/react-query'

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

function isMarketOpen(): boolean {
  const now = new Date()
  const et = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }))
  const day = et.getDay()
  if (day === 0 || day === 6) return false
  const timeInMinutes = et.getHours() * 60 + et.getMinutes()
  return timeInMinutes >= 570 && timeInMinutes < 960
}

export function useStockPrice(symbol: string) {
  const marketOpen = isMarketOpen()
  const interval = marketOpen ? 60_000 : 5 * 60_000
  return useQuery<StockQuote>({
    queryKey: ['stock', symbol],
    queryFn: async () => {
      const response = await fetch(`/api/stock/${symbol}`)
      if (!response.ok) throw new Error('Failed to fetch stock price')
      return response.json()
    },
    refetchInterval: interval,
    staleTime: marketOpen ? 120_000 : 5 * 60_000,
  })
}
