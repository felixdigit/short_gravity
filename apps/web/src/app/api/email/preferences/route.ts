/**
 * Email Preferences
 * GET /api/email/preferences?token=... -> returns current preferences
 * POST /api/email/preferences -> updates preferences
 *
 * Token-based access. No auth required.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getServiceClient } from '@/lib/supabase'

export const dynamic = 'force-dynamic'

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 30 },
  handler: async (req: NextRequest) => {
    const token = req.nextUrl.searchParams.get('token')

    if (!token) {
      return NextResponse.json({ error: 'Missing token' }, { status: 400 })
    }

    const supabase = getServiceClient()

    const { data: subscriber } = await supabase
      .from('subscribers')
      .select('email, status, daily_brief, signal_alerts')
      .eq('unsubscribe_token', token)
      .single()

    if (!subscriber) {
      return NextResponse.json({ error: 'Invalid token' }, { status: 404 })
    }

    return NextResponse.json({ success: true, preferences: subscriber })
  },
})

export const POST = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 10 },
  handler: async (req: NextRequest) => {
    const body = await req.json()
    const { token, daily_brief, signal_alerts } = body

    if (!token) {
      return NextResponse.json({ error: 'Missing token' }, { status: 400 })
    }

    const supabase = getServiceClient()

    const { data: subscriber } = await supabase
      .from('subscribers')
      .select('id')
      .eq('unsubscribe_token', token)
      .single()

    if (!subscriber) {
      return NextResponse.json({ error: 'Invalid token' }, { status: 404 })
    }

    const update: Record<string, unknown> = {}
    if (typeof daily_brief === 'boolean') update.daily_brief = daily_brief
    if (typeof signal_alerts === 'boolean') update.signal_alerts = signal_alerts

    if (Object.keys(update).length === 0) {
      return NextResponse.json({ error: 'No preferences to update' }, { status: 400 })
    }

    await supabase
      .from('subscribers')
      .update(update)
      .eq('id', subscriber.id)

    return NextResponse.json({ success: true, updated: update })
  },
})
