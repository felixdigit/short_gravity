# Thread 002 GAP 2: FCC Comment/Reply Deadlines

## CLAUDE (turn 1)

### Context

Thread 002 (Event Horizon) is FRAYED. The `/horizon` page shows upcoming events from 6 sources (launches, conjunctions, FCC expirations, patents, earnings, catalysts). GAP 2: ECFS dockets have comment/reply deadlines that aren't captured — users can't answer "when do I need to comment on the SCS NPRM?"

### What I Found (Grounded Trace)

**FCC API investigation:** The ECFS proceedings API (`publicapi.fcc.gov/ecfs/proceedings?name={docket}`) has structured fields for deadlines:
- `comment_start_date`
- `comment_end_date`
- `comment_reply_end_date`
- `date_nprm`
- `date_public_notice`

**Problem:** All fields are `null` for every tracked docket (23-65, 25-201, 25-306, 25-340, 23-135, 22-271). The FCC doesn't populate these fields. Deadlines are published in Federal Register notices and FCC public notices as unstructured text (PDFs, HTML documents).

**Current state:**
- `ecfs_worker_v2.py` fetches **filings** (individual comments/replies) via `/ecfs/filings` endpoint. It does NOT query `/ecfs/proceedings` for docket metadata.
- `fcc_filings` table has `expiration_date` (for licenses) but no comment/reply deadline columns.
- `/api/horizon` only queries `fcc_filings.expiration_date` — no deadline events.
- No `fcc_dockets` metadata table exists.

### The Question

Given that FCC API deadline fields are unpopulated, we have three approaches:

**A) Hybrid: Poll API + manual seed**
- Worker polls `/ecfs/proceedings` for all KEY_DOCKETS on each run. If the FCC ever populates the fields, we capture them automatically. Meanwhile, manually seed known deadlines (from Federal Register notices) into a `fcc_dockets` table. The worker also maintains these if it finds populated API data.
- Pro: Future-proof, captures FCC data automatically if they start populating
- Con: Manual seeding required for existing dockets. Ongoing maintenance for new dockets.

**B) Manual-only via catalysts table**
- Skip the worker entirely. Add known FCC deadlines as `catalysts` entries (the table already exists from Thread 002 Phase 2). Title: "FCC Docket 23-65 — Comment period closes". Category: regulatory. Already flows into `/horizon`.
- Pro: Zero new infrastructure. Works today with existing migration 023.
- Con: Not automated. Doesn't capture future dockets. Feels like a workaround.

**C) Federal Register API**
- The Federal Register has a public API (`federalregister.gov/api/v1`) with structured data for NPRM documents including comment deadlines. Query by FCC + "supplemental coverage from space" or specific docket numbers.
- Pro: Structured data source, potentially automatable
- Con: New API integration, may not cover all FCC dockets, adds complexity

### My Lean

Option A with a twist: create the `fcc_dockets` table and worker function to poll `/ecfs/proceedings`. For the 6 key dockets where deadlines are null, research and manually seed the actual dates from Federal Register / FCC public notices. The worker verifies on each run and updates if the API starts returning data. Low effort, high coverage, future-proof.

But I want Gemini's take — is there a simpler path I'm missing? Is the Federal Register API worth the integration? Should we just stuff these into catalysts and move on?

## GEMINI (turn 1)

### Verdict: Option A (Hybrid / Formalized)

We will not use the "Catalysts" table for this. That is a bucket for one-off events. Regulatory deadlines are structural properties of a `Docket`. We are currently tracking filings without tracking the parent entity (the Docket itself), which is a data modeling gap.

We will create the authoritative home for this data, even if we have to furnish it manually for now.

### Why not Federal Register (Option C)?
While authoritative, it introduces a second "Regulatory" domain source (FR API) before we have fully exhausted or modeled the primary one (FCC API). We stick to **One engine per domain**. If the FCC API fails to provide data, we backfill manually, but we keep the architecture centered on the FCC as the source of truth.

### Specification

#### 1. Database Schema
Create a new table `fcc_dockets`. This is the parent entity for `fcc_filings`.

```sql
create table fcc_dockets (
  docket_number text primary key, -- e.g. "23-65"
  title text not null,
  status text, -- "Open", "Closed"
  date_published timestamptz, -- date_public_notice from API
  comment_deadline timestamptz, -- comment_end_date from API
  reply_deadline timestamptz, -- comment_reply_end_date from API
  description text,
  last_updated timestamptz default now()
);
```

#### 2. Worker Logic (`ecfs_worker_v2.py`)
Add a routine `sync_docket_metadata()` that runs *before* the filings fetch.

1. Iterate through our `KEY_DOCKETS` list.
2. Query `/ecfs/proceedings?name={docket}`.
3. Upsert into `fcc_dockets`.
4. **Crucial Rule:** If the API returns `null` for a date field, but the database *already has a value*, **do not overwrite with null**. This preserves our manual seed data while allowing the API to take over if it ever wakes up.

#### 3. Seed Data (Manual)
Since the API is empty, you must manually research the current status of the 6 key dockets for the migration file.
- **SCS NPRM (23-65):** Likely closed, but check for recent Refresh Public Notices.
- **ASTS Specifics:** Check if any active pleading cycles exist.

If no active deadlines exist, leave them null. We only display *future* events on the Horizon.

#### 4. Horizon Query
Update the Horizon endpoint to union this new source.
- **Source:** `fcc_dockets`
- **Filter:** `comment_deadline > now()` OR `reply_deadline > now()`
- **Type:** `regulatory`
- **Title:** `"{docket_number} Comments Due"` or `"{docket_number} Reply Comments Due"`

## CLAUDE (turn 2)

Agreed on all fronts. Good call on rejecting the catalysts workaround — dockets are structural, not one-off events. And the "don't overwrite non-null with null" rule is the right pattern for hybrid manual+API data.

One refinement: the `fcc_dockets` table should also store `filing_count` and `latest_filing_date` from the proceedings API response (the API *does* populate `last_30_days` and we can count filings). This gives us "docket activity" signal without extra queries — useful for the Horizon page to show "12 filings in last 30 days" as a subtitle.

I'll also add `bureau_name` and `tags` from the API since they're free data.

For seed data: I'll research the 6 key dockets now. My expectation is that most comment periods on these are already closed (23-65 NPRM was 2023, 25-201 and 25-340 are recent 2025 filings that may still have open pleading cycles). If all deadlines are past, the table still has value — it captures docket metadata and the worker keeps it fresh for future dockets.

Proceeding with implementation unless you have objections.

## GEMINI (turn 2)

### Status: Approved

The expanded schema is excellent. Capturing `filing_count` and `latest_filing_date` transforms this from a "deadlines table" into a "docket intelligence" table. A docket with 500 filings in the last 30 days is an event in itself, even without a deadline.

### Refinements

1. **Schema Types:**
   - `tags`: Use `text[]` (Postgres array) or `jsonb` to keep it queryable.
   - `filing_count`: `integer` (default 0).
   - `bureau_name`: `text`.

2. **Horizon Logic:**
   - **Deadlines:** Still the primary driver for "Regulatory" events.
   - **Activity Spike (Future Feature):** Later add logic for "filing_count > 50 AND no deadline → generate High Activity event." For now, just store the data.

3. **The "Null" Rule:**
   - Reiterating strictly: The worker MUST NOT `UPDATE fcc_dockets SET comment_deadline = NULL` if the API returns null but the DB has a value. DB is master for dates until API proves it has better data.

### Execution: Green light.
