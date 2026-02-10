# User Auth — Handover Doc

## Context
Building Patreon for Short Gravity. The auth model needs to support tiered access to the Terminal platform.

## Decided

- **Platform is open** — anyone can use the Terminal (satellite tracking, filing archives, patent data, AI search)
- **Public AI is basic** — shorter context, simpler answers
- **Paid tier ($15/mo "Full Spectrum" via Patreon)** gives:
  - Enhanced AI: deeper context, full citation chains, cross-reference analysis
  - Broader market coverage beyond $ASTS (spectrum, competitors, adjacent tickers)
  - Discord access with real-time notifications (filings, patents, orbital events)
  - Early access to research

## Open Questions

### 1. Account tiers — what's the model?
Three possible approaches:

**A) Two states: Anonymous + Paid**
- No accounts for free users. Just use the site.
- Only create an account if you're a Patreon subscriber.
- Simplest to build. No user table bloat.

**B) Three states: Anonymous + Free Account + Paid**
- Anyone can create a free account (saves preferences, search history, etc.)
- Patreon subscribers get the premium AI layer.
- More engagement surface, but more to build.

**C) Everyone gets an account, AI tier is gated**
- Require account creation for AI search (even basic).
- Patreon unlocks the enhanced tier.
- Gives you a user base to convert, but adds friction to the open platform promise.

### 2. Patreon integration
- Need to verify Patreon subscription status from the web app
- Options: Patreon OAuth, Patreon API webhook on subscribe/cancel, or manual Discord role check
- Patreon OAuth is cleanest — user links Patreon account, app checks active pledge

### 3. Auth provider
- Supabase Auth is already in the stack (Supabase is the DB)
- Supabase supports OAuth providers, magic links, email/password
- Could add Patreon as a custom OAuth provider or use Supabase Auth + separate Patreon API check

### 4. Session handling
- How does the AI route know if a request is free vs paid?
- Likely: JWT with subscription tier claim, checked server-side on API routes
- AI API route checks tier → adjusts system prompt context, token limits, data sources

## Tech Notes
- **Stack:** Next.js 14, Supabase (DB + potentially Auth), Vercel
- **AI routes:** `short-gravity-web/app/api/` — these need tier-aware logic
- **Supabase Auth docs:** built-in, supports custom claims via RLS or edge functions
- **Patreon API:** v2, OAuth2 flow, webhook support for pledge events

## Suggested Implementation Order
1. Pick account model (A, B, or C above)
2. Set up Supabase Auth (if not already)
3. Build Patreon OAuth integration
4. Add subscription status to user profile
5. Gate AI context depth based on tier in API routes
6. Wire up Discord invite to verified patrons
