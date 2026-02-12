# Gemini Spec Output — Loop 4: Intel → Signals Merge

**Recommendation:** Intel → Signals consolidation is the highest-leverage task. The duplicate signal pages are the biggest source of user confusion, and consolidating them into a single, database-powered feed makes the entire platform more coherent and robust.

## Build Spec

### 1. Database Migration
- Run migration 022 to add `category`, `confidence_score`, `price_impact_24h` columns to `signals` table.

### 2. Backend Worker Enhancement (`signal_scanner.py`)
- Add new detectors ported from /intel client-side computation:
  - `detect_patent_regulatory_cross_reference()` — patent↔regulatory correlation
  - `detect_earnings_call_language_shift()` — semantic diff between recent transcripts
- Populate `category` and `confidence_score` for ALL signals (existing + new):

| signal_type | category | confidence_score |
|---|---|---|
| patent_regulatory_cross_ref | Strategic | 0.85 |
| earnings_language_shift | Corporate | 0.75 |
| sentiment_shift | Market | 0.60 |
| filing_cluster | Regulatory | 0.90 |
| fcc_status_change | Regulatory | 0.95 |
| cross_source | Strategic | 0.80 |
| short_interest_spike | Market | 0.70 |
| new_content | Corporate | 0.50 |

### 3. Frontend Redirect
- Add permanent `/intel` → `/signals` redirect in `next.config.mjs`
- Remove obsolete `/intel` page and exclusive API routes
- Update navigation links

### 4. (Stretch) Brain/RAG integration on /signals
- Move the RAG search component from /intel to /signals for feature parity
