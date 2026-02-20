export type SignalSeverity = 'critical' | 'high' | 'medium' | 'low'

export interface Signal {
  id: number | string
  title: string
  description?: string
  severity: string
  signal_type: string
  category?: string
  detected_at: string
  price_impact_24h?: number | null
}

export interface WidgetManifest {
  id: string
  name: string
  category?: string
  sizing?: 'fixed' | 'flexible'
  separator?: boolean
}
