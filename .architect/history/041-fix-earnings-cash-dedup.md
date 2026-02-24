TARGET: .
---

MISSION:
Resolve the earnings_worker redundancy and cash_position_worker duplication issues. Determine if earnings_worker.py is redundant with transcript_worker.py and if cash_position_worker.py duplicates widget_data_worker.py. Disable or fix accordingly.

DIRECTIVES:

1. Read the ENTIRE `scripts/data-fetchers/earnings_worker.py` file.

2. Read the ENTIRE `scripts/data-fetchers/transcript_worker.py` file.

3. Compare the two:
   a. What table does earnings_worker write to? (Should be `earnings_transcripts` after the fix. If it writes to anything else, it's still broken.)
   b. What table does transcript_worker write to?
   c. Do they fetch from the same source (Finnhub vs roic.ai)?
   d. Do they overlap in functionality?

4. Decision logic:
   - If earnings_worker and transcript_worker write to DIFFERENT tables with DIFFERENT data → keep both
   - If they write to the SAME table or have significant overlap → disable earnings_worker by adding `exit(0)` at the top with a comment: `# DISABLED: Functionality covered by transcript_worker.py`
   - If earnings_worker was fixed to write to `earnings_transcripts` but transcript_worker writes to `inbox` → they serve different purposes, keep both but document the distinction

5. Read the ENTIRE `scripts/data-fetchers/cash_position_worker.py` file.

6. Read the ENTIRE `scripts/data-fetchers/widget_data_worker.py` file.

7. Compare cash_position_worker vs widget_data_worker:
   a. Does widget_data_worker already sync cash_position data?
   b. Do they write to the same table?
   c. Would running both cause data conflicts or duplicates?

8. Decision logic:
   - If widget_data_worker fully covers cash_position functionality → disable cash_position_worker
   - If they complement each other (different data sources or granularity) → keep both but document
   - If cash_position_worker provides more detailed data → keep it as the primary, let widget_data_worker read from its output

9. For any disabled worker, also check the corresponding GitHub Actions workflow in `../../.github/workflows/`. If the worker is disabled:
   - Read the workflow YAML
   - Add `if: false` to the job to prevent it from running, OR
   - Comment out the cron trigger and add a comment explaining why

10. Document all decisions in `scripts/data-fetchers/WORKER_STATUS.md`:
    ```
    # Worker Status

    ## Active Workers
    - [list all active workers with brief purpose]

    ## Disabled Workers
    - earnings_worker.py — DISABLED: [reason]
    - cash_position_worker.py — DISABLED: [reason] (if applicable)

    ## Notes
    - [any important operational notes]
    ```
