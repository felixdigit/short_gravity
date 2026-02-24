import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const dynamic = 'force-dynamic'

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 30 },
  handler: async (request) => {
    const supabase = getAnonClient()
    const noradIdsParam = request.nextUrl.searchParams.get('noradIds')

    if (!noradIdsParam) {
      return NextResponse.json(
        { error: 'Missing noradIds parameter' },
        { status: 400 }
      )
    }

    const noradIds = noradIdsParam.split(',').map(id => id.trim()).filter(Boolean)

    if (noradIds.length === 0) {
      return NextResponse.json(
        { error: 'No NORAD IDs provided' },
        { status: 400 }
      )
    }

    if (noradIds.length > 20) {
      return NextResponse.json(
        { error: 'Maximum 20 satellites per request' },
        { status: 400 }
      )
    }

    const invalidIds = noradIds.filter(id => !/^\d+$/.test(id))
    if (invalidIds.length > 0) {
      return NextResponse.json(
        { error: `Invalid NORAD IDs: ${invalidIds.join(', ')}` },
        { status: 400 }
      )
    }

    const { data, error } = await supabase
      .from('satellites')
      .select('norad_id, name, tle_line0, tle_line1, tle_line2, tle_epoch, tle_source, inclination, ra_of_asc_node, bstar, eccentricity, mean_motion, mean_motion_dot, period_minutes, apoapsis_km, periapsis_km, updated_at, raw_gp')
      .in('norad_id', noradIds)

    if (error) throw error

    const serverNow = Date.now()

    const sf = (v: unknown): number | null => {
      if (v == null || v === '') return null
      const n = parseFloat(String(v))
      return isNaN(n) ? null : n
    }

    const satellites = (data || [])
      .filter(sat => sat.tle_line1 && sat.tle_line2)
      .map(sat => {
        const apoapsis = sf(sat.apoapsis_km)
        const periapsis = sf(sat.periapsis_km)
        const avgAltitude = apoapsis != null && periapsis != null
          ? (apoapsis + periapsis) / 2
          : null

        return {
          noradId: sat.norad_id,
          name: sat.name,
          tleSource: sat.tle_source || (sat.raw_gp as Record<string, unknown>)?._source || 'unknown',
          tle: {
            line0: sat.tle_line0 || `0 ${sat.name}`,
            line1: sat.tle_line1,
            line2: sat.tle_line2,
            epoch: sat.tle_epoch,
          },
          orbital: {
            inclination: sf(sat.inclination),
            raan: sf(sat.ra_of_asc_node),
            bstar: sf(sat.bstar),
            avgAltitude,
            eccentricity: sf(sat.eccentricity),
            meanMotion: sf(sat.mean_motion),
            meanMotionDot: sf(sat.mean_motion_dot),
            periodMinutes: sf(sat.period_minutes),
            apoapsis,
            periapsis,
          },
          freshness: {
            tleEpoch: sat.tle_epoch,
            updatedAt: sat.updated_at,
            hoursOld: sat.tle_epoch
              ? (serverNow - new Date(sat.tle_epoch).getTime()) / (1000 * 60 * 60)
              : null,
          },
        }
      })

    const foundIds = new Set(satellites.map(s => s.noradId))
    const errors: Record<string, string> = {}
    for (const id of noradIds) {
      if (!foundIds.has(id)) {
        errors[id] = 'Satellite not found in database'
      }
    }

    return NextResponse.json({
      satellites,
      errors: Object.keys(errors).length > 0 ? errors : undefined,
      count: satellites.length,
      source: 'supabase',
      lastUpdated: new Date().toISOString(),
    })
  },
})
