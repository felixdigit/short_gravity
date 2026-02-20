'use client'

import { useTerminalStore } from '@/lib/stores/terminal-store'
import { useStockPrice } from '@/lib/hooks/useStockPrice'
import { ErrorBoundary } from '@shortgravity/ui'
import { Search } from 'lucide-react'
import { cn } from '@/lib/utils'

export function TopBar({ mode }: { mode: 'standard' | 'immersive' }) {
  const setCommandPaletteOpen = useTerminalStore((s) => s.setCommandPaletteOpen)

  return (
    <header
      className={cn(
        'fixed top-0 right-0 z-40 h-12 flex items-center px-4 transition-colors',
        mode === 'immersive'
          ? 'left-0 bg-transparent'
          : 'left-12 bg-[var(--void-black)] border-b border-white/[0.04]'
      )}
    >
      <div className="flex items-center gap-3">
        <span className="text-[11px] tracking-[0.25em] text-white/50 font-mono uppercase">
          SHORT GRAVITY
        </span>
      </div>

      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
        <button
          onClick={() => setCommandPaletteOpen(true)}
          className={cn(
            'flex items-center gap-2 px-3 py-1.5 rounded border transition-all',
            mode === 'immersive'
              ? 'border-white/[0.06] bg-black/40 backdrop-blur-sm hover:border-white/[0.12]'
              : 'border-white/[0.06] bg-white/[0.02] hover:border-white/[0.12]'
          )}
        >
          <Search className="w-3 h-3 text-white/50" />
          <span className="text-[11px] text-white/50 tracking-wider">Search or ask...</span>
          <kbd className="text-[11px] text-white/40 font-mono border border-white/[0.06] px-1.5 py-0.5 rounded ml-8">
            {'\u2318'}K
          </kbd>
        </button>
      </div>

      <div className="ml-auto flex items-center gap-4">
        <ErrorBoundary name="StockTicker">
          <CompactTicker symbol="ASTS" />
        </ErrorBoundary>
      </div>
    </header>
  )
}

function CompactTicker({ symbol }: { symbol: string }) {
  const { data: stock } = useStockPrice(symbol)

  if (!stock) {
    return <div className="w-20 h-4 animate-pulse bg-white/5 rounded" />
  }

  const isPositive = stock.change >= 0

  return (
    <div className="hidden sm:flex items-center gap-2 font-mono">
      <span className="text-[11px] text-white/50 tracking-wider">${symbol}</span>
      <span className="text-[13px] font-light text-white tabular-nums">
        ${stock.currentPrice.toFixed(2)}
      </span>
      <span
        className={cn(
          'text-[9px] tabular-nums',
          isPositive ? 'text-green-400/70' : 'text-red-400/70'
        )}
      >
        {isPositive ? '+' : ''}{stock.changePercent.toFixed(2)}%
      </span>
    </div>
  )
}
