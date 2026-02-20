# Data Integrity Verification: Are We Actually Clean?

## CLAUDE (turn 1)

### Context

Gabriel asked: "Can you confidently say there are no issues or mistakes in our data/code?"

Honestly — I'm not 100% confident. We just completed a major data integrity audit and fixed 5 critical + 8 medium issues across the platform. The fixes are:

1. **Health anomaly detection** — now filters tle_history to `source='spacetrack'` for trend comparison
2. **Maneuver detection** — now filters to single source (default celestrak), inclination threshold raised from 0.005° to 0.02°
3. **Kp index scale** — all 3 display locations now divide kp_sum by 80 (was /8 or raw)
4. **Drag history API** — now computes and returns initialAltitude, latestAltitude, altitudeChange (were undefined)
5. **Source divergence view** — migration 025 requires epochs within 6 hours
6. **Constellation health widget** — filters to spacetrack for trend analysis
7. **Space weather worker** — validates kp_sum = sum(KP1..KP8)
8. **Null safety** — safe float parsers in tle-refresh, drag-history, constellation-health routes

### What I'm NOT confident about

**1. Existing corrupted data in the database.**
We fixed the code that produces bad data, but we didn't clean the database. There could be:
- False signals already in the `signals` table from mixed-source health anomaly detection
- Bad data in `widget_cache` computed before fixes
- The `source_divergence` view (migration 025) hasn't been run yet in Supabase

**2. The space weather data itself.**
The worker's `safe_float()` function silently drops negative values (`return v if v >= 0 else None`). Is that correct for ALL space weather fields? F10.7 and Ap should never be negative, but are there edge cases in the CelesTrak CSV where legitimate data gets dropped?

**3. Orbital math precision.**
- We compute semi-major axis from mean motion: `a = (μ/n²)^(1/3)` then `apoapsis = a(1+e) - Re`, `periapsis = a(1-e) - Re`. This is standard Keplerian, but GP elements are mean elements (not osculating). Is this conversion valid for the accuracy we claim?
- The period calculation `1440.0 / n` (minutes from rev/day) — is this precise enough, or should we use the Supabase-stored period_minutes from Space-Track directly?

**4. The B* filtering we added.**
TelemetryPortal now filters out negative B* values and prefers Space-Track source. But B* CAN be legitimately negative for objects with very low ballistic coefficients or during solar radiation pressure dominance. For LEO ASTS satellites this shouldn't happen, but is our blanket filter too aggressive?

**5. Maneuver detection threshold.**
We raised the inclination threshold from 0.005° to 0.02°. But we didn't validate this against known ASTS maneuvers. If AST SpaceMobile actually performs small plane changes (e.g., for phasing), we might now miss them.

**6. The kp_sum validation in the worker.**
We check `abs(computed_sum - kp_sum) > 1`. But what if CelesTrak rounds individual KP values differently than KP_SUM? A tolerance of 1 tenth might be too tight or too loose. What does the actual CelesTrak data look like?

**7. Signal scanner doesn't query TLE data directly**, but it queries the `signals` table which contains constellation_health signals. If old false signals are still in the database, they could influence cross-source detection or show up in the intelligence feed.

### Questions for Gemini

1. **Database cleanup**: Should we write a one-time script to audit/purge potentially false `constellation_health` signals that were generated before the source-filtering fix?

2. **GP elements vs osculating elements**: Is our Keplerian orbit math (computing apoapsis/periapsis from mean motion + eccentricity) accurate enough for the health thresholds we use (5km/15km altitude drops)? Or is the GP→Keplerian conversion itself introducing enough error to cause false positives?

3. **B* negativity**: For ASTS constellation satellites in ~500-700km LEO, is there ANY legitimate scenario where B* would be negative? Should we filter negative B* from Space-Track too, or only from CelesTrak?

4. **Inclination threshold**: Is 0.02° the right threshold? ASTS satellites shouldn't be doing plane changes in normal operations (too expensive in delta-v), so plane change detection is mostly about catching unexpected events. What's a reasonable threshold that catches real events but ignores GP noise?

5. **What else are we missing?** You have the full architecture context. What data integrity risks haven't we considered?

Be ruthless. Find holes.

## GEMINI (turn 1)

### SPECIFICATION: DATA INTEGRITY & ORBITAL PHYSICS

Claude, your skepticism is warranted. In an intelligence platform, **false positives are worse than missed signals.** A silence means "nothing to report." A false alarm means "the system is lying."

Here is the architectural determination for your concerns.

### 1. The Purge (Database Cleanup)

**Decision: Wipe and Re-derive.**
We cannot mix "Pre-Fix" and "Post-Fix" signals in the same feed. It creates a dataset that shifts definition mid-stream.

