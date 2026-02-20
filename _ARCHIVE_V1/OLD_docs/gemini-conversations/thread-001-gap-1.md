# Thread 001: Signal-to-Source — GAP 1

## CLAUDE (turn 1) — THE TRACE

I'm Claude, the coding agent for Short Gravity. You're Gemini, our architecture analyst. We're executing the Thread System. I'm sending you a grounded trace with a GAP. Your job: critique the trace, then spec the transition that bridges the GAP.

### Thread Context

**Thread 001: Signal-to-Source**
- **Intent:** "Something just happened. Is it real? Show me the primary source document."
- **Status:** BROKEN
- **North Star:** Signal detection → source document with proof in under 30 seconds.

### The Grounded Trace

Here's what ACTUALLY happens today when a user tries to go from signal to source:

```
[User lands on /signals]
  → sees signal cards (severity, category, title, time) ✅
  → clicks a signal card
  → [Signal detail panel opens on right — 360px, non-modal] ✅
    → sees: title, severity, category, description, metrics, confidence ✅
    → scrolls to EVIDENCE section
    → sees source references as STATIC TEXT:
      [FCC FILING] "STA Application — 2024-06-15"
      [SEC FILING] "8-K — 2024-06-10"
    → ❌ GAP: Cannot click. No onClick. No href. Dead end.
    → User wants to read the actual filing. Thread snaps here.
```

### What Exists (infrastructure audit)

**Signal data model:**
Each signal has a `source_refs` JSONB array:
```json
[
  {"table": "fcc_filings", "id": "0005678901", "title": "STA Application", "date": "2024-06-15"},
  {"table": "filings", "id": "0001193125-24-123456", "title": "8-K", "date": "2024-06-10"}
]
```
- `table`: filings, fcc_filings, patents, x_posts, press_releases, earnings_transcripts, short_interest
- `id`: human-readable identifier (accession_number, file_number, patent_number, source_id)
- `title` and `date`: display text

**Document API (`/api/widgets/document`):**
Accepts IDs in format `{type}-{uuid}`:
- `sec-{uuid}` → SEC filing (form, date, url, summary, content_text)
- `fcc-{uuid}` → FCC filing (title, date, source_url, ai_summary, file_number)
- `pr-{uuid}` → Press release (title, url, summary, content_text)
- `x-{uuid}` → X post (author, content, url, sentiment)
- `call-{uuid}` → Earnings call (title, content)
- `signal-{uuid}` → Nested signal (source_refs + metrics)
- `patent-{uuid}` → NOT IMPLEMENTED (returns 404)

**DocumentViewer component:**
Full modal document viewer that:
- Fetches from `/api/widgets/document?id={type}-{uuid}`
- Renders title, date, badge, summary, full content
- Has external URL link
- Escape key to close
- ONLY used in ActivityFeed widget on /asts terminal page

**The mismatch:**
- Signal scanner stores IDs as human-readable strings (accession_number like `0001193125-24-123456`, file_number like `0005678901`)
- Document API expects database UUIDs
- No conversion logic exists

### What I Need From You

1. **Critique the trace.** Is there a better path I'm missing? Is the GAP correctly identified?

2. **Spec the transition.** How should evidence items become clickable? Options I see:
   - **Option A:** Import DocumentViewer into /signals page. Evidence items click → open DocumentViewer modal. Requires solving the ID mismatch (lookup by accession_number/file_number to get UUID, or change the Document API to accept both).
   - **Option B:** Evidence items navigate to existing pages (/patents for patents, etc.) but most source types don't have dedicated pages.
   - **Option C:** Something else?

3. **The ID bridge.** Signal scanner stores `accession_number`, Document API expects UUID. What's the cleanest solution? Options:
   - Change signal_scanner to store database UUIDs in source_refs
   - Change Document API to accept accession_number/file_number directly
   - Add a lookup endpoint that converts identifier → UUID
   - Change Document API to query by natural key instead of UUID

4. **Scope.** Should this GAP fix ONLY make evidence clickable in SignalDetail? Or should it also add DocumentViewer to the /signals page globally (for brain search citations too)?

Be specific. I need to know exactly what to build.

## GEMINI (turn 1)

The GAP is critical and correctly identified.

### The Transition Spec

**Option A, modified for architectural robustness.**

**UX:** When a user clicks an evidence item in SignalDetail, the existing DocumentViewer opens as a full-screen modal displaying the source document.

**The ID Bridge — extend Document API to accept natural keys:**

1. **New method:** `GET /api/widgets/document?table={table_name}&id={natural_id}` — queries by accession_number, file_number, patent_number, etc.
2. **Legacy method:** `GET /api/widgets/document?id={type}-{uuid}` — maintained for backward compatibility (ActivityFeed).
3. **Patent support mandatory** — no more 404 for patents.

**Scope:** This is an architectural upgrade, not a feature patch. DocumentViewer + its API become the single engine for viewing any source document platform-wide. Future consumers (brain citations, briefings) reuse this same pattern.
