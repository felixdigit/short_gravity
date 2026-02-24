import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const dynamic = 'force-dynamic'

export const GET = createApiHandler({
  handler: async () => {
    const supabase = getAnonClient()

    const { data, error } = await supabase
      .from('source_divergence')
      .select('norad_id, ct_bstar, st_bstar, bstar_delta, diverged, ct_epoch, st_epoch, epoch_gap_hours')

    if (error) {
      // View may not exist yet — return empty gracefully
      if (error.code === '42P01' || error.message?.includes('does not exist')) {
        return NextResponse.json({ satellites: [], error: 'source_divergence view not created yet' })
      }
      throw error
    }

    const satellites = (data || []).map((row: Record<string, unknown>) => ({
      noradId: row.norad_id,
      ctBstar: row.ct_bstar != null ? parseFloat(String(row.ct_bstar)) : null,
      stBstar: row.st_bstar != null ? parseFloat(String(row.st_bstar)) : null,
      bstarDelta: row.bstar_delta != null ? parseFloat(String(row.bstar_delta)) : 0,
      diverged: (row.diverged as boolean) ?? false,
      ctEpoch: row.ct_epoch,
      stEpoch: row.st_epoch,
      epochGapHours: row.epoch_gap_hours != null ? parseFloat(String(row.epoch_gap_hours)) : null,
    }))

    return NextResponse.json({ satellites })
  },
})
