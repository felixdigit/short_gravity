TARGET: .
---

MISSION:
Add CLAUDE.md microkernels to every ungoverned directory that Lingot agents may be spawned into. The constitution says "each room contains a CLAUDE.md file dictating what an agent can and cannot do." Directories without microkernels are context bleed risks — agents spawned there have no local physics.

DIRECTIVES:

1. Check if `scripts/data-fetchers/CLAUDE.md` exists. If not, create it:
   ```markdown
   # MICROKERNEL: DATA FETCHERS
   You are working in the Python data collection scripts directory.

   YOUR LAWS OF PHYSICS:
   1. PYTHON ONLY: All worker scripts are Python 3.11+. Do not create JavaScript or TypeScript files.
   2. STDLIB ONLY: Use only Python standard library (`urllib`, `json`, `os`, `sys`, `datetime`, `hashlib`, `re`, `ssl`, `time`, `csv`, `io`, `base64`). Do NOT use `requests`. Exceptions: `yfinance`, `playwright`, `pdfplumber`, `PyPDF2` where already established.
   3. SUPABASE REST: All database access goes through Supabase REST API via the `supabase_request()` helper pattern. Never use a Python ORM or direct PostgreSQL connection.
   4. ENV VARS: All credentials come from environment variables. Never hardcode API keys, URLs, or passwords. Fail clearly if required env vars are missing.
   5. IDEMPOTENT: Every worker must be safe to run twice. Use upsert patterns with correct `on_conflict` columns. Never create duplicates.
   6. EXIT CODES: Exit 0 on success, non-zero on failure. GitHub Actions depends on this.
   ```

2. Check if `.github/CLAUDE.md` exists. If not, create it:
   ```markdown
   # MICROKERNEL: GITHUB ACTIONS
   You are working in the GitHub Actions workflow directory.

   YOUR LAWS OF PHYSICS:
   1. YAML ONLY: Workflow files are YAML (`.yml`). Do not create scripts here — scripts live in `scripts/data-fetchers/`.
   2. SECRETS ONLY: All credentials must use `${{ secrets.VARIABLE_NAME }}` syntax. Never hardcode API keys or tokens.
   3. SCRIPT PATHS: All Python scripts are at `scripts/data-fetchers/<name>.py` relative to the repo root.
   4. STANDARD ACTIONS: Use `actions/checkout@v4` and `actions/setup-python@v5`. Keep action versions current.
   5. MANUAL TRIGGER: Every workflow must include `workflow_dispatch:` to allow manual triggering in addition to cron schedules.
   ```

3. Check if `docs/CLAUDE.md` exists. If not, create it:
   ```markdown
   # MICROKERNEL: DOCUMENTATION
   You are working in the documentation directory.

   YOUR LAWS OF PHYSICS:
   1. READ-ONLY REFERENCE: This directory contains project documentation. Do not create application code here.
   2. MARKDOWN ONLY: All documents are Markdown (`.md`).
   3. NO SECRETS: Never include API keys, passwords, or credentials in documentation files.
   ```

4. Check if `apps/sync/CLAUDE.md` already exists. Read it and verify it properly constrains the sync workers room: no UI code, no React, database and core imports only.

5. Verify that `packages/ui/CLAUDE.md` explicitly forbids importing from `@shortgravity/core` and `@shortgravity/database`. Read the current file. If these constraints are missing, add them. The ui package must be fully amnesiac — pure visual primitives only.

6. Verify that `packages/core/CLAUDE.md` explicitly forbids importing from `@shortgravity/ui` and `@shortgravity/database`. If missing, add the constraints.

7. Verify that `packages/database/CLAUDE.md` explicitly states it's a leaf node — no imports from any other `@shortgravity/*` package.

8. List all directories that could be Lingot targets (anywhere with a CLAUDE.md or that appears as a TARGET in mandate files). Verify each one now has a microkernel. Report any gaps.
