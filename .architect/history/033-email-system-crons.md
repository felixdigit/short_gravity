TARGET: apps/web
---

MISSION:
Migrate the complete email system — React Email templates, subscriber management API routes, and both email cron handlers (daily-brief for morning intelligence briefs, signal-alerts for real-time critical notifications). This is the subscriber communication layer.

DIRECTIVES:

1. Create `src/emails/` directory and copy both email templates from the archive:
   - `../../_ARCHIVE_V1/short-gravity-web/emails/DailyBrief.tsx` → `src/emails/DailyBrief.tsx`
   - `../../_ARCHIVE_V1/short-gravity-web/emails/SignalAlert.tsx` → `src/emails/SignalAlert.tsx`

   AUDIT each template:
   a. Verify imports from `@react-email/components` use standard exports: `Html`, `Head`, `Body`, `Container`, `Text`, `Link`, `Section`, `Hr`, `Img`, `Font`, etc.
   b. Verify the templates are valid React components with proper TypeScript interfaces for their props.
   c. DailyBrief props should include: `date`, `price?`, `signals`, `horizonEvents`, `newFilingsCount`, `unsubscribeUrl?`.
   d. SignalAlert props should include: `signal` (with `severity`, `title`, `signal_type`, `category`, `description`, `detected_at`, `source_refs?`), `unsubscribeUrl?`.
   e. Verify no hardcoded URLs that reference the old domain — all URLs should use `NEXT_PUBLIC_SITE_URL` env var.

2. Create email management API routes:
   - `src/app/api/email/unsubscribe/route.ts` — copy from `../../_ARCHIVE_V1/short-gravity-web/app/api/email/unsubscribe/route.ts`
   - `src/app/api/email/preferences/route.ts` — copy from `../../_ARCHIVE_V1/short-gravity-web/app/api/email/preferences/route.ts`

   AUDIT both routes:
   a. Verify they query the `subscribers` table with columns: `id`, `email`, `status`, `daily_brief`, `signal_alerts`, `unsubscribe_token`.
   b. Unsubscribe route: Accepts `token` and `type` (all|daily_brief|signal_alerts) query params. Updates subscriber status or preference flags. Returns styled HTML confirmation page.
   c. Preferences route: GET returns current preferences by token, POST updates `daily_brief` and/or `signal_alerts` boolean flags.
   d. Neither route should require authentication (users click unsubscribe links from emails).
   e. Verify both use `getServiceClient()` from `@/lib/supabase` for writes.

3. Create daily-brief cron route: `src/app/api/cron/daily-brief/route.ts` — copy from `../../_ARCHIVE_V1/short-gravity-web/app/api/cron/daily-brief/route.ts`.

   CRITICAL AUDIT — this route has KNOWN bugs that must be fixed:
   a. **Table name fix**: Search for ANY reference to `earnings_calls` and replace with `earnings_transcripts`. The `earnings_calls` table does NOT exist.
   b. **Table existence check**: Search for references to `catalysts` table. The `catalysts` table exists in the schema but may have zero rows. The query must handle empty results gracefully (not crash on null/empty).
   c. **Table existence check**: Search for references to `fcc_dockets` table. Verify this table exists and has a `comment_deadline` or `reply_deadline` column for horizon event queries.
   d. Verify Resend integration: imports `Resend` from `resend`, creates client with `process.env.RESEND_API_KEY`.
   e. Verify React Email rendering: imports `render` from `@react-email/components` to convert JSX → HTML.
   f. Verify subscriber query filters: `status = 'active'` AND `daily_brief = true`.
   g. Verify batch send pattern: sends up to 100 emails per Resend batch call.
   h. Verify each email includes personalized `unsubscribeUrl` using the subscriber's `unsubscribe_token`.
   i. Verify env vars: `RESEND_API_KEY`, `RESEND_FROM_EMAIL` (fallback: `'Short Gravity <updates@shortgravity.com>'`), `NEXT_PUBLIC_SITE_URL`.
   j. Verify `auth: 'cron'` is set on the handler config.

4. Create signal-alerts cron route: `src/app/api/cron/signal-alerts/route.ts` — copy from `../../_ARCHIVE_V1/short-gravity-web/app/api/cron/signal-alerts/route.ts`.

   AUDIT:
   a. Queries `signals` table for `severity IN ('critical', 'high')` created in the last 1 hour.
   b. Deduplicates via `signal_alert_log` table — checks `fingerprint` column to skip already-alerted signals.
   c. After sending, writes to `signal_alert_log` with columns: `signal_fingerprint`, `sent_at`, `recipient_count`.
   d. Subscriber filter: `status = 'active'` AND `signal_alerts = true`.
   e. Renders `SignalAlert` email template per signal, personalized per subscriber.
   f. Batch send via Resend (100 subscribers per batch).
   g. Verify `auth: 'cron'` is set.
   h. Error handling: if Resend API fails for one signal, log the error and continue to the next signal (don't abort the entire run).

5. Verify the email template import path chain. The cron routes import templates as:
   - `import { DailyBrief } from '@/emails/DailyBrief'` (or similar)
   - `import { SignalAlert } from '@/emails/SignalAlert'`
   In the monorepo, `@/` maps to `src/`, so `src/emails/` must contain these files. If the import uses a default export (`import DailyBrief from ...`), verify the template exports match.

6. Verify the `render()` function import. In `@react-email/components`, the render function may be at:
   - `import { render } from '@react-email/components'` OR
   - `import { render } from '@react-email/render'`
   Check which one the archive uses and verify it matches the installed package version.

7. Run `pnpm typecheck` to verify all email templates, routes, and cron handlers compile without errors.

8. If typecheck fails due to missing types or packages, fix the issues:
   - Missing `@react-email/render` → add to package.json if needed
   - Type mismatches in Resend SDK → update Resend types or cast as needed
   - Missing subscriber table types → define inline interfaces
