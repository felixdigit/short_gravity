# Short Gravity — Discord Setup

## Server Structure

### Roles
| Role | Color | Purpose |
|------|-------|---------|
| **Full Spectrum** | `#FF6B35` (asts-orange) | Patreon subscribers — auto-assigned via Patreon integration |
| **Ground Control** | `#FFFFFF` | Gabriel (admin) |

### Channels

```
SHORT GRAVITY
├── #welcome              (public, read-only)  — Server rules, links, what this is
├── #announcements        (public, read-only)  — Major milestones, Patreon updates
│
├── TERMINAL FEED (Full Spectrum only)
│   ├── #sec-filings      — New 10-K, 10-Q, 8-K with AI summaries
│   ├── #fcc-regulatory   — FCC filings, spectrum decisions, license status
│   ├── #patents          — Patent grants, new applications
│   ├── #press-releases   — Official company announcements
│   ├── #launches         — Launch events, mission updates
│   ├── #earnings         — Earnings call transcripts, summaries
│   ├── #orbital-ops      — TLE updates, conjunction alerts, constellation health
│   └── #signals          — Cross-source anomaly alerts (signal scanner)
│
├── COMMUNITY (Full Spectrum only)
│   ├── #general          — Discussion
│   ├── #research         — Share findings, ask questions
│   └── #market-talk      — Price action, short interest, positioning
│
└── META
    └── #bot-log          (admin only) — Worker run status, errors
```

### Permissions
- **Public channels:** `#welcome`, `#announcements` — visible to all, post-locked
- **Full Spectrum channels:** All Terminal Feed + Community — visible only to Patreon role
- **Admin channels:** `#bot-log` — Ground Control only

## Patreon Integration

1. Go to Patreon Creator Settings → Apps & Integrations → Discord
2. Connect your Discord server
3. Map **Full Spectrum ($15/mo)** tier → **Full Spectrum** role
4. Patreon handles role assignment/removal automatically on subscribe/cancel

## Webhook Setup

Each notification channel gets its own webhook:

1. In Discord: Channel Settings → Integrations → Webhooks → New Webhook
2. Name it matching the channel (e.g., "SEC Filing Bot")
3. Copy the webhook URL
4. Add to `scripts/data-fetchers/.env`:

```env
DISCORD_WEBHOOK_SEC=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_FCC=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_PATENTS=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_PRESS=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_LAUNCHES=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_EARNINGS=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_ORBITAL=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_SIGNALS=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_BOT_LOG=https://discord.com/api/webhooks/...
```

## Notification Pipeline

Workers already run on schedule and write to Supabase. The Discord integration adds a single webhook call at the end of each worker's insert/update cycle.

```
Worker runs → Data to Supabase → Format message → POST to Discord webhook
```

Uses `scripts/discord/notify.py` — a shared utility all workers import.

## Worker → Channel Mapping

| Worker | Channel | Trigger |
|--------|---------|---------|
| `filing_worker.py` | `#sec-filings` | New filing inserted |
| `fcc_worker.py` / `fcc_rss_monitor.py` | `#fcc-regulatory` | New FCC filing detected |
| `icfs_worker.py` | `#fcc-regulatory` | License status change |
| `patent_worker_v2.py` | `#patents` | New patent or grant |
| `press_release_worker.py` | `#press-releases` | New press release |
| `launch_worker.py` | `#launches` | Launch event update |
| `transcript_worker.py` | `#earnings` | New transcript available |
| `tle_worker.py` | `#orbital-ops` | Conjunction alert or new satellite |
| `signal_scanner.py` | `#signals` | Anomaly detected |
| `x_worker.py` | `#signals` | High-signal social event |
| All workers | `#bot-log` | Run status, errors |
