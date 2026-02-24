import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const revalidate = 900

export const GET = createApiHandler({
  handler: async (request) => {
    const supabase = getAnonClient()
    const days = Math.min(
      parseInt(request.nextUrl.searchParams.get('days') || '14'),
      90
    )

    const cutoffDate = new Date(Date.now() - days * 86400000).toISOString()
    const noradId = request.nextUrl.searchParams.get('norad_id')

    let query = supabase
      .from('conjunctions')
      .select('cdm_id, tca, min_range_km, collision_probability, sat1_name, sat2_name, sat1_norad, sat2_norad, created_at')
      .gte('tca', cutoffDate)

    if (noradId) {
      query = query.or(`sat1_norad.eq.${noradId},sat2_norad.eq.${noradId}`)
    }

    const { data, error } = await query
      .order('tca', { ascending: true })
      .limit(100)

    if (error) throw error

    const results = (data || []).map(row => ({
      cdmId: row.cdm_id,
      tca: row.tca,
      minRange: row.min_range_km != null ? parseFloat(String(row.min_range_km)) : null,
      probability: row.collision_probability != null ? parseFloat(String(row.collision_probability)) : null,
      sat1: row.sat1_name,
      sat2: row.sat2_name,
      sat1Norad: row.sat1_norad ?? null,
      sat2Norad: row.sat2_norad ?? null,
    }))

    return NextResponse.json({
      data: results,
      count: results.length,
      lastUpdated: new Date().toISOString(),
    })
  },
})
