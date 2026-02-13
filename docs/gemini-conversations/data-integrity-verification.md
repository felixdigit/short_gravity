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
