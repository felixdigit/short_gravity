import type { ComponentType } from 'react'

export interface WidgetManifest {
  id: string
  name: string
  category: 'data' | 'navigation' | 'engagement'
  panelPreference: 'left' | 'right' | 'either'
  sizing: 'fixed' | 'flexible'
  expandable: boolean
  separator: boolean
}

export interface WidgetSlot {
  widgetId: string
  sizing?: 'fixed' | 'flexible'
}

export interface WidgetRegistryEntry {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  component: ComponentType<any>
  manifest: WidgetManifest
}

export interface LayoutPreset {
  id: string
  name: string
  left: WidgetSlot[]
  right: WidgetSlot[]
}
