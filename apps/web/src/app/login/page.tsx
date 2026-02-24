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
