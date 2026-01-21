# Deployment & DevOps Architecture

**Version:** 1.0

---

## Overview

Short Gravity uses a modern JAMstack deployment model with automated CI/CD, preview environments, and managed infrastructure.

---

## Infrastructure Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DEPLOYMENT ARCHITECTURE                             │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────────────────────────────┐
                    │              GitHub Repository            │
                    │  ┌────────┐ ┌────────┐ ┌──────────────┐  │
                    │  │  main  │ │ develop│ │ feature/*    │  │
                    │  └───┬────┘ └───┬────┘ └──────┬───────┘  │
                    └──────┼──────────┼─────────────┼──────────┘
                           │          │             │
                           ▼          ▼             ▼
                    ┌──────────────────────────────────────────┐
                    │           GitHub Actions CI/CD            │
                    │  ┌──────────────────────────────────┐    │
                    │  │  Lint → Test → Build → Deploy    │    │
                    │  └──────────────────────────────────┘    │
                    └──────────────────────────────────────────┘
                           │          │             │
         ┌─────────────────┘          │             └─────────────────┐
         ▼                            ▼                               ▼
┌─────────────────┐        ┌─────────────────┐             ┌─────────────────┐
│   PRODUCTION    │        │    STAGING      │             │    PREVIEW      │
│                 │        │                 │             │   (per PR)      │
│  ┌───────────┐  │        │  ┌───────────┐  │             │  ┌───────────┐  │
│  │  Vercel   │  │        │  │  Vercel   │  │             │  │  Vercel   │  │
│  │  (Web)    │  │        │  │  (Web)    │  │             │  │  (Web)    │  │
│  └───────────┘  │        │  └───────────┘  │             │  └───────────┘  │
│                 │        │                 │             │                 │
│  ┌───────────┐  │        │  ┌───────────┐  │             │                 │
│  │ App Store │  │        │  │ TestFlight│  │             │                 │
│  │  (iOS)    │  │        │  │  (iOS)    │  │             │                 │
│  └───────────┘  │        │  └───────────┘  │             │                 │
│                 │        │                 │             │                 │
│  ┌───────────┐  │        │  ┌───────────┐  │             │  ┌───────────┐  │
│  │ Supabase  │  │        │  │ Supabase  │  │             │  │ Supabase  │  │
│  │ (Prod)    │  │        │  │ (Staging) │  │             │  │ (Branch)  │  │
│  └───────────┘  │        │  └───────────┘  │             │  └───────────┘  │
└─────────────────┘        └─────────────────┘             └─────────────────┘
```

---

## Environments

| Environment | Purpose | URL Pattern | Supabase |
|-------------|---------|-------------|----------|
| **Production** | Live users | `app.shortgravity.com` | Production project |
| **Staging** | Pre-release testing | `staging.shortgravity.com` | Staging project |
| **Preview** | PR review | `pr-123.shortgravity.vercel.app` | Branch database |
| **Local** | Development | `localhost:3000` | Local or dev project |

---

## Web Deployment (Vercel)

### Configuration

```json
// vercel.json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "installCommand": "npm ci",
  "regions": ["iad1", "sfo1"],
  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        { "key": "Cache-Control", "value": "no-store, must-revalidate" }
      ]
    },
    {
      "source": "/textures/(.*)",
      "headers": [
        { "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }
      ]
    }
  ],
  "rewrites": [
    {
      "source": "/ingest/:path*",
      "destination": "https://app.posthog.com/:path*"
    }
  ]
}
```

### Environment Variables (Vercel Dashboard)

| Variable | Scope | Description |
|----------|-------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | All | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | All | Supabase anonymous key |
| `SUPABASE_SERVICE_ROLE_KEY` | Server only | Service role key (secrets) |
| `ANTHROPIC_API_KEY` | Server only | Claude API key |
| `SENTRY_DSN` | All | Error tracking |

### Branch Deployments

Vercel automatically creates preview deployments for each PR:
- Unique URL per PR
- Isolated from production
- Comments deployment URL on PR

---

## iOS Deployment (EAS)

### Build Profiles

```json
// eas.json
{
  "cli": { "version": ">= 7.0.0" },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal",
      "ios": {
        "simulator": true
      },
      "env": {
        "EXPO_PUBLIC_SUPABASE_URL": "https://dev.supabase.co",
        "EXPO_PUBLIC_ENV": "development"
      }
    },
    "preview": {
      "distribution": "internal",
      "ios": {
        "resourceClass": "m-medium"
      },
      "channel": "preview",
      "env": {
        "EXPO_PUBLIC_SUPABASE_URL": "https://staging.supabase.co",
        "EXPO_PUBLIC_ENV": "staging"
      }
    },
    "production": {
      "ios": {
        "resourceClass": "m-medium"
      },
      "channel": "production",
      "autoIncrement": true,
      "env": {
        "EXPO_PUBLIC_SUPABASE_URL": "https://prod.supabase.co",
        "EXPO_PUBLIC_ENV": "production"
      }
    }
  },
  "submit": {
    "production": {
      "ios": {
        "appleId": "team@shortgravity.com",
        "ascAppId": "1234567890",
        "appleTeamId": "XXXXXXXXXX"
      }
    }
  }
}
```

### Update Channels

EAS Update allows OTA (over-the-air) updates without App Store review:

```bash
# Push JS-only updates to production
eas update --channel production --message "Bug fix for signal feed"
```

| Channel | Purpose | Auto-update |
|---------|---------|-------------|
| `production` | App Store users | On app launch |
| `preview` | TestFlight testers | On app launch |
| `development` | Internal testing | Manual |

---

## Supabase Deployment

### Project Structure

```
Supabase Organization
├── short-gravity-prod    (Production)
├── short-gravity-staging (Staging)
└── short-gravity-dev     (Development/Preview)
```

### Database Migrations

```bash
# Create a new migration
supabase migration new add_new_table

# Apply migrations locally
supabase db reset

# Push to remote (staging)
supabase db push --linked

# Push to production (via CI)
supabase db push --db-url $PROD_DATABASE_URL
```

### Edge Function Deployment

```bash
# Deploy all functions
supabase functions deploy

# Deploy specific function
supabase functions deploy generate-briefing

# Set secrets
supabase secrets set ANTHROPIC_API_KEY=sk-xxx
```

---

## CI/CD Pipelines

### GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  NODE_VERSION: '20'

jobs:
  # ─────────────────────────────────────────────────────────────
  # Lint and Type Check
  # ─────────────────────────────────────────────────────────────
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Lint
        run: npm run lint
      
      - name: Type check
        run: npm run type-check

  # ─────────────────────────────────────────────────────────────
  # Tests
  # ─────────────────────────────────────────────────────────────
  test:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run tests
        run: npm test -- --coverage
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  # ─────────────────────────────────────────────────────────────
  # Deploy Web (Vercel handles this automatically, but we can add checks)
  # ─────────────────────────────────────────────────────────────
  deploy-web:
    runs-on: ubuntu-latest
    needs: [lint, test]
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Trigger Vercel deployment
        run: |
          curl -X POST "${{ secrets.VERCEL_DEPLOY_HOOK }}"

  # ─────────────────────────────────────────────────────────────
  # Deploy Supabase Functions
  # ─────────────────────────────────────────────────────────────
  deploy-functions:
    runs-on: ubuntu-latest
    needs: [lint, test]
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Supabase CLI
        uses: supabase/setup-cli@v1
        with:
          version: latest
      
      - name: Deploy Edge Functions
        run: |
          supabase functions deploy --project-ref ${{ secrets.SUPABASE_PROJECT_REF }}
        env:
          SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}

  # ─────────────────────────────────────────────────────────────
  # Database Migrations
  # ─────────────────────────────────────────────────────────────
  migrate-db:
    runs-on: ubuntu-latest
    needs: [lint, test]
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Supabase CLI
        uses: supabase/setup-cli@v1
      
      - name: Run migrations
        run: |
          supabase db push --db-url "${{ secrets.DATABASE_URL }}"

  # ─────────────────────────────────────────────────────────────
  # Build iOS (on release tags)
  # ─────────────────────────────────────────────────────────────
  build-ios:
    runs-on: ubuntu-latest
    needs: [lint, test]
    if: startsWith(github.ref, 'refs/tags/v')
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
      
      - name: Setup EAS
        uses: expo/expo-github-action@v8
        with:
          eas-version: latest
          token: ${{ secrets.EXPO_TOKEN }}
      
      - name: Install dependencies
        run: npm ci
        working-directory: ./mobile
      
      - name: Build iOS
        run: eas build --platform ios --profile production --non-interactive
        working-directory: ./mobile
      
      - name: Submit to App Store
        run: eas submit --platform ios --latest --non-interactive
        working-directory: ./mobile
```

### PR Checks Workflow

```yaml
# .github/workflows/pr-checks.yml
name: PR Checks

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  preview-url:
    runs-on: ubuntu-latest
    steps:
      - name: Wait for Vercel Preview
        uses: patrickedqvist/wait-for-vercel-preview@v1.3.1
        id: vercel
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          max_timeout: 300
      
      - name: Comment Preview URL
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '🚀 Preview deployed to: ${{ steps.vercel.outputs.url }}'
            })
```

---

## Monitoring & Observability

### Error Tracking (Sentry)

```typescript
// lib/sentry.ts (Next.js)
import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV,
  tracesSampleRate: 0.1,
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
});
```

```typescript
// iOS app
import * as Sentry from '@sentry/react-native';

Sentry.init({
  dsn: process.env.EXPO_PUBLIC_SENTRY_DSN,
  environment: process.env.EXPO_PUBLIC_ENV,
});
```

### Uptime Monitoring

Use Vercel's built-in analytics or external service (e.g., Better Uptime):

| Check | Endpoint | Frequency |
|-------|----------|-----------|
| Web health | `api/health` | 1 min |
| Auth health | Supabase status | 5 min |
| Edge functions | `functions/v1/health` | 5 min |

### Logging

Supabase provides built-in logging for:
- Edge Function invocations
- Database queries (via `pg_stat_statements`)
- Auth events

Access via Supabase Dashboard → Logs.

---

## Secrets Management

### GitHub Secrets

| Secret | Used In | Description |
|--------|---------|-------------|
| `VERCEL_DEPLOY_HOOK` | CI | Trigger Vercel deploy |
| `SUPABASE_ACCESS_TOKEN` | CI | Supabase CLI auth |
| `SUPABASE_PROJECT_REF` | CI | Production project ID |
| `DATABASE_URL` | CI | Direct Postgres connection |
| `EXPO_TOKEN` | CI | EAS authentication |
| `ANTHROPIC_API_KEY` | Functions | Claude API |
| `SENTRY_DSN` | All | Error tracking |

### Supabase Vault (Runtime Secrets)

```bash
# Set secrets for Edge Functions
supabase secrets set ANTHROPIC_API_KEY=sk-ant-xxx
supabase secrets set SPACE_TRACK_USERNAME=xxx
supabase secrets set SPACE_TRACK_PASSWORD=xxx

# List secrets
supabase secrets list
```

---

## Rollback Procedures

### Web (Vercel)

1. Go to Vercel Dashboard → Deployments
2. Find last known good deployment
3. Click "..." → "Promote to Production"

### iOS (EAS Update)

```bash
# Revert to previous update
eas update:rollback --channel production
```

### Database

```bash
# List migrations
supabase migration list

# Rollback (manually create down migration)
supabase migration new rollback_xxx
# Edit migration file with DOWN SQL
supabase db reset
```

### Edge Functions

```bash
# Redeploy from specific commit
git checkout <commit>
supabase functions deploy
```

---

## Cost Estimation

### Monthly Costs at Scale

| Service | Free Tier | 10K MAU | 100K MAU |
|---------|-----------|---------|----------|
| Vercel | $0 | $20 | $100 |
| Supabase | $0 | $25 | $75 |
| EAS Build | $0 (limited) | $15 | $30 |
| Claude API | Pay-per-use | ~$50 | ~$500 |
| Sentry | $0 | $26 | $80 |
| **Total** | **$0** | **~$136** | **~$785** |

*Actual costs vary based on usage patterns.*

---

## Checklist: Production Launch

- [ ] All environment variables set in Vercel
- [ ] Supabase RLS policies tested
- [ ] Edge Functions deployed with secrets
- [ ] Sentry configured and tested
- [ ] iOS build submitted to App Store
- [ ] DNS configured for custom domain
- [ ] SSL certificates active
- [ ] Monitoring alerts configured
- [ ] Backup strategy documented
- [ ] Incident response plan documented
