import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const dynamic = 'force-dynamic'

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 60 },
  handler: async (request, ctx) => {
    const supabase = getAnonClient()
    const { noradId } = await ctx!.params

    if (!/^\d+$/.test(noradId)) {
      return NextResponse.json({ error: 'Invalid NORAD ID' }, { status: 400 })
    }

    const { data, error } = await supabase
      .from('satellites')
      .select('norad_id, name, tle_line0, tle_line1, tle_line2, tle_epoch, tle_source, inclination, ra_of_asc_node, bstar, eccentricity, mean_motion, mean_motion_dot, period_minutes, apoapsis_km, periapsis_km, updated_at')
      .eq('norad_id', noradId)
      .single()

    if (error || !data) {
      return NextResponse.json(
        { error: `Satellite ${noradId} not found` },
        { status: 404 }
      )
    }

    const sf = (v: unknown): number | null => {
      if (v == null || v === '') return null
      const n = parseFloat(String(v))
      return isNaN(n) ? null : n
    }

    const apoapsis = sf(data.apoapsis_km)
    const periapsis = sf(data.periapsis_km)

    return NextResponse.json({
      noradId: data.norad_id,
      name: data.name,
      tle: data.tle_line1 && data.tle_line2 ? {
        line0: data.tle_line0 || `0 ${data.name}`,
        line1: data.tle_line1,
        line2: data.tle_line2,
        epoch: data.tle_epoch,
        bstar: sf(data.bstar),
      } : null,
      metadata: {
        orbit: {
          inclination: sf(data.inclination),
          raan: sf(data.ra_of_asc_node),
          eccentricity: sf(data.eccentricity),
          apogee: apoapsis,
          perigee: periapsis,
        },
      },
      freshness: {
        tleEpoch: data.tle_epoch,
        updatedAt: data.updated_at,
        hoursOld: data.tle_epoch
          ? (Date.now() - new Date(data.tle_epoch).getTime()) / (1000 * 60 * 60)
          : null,
        source: data.tle_source || 'unknown',
      },
    })
  },
})
