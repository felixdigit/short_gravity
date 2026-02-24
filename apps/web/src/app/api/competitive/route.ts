import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const revalidate = 900

const COMPETITORS = [
  {
    company: 'AST SpaceMobile',
    ticker: 'ASTS',
    approach: 'Direct-to-cell via massive phased arrays (64-225m²)',
    constellation: '5 Block 1 + 1 Block 2 (of 168 planned)',
    spectrum: 'Licensed MNO spectrum (AT&T, Vodafone, Rakuten)',
    status: 'Operational testing',
    highlight: true,
  },
  {
    company: 'SpaceX / T-Mobile',
    ticker: null,
    approach: 'Starlink v2 mini with D2C capability',
    constellation: '840+ D2C-capable satellites launched',
    spectrum: 'T-Mobile PCS spectrum (1900 MHz)',
    status: 'Text messaging beta',
    highlight: false,
  },
  {
    company: 'Lynk Global',
    ticker: null,
    approach: 'Small satellites, text/SMS focus',
    constellation: '6 satellites',
    spectrum: 'MNO partnerships (multiple)',
    status: 'Limited commercial service',
    highlight: false,
  },
  {
    company: 'Apple / Globalstar',
    ticker: 'GSAT',
    approach: 'Emergency SOS via Globalstar constellation',
    constellation: '24 Globalstar satellites',
    spectrum: 'S-band (licensed to Globalstar)',
    status: 'Emergency SOS live on iPhone',
    highlight: false,
  },
]

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 30 },
  handler: async () => {
    const supabase = getAnonClient()

    const { data: signals } = await supabase
      .from('signals')
      .select('id, signal_type, severity, title, detected_at')
      .in('signal_type', [
        'competitor_docket_activity',
        'competitor_fcc_grant',
        'competitor_patent_grant',
      ])
      .order('detected_at', { ascending: false })
      .limit(10)

    return NextResponse.json({
      competitors: COMPETITORS,
      recentActivity: signals || [],
    })
  },
})
