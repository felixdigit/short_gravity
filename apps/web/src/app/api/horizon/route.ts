import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

// ---------------------------------------------------------------------------
// Horizon API — Unified timeline of future events
// Aggregates: launches, conjunctions, FCC expirations, FCC docket deadlines, patent expirations, earnings, catalysts
// ---------------------------------------------------------------------------

export interface HorizonEvent {
  id: string
  date: string
  type: 'launch' | 'conjunction' | 'regulatory' | 'patent' | 'earnings' | 'catalyst'
  title: string
  subtitle: string | null
  severity: 'critical' | 'high' | 'medium' | 'low'
  source_table: string
  source_ref: string | null
  /** For catalysts without precise dates — fuzzy period like "Q2 2026" */
  estimated_period?: string
}

// Convert fuzzy period strings to approximate ISO dates for timeline ordering
function estimateDateFromPeriod(period: string | null): string | null {
  if (!period) return null
  const p = period.toUpperCase().trim()

  // "FEB 2026", "MAR 2026", etc.
  const monthYear = p.match(/^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(\d{4})$/)
  if (monthYear) {
    const months: Record<string, string> = { JAN: '01', FEB: '02', MAR: '03', APR: '04', MAY: '05', JUN: '06', JUL: '07', AUG: '08', SEP: '09', OCT: '10', NOV: '11', DEC: '12' }
    return `${monthYear[2]}-${months[monthYear[1]]}-15`
  }

  // "Q1 2026", "Q2 2026", etc.
  const quarterYear = p.match(/^Q([1-4])\s+(\d{4})$/)
  if (quarterYear) {
    const midMonths = ['02', '05', '08', '11']
    return `${quarterYear[2]}-${midMonths[parseInt(quarterYear[1]) - 1]}-15`
  }

  // "H1 2026", "H2 2026"
  const halfYear = p.match(/^H([12])\s+(\d{4})$/)
  if (halfYear) {
    return halfYear[1] === '1' ? `${halfYear[2]}-03-15` : `${halfYear[2]}-09-15`
  }

  // "2026" or "2026-2027"
  const yearOnly = p.match(/^(\d{4})/)
  if (yearOnly) return `${yearOnly[1]}-06-15`

  return null
}

