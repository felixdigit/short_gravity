# Required Environment Variables

## Supabase (all routes)
- `NEXT_PUBLIC_SUPABASE_URL` — Supabase project URL (public, used client + server side)
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — Supabase anonymous key (public, RLS-gated reads)
- `SUPABASE_SERVICE_KEY` — Supabase service role key (server only, bypasses RLS)

## Cron Authentication
- `CRON_SECRET` — Shared secret for Vercel cron job authentication

## Admin
- `ADMIN_SECRET_KEY` — Bearer token for admin-only API routes

## External APIs
- `SPACE_TRACK_USERNAME` — Space-Track.org login (TLE refresh cron)
- `SPACE_TRACK_PASSWORD` — Space-Track.org password (TLE refresh cron)
- `OPENAI_API_KEY` — OpenAI API key (brain search embeddings, inline PR embedding)
- `ANTHROPIC_API_KEY` — Anthropic API key (brain query LLM responses)
- `FINNHUB_API_KEY` — Finnhub API key (stock quotes)

## Email (Resend)
- `RESEND_API_KEY` — Resend email service API key (daily briefs, signal alerts)
- `RESEND_FROM_EMAIL` — Sender address for emails (default: `Short Gravity <updates@shortgravity.com>`)

## Public / UI
- `NEXT_PUBLIC_SITE_URL` — Base URL for the site (used in emails, unsubscribe links; default: `https://shortgravity.com`)
- `NEXT_PUBLIC_DISCORD_INVITE_URL` — Discord invite URL shown in ClearanceModal

## Notifications (optional)
- `DISCORD_WEBHOOK_URL` — Discord webhook for new filing/PR alerts (optional, check-feeds cron)

## Runtime
- `NODE_ENV` — Node.js environment (`development` | `production`)
