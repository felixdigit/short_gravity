import { useQuery } from '@tanstack/react-query'

export interface Candle {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface CandleData {
  symbol: string
  resolution: string
  candles: Candle[]
}

export function useStockCandles(symbol: string, resolution: 'D' | 'W' = 'D', days: number = 365) {
  return useQuery<CandleData>({
    queryKey: ['stock-candles', symbol, resolution, days],
    queryFn: async () => {
      const response = await fetch(
        `/api/stock/${symbol}/candles?resolution=${resolution}&days=${days}`
      )
      if (!response.ok) throw new Error('Failed to fetch stock candles')
      return response.json()
    },
    staleTime: 3600000,
    refetchInterval: 3600000,
  })
}
