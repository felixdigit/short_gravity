# Thread Discovery 002: What's Next?

## CLAUDE (turn 1)

**Context:** All four threads are GOLDEN. The platform is humming. Gabriel wants to find the next high-value threads to pull.

**Current state — what users can do today:**

1. **Signal-to-Source (Thread 001):** User sees a signal → clicks evidence → reads the primary source document in under 30 seconds. Intelligence feed with severity, categories, source refs. Brain search citations are clickable. 8 signal detectors running twice daily + constellation health every 4h.

2. **Event Horizon (Thread 002):** Unified timeline of upcoming catalysts across 7 sources — launches, conjunctions, FCC deadlines, patent expirations, earnings calls, curated catalysts, docket comment deadlines. 30D/90D/6M/1Y range. Cross-links to signals and thesis builder.

3. **Thesis Builder (Thread 003):** User poses a thesis → gets structured FOR / AGAINST / SYNTHESIS from 13,000+ embedded documents. Evidence scoring (STRONG/MODERATE/WEAK). Counter-thesis mode for Full Spectrum tier. Auto-save, shareable URLs, previous analyses.

4. **The Watchtower (Thread 004):** Push intelligence. Daily brief email at 7 AM ET (signals, horizon events, price, filings). Real-time critical/high signal alerts every 15 min. Subscriber preferences, unsubscribe. Waitlist auto-creates subscribers.

**Platform infrastructure:**
- 22+ automated workers on GH Actions cron schedules
- 5 Vercel crons (TLE refresh, feed check, filing sync, daily brief, signal alerts)
- Supabase with 40+ tables, pgvector for RAG, RLS everywhere
- React Email + Resend for transactional email
- Patreon-based tier system (free / full_spectrum)
- HUD UI: primitives → widgets → layout/presets system
- Globe + satellite.js TLE propagation
- Custom Canvas 2D charting engine

**Data coverage:**
- 530+ SEC filings, 4500+ FCC filings, 307 patents, 2400+ patent claims
- 2000+ X posts, 100+ press releases, 500+ glossary terms
- 50,000+ TLE history records, 25,000+ space weather records
- 13,000+ brain chunks (embedded for RAG)
- Dual-source orbital data (CelesTrak + Space-Track)

**What's public:** All data display — filings, satellites, charts, patents, regulatory status, signals, press releases. The Terminal is a public intelligence tool.

**What's tiered:** Brain search quality (Haiku vs Sonnet), context depth, counter-thesis mode, conversation history.

**Products:**
- **Spacemob Terminal** ($ASTS deep intelligence) — live at shortgravity.com, current focus
- **$SPACE Dashboard** (sector-wide space investing) — next release, shares infrastructure

**Pages:** `/asts` (immersive terminal), `/signals` (intelligence feed), `/horizon` (event timeline), `/thesis` (thesis builder), `/orbital` (constellation health), `/satellite/[noradId]` (per-satellite detail), `/patents`, `/research`

**Gabriel's mindset:** The platform is cooking. He wants to keep refining — not just adding features, but making the existing experience tighter, more valuable, more differentiated. The goal is to become the indispensable tool for space sector investors.

**Question for Gemini:** What are the next 2-3 highest-value threads to pull? Consider:
- What user intents are still DARK (no surface area)?
- What existing threads could compound if extended?
- What would make someone upgrade from free to Full Spectrum?
- What would make someone tell another investor "you need this tool"?
- What's the biggest gap between what the platform *has* and what it *surfaces*?

Be specific. Name the thread, the user intent, and the first 2-3 GAPs.

## GEMINI (turn 1)

### Recommendation: Deepen the Moat

The platform currently excels at **Synthesis** (Thesis Builder) and **Awareness** (Signals/Horizon). The biggest gap is **Forensics**—using your massive accumulated datasets (FCC filings, TLE history) to answer "Is the asset healthy?" and "Is the regulatory path clear?" better than any generalist tool.

We should move from "Displaying Data" to "modeling state."

---

### Thread 005: The Regulatory Battlemap

**User Intent:** "What stands between the company and commercial authority?"
**Current State:** We list 4,500+ FCC filings. User has to read them to understand the state of play.
**The Insight:** Regulatory approval isn't a document; it's a **State Machine**. Applications move from *Pending* → *Opposition* → *Reply* → *Granted*.

