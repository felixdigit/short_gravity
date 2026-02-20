import type { WidgetSlot } from '@/components/hud/widgets/types'

export interface LayoutPreset {
  id: string
  name: string
  left: WidgetSlot[]
  right: WidgetSlot[]
}

export const PRESETS: Record<string, LayoutPreset> = {
  default: {
    id: 'default',
    name: 'DEFAULT',
    left: [
      { widgetId: 'constellation-matrix' },
      { widgetId: 'signal-feed', sizing: 'flexible' },
      { widgetId: 'regulatory-status' },
    ],
    right: [
      { widgetId: 'short-interest' },
      { widgetId: 'cash-position' },
      { widgetId: 'next-event' },
      { widgetId: 'earnings-ledger' },
    ],
  },

  'launch-day': {
    id: 'launch-day',
    name: 'LAUNCH DAY',
    left: [
      { widgetId: 'constellation-matrix' },
      { widgetId: 'environment-strip' },
      { widgetId: 'fm1-monitor' },
    ],
    right: [
      { widgetId: 'next-event' },
      { widgetId: 'fm1-watch' },
      { widgetId: 'signal-feed', sizing: 'flexible' },
    ],
  },

  'post-unfold': {
    id: 'post-unfold',
    name: 'POST UNFOLD',
    left: [
      { widgetId: 'constellation-matrix' },
      { widgetId: 'signal-feed', sizing: 'flexible' },
      { widgetId: 'regulatory-status' },
    ],
    right: [
      { widgetId: 'environment-strip' },
      { widgetId: 'fm1-monitor' },
      { widgetId: 'activity-feed', sizing: 'flexible' },
    ],
  },

  'earnings-week': {
    id: 'earnings-week',
    name: 'EARNINGS WEEK',
    left: [
      { widgetId: 'constellation-matrix' },
      { widgetId: 'signal-feed', sizing: 'flexible' },
    ],
    right: [
      { widgetId: 'short-interest' },
      { widgetId: 'cash-position' },
      { widgetId: 'earnings-ledger' },
      { widgetId: 'next-event' },
    ],
  },
}

export function getPreset(id: string): LayoutPreset {
  return PRESETS[id] || PRESETS.default
}
