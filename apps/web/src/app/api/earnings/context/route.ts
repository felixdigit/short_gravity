/**
 * API Route: Earnings Context
 * GET /api/earnings/context
 *
 * Unified endpoint for the Earnings Command Center.
 * Returns: earnings metadata, transcript, topic analysis, price reaction, guidance.
 *
 * Query params:
 * - quarter: e.g., "2024-Q4" (defaults to latest available)
 */

import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getServiceClient } from '@shortgravity/database'
import { GUIDANCE_ITEMS } from '@/lib/data/guidance'

export const dynamic = 'force-dynamic'
export const revalidate = 300

// Topic extraction (same logic as earnings-diff widget)
const TRACKED_TOPICS = [
  { key: 'satellites', label: 'Satellites', patterns: ['satellite', 'bluebird', 'bluebwalker', 'constellation', 'deployment'] },
  { key: 'revenue', label: 'Revenue', patterns: ['revenue', 'bookings', 'arpu', 'monetization', 'commercial service'] },
  { key: 'partnerships', label: 'Partnerships', patterns: ['partner', 'mno', 'operator', 'at&t', 'verizon', 'vodafone', 'subscriber'] },
  { key: 'spectrum', label: 'Spectrum', patterns: ['spectrum', 'frequency', 'mhz', 'l-band', 's-band', 'license'] },
  { key: 'manufacturing', label: 'Manufacturing', patterns: ['manufactur', 'production', 'assembly', 'cadence', 'factory'] },
  { key: 'launches', label: 'Launches', patterns: ['launch', 'spacex', 'isro', 'rocket', 'orbital', 'payload'] },
  { key: 'government', label: 'Government', patterns: ['government', 'defense', 'dod', 'military', 'pentagon', 'contract'] },
  { key: 'cash', label: 'Cash/Funding', patterns: ['cash', 'liquidity', 'burn', 'runway', 'funded', 'convertible', 'atm'] },
  { key: 'coverage', label: 'Coverage', patterns: ['coverage', 'nationwide', 'continuous', 'intermittent', 'service area'] },
  { key: 'technology', label: 'Technology', patterns: ['technology', 'patent', 'beamforming', 'phased array', 'mimo', 'throughput'] },
]

function extractTopicCounts(text: string): Record<string, number> {
  const sentences = text.split(/[.!?]+/).map(s => s.trim()).filter(s => s.length > 20)
  const counts: Record<string, number> = {}
  for (const topic of TRACKED_TOPICS) {
    counts[topic.key] = sentences.filter(s => {
      const lower = s.toLowerCase()
      return topic.patterns.some(p => lower.includes(p))
    }).length
  }
  return counts
}

function parseQuarter(q: string): { year: number; quarter: number } | null {
  const match = q.match(/^(\d{4})-Q([1-4])$/)
  if (!match) return null
  return { year: parseInt(match[1]), quarter: parseInt(match[2]) }
}

