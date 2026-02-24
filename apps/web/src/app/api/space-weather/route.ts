import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const revalidate = 21600

export const GET = createApiHandler({
  handler: async (request) => {
    const supabase = getAnonClient()
    const days = Math.min(
      parseInt(request.nextUrl.searchParams.get('days') || '90'),
      365
    )

    const { data, error } = await supabase
      .from('space_weather')
      .select('date, kp_sum, ap_avg, f107_obs, f107_adj, f107_center81, sunspot_number, data_type')
      .order('date', { ascending: false })
      .limit(days)

    if (error) throw error

    return NextResponse.json({
      days,
      count: data?.length ?? 0,
      data: data || [],
      lastUpdated: new Date().toISOString(),
    })
  },
})