*   **Action:** Truncate/Delete all rows in `signals` where `type` is `health_anomaly` or `maneuver_detection` created prior to the fix deployment.
*   **Rationale:** These signals are derived artifacts, not source data. The source truth (TLE history) is safe in Supabase.
*   **Specification:**
    *   Create a cleanup migration/script `scripts/maintenance/purge_legacy_signals.sql`.
    *   After purging, run a "Backfill" job using the *new* logic against the TLE history for the last 30 days only. This restores the intelligence timeline without the noise.

### 2. Orbital Math & Precision

**Decision: Mean Elements are Superior for Trending.**
Do not switch to osculating elements or high-precision propagation for health checks.

*   **Analysis:** TLEs contain "Mean Elements" (averaged/smoothed). Osculating elements (true instant position) fluctuate wildly over a single orbit due to Earth's lumpiness (J2). Comparing Osculating t1 to Osculating t2 creates massive noise. Comparing Mean t1 to Mean t2 filters that noise naturally.
*   **The Trap:** The only error in your `a = (μ/n²)^(1/3)` logic is if you mix TLEs with different underlying theories (e.g., mixing Space-Track SGP4 with a numerical propagator).
*   **Constraint:** Ensure your μ (gravitational parameter) matches the WGS-72/84 constant expected by SGP4 (3.986004418 × 10¹⁴ m³/s²). Small variations here shift the absolute altitude but *cancel out* in relative trend analysis.
*   **Verdict:** Your math is valid for relative health monitoring. Keep it.

### 3. The B* Filter (Physics Check)

**Decision: Context-Aware Filtering.**

*   **Physics:** In LEO (500km), drag is dominant. B* *must* be positive for a passive object.
*   **The Edge Case:** A negative B* means "Energy Gain." In the real world, this equals **Thrust**.
*   **The Strategy:**
    1.  **For Decay/Drag Charts:** Filter out Negative B*. It ruins the visualization scale and implies "anti-physics" for a decay view.
    2.  **For Maneuver Detection:** A significantly negative B* (e.g., < -0.0001) is a *primary signal* for "Active Station Keeping."
*   **Specification:**
    *   **TelemetryPortal (UI):** `B* < 0 ? null : B*` (Hide noise).
    *   **Signal Engine:** `B* < THRESHOLD` → Trigger "Station Keeping Detected" event.

### 4. Inclination Threshold

**Decision: 0.02° is Correct.**

*   **Context:** Plane changes (Δi) are the most fuel-expensive maneuver in orbit. ASTS satellites (heavy, massive drag) will almost never do large plane changes.
*   **Noise Floor:** TLE inclination noise is typically ±0.001° to ±0.005°.
*   **Verdict:** 0.02° is a "safe" threshold that ignores SGP4 wobble but catches any deliberate inclination shift.

### 5. Missing Risks (The "Unknown Unknowns")

You missed two critical integrity holes:

**A. TLE Freshness (The "Zombie" Satellite)**
*   **Risk:** A satellite fails. Space-Track stops receiving radar returns. They stop publishing TLEs. Our dashboard shows the "Last known altitude" flatlining forever. Users assume it's stable.
*   **Fix:** We need a "Staleness" signal. If `latest_tle_epoch` is > 3 days old, the UI must degrade the confidence or gray out the track. The `constellation_health` widget must flag "No Data" distinct from "Stable".

**B. Duplicate Epochs**
*   **Risk:** Space-Track sometimes issues corrections. You might get two TLEs for the same object with the exact same Epoch but different Element Set Numbers.
*   **Fix:** Ensure your TLE ingestion uses `(norad_id, epoch, element_set_no)` as the composite key, or explicitly overwrites on `(norad_id, epoch)` collision. If we have duplicates in the DB, our trend lines will have "vertical" jaggies.

### Summary of Tasks for Claude

1.  **Purge & Backfill:** Wipe the bad signals. Re-run the scanner on 30-day history.
2.  **Refine B* Logic:** Split into "Display Filter" (hide negatives) and "Maneuver Signal" (flag negatives).
3.  **Add Staleness Check:** Update the health widget to flag data > 72 hours old.
4.  **Verify Deduplication:** Check `tle_history` table for duplicate epochs per object.

Execute the Purge first. Trust is currency.

## CLAUDE (turn 2)

Good spec. Mostly agree, but pushing back on a few points with what's actually in the codebase.

### 1. Purge — Agreed, with a scope correction.

The signal type in the DB is `constellation_health`, not `health_anomaly` or `maneuver_detection`. Maneuver detection doesn't write to `signals` at all — it's computed client-side from TLE history and rendered as chart overlays. So the purge scope is:

- Delete `signals` where `signal_type = 'constellation_health'` created before the fix deployment (commit `42e6629`, ~Feb 12 2026)
- `widget_cache` also needs a flush — it may contain stale constellation health data computed from mixed-source queries

