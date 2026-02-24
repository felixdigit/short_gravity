TARGET: .
---

MISSION:
Fix the CHECK constraint risk in ALL international filing workers (ITU, ISED, OFCOM) and verify ULS worker compliance. The `fcc_filings` table has a CHECK constraint: `filing_system IN ('ICFS', 'ECFS', 'ELS')`. Any worker that tries to insert a different value WILL crash with a PostgreSQL constraint violation.

DIRECTIVES:

1. Read ALL four international/regulatory filing workers:
   - `scripts/data-fetchers/itu_worker.py`
   - `scripts/data-fetchers/ised_worker.py`
   - `scripts/data-fetchers/ofcom_worker.py`
   - `scripts/data-fetchers/uls_worker.py`

2. For EACH worker, search for where it sets the `filing_system` field when inserting into `fcc_filings`. Verify:
   - `itu_worker.py` MUST use `filing_system='ICFS'` (with `file_number` like `'ITU-*'` for identification)
   - `ised_worker.py` MUST use `filing_system='ICFS'` (with `file_number` like `'ISED-*'`)
   - `ofcom_worker.py` MUST use `filing_system='ICFS'` (with `file_number` like `'OFCOM-*'`)
   - `uls_worker.py` MUST use `filing_system='ELS'`

   If ANY worker uses a custom filing_system value like `'ITU'`, `'ISED'`, `'OFCOM'`, or anything NOT in the CHECK constraint list, FIX IT to use the correct value.

3. For each worker, verify the `file_number` prefix convention is correct and consistent:
   - ITU filings: `file_number` starts with `'ITU-SNL-'` or `'ITU-'`
   - ISED filings: `file_number` starts with `'ISED-'`
   - OFCOM filings: `file_number` starts with `'OFCOM-'`
   - ULS/ELS filings: native FCC file numbers (no prefix needed)

4. For each worker, verify the `on_conflict` column used in upsert operations. For `fcc_filings`, the unique constraint is `(filing_system, file_number)`. The upsert must use `on_conflict=filing_system,file_number`.

5. Add a validation guard BEFORE each insert/upsert. Before calling `supabase_request()`, check that `filing_system` is one of `('ICFS', 'ECFS', 'ELS')`:
   ```python
   VALID_FILING_SYSTEMS = {'ICFS', 'ECFS', 'ELS'}
   if record.get('filing_system') not in VALID_FILING_SYSTEMS:
       log(f"ERROR: Invalid filing_system '{record.get('filing_system')}' — must be one of {VALID_FILING_SYSTEMS}")
       continue  # skip this record
   ```

6. For `itu_worker.py`, also verify:
   - HTML table parsing handles empty/malformed rows without crashing
   - AST keyword matching is case-insensitive
   - The worker logs which specific keyword triggered a match

7. For `ised_worker.py`, verify:
   - ISED Drupal API endpoint is still valid
   - Canada Gazette URL construction is correct
   - HTML parsing handles unexpected page structures

8. For `ofcom_worker.py`, verify:
   - Wayback Machine URL construction is correct
   - Timeout for Wayback fetches is appropriate (Wayback can be very slow)
   - Fallback logic when Wayback doesn't have a cached version

9. Test each script can be invoked without crashing: `python scripts/data-fetchers/<script>.py --help` or just a dry import check.