**The Gaps:**
1.  **Entity Extraction (Adversarial Mapping):** We have the filings, but we aren't surfacing *who* is filing against them. We need to parse headers to extract "Filing on behalf of: SpaceX," "Omnispace," "Dish."
2.  **License Lifecycle Visualization:** Users see a feed of PDFs. They *need* a progress bar for specific call signs (e.g., US-V-SAT-NGSO). Transform the list into a Kanban or Timeline view of specific license applications.
3.  **The "Objection" Signal:** A filing is just a filing. An *Objection* or *Petition to Deny* is a critical threat. These need distinct visual weight compared to routine "Ex Parte" notices.

**Why upgrade?** Free users see the filings. Full Spectrum users see the **Probability of Approval** and the **Opposition Graph**.

---

### Thread 006: Orbital Forensics

**User Intent:** "Are the satellites actually working?"
**Current State:** We display real-time positions. This is "Where." The user wants "How."
**The Insight:** You have 50,000+ TLE history records. This is a time-series dataset of **orbital decay and maneuvers**.

**The Gaps:**
1.  **Decay vs. Maintenance Charts:** We show where the satellite *is*. We should graph altitude over time (last 90 days). A flat line means active station-keeping (thrusters working). A downward slope means drag (passive). An upward spike means a re-boost maneuver.
2.  **Maneuver Detection:** Using the TLE history, we can algorithmically detect "Events" where the orbit changed non-naturally. "BlueWalker 3 fired thrusters on Feb 12" is a huge signal of operational health that no news outlet reports.
3.  **Space Weather Correlation:** You have 25k space weather records. Overlay K-Index (geomagnetic storms) onto the drag charts. Show the correlation between solar activity and orbital decay.

**Why upgrade?** Free users see where the satellite is. Full Spectrum users see **Asset Health** and **Maneuver History**.

---

### Summary of Value

1.  **Regulatory Battlemap** turns a "Document Dump" into a **Risk Dashboard**.
2.  **Orbital Forensics** turns a "Map" into **Technical Verification**.

**Recommendation:** Start with **Thread 006 (Orbital Forensics)**. You already have the structured data (TLEs) ready to graph. Regulatory data (Thread 005) requires complex NLP/parsing of PDFs which is higher friction. Visualizing the "Heartbeat" of the constellation is immediate alpha.

## CLAUDE (turn 2)

Strong framing. "Displaying Data → Modeling State" is the right evolution. Two pushbacks:

**On Thread 005 (Regulatory Battlemap):**
I agree this is high-value but the GAPs as spec'd are heavier than they look. Entity extraction from FCC filings requires NLP on PDFs — many are scanned images, not text. We already have `fcc_filings` with `filing_type` and `filer_name` fields from ECFS metadata. The low-friction version:
- GAP 1 could be a **Docket Timeline view** — we already have `fcc_dockets` with 6 tracked dockets. Visualize filings-per-docket as a timeline, color-coded by filer. No NLP needed — ECFS metadata already has filer names.
- GAP 2: Classify filing types (Comment, Reply, Ex Parte, Petition to Deny) from existing metadata, not PDF parsing.
- GAP 3: The "Objection Signal" — flag Petitions to Deny and Oppositions as critical signals. This hooks into the existing signal_scanner.

**On Thread 006 (Orbital Forensics):**
Agree this is the faster win. But we already have pieces of this:
- `/orbital` page exists with constellation health widgets
- `/satellite/[noradId]` has per-satellite detail with TLE history
- `bstar_trends` view already computes 30-day drag analysis
- Health anomaly detection (altitude drops, drag spikes, orbit raises) already runs every 4h

The real gap isn't "can we graph altitude" — we can. The gap is **narrative**. The data exists but it's scattered across widgets. The user can't answer "what happened to BW3 this month?" in one place. Proposal:

**Thread 006 revised — Constellation Narrative:**
- GAP 1: **Satellite Timeline** — per-satellite event log combining TLE maneuvers, signals, and space weather into one chronological view. "BW3: Feb 3 re-boost (+2km), Feb 8 drag spike (Kp=7 storm), Feb 12 altitude nominal."
- GAP 2: **Fleet Health Dashboard** — one view showing all satellites' altitude trend (sparkline), days since last maneuver, drag rate. The "vital signs" panel.
- GAP 3: **Maneuver-to-Signal bridge** — when a maneuver is detected, auto-create a signal with the orbital delta as metrics. Currently health anomalies create signals, but routine maneuvers don't.

This builds on existing infrastructure rather than starting from scratch. Thoughts?

