/**
 * API Route Wrapper — secure-by-default handler for all API routes
 *
 * Provides: rate limiting, auth, error handling.
 */

import { NextRequest } from 'next/server'
import { rateLimit, rateLimitResponse } from '@/lib/rate-limit'

type RouteContext = { params: Promise<Record<string, string>> }

interface ApiHandlerConfig {
  /** Rate limiting — omit for no rate limit */
  rateLimit?: { windowMs: number; max: number }

  /** Auth requirement: 'none' (default), 'cron', 'admin' */
  auth?: 'none' | 'cron' | 'admin'

  /** The actual route handler */
  handler: (req: NextRequest, ctx?: RouteContext) => Promise<Response>
}

function checkCronAuth(req: NextRequest): boolean {
  const cronSecret = process.env.CRON_SECRET || ''
  if (!cronSecret && process.env.NODE_ENV !== 'development') return false

  const cronHeader = req.headers.get('x-vercel-cron-secret')
  if (cronHeader && cronHeader === cronSecret) return true

  const authHeader = req.headers.get('authorization')
  if (authHeader) {
    const token = authHeader.replace('Bearer ', '')
    if (token === cronSecret) return true
  }

  const qstashSig = req.headers.get('upstash-signature')
  if (qstashSig) return true

  if (process.env.NODE_ENV === 'development') return true

  return false
}

function checkAdminAuth(req: NextRequest): boolean {
  const secretKey = process.env.ADMIN_SECRET_KEY || ''

  const authHeader = req.headers.get('authorization')
  if (authHeader && authHeader === `Bearer ${secretKey}`) return true

  if (process.env.NODE_ENV === 'development') return true

  return false
}

export function createApiHandler(config: ApiHandlerConfig) {
  const limiter = config.rateLimit
    ? rateLimit({ windowMs: config.rateLimit.windowMs, max: config.rateLimit.max })
    : null

  return async function (req: NextRequest, ctx?: RouteContext): Promise<Response> {
    try {
      // 1. Rate limiting
      if (limiter) {
        const { allowed, resetMs } = limiter.check(req)
        if (!allowed) return rateLimitResponse(resetMs)
      }

      // 2. Auth check
      const authMode = config.auth || 'none'
      if (authMode === 'cron' && !checkCronAuth(req)) {
        return Response.json({ error: 'Unauthorized' }, { status: 401 })
      }
      if (authMode === 'admin' && !checkAdminAuth(req)) {
        return Response.json({ error: 'Unauthorized' }, { status: 401 })
      }

      // 3. Call handler
      return await config.handler(req, ctx)
    } catch (err) {
      const path = req.nextUrl?.pathname || 'unknown'
      console.error(`[${path}] Unhandled error:`, err)
      return Response.json({ error: 'Internal server error' }, { status: 500 })
    }
  }
}
