TARGET: apps/web
---
MISSION:
Build the /patents page and supporting API route. The patents table has 307 entries with patent numbers, titles, abstracts, status, jurisdictions, and claims.

DIRECTIVES:

## 1. Create the patents API route

Create `src/app/api/patents/route.ts`:

```ts
import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 30 },
  handler: async (request) => {
    const supabase = getAnonClient()
    const q = request.nextUrl.searchParams.get('q') || ''
    const status = request.nextUrl.searchParams.get('status') || ''
    const limit = Math.min(parseInt(request.nextUrl.searchParams.get('limit') || '50'), 200)
    const offset = parseInt(request.nextUrl.searchParams.get('offset') || '0')

    let query = supabase
      .from('patents')
      .select('id, patent_number, title, abstract, status, filing_date, grant_date, jurisdiction, assignee, inventors, created_at', { count: 'exact' })
      .order('filing_date', { ascending: false })

    if (q.trim()) {
      query = query.or(`title.ilike.%${q}%,abstract.ilike.%${q}%,patent_number.ilike.%${q}%`)
    }

    if (status) {
      query = query.eq('status', status)
    }

    const { data, error, count } = await query.range(offset, offset + limit - 1)
    if (error) throw error

    return NextResponse.json({
      patents: data || [],
      total: count || 0,
    })
  },
})
```

IMPORTANT: Check the actual `patents` table columns first. Read the database schema or check what columns exist. The column names above (patent_number, title, abstract, status, filing_date, grant_date, jurisdiction, assignee, inventors) are from the database reference. Adjust if needed.

## 2. Create a usePatents hook

Create `src/lib/hooks/usePatents.ts`:

```ts
'use client'

import { useQuery } from '@tanstack/react-query'

interface Patent {
  id: string
  patent_number: string
  title: string
  abstract?: string | null
  status: string
  filing_date?: string | null
  grant_date?: string | null
  jurisdiction?: string | null
  assignee?: string | null
}

interface PatentsResponse {
  patents: Patent[]
  total: number
}

export function usePatents(filters: { q?: string; status?: string; limit?: number; offset?: number } = {}) {
  const params = new URLSearchParams()
  if (filters.q) params.set('q', filters.q)
  if (filters.status) params.set('status', filters.status)
  if (filters.limit) params.set('limit', String(filters.limit))
  if (filters.offset) params.set('offset', String(filters.offset))

  return useQuery<PatentsResponse>({
    queryKey: ['patents', filters],
    queryFn: async () => {
      const res = await fetch(`/api/patents?${params}`)
      if (!res.ok) throw new Error('Failed to fetch patents')
      return res.json()
    },
    staleTime: 15 * 60 * 1000,
  })
}
```

## 3. Create the /patents page

Create `src/app/patents/page.tsx`:

Page structure:
- Header: "PATENT PORTFOLIO" + total count (307 patents)
- Search input: text search across titles, abstracts, patent numbers
- Status filter chips: ALL | GRANTED | PENDING | ABANDONED
- Patent list as table or cards:
  - Patent number, title, status badge, filing date, jurisdiction
  - Status colors: granted=green, pending=amber, abandoned=red/50
  - Truncated abstract (2 lines)
- Pagination (load more or offset-based)
- Dark theme, font-mono
- Back nav links

## 4. Run `npx tsc --noEmit`
