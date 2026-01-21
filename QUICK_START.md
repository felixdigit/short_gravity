# Quick Start Guide

## What We Just Set Up

Your project now has a complete, production-ready environment variable system!

## 📁 Files Created

### Configuration Files
- `.env.example` - Template showing what variables are needed (committed to Git)
- `.env.local` - Your actual secrets (NOT committed, you need to fill this in)
- `.gitignore` - Protects your secrets from being committed

### Code Files (in `short-gravity-web/`)
1. **`lib/env.ts`** - Type-safe environment variable access
2. **`lib/hooks/useXApi.ts`** - React hook for X API calls
3. **`app/api/x/route.ts`** - Server-side API endpoint

### Documentation
- `ENV_SETUP_GUIDE.md` - Complete guide (read this for deep understanding)
- `scripts/setup-vercel-env.sh` - Interactive script to add vars to Vercel

## 🚀 Next Steps (In Order)

### 1. Fill in Your Local Environment Variables

```bash
# Open .env.local and add your X API credentials
nano .env.local

# Or just edit it in your editor
# You'll need to get these from: https://developer.x.com/en/portal/dashboard
```

### 2. Test Locally

```bash
cd short-gravity-web
npm run dev
# Visit http://localhost:3000
```

### 3. When Ready to Deploy, Add Vars to Vercel

**Option A: Use the script (easier)**
```bash
./scripts/setup-vercel-env.sh
```

**Option B: Manual**
```bash
vercel env add X_API_KEY production,preview,development
# Then paste your value when prompted
```

## 💡 Key Concepts Explained

### Why Two Types of Variables?

**1. Server-Side Only (Secure)**
```typescript
// These have NO prefix
X_API_KEY=abc123
X_API_SECRET=xyz789

// Access in code (server-side only):
import { serverEnv } from '@/lib/env';
const key = serverEnv.x.apiKey();
```

**2. Public (Browser-Accessible)**
```typescript
// These start with NEXT_PUBLIC_
NEXT_PUBLIC_API_BASE_URL=/api
NEXT_PUBLIC_ENABLE_DEBUG_MODE=true

// Access anywhere:
import { publicEnv } from '@/lib/env';
const url = publicEnv.apiBaseUrl;
```

### The Data Flow

```
Browser Component
    ↓ (calls)
useXApi() hook
    ↓ (fetch)
/api/x route (server)
    ↓ (uses serverEnv)
X API (Twitter)
```

**Why?** This keeps your API keys secure on the server, never exposed to browser.

## 📚 Learning Resources

### Read These Files (in order):
1. Start here: `ENV_SETUP_GUIDE.md` (comprehensive guide)
2. Then: `short-gravity-web/lib/env.ts` (see how variables are accessed)
3. Then: `short-gravity-web/lib/hooks/useXApi.ts` (see client-side usage)
4. Then: `short-gravity-web/app/api/x/route.ts` (see server-side usage)

### Each file has:
- ✅ Extensive comments explaining WHY things work this way
- ✅ Example code showing HOW to use it
- ✅ Security notes about what NOT to do

## 🔒 Security Checklist

- [x] `.env.local` is in `.gitignore`
- [x] Secrets use server-side only variables (no `NEXT_PUBLIC_` prefix)
- [x] Public variables don't contain sensitive data
- [x] API routes validate and sanitize input
- [x] Error messages don't leak credentials

## 🆘 Common Issues

### "Missing required environment variable"
→ Add it to `.env.local` and restart dev server

### Variable is undefined in browser
→ Make sure it starts with `NEXT_PUBLIC_`

### Works locally but not on Vercel
→ Add the variable to Vercel using `vercel env add`

## ✅ What You Can Do Now

1. **Safely call X API** from your React components using the hook
2. **Keep secrets secure** on the server
3. **Different configs** for dev/preview/prod
4. **Type-safe access** - TypeScript will catch typos
5. **Easy team onboarding** - teammates just copy `.env.example`

## 🎯 Example Usage

```typescript
// In any React component:
'use client';

import { useXApi } from '@/lib/hooks/useXApi';

export function MyComponent() {
  const { callXApi, loading } = useXApi();

  const handleClick = async () => {
    const result = await callXApi({
      action: 'post-tweet',
      data: { text: 'Hello from my app!' }
    });

    if (result.success) {
      console.log('Success!', result.data);
    }
  };

  return (
    <button onClick={handleClick} disabled={loading}>
      Post Tweet
    </button>
  );
}
```

That's it! The hook handles everything securely.

---

## 📞 Questions?

All the files have detailed comments. Read through:
- `ENV_SETUP_GUIDE.md` for the full explanation
- The code files for implementation examples

Happy coding! 🚀
