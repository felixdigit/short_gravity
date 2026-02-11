# Patent Worker Handoff

## Core Goal

**Build a complete, authoritative source of truth for ASTS patent data.**

Gabriel needs to research, cite, and produce content about ASTS's intellectual property. The database must have:
- Every patent (granted + pending)
- Every claim (the actual legal protection)
- Every figure URL (visual diagrams for content/research)
- All text searchable via RAG

**No approximations. No gaps. Complete data.**

---

## Current State

### Database (`patents` + `patent_claims` tables)

| Metric | Current | Target |
|--------|---------|--------|
| Patents | 270 | 270 ✅ |
| Claims | 3,650 | ~4,000 |
| Patents with claims | 195/270 (72%) | 100% |
| Titles | 270/270 ✅ | Complete |
| Abstracts | 17/270 | Best effort |
| Figure URLs | 95/270 (35%) | **100%** |
| RAG content_text | 269/270 ✅ | Complete |

### What's Working

1. **Unified worker deployed**: `patent_worker_v2.py`
   - Location: `short-gravity-web/scripts/data-fetchers/patent_worker_v2.py`
   - GitHub Actions cron: daily at 6 AM UTC
   - Workflow: `.github/workflows/patent-worker.yml` (60 min timeout)

2. **5-stage pipeline**:
   - Stage 1: Discovery (PatentsView + EPO OPS)
   - Stage 2: Claims fetching
   - Stage 3: Enrichment (Google Patents scraping)
   - Stage 4: Cleanup (B1/B2 dedup, RAG field building)
   - Stage 5: Report

3. **Data sources configured**:
   - PatentsView API (US patents + claims)
   - EPO OPS (international families)
   - Google Patents scraping via Playwright (titles, abstracts, figures)

---

## Remaining Work

### Priority 1: Figure URLs (Gabriel's request)

**175 patents missing figure URLs.** The enrichment stage scrapes Google Patents but:
- Some pages timeout (30s limit)
- Some international patents (KR, JP) load slowly
- Some applications don't have figures yet

**Solution options:**
1. Increase scraper timeout per page (currently 30s)
2. Run dedicated figure-only scraper with longer waits
3. Add retry logic for failed patents
4. Accept that some patents genuinely don't have figures

### Priority 2: Missing Claims (75 patents)

75 patents have no claims in `patent_claims` table. Likely:
- International filings where claims aren't public yet
- Pending applications
- Patents the claims fetcher couldn't find

**Check**: Query which patents are missing claims, cross-reference with their status.

---

## Key Files

```
short-gravity-web/
├── scripts/data-fetchers/
│   ├── patent_worker_v2.py      # Main unified worker
│   └── archive/                 # Deprecated scripts (don't use)
├── .github/workflows/
│   └── patent-worker.yml        # GitHub Actions cron config
```

## Environment (GitHub Secrets)

All set in `felixdigit/short-gravity-web` repo:
- `PATENTSVIEW_API_KEY`
- `EPO_CONSUMER_KEY`
- `EPO_CONSUMER_SECRET`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`

## Quick Commands

```bash
# Check workflow runs
cd short-gravity-web
gh run list --workflow=patent-worker.yml --limit=5

# View logs from last run
gh run view <run_id> --log

# Manual trigger
gh workflow run patent-worker.yml

# Check database stats
cd scripts/data-fetchers
export $(grep -v '^#' .env | xargs)
curl -s -G -H "apikey: $SUPABASE_SERVICE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  "$SUPABASE_URL/rest/v1/patents?select=patent_number&figure_urls=is.null" | python3 -c "import json,sys; print(f'Missing figures: {len(json.load(sys.stdin))}')"
```

---

## Gabriel's Directive

> "We want a source of truth, so yes we want all figures."

Figure URLs are publicly accessible (Google CDN, no auth). They're valuable for:
- Visual content for X posts / articles
- Research reference
- Terminal display (future feature)

**Don't settle for 35% coverage. Get them all.**
