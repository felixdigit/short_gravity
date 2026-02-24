/**
 * Daily Brief Cron
 * POST /api/cron/daily-brief
 *
 * Sends a morning intelligence email to all active subscribers.
 * Queries last 24h signals, next 48h horizon events, recent filings,
 * and ASTS price. Renders via React Email, sends via Resend.
 *
 * Triggered by Vercel cron at 12:00 UTC (7 AM ET).
 */

import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getServiceClient } from '@/lib/supabase'
import { Resend } from 'resend'
import { render } from '@react-email/components'
import DailyBrief from '@/emails/DailyBrief'

export const dynamic = 'force-dynamic'
export const maxDuration = 30

const resend = new Resend(process.env.RESEND_API_KEY)

export const POST = createApiHandler({
  auth: 'cron',
  handler: async () => {
    const supabase = getServiceClient()
    const now = new Date()
    const twentyFourHoursAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString()
    const fortyEightHoursAhead = new Date(now.getTime() + 48 * 60 * 60 * 1000).toISOString()
    const todayStr = now.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })

    // Parallel data queries
    const [signalsRes, horizonRes, filingsRes, priceRes, subscribersRes] = await Promise.all([
      // Top signals from last 24h
      supabase
        .from('signals')
        .select('severity, title, signal_type, detected_at')
        .gte('detected_at', twentyFourHoursAgo)
        .order('severity', { ascending: true }) // critical first (alphabetical: critical < high < medium)
        .limit(5),

      // Horizon events in next 48h (use the horizon API logic inline)
      supabase
        .from('next_launches')
        .select('mission, target_date')
        .neq('status', 'LAUNCHED')
        .gte('target_date', now.toISOString())
        .lte('target_date', fortyEightHoursAhead)
        .order('target_date', { ascending: true })
        .limit(5),

      // Filing count in last 24h
      supabase
        .from('filings')
        .select('id', { count: 'exact', head: true })
        .gte('filing_date', twentyFourHoursAgo.slice(0, 10)),

      // ASTS price (latest)
      supabase
        .from('daily_prices')
        .select('close, open, date')
        .eq('symbol', 'ASTS')
        .order('date', { ascending: false })
        .limit(2),

      // Active subscribers who want daily briefs
      supabase
        .from('subscribers')
        .select('email, unsubscribe_token')
        .eq('status', 'active')
        .eq('daily_brief', true),
    ])

    const signals = signalsRes.data || []

    // Build horizon events from multiple sources
    const horizonEvents: Array<{ type: string; title: string; date: string; severity: string }> = []

    // Launches
    for (const l of horizonRes.data || []) {
      horizonEvents.push({ type: 'launch', title: l.mission, date: l.target_date, severity: 'critical' })
    }

    // Also check earnings transcripts, catalysts, and dockets in the 48h window
    // FIX: earnings_calls -> earnings_transcripts (the correct table name)
    // FIX: catalysts query handles empty results gracefully (table may have zero rows)
    const [earningsRes, catalystsRes, docketsRes] = await Promise.all([
      supabase
        .from('earnings_transcripts')
        .select('company, fiscal_year, fiscal_quarter, call_date')
        .gte('call_date', now.toISOString().slice(0, 10))
        .lte('call_date', fortyEightHoursAhead.slice(0, 10)),
      supabase
        .from('catalysts')
        .select('title, event_date')
        .eq('status', 'upcoming')
        .not('event_date', 'is', null)
        .gte('event_date', now.toISOString().slice(0, 10))
        .lte('event_date', fortyEightHoursAhead.slice(0, 10)),
      supabase
        .from('fcc_dockets')
        .select('docket_number, title, comment_deadline, reply_deadline')
        .or(`comment_deadline.gte.${now.toISOString()},reply_deadline.gte.${now.toISOString()}`)
        .or(`comment_deadline.lte.${fortyEightHoursAhead},reply_deadline.lte.${fortyEightHoursAhead}`),
    ])

    // Earnings (handle empty/error gracefully)
    if (earningsRes.data && earningsRes.data.length > 0) {
      for (const e of earningsRes.data) {
        horizonEvents.push({
          type: 'earnings',
          title: `${e.company} Q${e.fiscal_quarter} FY${e.fiscal_year} Earnings`,
          date: e.call_date,
          severity: 'critical',
        })
      }
    }

    // Catalysts (handle empty/error gracefully — table may have zero rows)
    if (catalystsRes.data && catalystsRes.data.length > 0) {
      for (const c of catalystsRes.data) {
        horizonEvents.push({ type: 'catalyst', title: c.title, date: c.event_date, severity: 'high' })
      }
    }

    // Dockets (handle empty/error gracefully)
    if (docketsRes.data && docketsRes.data.length > 0) {
      for (const d of docketsRes.data) {
        if (d.comment_deadline && new Date(d.comment_deadline) >= now && new Date(d.comment_deadline) <= new Date(fortyEightHoursAhead)) {
          horizonEvents.push({ type: 'regulatory', title: `Docket ${d.docket_number} — Comments due`, date: d.comment_deadline, severity: 'high' })
        }
        if (d.reply_deadline && new Date(d.reply_deadline) >= now && new Date(d.reply_deadline) <= new Date(fortyEightHoursAhead)) {
          horizonEvents.push({ type: 'regulatory', title: `Docket ${d.docket_number} — Reply comments due`, date: d.reply_deadline, severity: 'high' })
        }
      }
    }

    // Sort horizon events by date
    horizonEvents.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

    const newFilingsCount = filingsRes.count || 0

    // Price data
    let price: { close: number; change: number; changePercent: number } | null = null
    const prices = priceRes.data || []
    if (prices.length >= 2) {
      const latest = prices[0]
      const prev = prices[1]
      const change = latest.close - prev.close
      price = {
        close: latest.close,
        change,
        changePercent: prev.close ? (change / prev.close) * 100 : 0,
      }
    } else if (prices.length === 1) {
      const latest = prices[0]
      const change = latest.close - latest.open
      price = {
        close: latest.close,
        change,
        changePercent: latest.open ? (change / latest.open) * 100 : 0,
      }
    }

    // Get subscribers
    const subscribers = subscribersRes.data || []
    if (subscribers.length === 0) {
      return NextResponse.json({
        success: true,
        message: 'No active subscribers',
        data: { signals: signals.length, horizonEvents: horizonEvents.length, newFilingsCount },
      })
    }

    // Send per-subscriber (each gets their own unsubscribe URL)
    const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://shortgravity.com'
    let sent = 0
    let failed = 0

    const batchSize = 100
    for (let i = 0; i < subscribers.length; i += batchSize) {
      const batch = subscribers.slice(i, i + batchSize)
      try {
        const messages = await Promise.all(
          batch.map(async (s: { email: string; unsubscribe_token: string }) => {
            const unsubscribeUrl = s.unsubscribe_token
              ? `${baseUrl}/api/email/unsubscribe?token=${s.unsubscribe_token}&type=daily_brief`
              : undefined
            const html = await render(
              DailyBrief({
                date: todayStr,
                price,
                signals,
                horizonEvents,
                newFilingsCount,
                unsubscribeUrl,
              })
            )
            return {
              from: process.env.RESEND_FROM_EMAIL || 'Short Gravity <updates@shortgravity.com>',
              to: s.email,
              subject: `Daily Brief — ${todayStr}`,
              html,
            }
          })
        )
        await resend.batch.send(messages)
        sent += batch.length
      } catch (err) {
        console.error('[DAILY BRIEF] Batch send error:', err)
        failed += batch.length
      }
    }

    console.log(`[DAILY BRIEF] Sent ${sent}, failed ${failed}. Signals: ${signals.length}, Horizon: ${horizonEvents.length}, Filings: ${newFilingsCount}`)

    return NextResponse.json({
      success: true,
      sent,
      failed,
      data: {
        signals: signals.length,
        horizonEvents: horizonEvents.length,
        newFilingsCount,
        price: price ? `$${price.close.toFixed(2)}` : null,
      },
    })
  },
})

export const GET = POST
