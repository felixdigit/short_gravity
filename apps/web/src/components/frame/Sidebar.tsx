'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { Monitor, Newspaper, DollarSign, Search, LayoutGrid, Settings } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useFrameStore } from '@/lib/stores/frame-store'
import { useTerminalStore } from '@/lib/stores/terminal-store'

const NAV_ITEMS = [
  { icon: Monitor, label: 'TERMINAL', route: '/asts', match: '/asts' },
  { icon: Newspaper, label: 'BRIEFING', route: '/briefing', match: '/briefing' },
  { icon: DollarSign, label: 'EARNINGS', route: '/earnings', match: '/earnings' },
  { icon: Search, label: 'BRAIN', route: '/research', match: '/research' },
]

export function Sidebar({ mode }: { mode: 'standard' | 'immersive' }) {
  const pathname = usePathname()
  const { sidebarExpanded, sidebarHovered, setSidebarHovered } = useFrameStore()
  const setCommandPaletteOpen = useTerminalStore(s => s.setCommandPaletteOpen)

  const isExpanded = sidebarExpanded || sidebarHovered

  if (mode === 'immersive') {
    return (
      <div
        className="fixed left-0 top-0 bottom-0 w-3 z-50 group"
        onMouseEnter={() => setSidebarHovered(true)}
      >
        <nav
          className={cn(
            'fixed left-0 top-0 bottom-0 z-50 flex flex-col bg-[var(--void-black)] border-r border-white/[0.04] transition-all duration-200',
            sidebarHovered ? 'w-[200px] opacity-100 translate-x-0' : 'w-0 opacity-0 -translate-x-full'
          )}
          onMouseLeave={() => setSidebarHovered(false)}
        >
          <div className="flex-1 pt-14 px-2 space-y-0.5">
            {NAV_ITEMS.map((item) => {
              const isActive = pathname?.startsWith(item.match)
              return (
                <Link
                  key={item.route}
                  href={item.route}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded transition-colors',
                    isActive ? 'text-[var(--asts-orange)]' : 'text-white/50 hover:text-white/70'
                  )}
                >
                  <item.icon className="w-4 h-4 flex-shrink-0" />
                  <span className="text-[11px] tracking-[0.15em] font-mono">{item.label}</span>
                </Link>
              )
            })}
          </div>
          <div className="px-2 pb-4 space-y-0.5">
            <button
              onClick={() => setCommandPaletteOpen(true)}
              className="flex items-center gap-3 px-3 py-2.5 rounded text-white/50 hover:text-white/70 transition-colors w-full"
            >
              <LayoutGrid className="w-4 h-4 flex-shrink-0" />
              <span className="text-[11px] tracking-[0.15em] font-mono">VAULT</span>
            </button>
            <Link
              href="/account"
              className="flex items-center gap-3 px-3 py-2.5 rounded text-white/50 hover:text-white/70 transition-colors"
            >
              <Settings className="w-4 h-4 flex-shrink-0" />
              <span className="text-[11px] tracking-[0.15em] font-mono">SETTINGS</span>
            </Link>
          </div>
        </nav>
      </div>
    )
  }

  // Standard mode
  return (
    <nav
      className={cn(
        'fixed left-0 top-0 bottom-0 z-40 flex flex-col bg-[var(--void-black)] border-r border-white/[0.04] transition-all duration-200',
        isExpanded ? 'w-[200px]' : 'w-12'
      )}
      onMouseEnter={() => setSidebarHovered(true)}
      onMouseLeave={() => setSidebarHovered(false)}
    >
      <div className="flex-1 pt-14 px-2 space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname?.startsWith(item.match)
          return (
            <Link
              key={item.route}
              href={item.route}
              title={!isExpanded ? item.label : undefined}
              className={cn(
                'flex items-center gap-3 px-2 py-2.5 rounded transition-colors',
                isActive ? 'text-[var(--asts-orange)]' : 'text-white/50 hover:text-white/70'
              )}
            >
              <item.icon className="w-4 h-4 flex-shrink-0" />
              {isExpanded && (
                <span className="text-[11px] tracking-[0.15em] font-mono whitespace-nowrap">{item.label}</span>
              )}
            </Link>
          )
        })}
      </div>
      <div className="px-2 pb-4 space-y-0.5">
        <button
          onClick={() => setCommandPaletteOpen(true)}
          title={!isExpanded ? 'VAULT' : undefined}
          className="flex items-center gap-3 px-2 py-2.5 rounded text-white/50 hover:text-white/70 transition-colors w-full"
        >
          <LayoutGrid className="w-4 h-4 flex-shrink-0" />
          {isExpanded && (
            <span className="text-[11px] tracking-[0.15em] font-mono">VAULT</span>
          )}
        </button>
        <Link
          href="/account"
          title={!isExpanded ? 'SETTINGS' : undefined}
          className="flex items-center gap-3 px-2 py-2.5 rounded text-white/50 hover:text-white/70 transition-colors"
        >
          <Settings className="w-4 h-4 flex-shrink-0" />
          {isExpanded && (
            <span className="text-[11px] tracking-[0.15em] font-mono">SETTINGS</span>
          )}
        </Link>
      </div>
    </nav>
  )
}
