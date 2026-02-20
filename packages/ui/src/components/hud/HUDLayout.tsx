'use client'

import { cn } from '../../lib/utils'
import { createContext, useContext, useState, type ReactNode } from 'react'

const HUDLayoutContext = createContext<{ isMinimal?: boolean }>({})

interface HUDLayoutProps {
  children: ReactNode
  className?: string
  onClick?: (e: React.MouseEvent) => void
}

function MobileWarning() {
  const [dismissed, setDismissed] = useState(false)
  if (dismissed) return null
  return (
    <div className="lg:hidden fixed inset-x-0 top-0 z-[100] bg-[var(--void-black)] border-b border-white/10 p-3 flex items-center justify-between">
      <span className="text-[10px] text-white/50 tracking-wider">SHORT GRAVITY IS DESIGNED FOR DESKTOP</span>
      <button
        onClick={() => setDismissed(true)}
        className="text-[10px] text-white/30 hover:text-white/60 tracking-wider px-2"
      >
        DISMISS
      </button>
    </div>
  )
}

export function HUDLayout({ children, className, onClick }: HUDLayoutProps) {
  return (
    <HUDLayoutContext.Provider value={{}}>
      <MobileWarning />
      <div
        className={cn(
          'fixed inset-0 bg-[var(--void-black)] font-mono text-[10px] select-none overflow-hidden',
          className
        )}
        onClick={onClick}
      >
        {children}
      </div>
    </HUDLayoutContext.Provider>
  )
}

HUDLayout.Canvas = function Canvas({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('absolute inset-0 z-0', className)}>{children}</div>
}

HUDLayout.TopLeft = function TopLeft({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('absolute top-6 left-6 z-10', className)} onClick={(e) => e.stopPropagation()}>{children}</div>
}

HUDLayout.TopRight = function TopRight({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('absolute top-6 right-6 z-20', className)} onClick={(e) => e.stopPropagation()}>{children}</div>
}

HUDLayout.LeftPanel = function LeftPanel({
  children,
  className,
  width = 'w-64',
}: {
  children: ReactNode
  className?: string
  width?: string
}) {
  return (
    <div
      className={cn(
        'absolute top-14 left-4 bottom-14 z-10 flex flex-col',
        'p-2 overflow-y-auto overflow-x-hidden scrollbar-thin',
        width,
        className
      )}
      onClick={(e) => e.stopPropagation()}
    >
      {children}
    </div>
  )
}

HUDLayout.RightPanel = function RightPanel({
  children,
  className,
  width = 'w-60',
}: {
  children: ReactNode
  className?: string
  width?: string
}) {
  return (
    <div
      className={cn(
        'absolute top-14 right-4 bottom-14 z-10 flex flex-col',
        'p-2 overflow-y-auto overflow-x-hidden scrollbar-thin',
        width,
        className
      )}
      onClick={(e) => e.stopPropagation()}
    >
      {children}
    </div>
  )
}

HUDLayout.BottomLeft = function BottomLeft({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <div className={cn('absolute bottom-6 left-6 z-10', className)}>{children}</div>
}

HUDLayout.BottomRight = function BottomRight({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <div className={cn('absolute bottom-6 right-6 z-10', className)}>{children}</div>
}

HUDLayout.BottomCenter = function BottomCenter({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn('absolute bottom-8 left-1/2 -translate-x-1/2 z-30', className)} onClick={(e) => e.stopPropagation()}>
      {children}
    </div>
  )
}

HUDLayout.Center = function Center({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn('absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50', className)}>
      {children}
    </div>
  )
}

HUDLayout.Overlay = function Overlay({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn('absolute inset-0 pointer-events-none z-[1]', className)}>
      {children}
    </div>
  )
}

HUDLayout.Attribution = function Attribution({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn('absolute bottom-2 left-1/2 -translate-x-1/2 text-[6px] text-white/10 tracking-wider', className)}>
      {children}
    </div>
  )
}

export function useHUDLayout() {
  return useContext(HUDLayoutContext)
}
