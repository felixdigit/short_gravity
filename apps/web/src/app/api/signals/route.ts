import { NextRequest, NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const revalidate = 300

/**
 * GET /api/signals
 *
 * Returns signals from the Supabase `signals` table in the shape
 * expected by the useSignals hook and SignalFeed widget.
 */
export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 60 },
  handler: async (req: NextRequest) => {
    const params = req.nextUrl.searchParams
    const severity = params.get('severity')
    const type = params.get('type')
    const limit = Number(params.get('limit') ?? 50)
    const offset = Number(params.get('offset') ?? 0)

    const supabase = getAnonClient()

    let query = supabase
      .from('signals')
      .select(
        'id, signal_type, severity, category, title, description, source_table, source_id, entity_name, observed_value, baseline_value, z_score, raw_data, fingerprint, detected_at, expires_at, created_at',
        { count: 'exact' },
      )
      .or('expires_at.is.null,expires_at.gt.now()')
      .order('detected_at', { ascending: false })

    if (severity) query = query.eq('severity', severity)
    if (type) query = query.eq('signal_type', type)

    query = query.range(offset, offset + limit - 1)

    const { data, count, error } = await query

    if (error) {
      console.error('[/api/signals] Supabase error:', error.message)
      return NextResponse.json({ data: [], count: 0 }, { status: 500 })
    }

    const mapped = (data ?? []).map((row) => ({
      id: row.id,
      signal_type: row.signal_type,
      severity: row.severity,
      category: row.category ?? null,
      title: row.title,
      description: row.description ?? null,
      source_refs: [
        {
          table: row.source_table,
          id: row.source_id ?? String(row.id),
          title: row.entity_name ?? row.title,
          date: row.detected_at,
        },
      ],
      metrics: {
        observed_value: row.observed_value ?? null,
        baseline_value: row.baseline_value ?? null,
        z_score: row.z_score ?? null,
        ...(row.raw_data as Record<string, unknown> | null),
      },
      confidence_score:
        row.z_score != null
          ? Math.min(Math.abs(Number(row.z_score)) / 10, 1)
          : null,
      price_impact_24h: null,
      fingerprint: row.fingerprint,
      detected_at: row.detected_at,
      expires_at: row.expires_at,
      created_at: row.created_at,
    }))

    return NextResponse.json({ data: mapped, count: count ?? mapped.length })
  },
})
