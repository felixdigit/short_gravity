# MICROKERNEL: DATA FETCHERS
You are working in the Python data collection scripts directory.

YOUR LAWS OF PHYSICS:
1. PYTHON ONLY: All worker scripts are Python 3.11+. Do not create JavaScript or TypeScript files.
2. STDLIB ONLY: Use only Python standard library (`urllib`, `json`, `os`, `sys`, `datetime`, `hashlib`, `re`, `ssl`, `time`, `csv`, `io`, `base64`). Do NOT use `requests`. Exceptions: `yfinance`, `playwright`, `pdfplumber`, `PyPDF2` where already established.
3. SUPABASE REST: All database access goes through Supabase REST API via the `supabase_request()` helper pattern. Never use a Python ORM or direct PostgreSQL connection.
4. ENV VARS: All credentials come from environment variables. Never hardcode API keys, URLs, or passwords. Fail clearly if required env vars are missing.
5. IDEMPOTENT: Every worker must be safe to run twice. Use upsert patterns with correct `on_conflict` columns. Never create duplicates.
6. EXIT CODES: Exit 0 on success, non-zero on failure. GitHub Actions depends on this.
