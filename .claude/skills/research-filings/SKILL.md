---
name: research-filings
description: Search SEC and FCC filings to answer questions, find citations, and track regulatory status
user-invocable: true
allowed-tools: Read, Bash, Grep, Glob, WebFetch
---

# Research Filings

Query the ASTS filing archive (SEC + FCC) to answer questions with citations.

## Capabilities

1. **Answer technical questions** — Search filings for specific topics (spectrum, satellites, commercial deals)
2. **Find citations** — Return exact quotes from filings for articles
3. **Track regulatory status** — Check FCC filing statuses, grant dates, pending applications
4. **Timeline analysis** — Find when things happened (filed dates, grant dates, amendments)
5. **Cross-reference** — Connect SEC disclosures to FCC filings

## Database

**SEC Filings** (530 total, 468 with full content)
- Table: `filings`
- Key columns: `form`, `filing_date`, `content_text`, `accession_number`, `summary`
- Forms: 10-K, 10-Q, 8-K, S-1, DEF 14A, 424B5, etc.

**FCC Filings** (666 total, all with structured content)
- Table: `fcc_filings`
- Key columns: `file_number`, `filing_type`, `title`, `description`, `content_text`, `application_status`, `filed_date`, `grant_date`, `call_sign`
- Types: SAT-LOA, SAT-MOD, SAT-AMD, SAT-STA, SES-LIC, etc.

## How to Query

### SEC Filings
```bash
cd /Users/gabriel/Desktop/short_gravity/scripts/data-fetchers
export $(grep -v '^#' .env | xargs)

# Search by keyword
curl -s -G -H "apikey: $SUPABASE_SERVICE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  "$SUPABASE_URL/rest/v1/filings" \
  --data-urlencode "select=form,filing_date,accession_number,content_text" \
  --data-urlencode "content_text=ilike.*KEYWORD*" \
  --data-urlencode "order=filing_date.desc" \
  --data-urlencode "limit=5"

# Get specific filing
curl -s -G -H "apikey: $SUPABASE_SERVICE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  "$SUPABASE_URL/rest/v1/filings" \
  --data-urlencode "select=*" \
  --data-urlencode "accession_number=eq.ACCESSION_NUMBER"

# Recent filings by form type
curl -s -G -H "apikey: $SUPABASE_SERVICE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  "$SUPABASE_URL/rest/v1/filings" \
  --data-urlencode "select=form,filing_date,summary" \
  --data-urlencode "form=eq.8-K" \
  --data-urlencode "order=filing_date.desc" \
  --data-urlencode "limit=10"
```

### FCC Filings
```bash
# Search by keyword
curl -s -G -H "apikey: $SUPABASE_SERVICE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  "$SUPABASE_URL/rest/v1/fcc_filings" \
  --data-urlencode "select=file_number,filing_type,title,filed_date,application_status" \
  --data-urlencode "content_text=ilike.*KEYWORD*" \
  --data-urlencode "order=filed_date.desc" \
  --data-urlencode "limit=10"

# Check filing status
curl -s -G -H "apikey: $SUPABASE_SERVICE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  "$SUPABASE_URL/rest/v1/fcc_filings" \
  --data-urlencode "select=file_number,title,application_status,filed_date,grant_date" \
  --data-urlencode "application_status=neq.null" \
  --data-urlencode "order=filed_date.desc"

# Find granted licenses
curl -s -G -H "apikey: $SUPABASE_SERVICE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  "$SUPABASE_URL/rest/v1/fcc_filings" \
  --data-urlencode "select=file_number,title,grant_date" \
  --data-urlencode "grant_date=not.is.null" \
  --data-urlencode "order=grant_date.desc"

# By filing type
curl -s -G -H "apikey: $SUPABASE_SERVICE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  "$SUPABASE_URL/rest/v1/fcc_filings" \
  --data-urlencode "select=file_number,title,filed_date,application_status" \
  --data-urlencode "filing_type=eq.SAT-LOA" \
  --data-urlencode "order=filed_date.desc"
```

## FCC Filing Types Reference

| Code | Meaning |
|------|---------|
| SAT-LOA | Launch and Operating Authority (initial constellation approval) |
| SAT-MOD | Modification to existing authorization |
| SAT-AMD | Amendment to pending application |
| SAT-STA | Special Temporary Authority (short-term operations) |
| SAT-ASG | Assignment (license transfer) |
| SAT-T/C | Transfer of Control |
| SES-LIC | Earth Station License |
| SES-MOD | Earth Station Modification |
| SES-STA | Earth Station Special Temporary Authority |

## CRITICAL: Source Hierarchy

**For regulatory status questions (FCC, spectrum, authorization):**
1. **ALWAYS check SEC filings FIRST** — Company's own disclosure is legally required to be accurate
2. FCC metadata is incomplete — shows file numbers/dates but NOT what was actually authorized
3. A "grant_date" in FCC data means *something* was granted, not necessarily full authorization
4. Cross-reference: FCC metadata → SEC filing language → actual status

**Never conclude regulatory status from FCC metadata alone.**

## Response Format

When answering questions:

1. **State the answer clearly** first
2. **Cite the source** with filing type, date, and accession number
3. **Quote relevant text** if available
4. **Note any caveats** (e.g., "based on most recent 10-K")
5. **For regulatory questions**: Always include the company's own language from SEC filings

Example:
```
ASTS has commercial agreements with AT&T, Verizon, Vodafone, Rakuten, and others.

Source: 10-K filed 2025-02-28 (0001780312-25-000015)
Quote: "We have entered into commercial agreements with mobile network operators
representing approximately 2.8 billion subscribers globally..."

Note: Subscriber count may have updated in subsequent filings.
```

## Common Research Tasks

### "What did they say about X?"
1. Search SEC filings for keyword
2. Return relevant passages with dates
3. Note if it appears in multiple filings (track evolution)

### "What's the status of FCC application Y?"
1. **FIRST**: Search SEC filings (10-K, 10-Q, 8-K) for company's own regulatory disclosure
2. Then query fcc_filings for metadata (dates, file numbers)
3. Cross-reference — FCC metadata without SEC context can be misleading
4. Quote the company's own language about what they still need

### "Timeline of satellite launches"
1. Search FCC for SAT-STA (launch authorizations)
2. Cross-reference with SEC 8-K filings
3. Build chronological view

### "Find citation for article about Z"
1. Search for most relevant filing
2. Extract exact quote
3. Format as: "Source: [FORM] ([DATE])"
