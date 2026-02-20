'use client'

import { cn } from '@/lib/utils'
import { FocusPanel } from '@/components/ui/FocusPanel'
import { useFocusPanelContext } from '@shortgravity/ui'
import type { WidgetManifest } from './types'

export const mercatorMapManifest: WidgetManifest = {
  id: 'mercator-map',
  name: 'GROUND TRACK',
  category: 'data',
  panelPreference: 'left',
  sizing: 'fixed',
  expandable: true,
  separator: false,
}

/**
 * MercatorMapPanel stub.
 * TODO: Wire ClientGroundTrackMap from the archive (requires leaflet or custom canvas map).
 */
export function MercatorMapPanel() {
  const { focusedPanelId } = useFocusPanelContext()
  const expanded = focusedPanelId === 'mercator-map'

  return (
    <FocusPanel
      panelId="mercator-map"
      collapsedPosition="inline"
      expandedSize={{ width: '70vw', height: '60vh' }}
      label="GROUND TRACK MAP"
    >
      <div className={cn('w-full font-mono', expanded ? 'h-full p-4 pt-10' : '')}>
        <div className="text-[11px] text-white/50 tracking-wider mb-2">GROUND TRACK</div>
        <div className={cn(
          'flex items-center justify-center border border-white/[0.04] rounded bg-black/20',
          expanded ? 'flex-1 h-full' : 'h-[40px]'
        )}>
          <span className="text-[11px] text-white/30">Map not yet wired</span>
        </div>
      </div>
    </FocusPanel>
  )
}
