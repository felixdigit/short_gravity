TARGET: apps/web
---
MISSION:
Build the /horizon event timeline page. The API route at /api/horizon already exists and returns unified events (launches, conjunctions, regulatory, patents, earnings, catalysts).

DIRECTIVES:

## 1. Read the existing API route

Read `src/app/api/horizon/route.ts` to understand the response shape. It queries multiple tables and returns unified events with fields like: `type`, `title`, `date`, `description`, `source`, `metadata`, etc. Note the exact field names.

## 2. Create a useHorizon hook

Create `src/lib/hooks/useHorizon.ts`:

```ts
'use client'

import { useQuery } from '@tanstack/react-query'

export interface HorizonEvent {
  type: string
  title: string
  date: string
  description?: string | null
  source?: string | null
  metadata?: Record<string, unknown>
}

interface HorizonResponse {
  events: HorizonEvent[]
  count: number
}

export function useHorizon(days: number = 90) {
  return useQuery<HorizonResponse>({
    queryKey: ['horizon', days],
    queryFn: async () => {
      const res = await fetch(`/api/horizon?days=${days}`)
      if (!res.ok) throw new Error('Failed to fetch horizon')
      return res.json()
    },
    staleTime: 15 * 60 * 1000,
  })
}
```

IMPORTANT: Read the actual API response shape and adjust the interfaces to match exactly. The route may return different field names.

## 3. Create the /horizon page

Create `src/app/horizon/page.tsx`:

Build a timeline page that:
- Fetches events via the useHorizon hook
- Groups events by month or week
- Color-codes by event type (launch=green, conjunction=red, regulatory=blue, patent=purple, earnings=amber, catalyst=orange)
- Shows event date, type badge, title, and description
- Dark theme consistent with other pages (bg-[#030305], font-mono, white text)
- Loading state and empty state
- Back nav links to / and /orbital

Event type badge labels:
```
launch → LAUNCH (green)
conjunction → CONJUNCTION (red)
regulatory → REGULATORY (blue)
patent → PATENT (purple)
earnings → EARNINGS (amber)
catalyst → CATALYST (orange)
```

Page structure:
- Header: "EVENT HORIZON" + event count
- Optional filter chips by event type
- Chronological timeline (grouped by month)
- Each event card: [type badge] [date] [title] [description]

## 4. Run `npx tsc --noEmit`