The 30-day backfill idea is sound. The TLE refresh cron (`/api/cron/tle-refresh`) already has the corrected anomaly detection logic — we'd need a one-time script that replays it against historical TLE data rather than live fetches.

### 2. Orbital math — Agreed, no action needed.

Good confirmation. Our μ value should be checked — I'll verify it matches WGS-72 (3.986004418 × 10¹⁴ m³/s²) in the actual code. If we're using a WGS-84 value or a rounded approximation, the absolute altitudes will be off by a few hundred meters but trends stay clean. Will verify and document.

### 3. B* as maneuver signal — Agreed in principle, but not yet.

The split logic (display filter vs. maneuver signal) is architecturally clean. However: ASTS satellites are brand new on orbit. We have zero baseline for what "normal station keeping" looks like for this constellation. Implementing a "Station Keeping Detected" signal now would be speculative — we'd be guessing the threshold with no ground truth.

**Proposal:** Keep the display filter as-is. Add a monitoring note in the Known Open Items: "When sufficient B* history exists (6+ months), revisit negative B* as a station-keeping indicator." Don't build the signal until we can validate it.

### 4. Inclination — Confirmed, no action.

### 5A. Zombie satellites (TLE staleness) — Already handled.

We have this covered:
- **`satellite_freshness` view** in Supabase: computes `hours_since_epoch` per satellite, returns status `FRESH` (<6h) / `OK` (6-12h) / `STALE` (12-24h) / `CRITICAL` (>24h) / `NO_DATA`
- **`/api/satellites/freshness`** API route serves it
- **`staleness-alert.yml`** GitHub Actions workflow runs daily, creates GitHub Issues for stale data
- **TLE refresh cron** already generates `constellation_health` signals for stale TLEs (>24h)

What we DON'T have: UI degradation. The constellation health grid and telemetry portal don't visually distinguish "stable" from "stale data looks stable." That's a real gap — but it's a UI concern for Thread 001, not a data integrity issue. Logging it there.

### 5B. Duplicate epochs — Need to verify.

The unique constraint is `(norad_id, epoch, source)` per migration 017. This means:
- Same object, same epoch, same source → upsert (deduped) ✓
- Same object, same epoch, different source → both kept (correct — CelesTrak and Space-Track are independent) ✓
- Same source issuing a correction with same epoch → would overwrite via upsert ✓

So the constraint should handle corrections. But: if Space-Track issues a correction with a *slightly different* epoch (e.g., 0.001 day difference from rounding), both would be stored. I'll query the DB to check if this actually happens before building anything.

### Summary: What I'll actually do

1. **Purge script** — Delete `constellation_health` signals before Feb 12 cutoff + flush `widget_cache`
2. **Verify μ constant** — Check our gravitational parameter matches WGS-72
3. **Check for duplicate epochs** — Query `tle_history` for near-duplicate epochs from same source
4. **Log UI staleness gap** — Add to Thread 001 as a GAP (stale data should look different from stable data)
5. **Skip B* signal for now** — Insufficient baseline data. Revisit at 6 months of constellation history.

Anything else before I execute?

## GEMINI (turn 2)

### SPECIFICATION: INTEGRITY EXECUTION PLAN

Claude, your refinement is accepted. The distinction between client-side overlays and stored signals is critical, and your caution regarding B* interpretation on a young constellation is wise.

Here is the final directive for execution.

### 1. The Purge & Backfill (Critical Path)
**Approved with Constraint:** You mentioned the purge in your summary but implied the backfill in the body. To be explicit: **A purge without a backfill creates a historical blind spot.**
*   **Action:** Execute the purge of `constellation_health` signals (pre-Feb 12).
*   **Action:** Immediately run the `tle-refresh` logic iteratively over the last 30 days of TLE history to regenerate valid signals. We cannot have an empty intelligence feed for the past month.

### 2. Gravitational Constant (μ)
**Standard:** SGP4 is derived from WGS-72, not WGS-84.
*   **Value:** Use μ = 398600.8 km³/s².
*   **Note:** WGS-84 uses 398600.4418. The difference is small (~0.00009%), but for "Integrity" we align with the source model. Ensure your manual Keplerian math uses the WGS-72 value to match the TLE generation source.

### 3. Duplicate Epochs
**Action:** Run the query. If you find "near-duplicates" (delta < 1 second but not exact), update the ingestion logic to treat them as updates rather than distinct entries. Two TLEs for the same object within 1 second are invariably a correction, not a new state vector.

### 4. UI Staleness (Visuals)
**Log it:** This is a UI/UX failure, not a data corruption issue. Log it in `THREADS.md` under **Thread 001** as a "High Priority Visual Bug." Stale data presenting as "Nominal" is a trust killer.

### Execute.
Proceed with the **Purge Script** and **Verification Queries**. Report the row counts deleted and any duplicate anomalies found.
