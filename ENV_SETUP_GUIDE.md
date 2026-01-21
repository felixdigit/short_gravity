# Environment Variables Setup Guide

This guide explains how environment variables are configured in this project and how to use them securely.

## 📚 Table of Contents

1. [What Are Environment Variables?](#what-are-environment-variables)
2. [File Structure](#file-structure)
3. [Local Development Setup](#local-development-setup)
4. [Vercel Deployment Setup](#vercel-deployment-setup)
5. [Using Environment Variables in Code](#using-environment-variables-in-code)
6. [Security Best Practices](#security-best-practices)
7. [Troubleshooting](#troubleshooting)

---

## What Are Environment Variables?

Environment variables are **key-value pairs** that store configuration data outside your code. They're essential for:

- **Security**: Keep API keys and secrets out of version control
- **Flexibility**: Different values for development, staging, and production
- **Configuration**: Change behavior without modifying code

### Example:
```bash
# Instead of hardcoding:
const apiKey = "sk_live_1234567890abcdef";  // ❌ NEVER DO THIS!

# Use environment variables:
const apiKey = process.env.X_API_KEY;  // ✅ SECURE
```

---

## File Structure

```
short_gravity/
├── .env.local              # Your actual secrets (NEVER commit!)
├── .env.example            # Template (safe to commit)
├── .gitignore              # Ensures .env.local is never committed
└── short-gravity-web/
    ├── lib/
    │   ├── env.ts          # Type-safe env variable access
    │   └── hooks/
    │       └── useXApi.ts  # Client-side API hook
    └── app/
        └── api/
            └── x/
                └── route.ts # Server-side API route
```

### File Purposes:

| File | Purpose | Commit to Git? |
|------|---------|----------------|
| `.env.local` | Your actual secrets | ❌ NEVER |
| `.env.example` | Template for teammates | ✅ YES |
| `.gitignore` | Blocks secret files | ✅ YES |
| `lib/env.ts` | Type-safe access to env vars | ✅ YES |

---

## Local Development Setup

### Step 1: Copy the Template

```bash
# Copy .env.example to .env.local
cp .env.example .env.local
```

### Step 2: Fill in Your Values

Edit `.env.local` with your actual credentials:

```bash
# X (Twitter) API Configuration
X_API_KEY=your_actual_key_here
X_API_SECRET=your_actual_secret_here
X_BEARER_TOKEN=your_actual_token_here
X_CLIENT_ID=your_client_id_here
X_CLIENT_SECRET=your_client_secret_here

# API Configuration
NEXT_PUBLIC_API_BASE_URL=http://localhost:3000/api

# Debug mode (optional)
NEXT_PUBLIC_ENABLE_DEBUG_MODE=true
```

### Step 3: Get X API Credentials

1. Go to [https://developer.x.com/en/portal/dashboard](https://developer.x.com/en/portal/dashboard)
2. Create a new app or select existing one
3. Go to "Keys and tokens" section
4. Copy your API Key, API Secret, Bearer Token, etc.
5. Paste them into `.env.local`

### Step 4: Start Development Server

```bash
cd short-gravity-web
npm run dev
```

Your environment variables are now loaded automatically!

---

## Vercel Deployment Setup

### Method 1: Using the Script (Recommended)

Run the interactive setup script:

```bash
./scripts/setup-vercel-env.sh
```

This will guide you through adding all variables to Vercel.

### Method 2: Manual CLI

Add variables one at a time:

```bash
# Syntax: vercel env add VARIABLE_NAME environment1,environment2
vercel env add X_API_KEY production,preview,development
# Then paste your value when prompted
```

### Method 3: Vercel Dashboard

1. Go to [vercel.com](https://vercel.com)
2. Select your project (`short_gravity`)
3. Go to **Settings** → **Environment Variables**
4. Click **Add New**
5. Enter name, value, and select environments
6. Click **Save**

### Environment Types in Vercel:

| Environment | When Used | Example |
|-------------|-----------|---------|
| **Development** | `vercel dev` locally | Local testing |
| **Preview** | Branch deployments | `development` branch |
| **Production** | `main` branch or manual prod deploy | Live site |

---

## Using Environment Variables in Code

### Server-Side (API Routes, Server Components)

```typescript
// app/api/example/route.ts
import { serverEnv } from '@/lib/env';

export async function GET() {
  // ✅ SECURE: Only accessible on server
  const apiKey = serverEnv.x.apiKey();

  // Use the API key to make requests
  const response = await fetch('https://api.x.com/...', {
    headers: { Authorization: `Bearer ${apiKey}` }
  });

  return Response.json({ data: await response.json() });
}
```

### Client-Side (React Components)

**Option 1: Use the Hook**

```typescript
'use client';

import { useXApi } from '@/lib/hooks/useXApi';

export function ShareButton() {
  const { callXApi, loading, error } = useXApi();

  const handleShare = async () => {
    // ✅ Calls your API route (which has the credentials)
    const result = await callXApi({
      action: 'post-tweet',
      data: { text: 'Check this out!' }
    });

    if (result.success) {
      alert('Posted!');
    }
  };

  return (
    <button onClick={handleShare} disabled={loading}>
      {loading ? 'Sharing...' : 'Share on X'}
    </button>
  );
}
```

**Option 2: Access Public Variables Directly**

```typescript
'use client';

import { publicEnv } from '@/lib/env';

export function DebugInfo() {
  // ✅ Safe: These start with NEXT_PUBLIC_
  return (
    <div>
      <p>API URL: {publicEnv.apiBaseUrl}</p>
      <p>Debug Mode: {publicEnv.enableDebugMode ? 'On' : 'Off'}</p>
    </div>
  );
}
```

### ⚠️ Important Rules:

1. **Server-side secrets** (without `NEXT_PUBLIC_` prefix):
   - ✅ Use in API routes
   - ✅ Use in Server Components
   - ❌ NEVER use in Client Components

2. **Public variables** (with `NEXT_PUBLIC_` prefix):
   - ✅ Use anywhere (client or server)
   - ⚠️ Visible in browser (don't put secrets here!)

---

## Security Best Practices

### ✅ DO:

- Store all secrets in `.env.local` (never hardcode)
- Use server-side API routes for sensitive operations
- Add `.env.local` to `.gitignore`
- Use `NEXT_PUBLIC_` prefix only for non-sensitive data
- Rotate API keys regularly
- Use different keys for dev/staging/prod

### ❌ DON'T:

- Commit `.env.local` to Git
- Put API keys in `NEXT_PUBLIC_` variables
- Hardcode secrets in your code
- Share your `.env.local` file
- Use production credentials in development
- Expose sensitive data in error messages

### Example of Bad vs Good:

```typescript
// ❌ BAD: Hardcoded secret
const apiKey = "sk_live_abc123";

// ❌ BAD: Public variable with secret
const apiKey = process.env.NEXT_PUBLIC_X_API_KEY; // Exposed to browser!

// ✅ GOOD: Server-side only
import { serverEnv } from '@/lib/env';
const apiKey = serverEnv.x.apiKey(); // Only accessible on server
```

---

## Troubleshooting

### Problem: "Missing required environment variable"

**Solution**: Check that:
1. Variable exists in `.env.local`
2. Variable name is spelled correctly
3. Development server was restarted after adding variable
4. On Vercel, variable is added to correct environment

### Problem: "undefined" when accessing variable

**Solution**:
- **Client-side**: Make sure variable starts with `NEXT_PUBLIC_`
- **Server-side**: Use `serverEnv` helper functions
- Restart dev server after adding new variables

### Problem: Variable works locally but not on Vercel

**Solution**:
1. Add variable to Vercel: `vercel env add VARIABLE_NAME`
2. Or add via Vercel dashboard
3. Redeploy: `vercel --prod`

### Problem: "Cannot find module '@/lib/env'"

**Solution**: Check `tsconfig.json` has path alias:
```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

---

## Quick Reference Commands

```bash
# View environment variables on Vercel
vercel env ls

# Add new environment variable
vercel env add VARIABLE_NAME production,preview,development

# Pull Vercel env vars to local file
vercel env pull .env.local

# Remove environment variable
vercel env rm VARIABLE_NAME

# Check what variables Next.js sees
npm run dev
# Then visit http://localhost:3000 and check browser console
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│                  Browser (Client)               │
│  ┌───────────────────────────────────────────┐  │
│  │  React Component                          │  │
│  │  - Uses publicEnv (NEXT_PUBLIC_*)        │  │
│  │  - Calls useXApi() hook                  │  │
│  └──────────────┬────────────────────────────┘  │
└─────────────────┼───────────────────────────────┘
                  │ fetch('/api/x')
                  ▼
┌─────────────────────────────────────────────────┐
│              Next.js Server (API Routes)        │
│  ┌───────────────────────────────────────────┐  │
│  │  app/api/x/route.ts                       │  │
│  │  - Uses serverEnv (secrets)               │  │
│  │  - Has X API credentials                  │  │
│  └──────────────┬────────────────────────────┘  │
└─────────────────┼───────────────────────────────┘
                  │ API call with credentials
                  ▼
         ┌─────────────────┐
         │   X API Server  │
         └─────────────────┘
```

**Why this architecture?**
- Credentials stay on your server (secure)
- Browser never sees API keys
- You control rate limiting, caching, error handling
- Easy to add logging, analytics, etc.

---

## Next Steps

1. ✅ Copy `.env.example` to `.env.local`
2. ✅ Fill in your X API credentials
3. ✅ Add variables to Vercel
4. ✅ Start building your app!
5. 📚 Read the code examples in `lib/env.ts` and `lib/hooks/useXApi.ts`

---

## Need Help?

- Check the example implementations in:
  - `short-gravity-web/lib/env.ts`
  - `short-gravity-web/lib/hooks/useXApi.ts`
  - `short-gravity-web/app/api/x/route.ts`

- Common resources:
  - [Next.js Environment Variables Docs](https://nextjs.org/docs/pages/building-your-application/configuring/environment-variables)
  - [Vercel Environment Variables Docs](https://vercel.com/docs/projects/environment-variables)
  - [X API Documentation](https://developer.x.com/en/docs)
