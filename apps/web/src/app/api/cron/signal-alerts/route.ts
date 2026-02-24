/**
 * Signal Alerts Cron
 * POST /api/cron/signal-alerts
 *
 * Polls for new critical/high severity signals that haven't been alerted yet.
 * Sends individual alert emails to all active subscribers via Resend.
 * Tracks sent alerts in signal_alert_log to prevent duplicate sends.
 *
 * Triggered by Vercel cron every 15 minutes.
 */

import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getServiceClient } from '@/lib/supabase'
import { Resend } from 'resend'
import { render } from '@react-email/components'
import SignalAlert from '@/emails/SignalAlert'

export const dynamic = 'force-dynamic'
export const maxDuration = 30

const resend = new Resend(process.env.RESEND_API_KEY)

export const POST = createApiHandler({
  auth: 'cron',
  handler: async () => {
    const supabase = getServiceClient()

    // Find critical/high signals from the last hour that haven't been alerted
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString()

    const { data: recentSignals } = await supabase
      .from('signals')
      .select('id, fingerprint, severity, title, signal_type, category, description, detected_at, source_refs')
      .in('severity', ['critical', 'high'])
      .gte('detected_at', oneHourAgo)
      .order('detected_at', { ascending: true })

    if (!recentSignals || recentSignals.length === 0) {
      return NextResponse.json({ success: true, message: 'No alertable signals', checked: 0 })
    }

    // Check which have already been alerted
    const fingerprints = recentSignals.map((s: { fingerprint: string }) => s.fingerprint)
    const { data: alreadySent } = await supabase
      .from('signal_alert_log')
      .select('signal_fingerprint')
      .in('signal_fingerprint', fingerprints)

    const sentFingerprints = new Set((alreadySent || []).map((a: { signal_fingerprint: string }) => a.signal_fingerprint))
    const newSignals = recentSignals.filter((s: { fingerprint: string }) => !sentFingerprints.has(s.fingerprint))

    if (newSignals.length === 0) {
      return NextResponse.json({ success: true, message: 'All signals already alerted', checked: recentSignals.length })
    }

    // Get active subscribers who want signal alerts
    const { data: subscribers } = await supabase
      .from('subscribers')
      .select('email, unsubscribe_token')
      .eq('status', 'active')
      .eq('signal_alerts', true)

    if (!subscribers || subscribers.length === 0) {
      return NextResponse.json({ success: true, message: 'No active subscribers for alerts', newSignals: newSignals.length })
    }

    const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://shortgravity.com'
    let totalSent = 0
    let totalFailed = 0

    // Send one email per signal (critical signals deserve individual attention)
    for (const signal of newSignals) {
      try {
        const severityLabel = signal.severity === 'critical' ? 'CRITICAL' : 'HIGH'
        const subject = `${severityLabel} — ${signal.title}`

        // Render per-subscriber for individual unsubscribe URLs
        const batchSize = 100
        for (let i = 0; i < subscribers.length; i += batchSize) {
          const batch = subscribers.slice(i, i + batchSize)
          const messages = await Promise.all(
            batch.map(async (s: { email: string; unsubscribe_token: string }) => {
              const unsubscribeUrl = s.unsubscribe_token
                ? `${baseUrl}/api/email/unsubscribe?token=${s.unsubscribe_token}&type=signal_alerts`
                : undefined
              const html = await render(
                SignalAlert({
                  signal: {
                    severity: signal.severity,
                    title: signal.title,
                    signal_type: signal.signal_type,
                    category: signal.category,
                    description: signal.description,
                    detected_at: signal.detected_at,
                    source_refs: signal.source_refs || [],
                  },
                  unsubscribeUrl,
                })
              )
              return {
                from: process.env.RESEND_FROM_EMAIL || 'Short Gravity <updates@shortgravity.com>',
                to: s.email,
                subject,
                html,
              }
            })
          )
          await resend.batch.send(messages)
        }

        // Log the alert
        await supabase
          .from('signal_alert_log')
          .upsert({
            signal_fingerprint: signal.fingerprint,
            sent_at: new Date().toISOString(),
            recipient_count: subscribers.length,
          }, { onConflict: 'signal_fingerprint' })

        totalSent++
        console.log(`[SIGNAL ALERT] Sent: ${severityLabel} — ${signal.title} to ${subscribers.length} subscribers`)
      } catch (err) {
        console.error(`[SIGNAL ALERT] Failed to send alert for signal ${signal.id}:`, err)
        totalFailed++
      }
    }

    console.log(`[SIGNAL ALERT] ${totalSent} alerts sent, ${totalFailed} failed. ${subscribers.length} subscribers.`)

    return NextResponse.json({
      success: true,
      signalsChecked: recentSignals.length,
      alertsSent: totalSent,
      alertsFailed: totalFailed,
      subscribers: subscribers.length,
    })
  },
})

export const GET = POST
