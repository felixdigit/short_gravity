TARGET: apps/web
---
MISSION:
Replace the CommandPalette stub with a fully functional command palette. Migrate from the V1 archive, create the required search API endpoints, and wire everything together.

DIRECTIVES:

## 1. Read the archive implementation

Read these files from the V1 archive to understand the full implementation:
- `../../_ARCHIVE_V1/short-gravity-web/components/command-palette/types.ts`
- `../../_ARCHIVE_V1/short-gravity-web/components/command-palette/commands.ts`
- `../../_ARCHIVE_V1/short-gravity-web/components/command-palette/useCommandSearch.ts`
- `../../_ARCHIVE_V1/short-gravity-web/components/command-palette/CommandPalette.tsx`

Use these as the reference implementation. Port them to the current codebase with the following adjustments.

## 2. Create types file

Create `src/components/command-palette/types.ts` based on the archive version. This should define:
- `CommandCategory` union type (navigation, preset, action, search, satellite)
- `CommandItem` interface with id, label, category, icon, action, keywords, etc.

## 3. Create commands file

Create `src/components/command-palette/commands.ts` based on the archive. This contains static command definitions for:
- **Navigation commands**: Link to all existing pages (/asts, /orbital, /signals, /satellite/*). For pages that don't exist yet (/briefing, /patents, etc.), either omit them or mark as "coming soon"
- **Preset commands**: Switch between layout presets (default, launch-day, post-unfold, earnings-week)
- **Action commands**: Toggle orbits, toggle coverage, toggle display mode, open brain search

Only include navigation links for pages that ACTUALLY EXIST:
- `/` (HOME)
- `/asts` (TERMINAL)
- `/signals` (SIGNALS)
- `/orbital` (ORBITAL INTELLIGENCE)

For presets, use the store: `useTerminalStore.getState().setActivePreset(presetId)`.
For toggles, use the store actions directly.

## 4. Create search API endpoints

### Create `src/app/api/brain/search/route.ts`:

```ts
import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getServiceClient } from '@shortgravity/database'
import OpenAI from 'openai'

export const dynamic = 'force-dynamic'

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY! })

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 30 },
  handler: async (request) => {
    const q = request.nextUrl.searchParams.get('q')
    const limit = Math.min(parseInt(request.nextUrl.searchParams.get('limit') || '5'), 20)

    if (!q || q.trim().length < 2) {
      return NextResponse.json({ results: [] })
    }

    // Embed query
    const embedding = await openai.embeddings.create({
      model: 'text-embedding-3-small',
      input: q.trim(),
    })

    const queryEmbedding = embedding.data[0].embedding

    // Search brain chunks
    const supabase = getServiceClient()
    const { data: chunks, error } = await supabase.rpc('brain_search', {
      query_embedding: queryEmbedding,
      match_count: limit,
    })

    if (error) {
      console.error('Brain search error:', error)
      return NextResponse.json({ results: [] })
    }

    const results = (chunks || []).map((chunk: Record<string, unknown>) => ({
      id: chunk.id,
      source: chunk.source_table,
      sourceId: chunk.source_id,
      title: (chunk.metadata as Record<string, string>)?.title || String(chunk.source_id),
      snippet: String(chunk.content || '').slice(0, 150),
      date: (chunk.metadata as Record<string, string>)?.date || null,
    }))

    return NextResponse.json({ results })
  },
})
```

If `getServiceClient` doesn't exist in `@shortgravity/database`, use `getAnonClient` instead.

### Create `src/app/api/satellites/search/route.ts`:

```ts
import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const GET = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 60 },
  handler: async (request) => {
    const name = request.nextUrl.searchParams.get('name') || ''

    if (name.trim().length < 1) {
      return NextResponse.json({ results: [] })
    }

    const supabase = getAnonClient()
    const { data, error } = await supabase
      .from('satellites')
      .select('norad_id, name, inclination, apoapsis_km, periapsis_km')
      .ilike('name', `%${name.trim()}%`)
      .limit(10)

    if (error) {
      return NextResponse.json({ results: [] })
    }

    const results = (data || []).map(sat => ({
      noradId: sat.norad_id,
      name: sat.name,
      inclination: sat.inclination ? parseFloat(String(sat.inclination)) : null,
      altitude: sat.apoapsis_km && sat.periapsis_km
        ? (parseFloat(String(sat.apoapsis_km)) + parseFloat(String(sat.periapsis_km))) / 2
        : null,
    }))

    return NextResponse.json({ results })
  },
})
```

## 5. Create useCommandSearch hook

Create `src/components/command-palette/useCommandSearch.ts` based on the archive version. Key behaviors:
- Accept a search query string
- Debounce API calls by 150ms
- Use AbortController to cancel in-flight requests
- Fetch from `/api/brain/search?q=${query}&limit=5` for document results
- Fetch from `/api/satellites/search?name=${query}` for satellite results
- Return `{ results: CommandItem[], isSearching: boolean }`
- Map API results to CommandItem format with appropriate categories

## 6. Replace CommandPalette component

Replace the stub in `src/components/command-palette/CommandPalette.tsx` with a full implementation based on the archive. Key features:

- **Keyboard shortcuts**: Cmd+K to open/close, Escape to close, Arrow Up/Down to navigate, Enter to execute
- **Search input**: Auto-focused on open, filters static commands + triggers API search
- **Grouped results**: Navigation, Presets, Actions, Documents, Satellites — each with a category header
- **Active item highlight**: Orange left border on active item, auto-scroll into view
- **Action execution**:
  - `navigate` → `router.push(path)`, close palette
  - `preset` → `store.setActivePreset(id)`, close palette
  - `toggle` → toggle store boolean, STAY OPEN for rapid toggles
  - `open-brain` → `store.setBrainOpen(true)`, close palette
  - `select-satellite` → `router.push('/satellite/[noradId]')`, close palette
- **Portal rendering**: Use `createPortal` to render above everything
- **Dark theme**: Match the terminal aesthetic (bg-[#0a0f14], border-white/[0.08], etc.)

IMPORTANT: The archive might use `framer-motion` for open/close animations. Check if framer-motion is in `package.json`. If not, use CSS transitions or skip animations. Do NOT add framer-motion as a dependency without checking first.

IMPORTANT: The archive imports might use different paths. Adapt all imports to match the current codebase:
- `@/lib/stores/terminal-store` (not `@/store/terminal`)
- `@shortgravity/ui` (not `@/components/ui/*`)
- `next/navigation` for `useRouter`

## 7. Verify the component is mounted in the layout

Check `src/app/layout.tsx` — the `<CommandPalette />` should already be rendered there. If not, add it.

## 8. Run `npx tsc --noEmit`
