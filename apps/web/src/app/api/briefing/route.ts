import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const revalidate = 300

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 10 },
  handler: async () => {
    const supabase = getAnonClient()
    const now = new Date()
    const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString()
    const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString()

    const [signalsRes, filingRes, satRes, weatherRes, priceRes] = await Promise.all([
      supabase
        .from('signals')
        .select('id, signal_type, severity, title, detected_at')
        .gte('detected_at', oneDayAgo)
        .or('expires_at.is.null,expires_at.gt.now()')
        .order('detected_at', { ascending: false })
        .limit(10),

      supabase
        .from('filings')
        .select('id, form, title, filing_date')
        .eq('status', 'completed')
        .gte('filing_date', oneWeekAgo)
        .order('filing_date', { ascending: false })
        .limit(5),

      supabase
        .from('satellites')
        .select('norad_id, name, tle_epoch, bstar')
        .order('name'),

      supabase
        .from('space_weather')
        .select('date, f107_obs, kp_sum, ap_avg, sunspot_number')
        .order('date', { ascending: false })
        .limit(1),

      supabase
        .from('daily_prices')
        .select('date, close, volume')
        .eq('symbol', 'ASTS')
        .order('date', { ascending: false })
        .limit(2),
    ])

    return NextResponse.json({
      generated: now.toISOString(),
      sections: {
        signals: {
          count: signalsRes.data?.length ?? 0,
          items: signalsRes.data ?? [],
          critical:
            signalsRes.data?.filter(
              (s) => s.severity === 'critical' || s.severity === 'high',
            ).length ?? 0,
        },
        filings: {
          count: filingRes.data?.length ?? 0,
          items: filingRes.data ?? [],
        },
        constellation: {
          count: satRes.data?.length ?? 0,
          satellites: (satRes.data ?? []).map((s) => ({
            name: s.name,
            noradId: s.norad_id,
            tleAge: s.tle_epoch
              ? ((now.getTime() - new Date(s.tle_epoch as string).getTime()) / (1000 * 60 * 60)).toFixed(1) + 'h'
              : 'N/A',
            bstar: s.bstar,
          })),
        },
        spaceWeather: weatherRes.data?.[0] ?? null,
        market: {
          latestPrice: priceRes.data?.[0] ?? null,
          previousPrice: priceRes.data?.[1] ?? null,
        },
      },
    })
  },
})
