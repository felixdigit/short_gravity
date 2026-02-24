TARGET: .
---

MISSION:
Fix all deprecated Claude model IDs and hardcoded Supabase URLs across all worker scripts. The audit found deprecated model references and 11+ scripts with hardcoded Supabase URL defaults. All should use environment variables exclusively.

DIRECTIVES:

1. Search ALL Python files in `scripts/data-fetchers/` for deprecated Claude model IDs. Look for:
   - `claude-3-5-haiku-20241022` → replace with `claude-haiku-4-5-20251001`
   - `claude-3-5-sonnet-20241022` → replace with `claude-sonnet-4-6`
   - `claude-3-haiku` → replace with `claude-haiku-4-5-20251001`
   - `claude-3-sonnet` → replace with `claude-sonnet-4-6`
   - Any other `claude-3` prefixed model IDs → update to Claude 4.5/4.6 equivalents

   Use these mappings:
   - Haiku tasks (classification, extraction, simple analysis): `claude-haiku-4-5-20251001`
   - Sonnet tasks (synthesis, complex reasoning): `claude-sonnet-4-6`

2. For each file where you update a model ID, also check if the model is stored in a variable or passed as a string literal. If it's a string literal, consider extracting it to a constant at the top of the file:
   ```python
   HAIKU_MODEL = "claude-haiku-4-5-20251001"
   SONNET_MODEL = "claude-sonnet-4-6"
   ```
   This makes future model updates a single-line change.

3. Search ALL Python files for hardcoded Supabase URLs. Look for:
   - `https://dviagnysjftidxudeuyo.supabase.co` as a default/fallback value
   - Any pattern like `SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://...')`

   For each instance found:
   - Remove the hardcoded default value
   - Change to: `SUPABASE_URL = os.environ.get('SUPABASE_URL')` (no default)
   - Add a guard at the top of `main()`:
     ```python
     if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
         print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
         sys.exit(1)
     ```

   This ensures the worker fails clearly if env vars are missing, rather than silently connecting to a hardcoded project.

4. Similarly, search for any hardcoded API keys that may have been missed:
   - Search for `d5p3731r01qqu4br1230` (Finnhub key fragment)
   - Search for `sk-ant-api03` (Anthropic key prefix)
   - Search for `sk-proj-` (OpenAI key prefix)
   - Search for `re_di8LCEem` (Resend key fragment)
   - Search for `eyJhbGciOi` (JWT token prefix)

   If any are found hardcoded (not in .env files), remove them and use env vars instead.

5. Verify the `storage_utils.py` shared utility:
   - Does it have hardcoded Supabase URLs? Fix if so.
   - Does it have hardcoded bucket names? (`sec-filings`, `fcc-filings` are correct bucket names — these CAN be hardcoded since they're not secrets)

6. Run a final grep across all `.py` files for any remaining hardcoded URLs or credentials. Report what you find.
