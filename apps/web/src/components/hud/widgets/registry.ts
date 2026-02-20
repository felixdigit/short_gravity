import type { WidgetRegistryEntry } from './types'

import { TelemetryFeed, telemetryFeedManifest } from './TelemetryFeed'
import { ConstellationProgress, constellationProgressManifest } from './ConstellationProgress'
import { ConstellationMatrix, constellationMatrixManifest } from './ConstellationMatrix'
import { EnvironmentStrip, environmentStripManifest } from './EnvironmentStrip'
import { FM1Monitor, fm1MonitorManifest } from './FM1Monitor'
import { FM1WatchPanel, fm1WatchManifest } from './FM1WatchPanel'
import { MercatorMapPanel, mercatorMapManifest } from './MercatorMapPanel'
import { ShortInterest, shortInterestManifest } from './ShortInterest'
import { CashPosition, cashPositionManifest } from './CashPosition'
import { LaunchCountdown, launchCountdownManifest } from './LaunchCountdown'
import { ActivityFeed, activityFeedManifest } from './ActivityFeed'
import { SignalFeed, signalFeedManifest } from './SignalFeed'
import { RegulatoryStatus, regulatoryStatusManifest } from './RegulatoryStatus'
import { NextEvent, nextEventManifest } from './NextEvent'
import { EarningsLedger, earningsLedgerManifest } from './EarningsLedger'

export const WIDGET_REGISTRY: Record<string, WidgetRegistryEntry> = {
  'telemetry-feed': { component: TelemetryFeed, manifest: telemetryFeedManifest },
  'constellation-progress': { component: ConstellationProgress, manifest: constellationProgressManifest },
  'constellation-matrix': { component: ConstellationMatrix, manifest: constellationMatrixManifest },
  'environment-strip': { component: EnvironmentStrip, manifest: environmentStripManifest },
  'fm1-monitor': { component: FM1Monitor, manifest: fm1MonitorManifest },
  'fm1-watch': { component: FM1WatchPanel, manifest: fm1WatchManifest },
  'mercator-map': { component: MercatorMapPanel, manifest: mercatorMapManifest },
  'short-interest': { component: ShortInterest, manifest: shortInterestManifest },
  'cash-position': { component: CashPosition, manifest: cashPositionManifest },
  'launch-countdown': { component: LaunchCountdown, manifest: launchCountdownManifest },
  'activity-feed': { component: ActivityFeed, manifest: activityFeedManifest },
  'signal-feed': { component: SignalFeed, manifest: signalFeedManifest },
  'regulatory-status': { component: RegulatoryStatus, manifest: regulatoryStatusManifest },
  'next-event': { component: NextEvent, manifest: nextEventManifest },
  'earnings-ledger': { component: EarningsLedger, manifest: earningsLedgerManifest },
}
