TARGET: apps/web
---
MISSION:
Fix 3 critical bugs: satellite detail page crash on Next.js 14, earnings table name mismatch, and missing waitlist API route.

DIRECTIVES:

## 1. Fix satellite page params (Next.js 14 compatibility)

File: `src/app/satellite/[noradId]/page.tsx`

The page uses `use(params)` to unwrap params as a Promise — this is a Next.js 15+ API. This project runs Next.js 14.2.3 where `params` is a plain object.

Change the component signature from:
```tsx
export default function SatelliteDetailPage({
  params,
}: {
  params: Promise<{ noradId: string }>
}) {
  const { noradId } = use(params)
```

To:
```tsx
export default function SatelliteDetailPage({
  params,
}: {
  params: { noradId: string }
}) {
  const { noradId } = params
```

Also remove the `use` import from React if it's no longer needed.

## 2. Fix earnings table name mismatch

The database table is `earnings_transcripts` but two API routes query `earnings_calls` which doesn't exist.

### File: `src/app/api/earnings/context/route.ts`

Find any reference to `.from('earnings_calls')` and change it to `.from('earnings_transcripts')`.

Also check the column names match. The `earnings_transcripts` table has columns:
- `id` (UUID)
- `company` (TEXT)
- `fiscal_year` (TEXT or INT)
- `fiscal_quarter` (TEXT)
- plus content columns

Verify the select/filter columns in the query match the actual table schema. If there are column name mismatches, fix them. Common differences:
- `earnings_calls` might use `ticker` → `earnings_transcripts` uses `company`
- `earnings_calls` might use `quarter` → `earnings_transcripts` uses `fiscal_quarter`
- `earnings_calls` might use `year` → `earnings_transcripts` uses `fiscal_year`

### File: `src/app/api/horizon/route.ts`

Same fix — find `.from('earnings_calls')` and change to `.from('earnings_transcripts')`. Verify column names match.

## 3. Create waitlist API route

The landing page email signup form POSTs to `/api/waitlist` but this route doesn't exist.

Create `src/app/api/waitlist/route.ts`:

```ts
import { NextResponse } from 'next/server'
import { createApiHandler } from '@/lib/api/handler'
import { getAnonClient } from '@shortgravity/database'

export const POST = createApiHandler({
  rateLimit: { windowMs: 60_000, max: 10 },
  handler: async (request) => {
    const body = await request.json()
    const { email } = body

    if (!email || typeof email !== 'string') {
      return NextResponse.json({ error: 'Email is required' }, { status: 400 })
    }

    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(email)) {
      return NextResponse.json({ error: 'Invalid email format' }, { status: 400 })
    }

    const supabase = getAnonClient()

    const { error } = await supabase
      .from('subscribers')
      .upsert(
        { email: email.toLowerCase().trim() },
        { onConflict: 'email' }
      )

    if (error) {
      console.error('Waitlist signup error:', error)
      return NextResponse.json({ error: 'Failed to subscribe' }, { status: 500 })
    }

    return NextResponse.json({ success: true })
  },
})
```

IMPORTANT: Check the `subscribers` table schema first. The database schema reference says: `subscribers | id UUID | email | waitlist API`. If the table has additional required columns (like `created_at`, `source`, etc.), include them in the upsert.

Also check what the EmailSignupForm component sends in the POST body — read `src/components/landing/EmailSignupForm.tsx` to verify the field name is `email`.

## 4. Run `npx tsc --noEmit`
