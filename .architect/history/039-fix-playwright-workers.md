TARGET: .
---

MISSION:
Harden ALL Playwright-dependent workers against browser automation fragility. These workers (icfs_servicenow_worker, transcript_worker, press_release_worker, patent_worker_v2, ecfs_worker_v2, uls_worker) are the most fragile scripts in the pipeline because they depend on external page structures that can change without notice.

DIRECTIVES:

1. Read ALL of these Playwright-dependent scripts:
   - `scripts/data-fetchers/icfs_servicenow_worker.py`
   - `scripts/data-fetchers/transcript_worker.py`
   - `scripts/data-fetchers/press_release_worker.py`
   - `scripts/data-fetchers/patent_worker_v2.py`
   - `scripts/data-fetchers/ecfs_worker_v2.py`
   - `scripts/data-fetchers/uls_worker.py`

2. For EACH script that uses Playwright, add a **screenshot-on-failure** pattern. Whenever a Playwright operation fails (page navigation, selector wait, content extraction), capture a screenshot before logging the error. Pattern:
   ```python
   try:
       # Playwright operation
   except Exception as e:
       try:
           page.screenshot(path=f"/tmp/debug_{worker_name}_{int(time.time())}.png")
           log(f"DEBUG: Screenshot saved for failure analysis")
       except:
           pass
       log(f"ERROR: {e}")
   ```
   This enables post-mortem debugging when page structures change.

3. For `icfs_servicenow_worker.py` specifically:
   a. Add validation after parsing each filing detail. If critical fields (file_number, filer_name) are empty after regex extraction, log a WARNING and skip the filing rather than inserting garbage data.
   b. Replace the broad `except Exception as e: pass` patterns with proper logging.
   c. Add a counter for parse failures vs successes — log the ratio at the end.

4. For `transcript_worker.py` specifically:
   a. Add fallback selectors for content extraction. Currently waits for `"Good day"` text — add alternative selectors like `"Operator"`, `"Earnings Call"`, or a generic `".transcript-content"` CSS selector.
   b. Log the extraction start position, end position, and extracted character count for debugging.
   c. Add a minimum quality check: if extracted transcript is less than 1000 characters, log a WARNING and skip it (likely a failed extraction).

5. For ALL Playwright scripts, add the `--disable-blink-features=AutomationControlled` browser launch argument to reduce bot detection:
   ```python
   browser = playwright.chromium.launch(
       headless=True,
       args=['--disable-blink-features=AutomationControlled']
   )
   ```

6. For ALL Playwright scripts, verify timeout settings are appropriate:
   - Page navigation timeout: 30-60 seconds (not unlimited)
   - Selector wait timeout: 15-30 seconds (not unlimited)
   - Overall script timeout: should match GitHub Actions workflow timeout

7. For ALL Playwright scripts, verify they properly close the browser in a `finally` block:
   ```python
   try:
       browser = playwright.chromium.launch(...)
       # ... work ...
   finally:
       browser.close()
   ```
   If using context manager (`with`), that's fine too.

8. Verify each script handles the case where Playwright/Chromium is not installed. The error message should be clear: "Playwright not installed. Run: pip install playwright && playwright install chromium"
