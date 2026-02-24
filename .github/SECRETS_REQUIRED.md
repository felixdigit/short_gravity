# Required GitHub Repository Secrets

All GitHub Actions workflows and Vercel crons depend on these secrets. Configure them in **Settings → Secrets and variables → Actions**. Vercel env vars are configured in **Vercel → Settings → Environment Variables**.

## Core (all workers)

- `SUPABASE_URL` — Supabase project REST API URL
- `SUPABASE_SERVICE_KEY` — Supabase service role key (full access, bypasses RLS)

## AI / Embeddings

- `ANTHROPIC_API_KEY` — Claude API for summaries, classification, glossary extraction, brain queries
- `OPENAI_API_KEY` — OpenAI `text-embedding-3-small` for vector embeddings (brain_chunks)

## Social Media

- `X_BEARER_TOKEN` — X/Twitter API v2 bearer token (x-worker)
- `X_API_KEY` — X/Twitter API v1.1 consumer key (x-worker)
- `X_API_SECRET` — X/Twitter API v1.1 consumer secret (x-worker)

## Financial Data

- `FINNHUB_API_KEY` — Finnhub API for news and earnings dates (news-worker, earnings-worker)

## Patent APIs

- `PATENTSVIEW_API_KEY` — PatentsView API for US patent discovery (patent-worker)
- `EPO_CONSUMER_KEY` — European Patent Office OPS API consumer key (patent-worker)
- `EPO_CONSUMER_SECRET` — European Patent Office OPS API consumer secret (patent-worker)
- `GOOGLE_API_KEY` — Google API for patent enrichment (patent_enricher, future)

## FCC

- `FCC_API_KEY` — FCC API key for ECFS queries (ecfs-worker, defaults to DEMO_KEY)
- `FCC_ICFS_USERNAME` — FCC ICFS login username (icfs-worker, future authenticated access)
- `FCC_ICFS_PASSWORD` — FCC ICFS login password (icfs-worker, future authenticated access)

## Space-Track (Vercel env vars, not GH Actions)

- `SPACE_TRACK_USERNAME` — Space-Track.org login (TLE refresh cron on Vercel)
- `SPACE_TRACK_PASSWORD` — Space-Track.org password (TLE refresh cron on Vercel)

## Discord Notifications (optional)

- `DISCORD_WEBHOOK_URL` — General Discord webhook (check-feeds cron)
- `DISCORD_WEBHOOK_SEC` — SEC filing alerts webhook
- `DISCORD_WEBHOOK_FCC` — FCC filing alerts webhook
- `DISCORD_WEBHOOK_PATENTS` — Patent alerts webhook
- `DISCORD_WEBHOOK_PRESS` — Press release alerts webhook
- `DISCORD_WEBHOOK_LAUNCHES` — Launch alerts webhook
- `DISCORD_WEBHOOK_EARNINGS` — Earnings alerts webhook
- `DISCORD_WEBHOOK_ORBITAL` — Orbital event alerts webhook
- `DISCORD_WEBHOOK_SIGNALS` — Signal alerts webhook
- `DISCORD_BOT_TOKEN` — Discord bot token (future interactive bot)

## Built-in (no configuration needed)

- `github.token` — Auto-generated GITHUB_TOKEN used by staleness-alert for creating issues

## Secret → Workflow Matrix

| Secret | Workflows / Crons |
|--------|-------------------|
| SUPABASE_URL | All 24 GH Actions workflows + Vercel crons |
| SUPABASE_SERVICE_KEY | All 24 GH Actions workflows + Vercel crons |
| ANTHROPIC_API_KEY | ecfs, glossary, icfs, itu, launch, news, press-release, sec-filing, signal-scanner, transcript, uls, x-worker |
| OPENAI_API_KEY | ecfs, filing-embedding, icfs, ised, itu, news, ofcom, patent, press-release, sec-filing, transcript, uls, x-worker |
| X_BEARER_TOKEN | x-worker |
| X_API_KEY | x-worker (when added to workflow) |
| X_API_SECRET | x-worker (when added to workflow) |
| FINNHUB_API_KEY | earnings, news |
| PATENTSVIEW_API_KEY | patent |
| EPO_CONSUMER_KEY | patent |
| EPO_CONSUMER_SECRET | patent |
| GOOGLE_API_KEY | patent (when patent_enricher is migrated) |
| FCC_API_KEY | ecfs (used in worker, not yet in GH Actions env) |
| FCC_ICFS_USERNAME | icfs (future authenticated access) |
| FCC_ICFS_PASSWORD | icfs (future authenticated access) |
| SPACE_TRACK_USERNAME | Vercel cron: /api/cron/tle-refresh |
| SPACE_TRACK_PASSWORD | Vercel cron: /api/cron/tle-refresh |
| DISCORD_WEBHOOK_URL | Vercel cron: /api/cron/check-feeds |
| DISCORD_WEBHOOK_* | Future per-topic alert workflows |
| DISCORD_BOT_TOKEN | Future interactive Discord bot |