## GEMINI (turn 2)

### Decision: Execute Thread 006 (Orbital Forensics)

You are correct. The "Narrative" gap is the critical missing link. We have the physics (data) and the map (3D), but we lack the **Logbook**.

The "Regulatory Battlemap" (Thread 005) is valuable but remains a document retrieval problem. The "Orbital Logbook" is a **physics problem**, which aligns tighter with the platform's unique "hard tech" moat. Let's own the physics layer first.

Here is the architectural spec for **Thread 006: The Orbital Logbook**.

---

### Thread 006: The Orbital Logbook

**Objective:** Transform raw orbital state vectors into a human-readable narrative of asset behavior.
**User Value:** "I can see exactly when they fired thrusters, how much drag the storm caused, and verify the satellite is under active control."

#### 1. Data Layer: The Maneuver Detector
We need to formalize "Maneuvers" as distinct events, separate from random noise or standard decay.

*   **Logic:** Enhance the existing `health_check` worker.
*   **Detection Strategy:** Compare current TLE vs. previous TLE (using `mean_motion` or `semi_major_axis`).
    *   **Event A: Decay (Drag):** Gradual decrease in semi-major axis over N epochs. (Already exists? Refine thresholds).
    *   **Event B: Station Keeping (Micro-burn):** Sudden small positive delta in semi-major axis (< 1km) returning to nominal slot.
    *   **Event C: Re-boost (Maneuver):** Significant positive delta in semi-major axis (> 1km).
    *   **Event D: Inclination Change:** Delta in `inclination` > 0.05 deg (indicates plane change).
*   **Output:** Create a new `Signal` type for confirmed maneuvers.
    *   `category`: `ORBITAL`
    *   `severity`: `HIGH` (for Re-boost/Plane change) or `INFO` (for Station Keeping).
    *   `summary`: "BW3 Orbit Raise Detected (+3.2km)"
    *   `metadata`: `{ "delta_km": 3.2, "old_alt": 501.2, "new_alt": 504.4 }`

#### 2. UI Layer: The Asset Logbook
We need a unified chronological view for a single satellite (`/satellite/[noradId]`).

*   **Component:** `AssetLogbook`
*   **Structure:** A vertical timeline merging three data streams:
    1.  **Maneuvers/Anomalies:** (From `signals` table where `related_asset = noradId`)
    2.  **Space Weather Events:** (From `space_weather` table, only if `K-Index > 5` during the window)
    3.  **Filings:** (From `fcc_filings` if tagged with specific satellite callsign - *stretch goal*)
*   **Visuals:**
    *   **Timeline Spine:** Dotted line for "passive decay", solid line for "stable", upward arrow icon for "maneuver".
    *   **Context:** When a drag spike occurs, show the K-Index badge next to it. Cause -> Effect.

#### 3. UI Layer: Fleet Vital Signs
We need a high-density dashboard widget for `/orbital`.

*   **Component:** `FleetVitals`
*   **Visual:** A table/grid row per satellite.
    *   **Col 1: Identity** (Name, COSPAR).
    *   **Col 2: Altitude Sparkline** (30-day Canvas chart).
        *   *Critical:* This must be normalized. A flat line is good. Down is drag. Up is maneuver.
    *   **Col 3: Drag Rate** (km/day loss, calculated from last 7 days).
    *   **Col 4: Last Maneuver** (e.g., "3 days ago").

### Implementation Plan (Codebase)

1.  **Backend (`scripts/data-fetchers`):**
    *   Modify `signal_scanner` or `health_check` to strictly classify TLE deltas as "Maneuvers" and insert them into the `signals` table.
2.  **Database:**
    *   Ensure `signals` table has a `related_satellite_id` or similar FK to link back to the satellite object easily.
3.  **Frontend (`components/satellite`):**
    *   Build `AssetLogbook.tsx`.
    *   Build `AltitudeSparkline.tsx` (Use the existing Canvas engine, stripping down the axes for micro-chart usage).

**Constraint Checklist:**
*   Does this require new data? **No.** (TLEs and Weather exist).
*   Does this require external APIs? **No.**
*   Is this "Bloomberg-grade"? **Yes.** (Converting raw data to derived financial/operational signals).

**Next Step for Claude:**
Investigate `scripts/data-fetchers/health_check.py` (or equivalent). Does it currently *persist* detected events as Signals, or does it just log them? We need these persisted to the DB to build the history.
