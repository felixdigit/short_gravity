'use client'

import { cn } from '../../lib/utils'
import { ErrorBoundary } from './ErrorBoundary'
import type { WidgetManifest } from '../../types'

interface WidgetHostProps {
  manifest: WidgetManifest
  sizing?: 'fixed' | 'flexible'
  isFirst?: boolean
  children: React.ReactNode
}

export function WidgetHost({ manifest, sizing, isFirst, children }: WidgetHostProps) {
  const effectiveSizing = sizing ?? manifest.sizing
  const isFlexible = effectiveSizing === 'flexible'

  return (
    <div
      className={cn(
        manifest.separator && 'mt-3 pt-2 border-t border-white/[0.03]',
        isFlexible && 'flex-1 min-h-0 mt-3 pt-3 border-t border-white/[0.03] overflow-y-auto scrollbar-thin -mr-3 pr-3',
        !manifest.separator && !isFlexible && !isFirst && 'mt-3'
      )}
    >
      <ErrorBoundary name={manifest.name}>
        {children}
      </ErrorBoundary>
    </div>
  )
}
