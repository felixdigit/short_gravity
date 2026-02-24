import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const revalidate = 1800 // 30min cache

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 60 },
  handler: async () => {
    const supabase = getAnonClient()

    const { data, error } = await supabase
      .from('next_launches')
      .select('mission, provider, site, target_date, status, satellite_count, notes')
      .neq('status', 'LAUNCHED')
      .order('target_date', { ascending: true })
      .limit(1)

    if (error || !data || data.length === 0) {
      return NextResponse.json({ launch: null })
    }

    const launch = data[0] as any
    return NextResponse.json({
      launch: {
        mission: launch.mission,
        provider: launch.provider,
        site: launch.site,
        targetDate: launch.target_date,
        status: launch.status,
        satelliteCount: launch.satellite_count,
        notes: launch.notes,
      },
    })
  },
})
