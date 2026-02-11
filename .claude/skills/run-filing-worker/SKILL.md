---
name: run-filing-worker
description: Run the SEC filing worker to fetch new filings and generate AI summaries
allowed-tools: Bash, Read
---

# Run Filing Worker

Execute the SEC filing worker:

```bash
cd /Users/gabriel/Desktop/short_gravity/scripts/data-fetchers
source .env
python3 filing_worker.py
```

The worker will:
1. Fetch recent ASTS filings from SEC EDGAR
2. Check Supabase for existing accession numbers (skip duplicates)
3. Generate Claude AI summaries for new filings
4. Store results in Supabase

Check logs at `/tmp/filing_worker.log` if running via cron.
