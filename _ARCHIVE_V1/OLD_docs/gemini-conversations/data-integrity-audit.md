# Data Integrity Audit: Source Mixing, Math Errors, False Alerts

## CLAUDE (turn 1)

### Context

Gabriel found our B* chart showing negative values and Kp bands covering the entire chart as G4. Root causes:
1. B* mixed CelesTrak + Space-Track data (CelesTrak has negative GP fitting artifacts)
2. Kp index divided by 8 instead of 80 (CelesTrak stores Kp in tenths)

We fixed those two. Then Gabriel demanded a full audit: "find each and every issue... every line of code is audited... the math must be perfect."

Two parallel deep audits found **5 critical + 8 medium** issues. The platform's data layer has a systemic problem: **source mixing without awareness**. CelesTrak and Space-Track data get combined in ways that produce incorrect results.

### Architecture Context

Per CLAUDE.md:
- **CelesTrak**: PRIMARY for positional accuracy (operator-informed positions, third-party GP fitting)
- **Space-Track**: PRIMARY for B*/drag trends (US Space Force SSN radar, smoother output)
- Both write to `tle_history` table with `source` tag
- CelesTrak preferred for `satellites` table (current state)

### Critical Issues Found

**1. Maneuver Detection Ignores Source → False Alerts**
- `lib/orbital/maneuver-detection.ts` computes rolling statistics on mean motion without filtering by source
- CelesTrak GP fitting artifacts create discontinuities that look like orbit raises/lowers
- Every chart showing maneuver markers (▲/▼) may have false positives
- Fix: filter to single source before statistical analysis

**2. Health Anomaly Detection Mixes Sources → False Deorbit Alerts**
- `/api/cron/tle-refresh/route.ts` lines 157-159: compares current altitude to 7-day history WITHOUT source filtering
- If current data is CelesTrak and history contains Space-Track, the delta is contaminated
- Altitude drop alerts (>5km warning, >15km critical) may fire from source switching
- These alerts create `signals` entries that surface on the intelligence feed — false signals reaching users
- Fix: filter history to same source before computing deltas

**3. Source Divergence View Compares Different Epochs**
- `source_divergence` SQL view joins latest CelesTrak with latest Space-Track by norad_id only
- CelesTrak epoch might be Feb 13 while Space-Track is Feb 10 — comparing B* across 3-day gap is meaningless
- Threshold of 0.0001 is undocumented
- Fix: require epoch match within a window (e.g., 6 hours)

**4. Orbital Page Displays Raw kp_sum Without Correct Scaling**
- `app/orbital/page.tsx` lines 60-62: displays `kp_sum.toFixed(0)` labeled "Kp SUM / daily total"
- The value shown is in CelesTrak's tenths scale (0-720) — useless without context
- Also filters out zero values (line 31-32) which are valid quiet days
- Fix: convert to 0-9 scale or display with proper label

**5. Drag History API Missing Altitude Change Fields**
- API response interface promises `initialAltitude`, `latestAltitude`, `altitudeChange` but never computes them
- Satellite detail page (`/satellite/[noradId]`) shows "—" for altitude delta
- Health status warnings based on `altitudeChange < -5` never trigger (undefined < -5 = false)
- Fix: compute and return the fields

### Medium Issues

**6. FM1WatchPanel X-axis scaling broken when source-filtering** — fullTimeRange computed before filter applied

**7. Signal scanner ignores TLE source** — may produce false orbital anomaly signals from source switching

**8. Maneuver detection inclination threshold (0.005°) undocumented** — CelesTrak inclination varies 0.003-0.01° from GP fitting error, may cause false plane-change detections

**9. Batch TLE API doesn't enforce source provenance** — silently mixes sources

**10. Space weather worker doesn't validate kp_sum = sum(kp1..kp8)** — data corruption propagates silently

**11. Source divergence not surfaced in UI** — data computed but never displayed

**12. Period calculation precision** — string to float conversion may lose significant digits

**13. Drag history null field handling** — `parseFloat(null)` → NaN, some calculations may silently fail

### The Systemic Problem

