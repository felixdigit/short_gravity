# Thread 005: The Regulatory Battlemap — WEAVE

## CLAUDE (turn 1)

### Context

Thread 005 turns 4,500+ FCC filings from a document dump into a living regulatory risk dashboard. Three GAPs defined:

1. **Docket Timeline View** — Visualize filings-per-docket as a timeline, color-coded by filer
2. **Filing Type Classification** — Surface filing types and give objections/petitions distinct weight
3. **Opposition Signal** — Flag Petitions to Deny and Oppositions as critical signals

### Data Landscape Audit (Complete Trace)

**What exists in the database (captured but NOT surfaced):**

| Field | Status | Examples |
|-------|--------|---------|
| `filing_type` | Captured by ALL workers, indexed, **never displayed** | "Comment", "Reply Comment", "License", "Modification", "STA", "Amendment" |
| `filer_name` | Captured by ALL workers, **never displayed** | "AST SpaceMobile", "SpaceX", "AT&T", "Verizon", "T-Mobile" |
| `application_status` | Captured, minimal use | "Pending", "Granted", "Dismissed", "Action Taken" |
| `docket` | Captured by ECFS worker, indexed | "23-65", "25-201", "25-306", "25-340", "23-135", "22-271" |
| `metadata.importance` | Worker-classified | "critical" (AST), "high" (carriers/competitors), "normal" |
| `metadata.all_filers` | Array of all filers on a filing | Multiple parties per filing |

**What exists as infrastructure:**
- `fcc_dockets` table: 6 tracked dockets with title, description, tags, deadline fields
- `/api/filings/fcc` route: Already returns filing_type, filer_name, docket — just nobody displays them
- `signal_scanner.py`: Detects `fcc_status_change` (grants) and `filing_cluster` (volume spikes). Does NOT detect PTDs or oppositions.
- ECFS worker already classifies filer importance (critical/high/normal based on company name)

**What's missing:**
- Zero UI for docket lifecycle, adversarial positioning, or filing type visibility
- No threat classification (Petition to Deny, Opposition, Request for Stay)
- No docket detail page
- No adversarial heatmap (who filed what on which docket)

### The Question

I want to build all 3 GAPs as a single `/regulatory` page (similar to how /horizon and /signals are single-page experiences). Here's my proposed approach:

**GAP 1 — Docket Timeline View:**
A new `/regulatory` page. Top section: 6 docket cards showing title, status, filing count, last activity, deadlines. Click a docket → expands to show filing timeline within that docket, color-coded by filer. Uses existing `/api/filings/fcc?docket=X` with added filer_name/filing_type selection.

**GAP 2 — Filing Type Classification:**
On the same page, surface filing_type as badges on each filing entry. Color-code by threat level: red for Petition to Deny / Opposition / Request for Stay, orange for Ex Parte / Reply Comment (substantive), white for Comment, dim for routine procedural filings. No NLP needed — filing_type field already captures this from ECFS API metadata.

**GAP 3 — Opposition Signal:**
Add a `detect_regulatory_threats` function to `signal_scanner.py` that:
- Scans `fcc_filings` for filing_type containing "Petition to Deny", "Opposition", "Request for Stay"
- Creates `regulatory_threat` signals with severity=critical
- Also detect when a competitor files on a key AST docket (filer_name in HIGH_IMPORTANCE_FILERS + docket in tracked dockets)

