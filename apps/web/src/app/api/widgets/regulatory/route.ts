import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const revalidate = 3600

interface RegulatoryItem {
  label: string
  value: string
  color: 'green' | 'yellow' | 'blue' | 'red' | 'white'
}

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 60 },
  handler: async () => {
    const supabase = getAnonClient()
    const items: RegulatoryItem[] = []

    // Single query: fetch all ICFS filings with the fields we need for aggregation
    const { data: allFilings, count: icfsTotal } = await supabase
      .from('fcc_filings')
      .select('filing_type, application_status, docket, filed_date', { count: 'exact' })
      .eq('filing_system', 'ICFS')

    const filings = (allFilings || []) as { filing_type: string; application_status: string; docket: string | null; filed_date: string }[]

    // 1. Satellite authorizations (SAT-*)
    const satFilings = filings.filter(f => f.filing_type?.startsWith('SAT-'))
    if (satFilings.length > 0) {
      const granted = satFilings.filter(f =>
        f.application_status === 'Action Taken Public Notice' ||
        f.application_status === 'Action Complete'
      ).length
      items.push({
        label: 'SAT LICENSES',
        value: `${granted}/${satFilings.length} GRANTED`,
        color: granted > 0 ? 'green' : 'yellow',
      })
    }

    // 2. Earth station authorizations (SES-*)
    const sesFilings = filings.filter(f => f.filing_type?.startsWith('SES-'))
    if (sesFilings.length > 0) {
      const granted = sesFilings.filter(f =>
        f.application_status === 'Action Taken Public Notice' ||
        f.application_status === 'Action Complete'
      ).length
      items.push({
        label: 'EARTH STATIONS',
        value: `${granted}/${sesFilings.length} GRANTED`,
        color: granted > 0 ? 'green' : 'yellow',
      })
    }

    // 3. Docket 25-201
    const docket25201 = filings.filter(f => f.docket === '25-201')
    if (docket25201.length > 0) {
      const sorted = docket25201.sort((a, b) => b.filed_date.localeCompare(a.filed_date))
      const d = new Date(sorted[0].filed_date + 'T00:00:00')
      const dateStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }).toUpperCase()
      items.push({
        label: 'DOCKET 25-201',
        value: `${docket25201.length} FILINGS · ${dateStr}`,
        color: 'blue',
      })
    }

    // 4. Total ICFS filings count
    if (icfsTotal != null) {
      items.push({
        label: 'ICFS TOTAL',
        value: `${icfsTotal} APPLICATIONS`,
        color: 'white',
      })
    }

    return NextResponse.json({ items })
  },
})