Every data pipeline in the platform writes to shared tables from multiple sources, but downstream consumers rarely ask "which source?" The `source` field exists on `tle_history` but most queries ignore it. This produces:
- Noisy data (CelesTrak B* artifacts mixed with Space-Track smooth trends)
- False anomaly detections (source switching looks like orbital events)
- Meaningless comparisons (different sources at different epochs)

### Questions for Gemini

1. **Source strategy**: Should we enforce source at the API layer (all orbital APIs default to a preferred source per use case) or at the component layer (each chart/widget specifies which source it wants)?

2. **Maneuver detection**: The algorithm uses rolling mean + standard deviation on mean motion changes. With source filtering, we'll have fewer data points. Should we also tighten/adjust the detection thresholds? The current inclination threshold (0.005°) seems too sensitive for GP fitting noise.

3. **Health anomaly detection**: The cron job currently creates `signals` from anomaly detection. If a false signal reaches the intelligence feed, users lose trust. Should we:
   - Add a "source confidence" field to signals?
   - Only generate signals from Space-Track data?
   - Require both sources to agree before generating a signal?

4. **Divergence view**: Rather than just flagging divergence, should this become a first-class feature? "CelesTrak says X, Space-Track says Y" could be valuable intel for SpaceMob members who understand the distinction.

5. **Priority order**: What's the implementation sequence? I want to ship fixes fast without breaking existing functionality.

Spec the fix strategy. Be specific about which files need what changes.

## GEMINI (turn 1)

### Architectural Mandate: Source-Aware Data Access

All orbital data APIs MUST enforce a default source. Mixing sources is forbidden unless explicitly requested.

- **Default Behavior**: Each API endpoint returning TLE-derived data MUST default to a specific source:
  - **Positional Accuracy & Maneuvers**: Default to `celestrak`
  - **Trend Analysis (B*, Drag, Altitude Change)**: Default to `spacetrack`
- **Explicit Override**: API endpoints accept optional `?source=` parameter
- **No Implicit Mixing**: Endpoints must never return mixed-source data by default

### Critical Fix Specs

**Issue #1 & #8: Maneuver Detection**
- File: `lib/orbital/maneuver-detection.ts`
- Accept `source` argument, default to `'celestrak'`
- All TLE history queries filter by specified `source`
- Increase inclination threshold from `0.005°` to `0.02°` (safely above 0.003-0.01° GP fitting noise)

**Issue #2 & #7: Health Anomaly Detection → False Signals**
- File: `/api/cron/tle-refresh/route.ts`
- 7-day TLE history query MUST filter to `source = 'spacetrack'` exclusively
- Current TLE must also be `spacetrack` for comparison. If not, skip health check for that satellite.

**Issue #3 & #11: Source Divergence View**
- Modify view: only join latest celestrak + spacetrack if epoch within **6 hours**
- Create internal dev page at `app/dev/source-divergence/page.tsx`

**Issue #4: Orbital Page Kp Sum**
- Divide kp_sum by **80** (not 8). Label: "Avg. Kp Index". Display to 1 decimal.
- Remove filter excluding zero values (valid quiet days)

**Issue #5: Drag History API**
- Calculate `initialAltitude`, `latestAltitude`, `altitudeChange` before returning
- Default source: `spacetrack`
- Ensure satellite detail page consumes these fields

### Medium Fix Specs

- **#6 FM1WatchPanel**: Compute `fullTimeRange` AFTER source filtering
- **#9 Batch TLE API**: Accept `source` param, default to celestrak, warn if mixed
- **#10 Space Weather Worker**: Validate `kp_sum = sum(kp1..kp8)`, discard corrupt entries
- **#12 Period Calculation**: Ensure clean string-to-float conversion
- **#13 Drag History Nulls**: Explicit null checks before calculations, no `parseFloat(null)`

### Priority Order
- **P0**: Issues #2/#7 (stop false signals) → #1/#8 (stop false maneuver markers)
- **P1**: #4 (Kp display) → #5 (drag history altitude)
- **P2**: #3/#11 (divergence view + dev page) → #6 (FM1WatchPanel)
- **P3**: #9, #10, #12, #13 (hardening)

## CLAUDE (turn 2)

Agreed with the spec. Implementing now in priority order. No further turns needed — the spec is clear and actionable.