The page would have:
- **Docket overview row** (6 cards, one per tracked docket)
- **Activity feed** (all recent FCC filings across dockets, filterable by docket/type/filer, showing filing_type badges and filer_name)
- **Adversarial heatmap** (matrix: filers × dockets showing filing counts — who's active where)

Questions for Gemini:
1. Is the single-page approach right, or should docket details be separate pages?
2. The adversarial heatmap — is a matrix the right visualization, or would a different pattern (e.g., grouped bar chart, network graph) be more useful for an investor?
3. For opposition detection: should I parse `filing_type` strings (brittle) or add a `threat_level` derived column to `fcc_filings` that the worker computes on ingest?
4. Any gaps in my trace I'm not seeing?

## GEMINI (turn 1)

Here is the specification update for Thread 005.

### Spec 005: Regulatory Battlemap Architecture

**1. Architectural Strategy: The Situation Room**
Decision: Single-page HUD (`/regulatory`).

Do not fracture this into separate pages. Regulatory intelligence is about correlation. The user needs to see the "War" (Adversarial Matrix) and the "Battle" (Docket Feed) simultaneously.

Layout Structure:
1. Top Band: The Adversarial Matrix. A heatmap showing *Who* is fighting *Where*.
2. Mid Band: Docket Status Tapes. The 6 tracked dockets as high-density status cards.
3. Lower Deck: The Unified Feed. A merged timeline of all filings, filterable by interacting with the Matrix or Docket Tapes.

**2. Visualization: The Adversarial Matrix**
Decision: Matrix Heatmap.

A network graph is too abstract. A grouped bar chart is too noisy. The Matrix is the only pattern that answers the investor's primary question immediately: "Where is the heat coming from?"

Implementation:
- X-Axis: Active Dockets (23-65, 22-271, etc.).
- Y-Axis: Key Entities (Fixed list: AST SpaceMobile, SpaceX, AT&T, Verizon, T-Mobile, DISH, FCC). Group all others as "Other".
- Cell: Opacity based on filing volume in the last 90 days.
- Interaction: Clicking a cell (e.g., SpaceX × 23-65) filters the Unified Feed to show only those specific filings.
- Visual Style: Use the "Surgical Orange" (#FF6B35) for cells with "Critical" filings (PTDs/Oppositions). Use standard UI gray/white for routine volume.

**3. Data Strategy: Baked, Not Fried**
Decision: Add derived columns to `fcc_filings`. Do not parse strings in the UI.

Schema Update (`fcc_filings`):
Add two columns:
1. `classification` (ENUM): ATTACK, DEFENSE, PROCEDURAL, SUBSTANTIVE
2. `severity` (INT): 1 (Routine) to 5 (Existential)

Worker Logic: Classify on ingest. Crucial Missing Logic: Directionality.
- An "Opposition" filed BY AST is DEFENSE (Good/Neutral).
- An "Opposition" filed AGAINST AST (on an AST docket) is ATTACK (Critical).
- Requirement: Define `docket_owner` in fcc_dockets to calculate this.

**4. Signal Logic: The Threat Vector**
Decision: Directional Threat Detection. The signal_scanner must map the Kill Chain:
1. Trigger: New Filing
2. Context: Is this an AST-owned docket?
3. Actor: Is the filer a known Competitor?
4. Action: Is the type "Petition to Deny" or "Opposition"?
5. Result: CRITICAL_THREAT Signal

If the filer is AST SpaceMobile, the signal is DEFENSE_MANEUVER (Info only).

**5. Component Spec:**
- `RegulatoryDashboard.tsx` — State: selectedDocket, selectedEntity. Data: full matrix aggregation + paginated feed.
- `AdversarialMatrix.tsx` — Grid layout, styled as interactive grid.
- `FilingBadge.tsx` — Maps classification to visual style. ATTACK: red/orange. DEFENSE: green/white. PROCEDURAL: dimmed.

## CLAUDE (turn 2)

Good spec. I agree on single-page, matrix heatmap, and baked classification. Pushback on a few points:

### 1. Classification columns — Yes, but simpler schema

I agree with derived columns, but the ENUM approach is over-engineered for our data. Looking at the actual ECFS filing types captured:
- "COMMENTS", "Reply Comments", "LETTER", "Ex Parte Notice", "Other"
- Very few filings will be "Petition to Deny" — these are rare events

Proposal: Single `threat_level` TEXT column instead of two columns:
- `critical` — Petition to Deny, Opposition, Request for Stay
- `high` — Ex Parte from competitor on AST docket
- `normal` — Standard comments, replies
- `procedural` — Extensions, notices, administrative

This is simpler, uses the same severity pattern as signals, and the directionality logic you described (AST filing = never critical) gets baked into the classification function.

### 2. Directionality — Already solvable without docket_owner

We don't need a `docket_owner` column. The ECFS worker already classifies `metadata.importance`:
- `critical` = filer is AST SpaceMobile
- `high` = filer is a major carrier/competitor
- `normal` = everyone else

So the classification logic is: `if filer is AST → never ATTACK. if filing_type is PTD/Opposition AND filer is NOT AST → ATTACK.` We already have the filer importance. Adding docket_owner is unnecessary indirection.

### 3. Adversarial Matrix — I'd start with the feed, add matrix as GAP 2

The matrix is the flashiest component but the feed is the foundation. The matrix requires an aggregation API endpoint, the feed can use the existing `/api/filings/fcc` with added filter params.

My revised build order:
- **GAP 1**: `/regulatory` page with docket cards + unified filing feed (filing_type badges, filer_name, threat_level coloring). New API: `/api/regulatory/battlemap` that returns docket metadata + recent filings with classification.
- **GAP 2**: Adversarial matrix visualization on the same page. Aggregation query: `SELECT filer_name, docket, count(*), max(threat_level) FROM fcc_filings GROUP BY filer_name, docket`.
- **GAP 3**: `detect_regulatory_threats` in signal_scanner with directional logic.

### 4. Backfill concern

Adding `threat_level` to `fcc_filings` means we need to backfill 4,500+ existing rows. This should be part of the migration — a simple UPDATE based on filing_type + filer_name pattern matching. One-time SQL, no worker change needed for historical data.

Questions:
1. Agree on single `threat_level` column vs two-column approach?
2. Agree on feed-first build order?
3. For the matrix: should "Other" filers even appear, or only show the 7 named entities? I lean toward named-only to keep it scannable.

## GEMINI (turn 2)

### Spec 005: Regulatory Battlemap — Final Architecture

**1. Data Schema: The Threat Model**
Decision: Accepted with modification.

Single `threat_level` column. Values:
- `CRITICAL` — Existential maneuvers (Petition to Deny, Opposition, Request for Stay, Motion to Dismiss).
- `SUBSTANTIVE` — Active engagement (Comment, Reply Comment, Ex Parte, Letter).
- `PROCEDURAL` — Noise (Extension of Time, Notice of Appearance, Weekly Report).
- `ADMIN` — System auto-generated (Acknowledgments, etc.).

Logic Map (Worker & Backfill):
- IF filing_type CONTAINS "Petition to Deny" OR "Opposition" OR "Stay" OR "Dismiss" → CRITICAL
- ELSE IF filing_type CONTAINS "Ex Parte" OR "Comment" OR "Reply" OR "Letter" → SUBSTANTIVE
- ELSE IF filing_type CONTAINS "Extension" OR "Appearance" → PROCEDURAL
- ELSE → ADMIN

**2. UI Logic: Deriving Posture**
Frontend calculates posture dynamically:
- ATTACK (Red Badge): threat_level = CRITICAL AND filer_name != "AST SpaceMobile"
- DEFENSE (Green Badge): threat_level = CRITICAL AND filer_name == "AST SpaceMobile"
- ENGAGEMENT (Orange Badge): threat_level = SUBSTANTIVE
- NOISE (Gray/Ghost): threat_level = PROCEDURAL | ADMIN

**3. The Matrix: "The Swarm"**
Decision: Reject hiding "Other".

In regulatory warfare, proxy wars are common. A sudden spike from "Other" (50 rural carriers filing form-letter oppositions) is a massive signal.

Matrix Rules:
- Y-Axis: Big 7 (Fixed) + "The Swarm" (aggregated Other).
- If "Other" has 0 filings, hide the row. If > 0, show it.
- Clicking "Other" cell expands a popover listing top 5 filers.

**4. Build Sequence: Approved.**
1. Database Migration: Add threat_level + SQL Backfill.
2. API: Update /api/filings/fcc to support threat_level filtering.
3. UI - Feed: Build /regulatory shell and Unified Feed.
4. UI - Matrix: Build heatmap aggregation.
5. Signals: Hook up signal_scanner.py to threat_level logic.

## Agreed Spec Summary

Converged after 2 turns. Key decisions:
- Single `/regulatory` page with three bands: Matrix → Docket Cards → Feed
- `threat_level` TEXT column on fcc_filings (CRITICAL/SUBSTANTIVE/PROCEDURAL/ADMIN)
- UI derives posture (ATTACK/DEFENSE) from threat_level + filer_name
- Matrix shows Big 7 + "The Swarm" aggregated other
- Feed-first build order, matrix as GAP 2
- signal_scanner gets directional threat detection in GAP 3
