# SEC Filing Worker

Polls SEC EDGAR for new ASTS filings, generates AI summaries via Claude, and stores in Supabase.

## Setup

### Environment Variables

```bash
export SUPABASE_SERVICE_KEY="your-service-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
```

Or create a `.env` file:
```
SUPABASE_SERVICE_KEY=your-service-key
ANTHROPIC_API_KEY=your-anthropic-key
```

### Database

Run the migration in Supabase SQL Editor:
```
short-gravity-web/supabase/migrations/001_filings.sql
```

## Usage

### Manual Run

```bash
cd /Users/gabriel/Desktop/short_gravity/scripts/data-fetchers

# With env vars inline
SUPABASE_SERVICE_KEY="..." ANTHROPIC_API_KEY="..." python3 filing_worker.py

# Or source from .env
source .env && python3 filing_worker.py
```

### Cron Setup (Every 15 minutes)

```bash
# Edit crontab
crontab -e

# Add this line:
*/15 * * * * cd /Users/gabriel/Desktop/short_gravity/scripts/data-fetchers && source .env && python3 filing_worker.py >> /tmp/filing_worker.log 2>&1
```

### Launchd (macOS - Preferred)

1. Copy the plist to LaunchAgents:
```bash
cp com.shortgravity.filing-worker.plist ~/Library/LaunchAgents/
```

2. Load the service:
```bash
launchctl load ~/Library/LaunchAgents/com.shortgravity.filing-worker.plist
```

3. Check status:
```bash
launchctl list | grep shortgravity
```

4. View logs:
```bash
tail -f /tmp/filing_worker.log
```

## How It Works

1. Fetches recent filings from SEC EDGAR API
2. Checks Supabase for existing accession numbers (deduplication)
3. For each new filing:
   - Inserts with "processing" status
   - Fetches filing HTML content
   - Extracts text from HTML
   - Calls Claude API to generate summary
   - Updates record with content + summary
4. Rate limits: 2 second delay between filings

## Cost

- ~$0.02 per filing summary (Claude API)
- 145 key filings (10-K, 10-Q, 8-K) = ~$3-5 one-time backfill
- Ongoing: ~$0.50-1.00/month for new filings

## Backfill All Filings

To process all 145 key filings instead of just recent 50:
1. Edit `filing_worker.py`
2. Change `fetch_recent_filings(limit=50)` to `limit=200`
3. Run the worker
