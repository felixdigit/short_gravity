/**
 * Email Unsubscribe
 * GET /api/email/unsubscribe?token=...&type=all|daily_brief|signal_alerts
 *
 * Token-based unsubscribe. No auth required.
 * - type=all -> sets status='unsubscribed' (stops everything)
 * - type=daily_brief -> sets daily_brief=false
 * - type=signal_alerts -> sets signal_alerts=false
 */

import { NextRequest, NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getServiceClient } from '@/lib/supabase'

export const dynamic = 'force-dynamic'

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://shortgravity.com'

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 10 },
  handler: async (req: NextRequest) => {
    const token = req.nextUrl.searchParams.get('token')
    const type = req.nextUrl.searchParams.get('type') || 'all'

    if (!token) {
      return NextResponse.json({ error: 'Missing token' }, { status: 400 })
    }

    const supabase = getServiceClient()

    // Look up subscriber by token
    const { data: subscriber } = await supabase
      .from('subscribers')
      .select('id, email, status')
      .eq('unsubscribe_token', token)
      .single()

    if (!subscriber) {
      return NextResponse.json({ error: 'Invalid token' }, { status: 404 })
    }

    // Apply unsubscribe action
    let update: Record<string, unknown> = {}
    if (type === 'all') {
      update = { status: 'unsubscribed' }
    } else if (type === 'daily_brief') {
      update = { daily_brief: false }
    } else if (type === 'signal_alerts') {
      update = { signal_alerts: false }
    } else {
      return NextResponse.json({ error: 'Invalid type' }, { status: 400 })
    }

    await supabase
      .from('subscribers')
      .update(update)
      .eq('id', subscriber.id)

    // Return a simple confirmation page
    const action = type === 'all' ? 'unsubscribed from all emails' :
      type === 'daily_brief' ? 'unsubscribed from daily briefs' :
      'unsubscribed from signal alerts'

    return new NextResponse(
      `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width" />
  <title>Unsubscribed — Short Gravity</title>
  <style>
    body { background: #030305; color: #fff; font-family: 'JetBrains Mono', monospace; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
    .box { text-align: center; max-width: 400px; padding: 32px; }
    h1 { font-size: 14px; letter-spacing: 4px; margin-bottom: 24px; }
    p { color: #71717A; font-size: 12px; line-height: 1.6; }
    a { color: #FF6B35; text-decoration: none; }
  </style>
</head>
<body>
  <div class="box">
    <h1>SHORT GRAVITY</h1>
    <p>You have been ${action}.</p>
    <p><a href="${siteUrl}">Return to Terminal</a></p>
  </div>
</body>
</html>`,
      { headers: { 'Content-Type': 'text/html' } }
    )
  },
})
