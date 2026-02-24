// Utility
export { cn } from './lib/utils'

// Types
export type { SignalSeverity, Signal, WidgetManifest } from './types'

// Primitives
export { Panel } from './components/primitives/Panel'
export { Text, Label, Value, Muted } from './components/primitives/Text'
export { Stat } from './components/primitives/Stat'
export { StatusDot } from './components/primitives/StatusDot'
export { LoadingState, Skeleton } from './components/primitives/LoadingState'
export { ProgressBar } from './components/primitives/ProgressBar'

// Chart Primitives
export { Crosshair } from './components/primitives/chart/Crosshair'
export { HairlinePath } from './components/primitives/chart/HairlinePath'
export { ValueReadout } from './components/primitives/chart/ValueReadout'
export { CornerBrackets } from './components/primitives/chart/CornerBrackets'
export { Baseline } from './components/primitives/chart/Baseline'
export { GhostTrend } from './components/primitives/chart/GhostTrend'

// UI Components
export { Badge } from './components/ui/Badge'
export { Card, CardHeader, CardTitle, CardContent } from './components/ui/Card'
export { ErrorBoundary } from './components/ui/ErrorBoundary'
export { FocusPanelProvider, useFocusPanelContext } from './components/ui/FocusPanelContext'
export { WidgetHost } from './components/ui/WidgetHost'

// HUD Layout
export { HUDLayout, useHUDLayout } from './components/hud/HUDLayout'

// Brand
export { LogoMark } from './components/brand/LogoMark'

// Signals
export { SignalCard } from './components/signals/SignalCard'

// Globe3D — NOT re-exported from barrel to avoid SSR crash.
// Import via subpath: '@shortgravity/ui/components/earth/Globe3D'
export type { SatelliteData } from './components/earth/Globe3D'