export const revalidate = 900 // 15min cache

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 60 },
  handler: async (request) => {
    const supabase = getAnonClient()
    const days = Math.min(
      parseInt(request.nextUrl.searchParams.get('days') || '90'),
      365
    )
    const typeFilter = request.nextUrl.searchParams.get('type') // optional filter

    const now = new Date().toISOString()
    const horizon = new Date(Date.now() + days * 86400000).toISOString()

    const events: HorizonEvent[] = []

    // Parallel queries
    const queries = []

    // 1. Launches
    if (!typeFilter || typeFilter === 'launch') {
      queries.push(
        supabase
          .from('next_launches')
          .select('id, mission, provider, site, target_date, satellite_count, notes')
          .neq('status', 'LAUNCHED')
          .gte('target_date', now)
          .lte('target_date', horizon)
          .order('target_date', { ascending: true })
          .then(({ data }) => {
            for (const r of data || []) {
              events.push({
                id: `launch-${r.id}`,
                date: r.target_date,
                type: 'launch',
                title: r.mission,
                subtitle: [r.provider, r.site, r.satellite_count ? `${r.satellite_count} sats` : null].filter(Boolean).join(' · '),
                severity: 'critical',
                source_table: 'next_launches',
                source_ref: null,
              })
            }
          })
      )
    }

    // 2. Conjunctions (only high-risk: < 5km or probability > 1e-5)
    if (!typeFilter || typeFilter === 'conjunction') {
      queries.push(
        supabase
          .from('conjunctions')
          .select('cdm_id, tca, min_range_km, collision_probability, sat1_name, sat2_name')
          .gte('tca', now)
          .lte('tca', horizon)
          .order('tca', { ascending: true })
          .limit(50)
          .then(({ data }) => {
            for (const r of data || []) {
              const range = typeof r.min_range_km === 'number' ? r.min_range_km : parseFloat(r.min_range_km)
              const prob = r.collision_probability != null
                ? (typeof r.collision_probability === 'number' ? r.collision_probability : parseFloat(r.collision_probability))
                : 0
              const severity = range < 1 || prob > 1e-4 ? 'critical'
                : range < 5 || prob > 1e-5 ? 'high'
                : range < 20 ? 'medium'
                : 'low'
              events.push({
                id: `conj-${r.cdm_id}`,
                date: r.tca,
                type: 'conjunction',
                title: `Close approach: ${r.sat1_name} ↔ ${r.sat2_name}`,
                subtitle: `${range.toFixed(1)} km · P=${prob.toExponential(1)}`,
                severity,
                source_table: 'conjunctions',
                source_ref: null,
              })
            }
          })
      )
    }

    // 3. FCC license expirations
    if (!typeFilter || typeFilter === 'regulatory') {
      queries.push(
        supabase
          .from('fcc_filings')
          .select('id, file_number, title, expiration_date, filing_type, call_sign')
          .not('expiration_date', 'is', null)
          .gte('expiration_date', now)
          .lte('expiration_date', horizon)
          .order('expiration_date', { ascending: true })
          .then(({ data }) => {
            for (const r of data || []) {
              events.push({
                id: `fcc-exp-${r.id}`,
                date: r.expiration_date,
                type: 'regulatory',
                title: `FCC ${r.filing_type || 'license'} expires: ${r.call_sign || r.file_number}`,
                subtitle: r.title,
                severity: 'high',
                source_table: 'fcc_filings',
                source_ref: r.file_number,
              })
            }
          })
      )
    }

    // 4. Patent expirations
    if (!typeFilter || typeFilter === 'patent') {
      queries.push(
        supabase
          .from('patents')
          .select('id, patent_number, title, expiration_date, status')
          .not('expiration_date', 'is', null)
          .gte('expiration_date', now)
          .lte('expiration_date', horizon)
          .eq('status', 'granted')
          .order('expiration_date', { ascending: true })
          .then(({ data }) => {
            for (const r of data || []) {
              events.push({
                id: `pat-exp-${r.id}`,
                date: r.expiration_date,
                type: 'patent',
                title: `Patent expires: ${r.patent_number}`,
                subtitle: r.title,
                severity: 'medium',
                source_table: 'patents',
                source_ref: r.patent_number,
              })
            }
          })
      )
    }

    // 5. Earnings calls
    if (!typeFilter || typeFilter === 'earnings') {
      queries.push(
        supabase
          .from('earnings_transcripts')
          .select('id, company, fiscal_year, fiscal_quarter, call_date, status')
          .not('call_date', 'is', null)
          .gte('call_date', now.slice(0, 10))
          .lte('call_date', horizon.slice(0, 10))
          .neq('status', 'complete')
          .order('call_date', { ascending: true })
          .then(({ data }) => {
            for (const r of data || []) {
              events.push({
                id: `earnings-${r.id}`,
                date: r.call_date,
                type: 'earnings',
                title: `${r.company} Q${r.fiscal_quarter} FY${r.fiscal_year} Earnings`,
                subtitle: r.status === 'scheduled' ? 'Scheduled' : 'Pending',
                severity: 'critical',
                source_table: 'earnings_transcripts',
                source_ref: null,
              })
            }
          })
      )
    }

    // 6. FCC docket deadlines (comment periods, reply deadlines)
    if (!typeFilter || typeFilter === 'regulatory') {
      queries.push(
        supabase
          .from('fcc_dockets')
          .select('docket_number, title, description, comment_deadline, reply_deadline')
          .or(`comment_deadline.gte.${now},reply_deadline.gte.${now}`)
          .then(({ data }) => {
            for (const r of data || []) {
              if (r.comment_deadline && new Date(r.comment_deadline) >= new Date(now) && new Date(r.comment_deadline) <= new Date(horizon)) {
                events.push({
                  id: `fcc-comment-${r.docket_number}`,
                  date: r.comment_deadline,
                  type: 'regulatory',
                  title: `Docket ${r.docket_number} — Comments due`,
                  subtitle: r.title,
                  severity: 'high',
                  source_table: 'fcc_dockets',
                  source_ref: r.docket_number,
                })
              }
              if (r.reply_deadline && new Date(r.reply_deadline) >= new Date(now) && new Date(r.reply_deadline) <= new Date(horizon)) {
                events.push({
                  id: `fcc-reply-${r.docket_number}`,
                  date: r.reply_deadline,
                  type: 'regulatory',
                  title: `Docket ${r.docket_number} — Reply comments due`,
                  subtitle: r.title,
                  severity: 'high',
                  source_table: 'fcc_dockets',
                  source_ref: r.docket_number,
                })
              }
            }
          })
      )
    }

    // 7. Catalysts (curated upcoming events)
    if (!typeFilter || typeFilter === 'catalyst') {
      queries.push(
        supabase
          .from('catalysts')
          .select('id, title, description, category, event_date, estimated_period, status')
          .eq('status', 'upcoming')
          .order('event_date', { ascending: true, nullsFirst: false })
          .then(({ data }) => {
            for (const r of data || []) {
              // Catalysts with precise dates go in the timeline normally
              // Catalysts with only estimated_period are included with a synthetic date
              const date = r.event_date || estimateDateFromPeriod(r.estimated_period)
              const severity = r.category === 'regulatory' || r.category === 'commercial' ? 'high'
                : r.category === 'launch' ? 'critical'
                : 'medium'
              if (date) {
                const dateObj = new Date(date)
                if (dateObj >= new Date(now) && dateObj <= new Date(horizon)) {
                  events.push({
                    id: `catalyst-${r.id}`,
                    date,
                    type: 'catalyst',
                    title: r.title,
                    subtitle: r.description,
                    severity,
                    source_table: 'catalysts',
                    source_ref: null,
                    estimated_period: r.event_date ? undefined : r.estimated_period || undefined,
                  })
                }
              }
            }
          })
      )
    }

    await Promise.all(queries)

    // Sort all events chronologically
    events.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

    return NextResponse.json({
      data: events,
      count: events.length,
      horizon: { from: now, to: horizon, days },
    })
  },
})
