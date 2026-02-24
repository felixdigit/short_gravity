TARGET: apps/web
---
MISSION:
Build the /thesis page — a bull/bear thesis builder with CRUD operations backed by the theses table in Supabase.

DIRECTIVES:

## 1. Create thesis API routes

### Create `src/app/api/theses/route.ts` (GET + POST):

```ts
import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const dynamic = 'force-dynamic'

// GET — list all theses
export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 30 },
  handler: async () => {
    const supabase = getAnonClient()
    const { data, error } = await supabase
      .from('theses')
      .select('*')
      .order('created_at', { ascending: false })

    if (error) throw error
    return NextResponse.json({ theses: data || [] })
  },
})

// POST — create a new thesis
export const POST = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 10 },
  handler: async (request) => {
    const body = await request.json()
    const { title, stance, content, tags } = body

    if (!title || !stance || !content) {
      return NextResponse.json({ error: 'title, stance, and content are required' }, { status: 400 })
    }

    if (!['bull', 'bear', 'neutral'].includes(stance)) {
      return NextResponse.json({ error: 'stance must be bull, bear, or neutral' }, { status: 400 })
    }

    const supabase = getAnonClient()
    const { data, error } = await supabase
      .from('theses')
      .insert({ title, stance, content, tags: tags || [] })
      .select()
      .single()

    if (error) throw error
    return NextResponse.json({ thesis: data })
  },
})
```

IMPORTANT: Check the actual `theses` table schema first. Read what columns exist. The columns above (title, stance, content, tags, created_at) are assumed from the architecture reference. Adjust if the schema differs. If the table requires a `user_id` or `session_id`, you may need to generate a session-based ID.

## 2. Create a useTheses hook

Create `src/lib/hooks/useTheses.ts`:

```ts
'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

interface Thesis {
  id: string
  title: string
  stance: 'bull' | 'bear' | 'neutral'
  content: string
  tags?: string[]
  created_at: string
}

export function useTheses() {
  return useQuery<{ theses: Thesis[] }>({
    queryKey: ['theses'],
    queryFn: async () => {
      const res = await fetch('/api/theses')
      if (!res.ok) throw new Error('Failed to fetch theses')
      return res.json()
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useCreateThesis() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (thesis: { title: string; stance: string; content: string; tags?: string[] }) => {
      const res = await fetch('/api/theses', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(thesis),
      })
      if (!res.ok) throw new Error('Failed to create thesis')
      return res.json()
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['theses'] }),
  })
}
```

## 3. Create the /thesis page

Create `src/app/thesis/page.tsx`:

Page structure:
- Header: "THESIS BUILDER"
- Two columns or tabbed view: BULL | BEAR | NEUTRAL
- Existing theses listed as cards with title, stance badge (bull=green, bear=red, neutral=white/40), content preview, timestamp
- "NEW THESIS" button that expands a form:
  - Title input
  - Stance selector (bull/bear/neutral toggle)
  - Content textarea (markdown-friendly)
  - Optional tags input
  - Submit button
- Each thesis card expandable to show full content
- Dark theme, font-mono
- Back nav links

## 4. Run `npx tsc --noEmit`
