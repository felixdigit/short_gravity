import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const dynamic = 'force-dynamic'

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 30 },
  handler: async (request, ctx) => {
    const supabase = getAnonClient()
    const { noradId } = await ctx!.params
    const days = Math.min(
      parseInt(request.nextUrl.searchParams.get('days') || '45'),
      180
    )

    const cutoff = new Date(Date.now() - days * 86400000).toISOString()

    // CRITICAL: use source = 'spacetrack' only for BSTAR/drag analysis
    const { data, error } = await supabase
      .from('tle_history')
      .select('epoch, bstar, mean_motion, period_minutes, apoapsis_km, periapsis_km')
      .eq('norad_id', noradId)
      .eq('source', 'spacetrack')
      .gte('epoch', cutoff)
      .order('epoch', { ascending: false })

    if (error) throw error

    if (!data || data.length === 0) {
      return NextResponse.json(
        { error: `No drag history found for NORAD ${noradId}` },
        { status: 404 }
      )
    }

    const sf = (v: unknown): number | null => {
      if (v == null || v === '') return null
      const n = parseFloat(String(v))
      return isNaN(n) ? null : n
    }

    // Reverse to oldest-first for charting
    const dataPoints = data.reverse().map(row => {
      const apoapsis = sf(row.apoapsis_km)
      const periapsis = sf(row.periapsis_km)
      return {
        epoch: row.epoch,
        bstar: sf(row.bstar) ?? 0,
        avgAltitude: apoapsis != null && periapsis != null ? (apoapsis + periapsis) / 2 : null,
        source: 'spacetrack',
      }
    })

    const first = dataPoints[0]
    const last = dataPoints[dataPoints.length - 1]
    const bstarChange = last.bstar - first.bstar
    const bstarChangePercent = first.bstar !== 0
      ? (bstarChange / Math.abs(first.bstar)) * 100
      : null

    return NextResponse.json({
      noradId,
      days,
      dataPoints,
      summary: {
        initialBstar: first.bstar,
        latestBstar: last.bstar,
        bstarChangePercent: bstarChangePercent != null
          ? Math.round(bstarChangePercent * 100) / 100
          : null,
      },
    })
  },
})
