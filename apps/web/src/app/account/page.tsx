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
