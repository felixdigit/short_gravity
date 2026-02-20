# XBRL Investigation Report

**Date:** 2026-02-04
**Investigator:** Claude
**Status:** Complete

## Executive Summary

The `content_text` field in the `filings` table stores extracted XBRL metadata instead of human-readable text for 10-Q and 10-K filings. **This is caused by the HTML parser not handling iXBRL format**, which embeds hidden XBRL data within HTML documents.

## Findings

### Scope of Impact

| Form Type | Total | Affected |
|-----------|-------|----------|
| 10-Q | 19 | All 19 |
| 10-K | 6 | All 6 |
| 10-Q/A | 1 | 1 |
| 10-K/A | 3 | All 3 |
| 8-K | 113 | Partially (minor metadata leakage) |

**Total affected: ~29 high-signal filings** (10-Q, 10-K, and their amendments)

### What the Data Looks Like

**Current content_text for 10-Q (2025-11-10):**
```
10-Q 183 183 false 0001780312 Q3 --12-31 http://fasb.org/srt/2025#ChiefExecutiveOfficerMember P0Y
http://fasb.org/us-gaap/2025#SecuredOvernightFinancingRateSofrMember 0001780312
asts:ClassACommonStockMember 2025-07-01 2025-09-30 0001780312 2023-12-31 0001780312...
```

This is XBRL semantic data (CIK numbers, member references, date ranges) - not readable text.

**Expected content_text:**
```
UNITED STATES SECURITIES AND EXCHANGE COMMISSION Washington, D.C. 20549 FORM 10-Q
QUARTERLY REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934
For the quarterly period ended September 30, 2025...
```

### Root Cause

**Location:** `scripts/data-fetchers/filing_worker.py:101-121`

```python
def extract_text_from_html(html: str) -> str:
    # Remove script and style tags
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    ...
```

**Problem:** Modern 10-Q/10-K filings use **Inline XBRL (iXBRL)** format:

1. The document contains a `<div style="display:none">` section with **massive XBRL metadata**:
   - Context definitions (`<xbrli:context>`)
   - Unit definitions (`<xbrli:unit>`)
   - Hidden facts (`<ix:hidden>`)
   - Schema references

2. This hidden section is ~100KB+ of pure XBRL data

3. The current parser:
   - Correctly strips `<script>` and `<style>` tags
   - Does NOT strip `display:none` content
   - Does NOT recognize XBRL namespaced tags
   - Results in XBRL metadata text being extracted

### Document Structure Analysis

SEC 10-Q filing index shows:
```
Document: asts-20250930.htm (iXBRL) - 3.4MB
Complete submission: 0001193125-25-274391.txt - 12MB
```

The primary document is flagged as `iXBRL` in the SEC's index page.

## Recommended Fix

### Option A: Enhanced HTML Parser (Recommended)

Add iXBRL-aware parsing to `extract_text_from_html()`:

```python
def extract_text_from_html(html: str) -> str:
    """Extract text from HTML/iXBRL, removing tags and XBRL metadata."""

    # Remove display:none sections (contains XBRL hidden data)
    text = re.sub(r'<div[^>]*style="[^"]*display:\s*none[^"]*"[^>]*>[\s\S]*?</div>', '', html, flags=re.IGNORECASE)

    # Remove ix:header sections (XBRL metadata)
    text = re.sub(r'<ix:header>[\s\S]*?</ix:header>', '', text, flags=re.IGNORECASE)

    # Remove script and style tags
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", text, flags=re.IGNORECASE)

    # Remove all HTML/XML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Decode common HTML entities
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = re.sub(r"&#\d+;", "", text)

    # Clean up whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text
```

**Pros:**
- Minimal code change
- No new dependencies
- Works for all form types

**Cons:**
- Regex-based, may need tuning for edge cases

### Option B: Use BeautifulSoup

```python
from bs4 import BeautifulSoup

def extract_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')

    # Remove hidden elements
    for hidden in soup.select('[style*="display:none"], [style*="display: none"]'):
        hidden.decompose()

    # Remove XBRL namespace elements
    for xbrl in soup.find_all(lambda tag: tag.name and ':' in tag.name):
        if tag.name.startswith(('ix:', 'xbrli:', 'link:', 'xbrldi:')):
            tag.decompose()

    return soup.get_text(separator=' ', strip=True)
```

**Pros:**
- More robust parsing
- Handles malformed HTML

**Cons:**
- New dependency (beautifulsoup4, lxml)
- Slower performance

### Option C: Fetch Different Document Format

SEC provides multiple formats for filings. We could:
1. Look for a plain `.txt` version of the filing
2. Use the "Complete submission" file and extract specific sections

**Pros:**
- Cleaner source data

**Cons:**
- Not all filings have alternate formats
- More complex URL logic

## Recommended Action Plan

1. **Implement Option A** (Enhanced regex parser)
2. **Test on sample filings** before deployment
3. **Reprocess affected filings** (~29 filings with `form IN ('10-Q', '10-K', '10-Q/A', '10-K/A')`)

### Reprocessing Query

```sql
-- Mark affected filings for reprocessing
UPDATE filings
SET status = 'pending_reprocess'
WHERE form IN ('10-Q', '10-K', '10-Q/A', '10-K/A');
```

Then run worker with `--reprocess` flag after deploying the fix.

## Impact Assessment

- **Summaries are NOT affected** - Claude generates summaries from the content, and summaries look correct
- **Full-text search is degraded** - Searching for business terms in content_text won't find 10-Q/10-K filings
- **RAG quality reduced** - Research queries won't return relevant 10-Q/10-K content

## Priority

**Medium-High** - The summary functionality (primary use case) works. Full-text search on high-signal filings is broken.
