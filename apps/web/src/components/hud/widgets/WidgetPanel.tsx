'use client'

import { WIDGET_REGISTRY } from './registry'
import { WidgetHost } from '@shortgravity/ui'
import type { WidgetSlot } from './types'

interface WidgetPanelProps {
  slots: WidgetSlot[]
}

export function WidgetPanel({ slots }: WidgetPanelProps) {
  return (
    <>
      {slots.map((slot, index) => {
        const entry = WIDGET_REGISTRY[slot.widgetId]
        if (!entry) {
          if (process.env.NODE_ENV === 'development') {
            console.warn(`[WidgetPanel] Unknown widget ID: "${slot.widgetId}"`)
          }
          return null
        }

        const { component: Component, manifest } = entry

        return (
          <WidgetHost key={slot.widgetId} manifest={manifest} sizing={slot.sizing} isFirst={index === 0}>
            <Component />
          </WidgetHost>
        )
      })}
    </>
  )
}
