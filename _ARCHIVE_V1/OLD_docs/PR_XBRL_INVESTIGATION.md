# PR Request: Investigate XBRL/XML Storage in SEC Filings Workers

## Issue Summary

The `content_text` field in the `filings` table is storing raw XBRL/XML markup for 10-Q and 10-K filings instead of human-readable text. This affects the usability of our RAG archive for research queries.

## Evidence

Query result from `filings` table for 10-Q (2025-11-10):

```
content_text starts with:
<?xml version="1.0" encoding="US-ASCII"?>
<!--XBRL Document Created with Workiva...
<html xmlns="http://www.w3.org/1999/xhtml"...
```

The `summary` field correctly contains extracted information, but the raw `content_text` is not readable.

## Scope of Investigation

1. **Audit affected filings**
   - How many filings have XBRL/XML in `content_text`?
   - Which form types are affected? (10-Q, 10-K, others?)
   - Are 8-K filings also affected or do they store clean text?

2. **Review filing_worker.py**
   - Location: `scripts/data-fetchers/filing_worker.py`
   - How is content being fetched from SEC EDGAR?
   - Is there a parsing step that should extract text from XBRL?
   - Are we fetching the wrong document URL (XBRL vs HTML/TXT)?

3. **SEC EDGAR document structure**
   - 10-Q/10-K filings often have multiple document formats:
     - Primary document (HTML/text)
     - XBRL instance document (XML)
     - iXBRL (inline XBRL embedded in HTML)
   - Confirm which document we're currently fetching
   - Determine which document should be fetched for readable text

4. **Proposed solutions to evaluate**
   - Option A: Fetch the correct document format (non-XBRL) from EDGAR
   - Option B: Parse XBRL/iXBRL to extract readable text
   - Option C: Use SEC's "filing-documents.xml" to find the right attachment
   - Option D: Combination approach based on form type

## Files to Review

```
scripts/data-fetchers/
├── filing_worker.py      # Main worker - check fetch/parse logic
├── sec_fetcher.py        # If exists - SEC API interaction
└── .env                  # API configs
```

## Database Query to Run

```sql
-- Check content_text patterns
SELECT
  form,
  filing_date,
  LEFT(content_text, 100) as content_preview,
  CASE
    WHEN content_text LIKE '%<?xml%' OR content_text LIKE '%<html xmlns%' THEN 'XBRL/XML'
    WHEN content_text LIKE '%UNITED STATES%SECURITIES%' THEN 'Clean Text'
    ELSE 'Unknown'
  END as content_type
FROM filings
WHERE form IN ('10-Q', '10-K', '8-K')
ORDER BY filing_date DESC
LIMIT 20;

-- Count by type
SELECT
  form,
  COUNT(*) as total,
  SUM(CASE WHEN content_text LIKE '%<?xml%' THEN 1 ELSE 0 END) as xml_count
FROM filings
GROUP BY form
ORDER BY total DESC;
```

## Expected Outcome

1. Report on which filings are affected
2. Root cause identification in the worker code
3. Recommended fix with implementation plan
4. Assessment of whether historical filings need reprocessing

## Priority

Medium - The `summary` field provides usable data, but full-text search on `content_text` is degraded for affected form types.

## Contact

Assign to: Claude (via `/research-filings` skill or direct investigation)
Requester: Gabriel
Date: 2026-02-04
