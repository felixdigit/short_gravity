# Security Architecture

**Version:** 1.0

---

## Overview

Short Gravity handles sensitive financial intelligence data. Security is implemented at every layer: authentication, authorization, data protection, and API security.

---

## Authentication

### Supabase Auth
- JWT-based authentication
- OAuth providers: Google, Apple
- Magic links (passwordless option)
- Session expiry: 7 days, refresh tokens: 30 days

### JWT Validation (Edge Functions)

```typescript
export async function validateRequest(req: Request) {
  const authHeader = req.headers.get('Authorization');
  if (!authHeader?.startsWith('Bearer ')) {
    throw new Error('Missing authorization header');
  }
  
  const token = authHeader.replace('Bearer ', '');
  const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    global: { headers: { Authorization: `Bearer ${token}` } },
  });
  
  const { data: { user }, error } = await supabase.auth.getUser();
  if (error || !user) throw new Error('Invalid token');
  
  return { user, supabase };
}
```

---

## Row-Level Security (RLS)

All tables with user data have RLS enabled.

### Policies Summary

| Table | SELECT | INSERT | UPDATE | DELETE |
|-------|--------|--------|--------|--------|
| `profiles` | Own only | Auto (trigger) | Own only | — |
| `watchlists` | Own only | Own only | Own only | Own only |
| `briefings` | Own only | Service role | — | — |
| `entities` | Public | Service role | Service role | Service role |
| `signals` | Public | Service role | Service role | — |
| `satellites` | Public | Service role | Service role | — |

### Example Policy

```sql
ALTER TABLE watchlists ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own watchlists"
  ON watchlists FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own watchlists"
  ON watchlists FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own watchlists"
  ON watchlists FOR DELETE
  USING (auth.uid() = user_id);
```

---

## API Security

### Rate Limiting

| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| Public queries | 1000 | per minute |
| Edge Functions | 100 | per minute |
| AI generation | 50 | per hour |
| Auth attempts | 5 | per minute |

### Implementation (Upstash)

```typescript
import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';

const ratelimit = new Ratelimit({
  redis: Redis.fromEnv(),
  limiter: Ratelimit.slidingWindow(100, '1 m'),
});

export async function checkRateLimit(userId: string): Promise<boolean> {
  const { success } = await ratelimit.limit(userId);
  return success;
}
```

### Input Validation

```typescript
import { z } from 'zod';

const generateBriefingSchema = z.object({
  signal_id: z.string().uuid(),
  briefing_type: z.enum(['flash', 'summary', 'deep']),
});

export function validateInput<T>(schema: z.ZodSchema<T>, data: unknown): T {
  const result = schema.safeParse(data);
  if (!result.success) {
    throw new Error(`Validation error: ${result.error.message}`);
  }
  return result.data;
}
```

---

## Secrets Management

### Storage Locations

| Secret Type | Storage | Access |
|-------------|---------|--------|
| API keys (Claude, etc.) | Supabase Vault | Edge Functions |
| Database URL | GitHub Secrets | CI/CD only |
| OAuth credentials | Supabase Dashboard | Auth system |
| Push notification keys | EAS Secrets | iOS builds |

### Never Commit

```gitignore
# .gitignore
.env
.env.local
.env.*.local
*.pem
*.key
serviceAccountKey.json
```

### Client-Side Safety

```typescript
// Only NEXT_PUBLIC_ or EXPO_PUBLIC_ vars are exposed to client
// Server-only secrets should never have these prefixes

// ❌ WRONG - exposes to client
NEXT_PUBLIC_ANTHROPIC_KEY=sk-xxx

// ✅ CORRECT - server only
ANTHROPIC_API_KEY=sk-xxx
```

---

## Data Protection

### Encryption

| Layer | Method | Managed By |
|-------|--------|------------|
| At rest | AES-256 | Supabase (AWS) |
| In transit | TLS 1.3 | Vercel/Supabase |
| Backups | Encrypted | Supabase |

### PII Handling

**Collected:**
- Email address (required for auth)
- Full name (optional)
- OAuth profile data

**Not Collected:**
- Payment info (handled by RevenueCat/Stripe)
- Location data
- Device identifiers (beyond what Expo requires)

### Data Retention

| Data Type | Retention | Deletion |
|-----------|-----------|----------|
| User profiles | Until account deletion | On request |
| Briefings | 1 year | Auto-archive |
| Signals | 90 days | Auto-delete |
| TLE history | 90 days | Auto-delete |
| Audit logs | 1 year | Auto-delete |

---

## CORS Configuration

```typescript
// Edge Functions CORS
const corsHeaders = {
  'Access-Control-Allow-Origin': process.env.ALLOWED_ORIGINS || '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Authorization, Content-Type',
  'Access-Control-Max-Age': '86400',
};

// Handle preflight
if (req.method === 'OPTIONS') {
  return new Response(null, { headers: corsHeaders });
}
```

---

## Security Headers (Vercel)

```json
// vercel.json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-XSS-Protection", "value": "1; mode=block" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
        { "key": "Permissions-Policy", "value": "camera=(), microphone=(), geolocation=()" }
      ]
    }
  ]
}
```

---

## Audit Logging

```sql
-- Audit log table
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  action TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id TEXT,
  metadata JSONB DEFAULT '{}',
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for user queries
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, created_at DESC);

-- Auto-log sensitive actions via trigger
CREATE OR REPLACE FUNCTION log_sensitive_action()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO audit_logs (user_id, action, resource_type, resource_id)
  VALUES (auth.uid(), TG_OP, TG_TABLE_NAME, NEW.id::text);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

---

## Incident Response

### Severity Levels

| Level | Description | Response Time |
|-------|-------------|---------------|
| P1 | Data breach, service down | 15 minutes |
| P2 | Security vulnerability, degraded service | 1 hour |
| P3 | Minor issue, no user impact | 24 hours |

### Response Steps

1. **Identify** — Confirm the issue via monitoring/alerts
2. **Contain** — Isolate affected systems
3. **Eradicate** — Remove threat/fix vulnerability
4. **Recover** — Restore service
5. **Document** — Post-mortem within 48 hours

### Emergency Contacts

- Supabase: support@supabase.io
- Vercel: security@vercel.com
- Expo: security@expo.dev

---

## Compliance Considerations

### GDPR Readiness

- [ ] Privacy policy published
- [ ] Data export functionality
- [ ] Account deletion functionality
- [ ] Cookie consent (if using analytics)
- [ ] Data processing agreements with vendors

### SOC 2 (Future)

Supabase and Vercel are both SOC 2 compliant, which simplifies future certification for Short Gravity.

---

## Security Checklist

**Before Launch:**
- [ ] RLS enabled on all user tables
- [ ] All API endpoints require authentication
- [ ] Rate limiting configured
- [ ] Input validation on all endpoints
- [ ] Secrets removed from codebase
- [ ] HTTPS enforced
- [ ] Security headers configured
- [ ] Error messages don't leak sensitive info

**Ongoing:**
- [ ] Dependency updates (weekly)
- [ ] Security audit (quarterly)
- [ ] Penetration testing (annual)
- [ ] Access review (quarterly)
