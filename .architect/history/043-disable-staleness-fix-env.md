TARGET: .
---

MISSION:
Fix the staleness-alert workflow that's flooding the user with GitHub issue emails, and ensure all worker scripts have proper environment variable access. The staleness alerts are firing because no data workers were running (they weren't migrated until now). The alerts are correct but unhelpful until the workers are actually active.

DIRECTIVES:

1. Read `.github/workflows/staleness-alert.yml` fully.

2. Add a TEMPORARY disable flag to the staleness-alert workflow. Don't delete it — just prevent it from running until the data workers are producing data. Add this at the top of the job:
   ```yaml
   jobs:
     check-staleness:
       # TEMPORARILY DISABLED: Re-enable once all data workers are active and populating tables.
       # The staleness alerts were firing because workers weren't migrated from the V1 archive.
       # To re-enable: remove the 'if: false' line below.
       if: false
       runs-on: ubuntu-latest
   ```

3. Read the archive's data-fetchers .env file at `_ARCHIVE_V1/short-gravity-web/scripts/data-fetchers/.env` to get ALL environment variable names (not values — those go in GitHub secrets, not in committed files).

4. Update `scripts/data-fetchers/.env.example` with the COMPLETE list of all environment variables used across all workers. Include comments explaining which workers need each variable. The current .env.example only has 9 variables — the archive has many more. Add ALL of these (with blank values):
   ```
   # Core — required by all workers
   SUPABASE_URL=
   SUPABASE_SERVICE_KEY=

   # AI / Embeddings
   ANTHROPIC_API_KEY=
   OPENAI_API_KEY=

   # Social Media
   X_BEARER_TOKEN=
   X_API_KEY=
   X_API_SECRET=

   # Financial Data
   FINNHUB_API_KEY=

   # Patent APIs
   PATENTSVIEW_API_KEY=
   EPO_CONSUMER_KEY=
   EPO_CONSUMER_SECRET=

   # Google (patent enrichment)
   GOOGLE_API_KEY=

   # FCC
   FCC_API_KEY=
   FCC_ICFS_USERNAME=
   FCC_ICFS_PASSWORD=

   # Space-Track
   SPACE_TRACK_USERNAME=
   SPACE_TRACK_PASSWORD=

   # Discord Notifications (optional)
   DISCORD_WEBHOOK_URL=
   DISCORD_WEBHOOK_SEC=
   DISCORD_WEBHOOK_FCC=
   DISCORD_WEBHOOK_PATENTS=
   DISCORD_WEBHOOK_PRESS=
   DISCORD_WEBHOOK_LAUNCHES=
   DISCORD_WEBHOOK_EARNINGS=
   DISCORD_WEBHOOK_ORBITAL=
   DISCORD_WEBHOOK_SIGNALS=
   DISCORD_BOT_TOKEN=
   ```

5. Also update `.github/SECRETS_REQUIRED.md` to include the FULL list of secrets needed across all workflows. The current version only lists 9 — add the missing ones:
   - `FCC_API_KEY`
   - `FCC_ICFS_USERNAME`
   - `FCC_ICFS_PASSWORD`
   - `GOOGLE_API_KEY`
   - `SPACE_TRACK_USERNAME`
   - `SPACE_TRACK_PASSWORD`
   - `X_API_KEY`
   - `X_API_SECRET`
   - `DISCORD_WEBHOOK_URL` (and per-topic webhooks if workflows reference them)
   - `DISCORD_BOT_TOKEN`

6. Check EVERY GitHub Actions workflow YAML in `.github/workflows/`. For each one, verify that EVERY env var it references with `${{ secrets.VARIABLE_NAME }}` is documented in `SECRETS_REQUIRED.md`. If any are missing from the docs, add them.

7. For the `staleness-alert.yml` workflow specifically, verify it uses `${{ github.token }}` (auto-provided) and not a custom `GH_TOKEN` secret. If it uses `GH_TOKEN`, change it to `github.token` since that's built-in.

8. Verify no workflow YAML file has hardcoded secrets or API keys in the `env:` section. All secrets must use `${{ secrets.VARIABLE_NAME }}` syntax.
