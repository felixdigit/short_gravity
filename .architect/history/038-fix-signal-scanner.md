TARGET: .
---

MISSION:
Fix reliability issues in `scripts/data-fetchers/signal_scanner.py`. This worker has no retry logic on Claude API calls, broad exception handling that masks real errors, and no signal expiry cleanup.

DIRECTIVES:

1. Read the entire `scripts/data-fetchers/signal_scanner.py` file.

2. Add retry logic to ALL Claude/Anthropic API calls. The scanner uses Haiku for synthesis — these calls can hit 429 rate limits. Add retry with exponential backoff (3 attempts, 2s/4s/8s delays). Pattern:
   ```python
   for attempt in range(3):
       try:
           # Claude API call
           break
       except Exception as e:
           error_str = str(e)
           if '429' in error_str or 'rate' in error_str.lower():
               wait = 2 ** (attempt + 1)
               log(f"Rate limited, retrying in {wait}s (attempt {attempt + 1}/3)")
               time.sleep(wait)
           elif attempt == 2:
               log(f"ERROR: Claude API failed after 3 attempts: {e}")
               raise
           else:
               time.sleep(2 ** (attempt + 1))
   ```

3. Replace broad `except Exception as e: pass` or `except Exception as e: log(...)` patterns with specific exception handling. At minimum:
   - Catch `urllib.error.HTTPError` separately from `urllib.error.URLError` separately from generic `Exception`
   - Log the exception type and message, not just a generic "failed"
   - Never use bare `pass` in exception handlers — always log something

4. Add signal expiry cleanup. At the END of the scanner run (after all detectors have run), add a cleanup step:
   ```python
   # Clean up expired signals
   now = datetime.utcnow().isoformat()
   # Delete signals where expires_at < now
   supabase_request('DELETE', f'signals?expires_at=lt.{now}')
   log(f"Cleaned up expired signals")
   ```
   If the `signals` table doesn't have an `expires_at` column, skip this step but add a comment noting the need.

5. Verify the Claude model ID used for synthesis. It should be `claude-haiku-4-5-20251001` (not a deprecated model like `claude-3-5-haiku-20241022`). Update if needed.

6. Add a summary log at the end of each run:
   - Total detectors run
   - Total new signals generated
   - Total duplicate signals skipped (fingerprint collision)
   - Total errors encountered
   - Runtime in seconds

7. Verify the `fingerprint` generation is deterministic and stable — the same anomaly should produce the same fingerprint across runs to prevent duplicates. Check the hash inputs.

8. Test the script can be invoked without crashing: `python scripts/data-fetchers/signal_scanner.py --dry-run` (if dry-run flag exists).
