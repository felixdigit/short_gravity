import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const revalidate = 300

function deriveFreshnessStatus(hoursOld: number): string {
  if (hoursOld < 6) return 'FRESH'
  if (hoursOld < 12) return 'OK'
  if (hoursOld < 24) return 'STALE'
  return 'CRITICAL'
}

export const GET = createApiHandler({
  handler: async () => {
    const supabase = getAnonClient()

    // Try the satellite_freshness view first
    const { data, error } = await supabase
      .from('satellite_freshness')
      .select('norad_id, name, tle_epoch, hours_since_epoch, freshness_status')

    if (!error && data) {
      return NextResponse.json({
        satellites: data.map(sat => ({
          noradId: sat.norad_id,
          name: sat.name,
          tleEpoch: sat.tle_epoch,
          hoursOld: sat.hours_since_epoch != null
            ? Math.round(parseFloat(String(sat.hours_since_epoch)) * 10) / 10
            : null,
          status: sat.freshness_status,
        })),
        count: data.length,
        lastChecked: new Date().toISOString(),
      })
    }

    // Fallback: view doesn't exist (42P01) — query satellites table directly
    if (error && (error.code === '42P01' || error.message?.includes('does not exist'))) {
      const { data: sats, error: fallbackError } = await supabase
        .from('satellites')
        .select('norad_id, name, tle_epoch')

      if (fallbackError) throw fallbackError

      const now = Date.now()
      const satellites = (sats || []).map(sat => {
        const hoursOld = sat.tle_epoch
          ? (now - new Date(sat.tle_epoch).getTime()) / (1000 * 60 * 60)
          : null
        return {
          noradId: sat.norad_id,
          name: sat.name,
          tleEpoch: sat.tle_epoch,
          hoursOld: hoursOld != null ? Math.round(hoursOld * 10) / 10 : null,
          status: hoursOld != null ? deriveFreshnessStatus(hoursOld) : 'CRITICAL',
        }
      })

      return NextResponse.json({
        satellites,
        count: satellites.length,
        lastChecked: new Date().toISOString(),
      })
    }

    // Unexpected error
    if (error) throw error

    return NextResponse.json({ satellites: [], count: 0, lastChecked: new Date().toISOString() })
  },
})
