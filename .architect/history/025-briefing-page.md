TARGET: apps/web
---
MISSION:
Build the /briefing page — a daily intelligence summary synthesized from recent signals, filings, satellite health, and market data.

DIRECTIVES:

## 1. Create the briefing API route

Create `src/app/api/briefing/route.ts`:

This route aggregates data from multiple sources into a structured briefing:

```ts
import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const dynamic = 'force-dynamic'

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 10 },
  handler: async () => {
    const supabase = getAnonClient()
    const now = new Date()
    const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString()
    const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString()

    // Parallel data fetches
    const [signalsRes, filingRes, satRes, weatherRes, priceRes] = await Promise.all([
      // Recent signals (24h)
      supabase.from('signals').select('id, signal_type, severity, title, detected_at')
        .gte('detected_at', oneDayAgo)
        .order('detected_at', { ascending: false })
        .limit(10),

      // Recent filings (7d)
      supabase.from('filings').select('id, form_type, title, filed_date')
        .gte('filed_date', oneWeekAgo)
        .order('filed_date', { ascending: false })
        .limit(5),

      // Satellite health
      supabase.from('satellites').select('norad_id, name, tle_epoch, bstar')
        .order('name'),

      // Latest space weather
      supabase.from('space_weather').select('date, f10_7, kp_index, ap_index')
        .order('date', { ascending: false })
        .limit(1),

      // Latest stock price
      supabase.from('daily_prices').select('date, close, volume')
        .eq('symbol', 'ASTS')
        .order('date', { ascending: false })
        .limit(2),
    ])

    return NextResponse.json({
      generated: now.toISOString(),
      sections: {
        signals: {
          count: signalsRes.data?.length || 0,
          items: signalsRes.data || [],
          critical: signalsRes.data?.filter(s => s.severity === 'critical' || s.severity === 'high').length || 0,
        },
        filings: {
          count: filingRes.data?.length || 0,
          items: filingRes.data || [],
        },
        constellation: {
          count: satRes.data?.length || 0,
          satellites: (satRes.data || []).map(s => ({
            name: s.name,
            noradId: s.norad_id,
            tleAge: s.tle_epoch
              ? ((now.getTime() - new Date(s.tle_epoch).getTime()) / (1000 * 60 * 60)).toFixed(1) + 'h'
              : 'N/A',
            bstar: s.bstar,
          })),
        },
        spaceWeather: weatherRes.data?.[0] || null,
        market: {
          latestPrice: priceRes.data?.[0] || null,
          previousPrice: priceRes.data?.[1] || null,
        },
      },
    })
  },
})
```

IMPORTANT: The column names above are guesses. Check the actual table schemas:
- `signals` columns: detected_at, severity, signal_type, title
- `filings` columns: filed_date, form_type, title (might be different)
- `satellites` columns: norad_id, name, tle_epoch, bstar
- `space_weather` columns: date, f10_7 or solar_flux, kp_index or kp, ap_index or ap
- `daily_prices` columns: date, close, volume, symbol

Adjust column names to match what actually exists in the database.

## 2. Create the /briefing page

Create `src/app/briefing/page.tsx`:

Build a structured daily intelligence briefing page:

- Header: "THE BRIEFING" + generation timestamp
- SITUATION section: Signal summary (X active signals, Y critical/high)
- MARKET section: Stock price + change from previous day
- CONSTELLATION section: Satellite health grid (name, TLE age, B*)
- FILINGS section: Recent SEC filings in the last 7 days
- SPACE WEATHER section: Latest solar flux, Kp, Ap
- Each section uses Panel-style borders and the standard dark theme
- Loading and empty states
- Auto-refresh on focus

Style: Think military intelligence briefing aesthetic — structured, scannable, monospace.

## 3. Run `npx tsc --noEmit`
