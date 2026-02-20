'use client'

import { type ReactNode } from 'react'
import { cn } from '@/lib/utils'

/**
 * FocusPanel stub — placeholder for the framer-motion expandable panel.
 * TODO: Migrate the full FocusPanel from the archive (requires framer-motion).
 * Currently renders children inline without expand/collapse behavior.
 */
interface FocusPanelProps {
  panelId: string
  collapsedPosition?: 'inline' | 'fixed'
  expandedSize?: { width: string; height: string }
  screenshotFilename?: string
  label?: string
  children: ReactNode
  className?: string
}

export function FocusPanel({ children, className }: FocusPanelProps) {
  return <div className={cn('w-full', className)}>{children}</div>
}
