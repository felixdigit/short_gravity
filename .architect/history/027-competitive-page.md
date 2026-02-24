TARGET: apps/web
---
MISSION:
Build the /competitive page (War Room) — D2C satellite landscape comparison showing AST SpaceMobile vs competitors.

DIRECTIVES:

## 1. Create the competitive API route

Create `src/app/api/competitive/route.ts`:

This aggregates competitor data from existing tables — FCC filings with competitor docket activity, competitor patent grants, and static company profiles.

```ts
import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const dynamic = 'force-dynamic'

// Static competitor profiles (these don't change often)
const COMPETITORS = [
  {
    company: 'AST SpaceMobile',
    ticker: 'ASTS',
    approach: 'Direct-to-cell via massive phased arrays (64-225m²)',
    constellation: '5 Block 1 + 1 Block 2 (of 168 planned)',
    spectrum: 'Licensed MNO spectrum (AT&T, Vodafone, Rakuten)',
    status: 'Operational testing',
  },
  {
    company: 'SpaceX / T-Mobile',
    ticker: null,
    approach: 'Starlink v2 mini with D2C capability',
    constellation: '840+ D2C-capable satellites launched',
    spectrum: 'T-Mobile PCS spectrum (1900 MHz)',
    status: 'Text messaging beta',
  },
  {
    company: 'Lynk Global',
    ticker: null,
    approach: 'Small satellites, text/SMS focus',
    constellation: '6 satellites',
    spectrum: 'MNO partnerships (multiple)',
    status: 'Limited commercial service',
  },
  {
    company: 'Apple / Globalstar',
    ticker: 'GSAT',
    approach: 'Emergency SOS via Globalstar constellation',
    constellation: '24 Globalstar satellites',
    spectrum: 'S-band (licensed to Globalstar)',
    status: 'Emergency SOS live on iPhone',
  },
]

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 30 },
  handler: async () => {
    const supabase = getAnonClient()

    // Fetch competitor-related signals
    const { data: signals } = await supabase
      .from('signals')
      .select('id, signal_type, severity, title, detected_at')
      .in('signal_type', ['competitor_docket_activity', 'competitor_fcc_grant', 'competitor_patent_grant'])
      .order('detected_at', { ascending: false })
      .limit(10)

    return NextResponse.json({
      competitors: COMPETITORS,
      recentActivity: signals || [],
    })
  },
})
```

## 2. Create the /competitive page

Create `src/app/competitive/page.tsx`:

Page structure:
- Header: "WAR ROOM" or "COMPETITIVE LANDSCAPE"
- Comparison table/grid:
  - Rows: Each competitor (AST, SpaceX/T-Mobile, Lynk, Apple/Globalstar)
  - Columns: Approach, Constellation, Spectrum, Status
  - AST row highlighted (border-[#FF6B35]/20 or similar)
- RECENT COMPETITOR ACTIVITY section:
  - Signal cards for competitor-related signals
  - Type badges: COMP FCC, COMP PATENT, COMP DOCKET
- Key differentiator callout:
  - AST's massive phased array vs others' small satellite approach
  - Broadband data vs SMS-only capability
- Dark theme, font-mono
- Back nav links

## 3. Run `npx tsc --noEmit`
