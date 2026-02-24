TARGET: apps/web
---
MISSION:
Build the /regulatory page — FCC battlemap showing satellite licenses, earth stations, ICFS applications, and docket activity.

DIRECTIVES:

## 1. Read existing data sources

Read these to understand available data:
- `src/app/api/widgets/regulatory/route.ts` — widget data (summary stats)
- `src/components/hud/widgets/RegulatoryStatus.tsx` — how the widget displays regulatory data
- Check if there's a `useRegulatoryStatus` hook

The widget already shows: SAT LICENSES (19/240 GRANTED), EARTH STATIONS (315/594 GRANTED), ICFS TOTAL (1301 APPLICATIONS). The page should show much more detail.

## 2. Create an expanded regulatory API route

Create `src/app/api/regulatory/filings/route.ts`:

```ts
import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 30 },
  handler: async (request) => {
    const supabase = getAnonClient()
    const system = request.nextUrl.searchParams.get('system') // ICFS, ECFS, ELS
    const limit = Math.min(parseInt(request.nextUrl.searchParams.get('limit') || '50'), 200)

    let query = supabase
      .from('fcc_filings')
      .select('id, filing_system, file_number, title, status, filed_date, description, applicant, created_at')
      .order('filed_date', { ascending: false })
      .limit(limit)

    if (system) {
      query = query.eq('filing_system', system)
    }

    const { data, error } = await query
    if (error) throw error

    return NextResponse.json({
      filings: data || [],
      count: data?.length || 0,
    })
  },
})
```

IMPORTANT: Check the actual `fcc_filings` table columns. The column names above are guesses — read the schema or check what existing API routes select from this table. Adjust accordingly. Key columns likely include: `id`, `filing_system`, `file_number`, `title`, `status`, `filed_date` or `created_at`.

## 3. Create the /regulatory page

Create `src/app/regulatory/page.tsx`:

Page structure:
- Header: "REGULATORY BATTLEMAP"
- Summary stats section (reuse the widget data pattern):
  - SAT LICENSES: X/Y GRANTED
  - EARTH STATIONS: X/Y GRANTED
  - ICFS APPLICATIONS: N total
- Filter tabs: ALL | ICFS | ECFS | ELS
- Filing list: table or card format showing recent filings
  - Columns: Date, System, File Number, Title, Status, Applicant
  - Status badges: color-coded (granted=green, pending=yellow, denied=red)
- Empty/loading states
- Dark theme, font-mono

Use the existing regulatory widget hook for summary stats, and the new /api/regulatory/filings route for the detailed listing.

## 4. Run `npx tsc --noEmit`
