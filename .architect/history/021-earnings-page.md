TARGET: apps/web
---
MISSION:
Build the /earnings page showing earnings call transcripts and financial context. The API route at /api/earnings/context exists (table name will be fixed by mandate 017).

DIRECTIVES:

## 1. Read the existing API

Read `src/app/api/earnings/context/route.ts` to understand the response shape. It queries the `earnings_transcripts` table (note: mandate 017 fixes the table name from `earnings_calls`).

Also read the EarningsLedger widget at `src/components/hud/widgets/EarningsLedger.tsx` to understand how it fetches and displays earnings data.

## 2. Create a useEarnings hook if not already present

Create `src/lib/hooks/useEarnings.ts`:

```ts
'use client'

import { useQuery } from '@tanstack/react-query'

export interface EarningsTranscript {
  id: string
  company: string
  fiscalYear: string | number
  fiscalQuarter: string
  date?: string | null
  summary?: string | null
  keyMetrics?: Record<string, unknown>
}

interface EarningsResponse {
  transcripts: EarningsTranscript[]
  count: number
}

export function useEarnings(company: string = 'ASTS') {
  return useQuery<EarningsResponse>({
    queryKey: ['earnings', company],
    queryFn: async () => {
      const res = await fetch(`/api/earnings/context?company=${company}`)
      if (!res.ok) throw new Error('Failed to fetch earnings')
      return res.json()
    },
    staleTime: 30 * 60 * 1000,
  })
}
```

IMPORTANT: Read the actual API response and adjust interfaces to match. The API may return fields differently.

## 3. Create the /earnings page

Create `src/app/earnings/page.tsx`:

Build a page that shows:
- Header: "EARNINGS" with transcript count
- Stock price context (use useStockPrice hook if it exists, or the /api/stock/ASTS endpoint)
- List of earnings transcripts sorted by most recent
- Each transcript card shows: fiscal quarter/year, date, summary or key excerpts
- If transcript has full content, show expandable sections
- Dark theme (bg-[#030305], font-mono)
- Loading and empty states
- Back nav links

## 4. Run `npx tsc --noEmit`
