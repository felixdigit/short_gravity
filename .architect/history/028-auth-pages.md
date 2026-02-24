TARGET: apps/web
---
MISSION:
Build the /login and /account pages with Supabase Auth integration. Basic magic link authentication — no password management needed.

DIRECTIVES:

## 1. Check Supabase Auth setup

The Supabase client is already configured. Check that `@supabase/supabase-js` or `@supabase/ssr` is in dependencies. The `getAnonClient()` from `@shortgravity/database` should support auth operations.

Read `packages/database/src/index.ts` to understand how the Supabase client is created. Check if there's already an auth-aware client or if you need to create one with `createBrowserClient` for client-side auth.

## 2. Create an auth utility

Create `src/lib/auth.ts`:

```ts
import { getAnonClient } from '@shortgravity/database'

export function getSupabaseClient() {
  return getAnonClient()
}

export async function signInWithEmail(email: string) {
  const supabase = getSupabaseClient()
  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: {
      emailRedirectTo: `${window.location.origin}/account`,
    },
  })
  return { error }
}

export async function signOut() {
  const supabase = getSupabaseClient()
  const { error } = await supabase.auth.signOut()
  return { error }
}

export async function getSession() {
  const supabase = getSupabaseClient()
  const { data: { session }, error } = await supabase.auth.getSession()
  return { session, error }
}

export async function getUser() {
  const supabase = getSupabaseClient()
  const { data: { user }, error } = await supabase.auth.getUser()
  return { user, error }
}
```

IMPORTANT: If `getAnonClient()` returns a server-side client that doesn't work in the browser, you may need to create a browser-specific client using `createClient` from `@supabase/supabase-js` with the `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` env vars. Adapt accordingly.

## 3. Create the /login page

Create `src/app/login/page.tsx`:

```tsx
'use client'

import { useState } from 'react'
import { signInWithEmail } from '@/lib/auth'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) return

    setLoading(true)
    setError(null)

    const { error: authError } = await signInWithEmail(email.trim())

    if (authError) {
      setError(authError.message)
    } else {
      setSent(true)
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen bg-[#030305] text-white font-mono flex items-center justify-center">
      <div className="w-full max-w-sm mx-4">
        <div className="text-center mb-8">
          <h1 className="text-lg tracking-wider mb-1">SHORT GRAVITY</h1>
          <p className="text-[11px] text-white/30">Sign in to access your account</p>
        </div>

        {sent ? (
          <div className="border border-white/[0.08] rounded-xl p-8 text-center">
            <div className="text-sm text-white/70 mb-2">Check your email</div>
            <div className="text-[11px] text-white/30">
              We sent a magic link to <span className="text-white/50">{email}</span>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="border border-white/[0.08] rounded-xl p-6 space-y-4">
            <div>
              <label className="block text-[10px] text-white/30 mb-1.5 tracking-wider">EMAIL</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-4 py-2.5 text-sm text-white/80 placeholder:text-white/15 focus:outline-none focus:border-white/[0.15]"
                autoFocus
              />
            </div>

            {error && (
              <div className="text-[11px] text-red-400/70">{error}</div>
            )}

            <button
              type="submit"
              disabled={loading || !email.trim()}
              className="w-full py-2.5 bg-white/[0.06] border border-white/[0.08] rounded-lg text-xs text-white/60 hover:text-white/80 transition-colors disabled:opacity-30"
            >
              {loading ? 'SENDING...' : 'SEND MAGIC LINK'}
            </button>
          </form>
        )}

        <div className="mt-6 text-center">
          <a href="/" className="text-[10px] text-white/20 hover:text-white/40 transition-colors">
            BACK TO TERMINAL
          </a>
        </div>
      </div>
    </div>
  )
}
```

## 4. Create the /account page

Create `src/app/account/page.tsx`:

```tsx
'use client'

import { useEffect, useState } from 'react'
import { getUser, signOut } from '@/lib/auth'

interface UserData {
  id: string
  email?: string
  created_at?: string
}

export default function AccountPage() {
  const [user, setUser] = useState<UserData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getUser().then(({ user: u }) => {
      setUser(u as UserData | null)
      setLoading(false)
    })
  }, [])

  const handleSignOut = async () => {
    await signOut()
    window.location.href = '/'
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#030305] text-white font-mono flex items-center justify-center">
        <div className="text-white/30 text-sm">Loading...</div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-[#030305] text-white font-mono flex items-center justify-center">
        <div className="text-center">
          <div className="text-white/30 text-sm mb-4">Not signed in</div>
          <a
            href="/login"
            className="text-[11px] text-white/50 border border-white/[0.08] px-4 py-2 rounded-lg hover:text-white/70 transition-colors"
          >
            SIGN IN
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#030305] text-white font-mono">
      <div className="max-w-lg mx-auto px-6 py-12">
        <h1 className="text-lg tracking-wider mb-8">ACCOUNT</h1>

        <div className="border border-white/[0.08] rounded-xl p-6 space-y-6">
          <div>
            <div className="text-[10px] text-white/30 tracking-wider mb-1">EMAIL</div>
            <div className="text-sm text-white/70">{user.email}</div>
          </div>

          <div>
            <div className="text-[10px] text-white/30 tracking-wider mb-1">TIER</div>
            <div className="text-sm text-white/70">FREE</div>
          </div>

          <div>
            <div className="text-[10px] text-white/30 tracking-wider mb-1">MEMBER SINCE</div>
            <div className="text-sm text-white/50">
              {user.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}
            </div>
          </div>

          <div className="pt-4 border-t border-white/[0.06] flex gap-3">
            <a
              href="https://www.patreon.com/shortgravity"
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 text-center py-2.5 bg-[#FF6B35]/10 border border-[#FF6B35]/30 rounded-lg text-[11px] text-[#FF6B35] hover:bg-[#FF6B35]/20 transition-colors"
            >
              UPGRADE
            </a>
            <button
              onClick={handleSignOut}
              className="flex-1 py-2.5 border border-white/[0.08] rounded-lg text-[11px] text-white/40 hover:text-white/60 transition-colors"
            >
              SIGN OUT
            </button>
          </div>
        </div>

        <div className="mt-8 text-center">
          <a href="/" className="text-[10px] text-white/20 hover:text-white/40 transition-colors">
            BACK TO TERMINAL
          </a>
        </div>
      </div>
    </div>
  )
}
```

## 5. Run `npx tsc --noEmit`

NOTE: If the Supabase auth methods aren't available on the client returned by `getAnonClient()`, you'll need to create a browser client. In that case, create a helper:

```ts
import { createClient } from '@supabase/supabase-js'

export function getBrowserClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}
```

And use `getBrowserClient()` instead of `getAnonClient()` in the auth utility.
