TARGET: .
---

MISSION:
Fix all reliability issues in `scripts/data-fetchers/news_worker.py`. This worker has no retry logic, no HTTP timeouts, and wastefully refetches all years every run. Make it production-solid.

DIRECTIVES:

1. Read the entire `scripts/data-fetchers/news_worker.py` file.

2. Add HTTP timeout to ALL `urllib.request.urlopen()` calls. Set timeout=30 seconds. If the worker uses a helper function like `fetch_json()`, add the timeout there. Example:
   ```python
   urllib.request.urlopen(req, timeout=30)
   ```

3. Add retry logic with exponential backoff to the Finnhub API fetch function. Retry up to 3 times with delays of 2s, 4s, 8s. On final failure, log the error and continue (don't crash the entire worker). Pattern:
   ```python
   for attempt in range(3):
       try:
           # fetch logic
           break
       except Exception as e:
           if attempt == 2:
               log(f"ERROR: Finnhub API failed after 3 attempts: {e}")
               return []
           time.sleep(2 ** (attempt + 1))
   ```

4. Add incremental fetching. Instead of fetching all news from 2021-2026 on every run:
   a. Before fetching, query Supabase for the most recent `created_at` timestamp in the `inbox` table where `source` matches the Finnhub source identifier.
   b. Use that timestamp as the `from` parameter in the Finnhub API call.
   c. If no existing records, fall back to fetching the last 30 days only (not 5+ years).
   d. This prevents hammering Finnhub's 60 calls/min rate limit.

5. Fix the source field — verify the worker uses a consistent source identifier when writing to the `inbox` table. If it uses `source='press_release'` but should use `source='finnhub_news'` or `source='news'`, fix it to be accurate and distinguishable from actual press releases.

6. Add proper logging:
   - Log how many articles were fetched from Finnhub
   - Log how many were new (not duplicates)
   - Log how many were successfully stored
   - Log any Finnhub API errors with status codes

7. Verify the Finnhub API key is read from `os.environ.get('FINNHUB_API_KEY')` and NOT hardcoded. The previous audit found a hardcoded key — if it's still there, remove it and use only the env var. Fail clearly if the env var is missing.

8. Test that the script can be invoked with `python scripts/data-fetchers/news_worker.py` without crashing (it will fail on API calls without env vars, but it should print a clear error message, not a stack trace).
