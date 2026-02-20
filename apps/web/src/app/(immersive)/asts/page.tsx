'use client'

export const dynamic = 'force-dynamic'

import { Suspense } from 'react'

// Data context + store
import { TerminalDataProvider, useTerminalData } from '@/lib/providers/TerminalDataProvider'
import { useTerminalStore } from '@/lib/stores/terminal-store'
import { getPreset } from '@/lib/terminal/presets'

// Shared data
import { getSatelliteInfo } from '@/lib/data/satellites'

// Layout — from @shortgravity/ui
import { FocusPanelProvider, HUDLayout } from '@shortgravity/ui'

// Overlays & controls — local
import { SatelliteInfoCard } from '@/components/hud/overlays/SatelliteInfoCard'
import { BrainSearch } from '@/components/hud/overlays/BrainSearch'
import { GlobeControls } from '@/components/hud/controls/GlobeControls'

// Widget panel system
import { WidgetPanel } from '@/components/hud/widgets/WidgetPanel'

// Dashboard ACL components
import { GlobeWidget } from '@/components/dashboard/GlobeWidget'

function TerminalContent() {
  const store = useTerminalStore()
  const { satellites } = useTerminalData()

  const handleSatelliteSelect = (noradId: string | undefined) => {
    if (!noradId) {
      store.deselectSatellite()
      return
    }
    store.toggleSatelliteCard(noradId)
  }

  const isMinimal = store.mode === 'minimal'
  const selectedData = store.selectedSatellite
    ? satellites.find((s) => s.noradId === store.selectedSatellite)
    : null

  const preset = getPreset(store.activePreset)

  return (
    <FocusPanelProvider>
      <HUDLayout onClick={() => store.deselectSatellite()}>
        <HUDLayout.Canvas>
          <GlobeWidget className="w-full h-full" />
        </HUDLayout.Canvas>

        {!isMinimal && (
          <>
            <HUDLayout.LeftPanel>
              <WidgetPanel slots={preset.left} />
            </HUDLayout.LeftPanel>

            <HUDLayout.RightPanel>
              <WidgetPanel slots={preset.right} />
            </HUDLayout.RightPanel>
          </>
        )}

        {isMinimal && (
          <div className="absolute bottom-32 left-1/2 -translate-x-1/2 text-center">
            <div className="text-[72px] font-extralight text-white leading-none tabular-nums font-mono">
              {satellites.length}
            </div>
            <div className="text-[9px] text-white/40 tracking-[0.3em] mt-2 font-mono">
              ACTIVE SATELLITES
            </div>
          </div>
        )}

        <HUDLayout.BottomCenter>
          <GlobeControls />
        </HUDLayout.BottomCenter>

        {store.showSatelliteCard && selectedData && (
          <SatelliteInfoCard
            noradId={selectedData.noradId}
            name={selectedData.name}
            type={selectedData.type}
            latitude={selectedData.latitude}
            longitude={selectedData.longitude}
            altitude={selectedData.altitude}
            velocity={selectedData.velocity}
            inclination={selectedData.inclination}
            bstar={selectedData.bstar}
            satelliteInfo={getSatelliteInfo(selectedData.noradId)}
            onClose={() => store.deselectSatellite()}
          />
        )}
      </HUDLayout>

      <BrainSearch
        open={store.brainOpen}
        onClose={() => store.setBrainOpen(false)}
      />
    </FocusPanelProvider>
  )
}

export default function TerminalPage() {
  return (
    <TerminalDataProvider>
      <Suspense>
        <TerminalContent />
      </Suspense>
    </TerminalDataProvider>
  )
}
