/**
 * In-memory sliding-window rate limiter
 * Per-IP tracking, auto-cleanup of expired entries
 */

import { NextRequest, NextResponse } from 'next/server'

interface RateLimitConfig {
  windowMs: number
  max: number
}

interface RateLimitEntry {
  timestamps: number[]
}

const store = new Map<string, RateLimitEntry>()

// Cleanup expired entries every 5 minutes
let lastCleanup = Date.now()
const CLEANUP_INTERVAL = 5 * 60 * 1000

function cleanup(windowMs: number) {
  const now = Date.now()
  if (now - lastCleanup < CLEANUP_INTERVAL) return
  lastCleanup = now

  const cutoff = now - windowMs
  store.forEach((entry, key) => {
    entry.timestamps = entry.timestamps.filter((t: number) => t > cutoff)
    if (entry.timestamps.length === 0) store.delete(key)
  })
}

export function rateLimit({ windowMs, max }: RateLimitConfig) {
  return {
    check(req: NextRequest): { allowed: boolean; remaining: number; resetMs: number } {
      const ip = req.headers.get('x-forwarded-for')?.split(',')[0]?.trim() || 'unknown'
      const now = Date.now()
      const cutoff = now - windowMs

      cleanup(windowMs)

      let entry = store.get(ip)
      if (!entry) {
        entry = { timestamps: [] }
        store.set(ip, entry)
      }

      entry.timestamps = entry.timestamps.filter(t => t > cutoff)

      if (entry.timestamps.length >= max) {
        const oldest = entry.timestamps[0]
        const resetMs = oldest + windowMs - now
        return { allowed: false, remaining: 0, resetMs }
      }

      entry.timestamps.push(now)
      return { allowed: true, remaining: max - entry.timestamps.length, resetMs: windowMs }
    },
  }
}

/**
 * Helper: return a 429 response with Retry-After header
 */
export function rateLimitResponse(resetMs: number): NextResponse {
  return NextResponse.json(
    { error: 'Too many requests' },
    {
      status: 429,
      headers: { 'Retry-After': String(Math.ceil(resetMs / 1000)) },
    }
  )
}
