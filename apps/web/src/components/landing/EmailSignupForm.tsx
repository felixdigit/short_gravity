'use client'

import { useState } from 'react'

export function EmailSignupForm() {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) return

    setStatus('loading')
    try {
      const res = await fetch('/api/waitlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      if (!res.ok) throw new Error('Failed')
      setStatus('success')
    } catch {
      setStatus('error')
    }
  }

  if (status === 'success') {
    return (
      <div className="text-center">
        <div className="text-[10px] text-[#22C55E]/80 tracking-wider font-mono">
          YOU&apos;RE IN. CHECK YOUR EMAIL FOR ACCESS.
        </div>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="you@example.com"
        className="flex-1 bg-transparent border border-white/10 px-3 py-2 text-[11px] text-white/70 font-mono placeholder:text-white/20 outline-none focus:border-white/20 transition-colors"
      />
      <button
        type="submit"
        disabled={status === 'loading'}
        className="px-4 py-2 text-[10px] text-white/80 tracking-wider font-mono border border-white/10 hover:border-white/20 transition-colors disabled:opacity-50"
      >
        {status === 'loading' ? '...' : 'NOTIFY ME'}
      </button>
    </form>
  )
}