function quarterLabel(year: number, quarter: number): string {
  return `${year}-Q${quarter}`
}

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 60 },
  handler: async (request) => {
    const searchParams = request.nextUrl.searchParams
    const quarterParam = searchParams.get('quarter')

    const supabase = getServiceClient()

    // 1. Get all earnings calls (for quarter selector + metadata)
    const { data: earningsCalls, error: ecError } = await supabase
      .from('earnings_transcripts')
      .select('id, company, fiscal_year, fiscal_quarter, call_date, call_time, status, summary, key_points, guidance, notable_quotes')
      .eq('company', 'ASTS')
      .order('call_date', { ascending: false })

    if (ecError) {
      console.error('Earnings calls query error:', ecError)
      return NextResponse.json({ error: 'Database error' }, { status: 500 })
    }

    // Build quarter list
    const quarters = (earningsCalls || []).map((ec: any) => ({
      quarter: quarterLabel(ec.fiscal_year, ec.fiscal_quarter),
      date: ec.call_date,
      status: ec.status,
      fiscal_year: ec.fiscal_year,
      fiscal_quarter: ec.fiscal_quarter,
    }))

    // Determine selected quarter — default to latest with a transcript, not future scheduled
    let selectedQuarter = quarterParam
    if (!selectedQuarter) {
      // Prefer the latest non-scheduled quarter (has actual content)
      const withContent = quarters.find((q: any) => q.status !== 'scheduled')
      selectedQuarter = withContent?.quarter || (quarters.length > 0 ? quarters[0].quarter : null)
    }
    if (!selectedQuarter) {
      return NextResponse.json({ error: 'No earnings data available' }, { status: 404 })
    }

    const parsed = parseQuarter(selectedQuarter)
    if (!parsed) {
      return NextResponse.json({ error: 'Invalid quarter format. Use YYYY-QN' }, { status: 400 })
    }

    // Find the earnings call for this quarter
    const earningsCall = (earningsCalls || []).find(
      (ec: any) => ec.fiscal_year === parsed.year && ec.fiscal_quarter === parsed.quarter
    )

    // 2. Get transcripts from inbox
    const { data: transcripts, error: txError } = await supabase
      .from('inbox')
      .select('title, published_at, content_text, summary, metadata')
      .eq('source', 'earnings_call')
      .not('content_text', 'is', null)
      .order('published_at', { ascending: false })

    if (txError) {
      console.error('Transcript query error:', txError)
    }

    // Match transcript to quarter (by title or metadata)
    const quarterStr = `Q${parsed.quarter}`
    const yearStr = `${parsed.year}`
    const fyStr = `FY${parsed.year}`

    const transcript = (transcripts || []).find((t: any) => {
      const title = (t.title || '').toUpperCase()
      return title.includes(quarterStr) && (title.includes(yearStr) || title.includes(fyStr))
    })

    // 3. Topic analysis across all transcripts (for the matrix)
    const topicMatrix: Array<{
      topic: string
      label: string
      counts: Record<string, number>
    }> = TRACKED_TOPICS.map(t => ({
      topic: t.key,
      label: t.label,
      counts: {},
    }))

    const transcriptQuarters: string[] = []
    for (const t of (transcripts || []) as any[]) {
      // Extract quarter from title
      const title = (t.title || '').toUpperCase()
      const qMatch = title.match(/Q([1-4])/)
      const yMatch = title.match(/(?:FY)?(\d{4})/)
      if (!qMatch || !yMatch) continue

      const q = quarterLabel(parseInt(yMatch[1]), parseInt(qMatch[1]))
      transcriptQuarters.push(q)

      const counts = extractTopicCounts(t.content_text || '')
      for (const tm of topicMatrix) {
        tm.counts[q] = counts[tm.topic] || 0
      }
    }

    // 4. Price reaction (5-day window around earnings date)
    let priceReaction = null
    if (earningsCall?.call_date) {
      const callDate = earningsCall.call_date
      // Get 10 trading days around the earnings date
      const { data: prices } = await supabase
        .from('daily_prices')
        .select('date, open, high, low, close, volume')
        .eq('symbol', 'ASTS')
        .gte('date', new Date(new Date(callDate).getTime() - 14 * 86400000).toISOString().split('T')[0])
        .lte('date', new Date(new Date(callDate).getTime() + 14 * 86400000).toISOString().split('T')[0])
        .order('date', { ascending: true })

      if (prices && prices.length > 0) {
        // Find the earnings date index (closest trading day)
        const callTime = new Date(callDate).getTime()
        let earningsIdx = 0
        let minDiff = Infinity
        for (let i = 0; i < prices.length; i++) {
          const diff = Math.abs(new Date(prices[i].date).getTime() - callTime)
          if (diff < minDiff) { minDiff = diff; earningsIdx = i }
        }

        // 5-day window: 2 before + earnings day + 2 after
        const start = Math.max(0, earningsIdx - 2)
        const end = Math.min(prices.length, earningsIdx + 3)
        const window = prices.slice(start, end).map((p: any) => ({
          date: p.date,
          close: parseFloat(p.close),
          volume: parseInt(p.volume || '0'),
          isEarningsDate: Math.abs(new Date(p.date).getTime() - callTime) < 86400000,
        }))

        // Compute reaction
        const preClose = earningsIdx > 0 ? parseFloat(prices[earningsIdx - 1]?.close || '0') : null
        const earningsClose = parseFloat(prices[earningsIdx]?.close || '0')
        const postClose = earningsIdx < prices.length - 1 ? parseFloat(prices[earningsIdx + 1]?.close || '0') : null

        // Average 30-day volume for spike factor
        const allVols = prices.map((p: any) => parseInt(p.volume || '0'))
        const avgVol = allVols.reduce((a: number, b: number) => a + b, 0) / allVols.length
        const earningsVol = parseInt(prices[earningsIdx]?.volume || '0')

        priceReaction = {
          preClose,
          earningsClose,
          postClose,
          deltaPct: preClose ? Number((((postClose || earningsClose) - preClose) / preClose * 100).toFixed(2)) : null,
          volumeSpikeFactor: avgVol > 0 ? Number((earningsVol / avgVol).toFixed(1)) : null,
          window,
        }
      }
    }

    // 5. Guidance items relevant to this quarter
    const guidanceActive = GUIDANCE_ITEMS.filter(g =>
      g.quarter_due === selectedQuarter && g.status === 'PENDING'
    )
    const guidanceResolved = GUIDANCE_ITEMS.filter(g =>
      g.quarter_due === selectedQuarter && g.status !== 'PENDING'
    )
    const guidanceAll = GUIDANCE_ITEMS

    return NextResponse.json({
      meta: {
        quarter: selectedQuarter,
        date: earningsCall?.call_date || null,
        time: earningsCall?.call_time || null,
        status: earningsCall?.status || null,
        fiscal_year: parsed.year,
        fiscal_quarter: parsed.quarter,
      },
      quarters,
      transcript: transcript ? {
        title: (transcript as any).title,
        date: (transcript as any).published_at,
        text: (transcript as any).content_text,
        summary: (transcript as any).summary || earningsCall?.summary || null,
        wordCount: ((transcript as any).content_text || '').split(/\s+/).length,
      } : null,
      topicMatrix: topicMatrix.map(tm => ({
        topic: tm.topic,
        label: tm.label,
        counts: tm.counts,
        currentCount: tm.counts[selectedQuarter] || 0,
      })),
      transcriptQuarters: Array.from(new Set(transcriptQuarters)).sort().reverse(),
      priceReaction,
      guidance: {
        active: guidanceActive,
        resolved: guidanceResolved,
        all: guidanceAll,
      },
      lastUpdated: new Date().toISOString(),
    })
  },
})
