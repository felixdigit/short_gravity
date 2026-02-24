import { NextRequest } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const dynamic = 'force-dynamic'

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 60 },
  handler: async (request: NextRequest) => {
    const name = request.nextUrl.searchParams.get('name') || ''

    if (name.trim().length < 1) {
      return Response.json({ results: [] })
    }

    const supabase = getAnonClient()
    const { data, error } = await supabase
      .from('satellites')
      .select('norad_id, name, inclination, apoapsis_km, periapsis_km')
      .ilike('name', `%${name.trim()}%`)
      .limit(10)

    if (error) {
      return Response.json({ results: [] })
    }

    const results = (data || []).map((sat: Record<string, unknown>) => ({
      noradId: sat.norad_id,
      name: sat.name,
      inclination: sat.inclination ? parseFloat(String(sat.inclination)) : null,
      altitude: sat.apoapsis_km && sat.periapsis_km
        ? (parseFloat(String(sat.apoapsis_km)) + parseFloat(String(sat.periapsis_km))) / 2
        : null,
    }))

    return Response.json({ results })
  },
})
