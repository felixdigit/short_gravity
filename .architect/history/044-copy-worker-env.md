TARGET: .
---

MISSION:
Copy the actual worker .env file from the archive so local development and manual worker runs work immediately. Also ensure the main repo's apps/web/.env.local has all the variables needed for the cron routes.

DIRECTIVES:

1. Copy the archive's data-fetchers env file to the main repo's worker scripts directory:
   ```
   cp _ARCHIVE_V1/short-gravity-web/scripts/data-fetchers/.env scripts/data-fetchers/.env
   ```
   This file contains the actual API keys needed for local worker runs.

2. Verify `scripts/data-fetchers/.env` is in `.gitignore`. Check the root `.gitignore` file for patterns that would match:
   - `.env`
   - `*.env`
   - `scripts/data-fetchers/.env`
   - `.env*` (but NOT `.env.example`)

   If `.env` is NOT gitignored, add the appropriate pattern to `.gitignore`:
   ```
   # Worker environment variables (contains secrets)
   scripts/data-fetchers/.env
   ```

3. Read the current `apps/web/.env.local` file. Verify it has ALL of these variables (needed by cron routes):
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_KEY`
   - `SPACE_TRACK_USERNAME`
   - `SPACE_TRACK_PASSWORD`
   - `OPENAI_API_KEY`
   - `ANTHROPIC_API_KEY`
   - `FINNHUB_API_KEY`
   - `RESEND_API_KEY`
   - `QSTASH_TOKEN`
   - `QSTASH_CURRENT_SIGNING_KEY`
   - `QSTASH_NEXT_SIGNING_KEY`

   If any are missing, add them (copy values from the archive's .env.local or scripts/data-fetchers/.env).

4. Add `CRON_SECRET` to `apps/web/.env.local` for local development. Set it to any value (e.g., `dev-cron-secret-local`). The handler.ts allows all requests in development mode, but having it set prevents confusing auth errors.

5. Verify `.gitignore` also covers `apps/web/.env.local`. It should already be there, but confirm.

6. Do NOT commit any .env files. This mandate only copies files locally for development use. The production secrets go in Vercel and GitHub Secrets (configured by the user manually).
