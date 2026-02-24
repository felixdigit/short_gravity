'use client'

import { cn } from '@/lib/utils'
import { FocusPanel } from '@/components/ui/FocusPanel'
import { useFocusPanelContext } from '@shortgravity/ui'
import { useTerminalData } from '@/lib/providers/TerminalDataProvider'
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

function latLonToSvg(lat: number, lon: number, width: number, height: number) {
  const x = ((lon + 180) / 360) * width
  const y = ((90 - lat) / 180) * height
  return { x, y }
}

const W = 600
const H = 300

export function MercatorMapPanel() {
  const { focusedPanelId } = useFocusPanelContext()
  const expanded = focusedPanelId === 'mercator-map'
  const { mapTracks } = useTerminalData()

  return (
    <FocusPanel
      panelId="mercator-map"
      collapsedPosition="inline"
      expandedSize={{ width: '70vw', height: '60vh' }}
      label="GROUND TRACK MAP"
    >
      <div className={cn('w-full font-mono', expanded ? 'h-full p-4 pt-10' : '')}>
        <div className="text-[11px] text-white/50 tracking-wider mb-2">GROUND TRACK</div>
        <div
          className={cn(
            'relative overflow-hidden border border-white/[0.04] rounded bg-[#030305]',
            expanded ? 'flex-1 h-full' : 'h-[160px]'
          )}
        >
          <svg
            viewBox={`0 0 ${W} ${H}`}
            className="w-full h-full"
            preserveAspectRatio="xMidYMid meet"
          >
            <rect width={W} height={H} fill="#030305" />

            {/* Longitude grid lines every 30deg */}
            {Array.from({ length: 12 }, (_, i) => {
              const x = (i / 12) * W
              return (
                <line
                  key={`lon-${i}`}
                  x1={x} y1={0} x2={x} y2={H}
                  stroke="white" strokeOpacity={0.04} strokeWidth={0.5}
                />
              )
            })}
            {/* Latitude grid lines every 30deg */}
            {Array.from({ length: 6 }, (_, i) => {
              const y = (i / 6) * H
              return (
                <line
                  key={`lat-${i}`}
                  x1={0} y1={y} x2={W} y2={y}
                  stroke="white" strokeOpacity={0.04} strokeWidth={0.5}
                />
              )
            })}
            {/* Equator */}
            <line
              x1={0} y1={H / 2} x2={W} y2={H / 2}
              stroke="white" strokeOpacity={0.08} strokeWidth={0.5}
            />

            {/* Satellite positions */}
            {mapTracks.map((sat) => {
              const pos = latLonToSvg(
                sat.currentPosition.latitude,
                sat.currentPosition.longitude,
                W,
                H
              )
              return (
                <g key={sat.noradId}>
                  <circle cx={pos.x} cy={pos.y} r={6} fill="#FF6B35" opacity={0.15} />
                  <circle cx={pos.x} cy={pos.y} r={3} fill="#FF6B35" opacity={0.9} />
                  <text
                    x={pos.x + 8}
                    y={pos.y + 3}
                    fill="white"
                    fillOpacity={0.4}
                    fontSize={8}
                    fontFamily="monospace"
                  >
                    {sat.name}
                  </text>
                </g>
              )
            })}
          </svg>

          {mapTracks.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-[11px] text-white/30">Awaiting satellite data…</span>
            </div>
          )}
        </div>
      </div>
    </FocusPanel>
  )
}
