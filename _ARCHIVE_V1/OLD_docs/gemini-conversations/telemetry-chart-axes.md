# Telemetry Portal Chart Axes: Time Scaling + Multi-Spacecraft Normalization

## CLAUDE (turn 1)

### Context

We just shipped the Telemetry Portal — an expandable left-column dashboard in the ASTS terminal (`/asts?view=telemetry`). It features an overlay chart that compares orbital metrics (altitude, B*, mean motion, inclination, eccentricity, RAAN) across multiple spacecraft simultaneously.

**The problem (screenshot confirmed):** The X-axis shows "07:00 PM" repeating across the entire axis. The chart uses integer index as the time value:

```typescript
// Current broken code in OverlayChart
sliced.forEach((d, i) => {
  if (d.apogee != null) apogee.push({ time: i, value: d.apogee })
  // ...
})
```

With `axes.x = 'time'`, the chart engine interprets `time: 0, 1, 2, 3...` as millisecond timestamps near epoch (Jan 1, 1970). `formatTime` sees a tiny range and formats as "HH:MM PM" — all resolving to ~07:00 PM.

**Second problem:** When comparing multiple spacecraft, the data doesn't align meaningfully:
- **FM1** (Block 2) — launched Dec 2025, ~2 months of TLE data
- **BB1-5** (Block 1) — launched Sep 2024, ~17 months of TLE data
- **BW3** (test) — launched Sep 2022, ~3.5 years of data

If we use real epoch dates (the obvious fix), FM1 only occupies the rightmost sliver of the chart while BB satellites span the full width. This is temporally honest but makes trend comparison visually difficult — the whole point of the overlay chart is to compare orbital behavior across the fleet.

### Data Shape

Each `DragDataPoint` has:
```typescript
interface DragDataPoint {
  epoch: string      // ISO date string e.g. "2024-09-15T12:00:00Z"
  bstar: number
  meanMotion: number
  eccentricity: number
  inclination: number
  raan: number | null
  apogee: number
  perigee: number
  avgAltitude: number
  source: string     // 'celestrak' | 'spacetrack'
}
```

The chart engine (`SGChart`) uses `TimeSeriesPoint { time: number | string | Date; value: number }` and has a `formatTime(timestamp, rangeMs)` function that auto-selects format based on data range:
- < 2 days → "HH:MM"
- < 90 days → "MMM DD"
- >= 90 days → "MMM 'YY"

### Maneuver Markers

Currently markers also use index-based time:
```typescript
const markers: MarkerData[] = maneuvers.map(m => ({
  time: m.index,  // <-- also broken
  // ...
}))
```

The `detectManeuvers` function returns `index` (array position) not epoch. Markers need the same fix.

### Question for Gemini

1. **The simple fix** is using `new Date(d.epoch).getTime()` as the time value and fixing maneuver markers. But this creates the normalization problem for multi-spacecraft comparison.

2. **What's the right UX for comparing satellites with wildly different data spans?** Options I see:
   - **Date-aligned (default)**: All on same timeline. FM1 starts late — honest but hard to compare trends.
   - **Percent-change mode**: Normalize each series to % change from first value. Good for trend comparison, loses absolute values.
   - **Days-since-launch**: X-axis = days from each satellite's first datapoint. Good for lifecycle comparison.
   - **Some combination**: Date-aligned by default, with a toggle for normalized view.

3. **Should we also handle the case where FM1's value range is very different?** E.g., FM1 altitude ~512km vs BB1-5 ~502km — on the same Y axis the difference looks negligible, but each satellite's internal trend matters.

Spec the approach. What should the overlay chart support, and how should the UX surface the modes?

## GEMINI (turn 1)

### Analysis & Philosophy

We are building a **Tactical HUD**, not a marketing deck. In orbital mechanics, **Time is Absolute**.

Spacecraft do not exist in a vacuum; they exist in a shared, dynamic atmosphere driven by solar weather. A geomagnetic storm on **Feb 13, 2026** hits FM1 and BB1 simultaneously.
- If we align by "Days Since Launch" (Mission Elapsed Time), we destroy the correlation between environmental events and orbital decay.
- If we normalize Y-values to percentages, we obscure the physical reality that 500km is a critical drag boundary.

**Decision:** The chart must remain **Date-Aligned (Absolute)** and **Value-Absolute**.

The "Sliver Problem" (FM1 being compressed to the right) is a **Viewport** problem, not a data shape problem. We solve it with **Range Selectors**, not by distorting the timeline.

### Specification

**A. Data Normalization (The Fix):** X-axis must be linear time (Unix Timestamp). Parse `d.epoch` to milliseconds. Maneuver markers must map `m.index` back to `data[m.index].epoch`.

**B. Time Range Controls:** `1M` | `3M` | `6M` | `YTD` | `ALL`. Default `3M` — captures FM1's entire life + recent BB context, maximizes visual resolution of active fleet comparison.

**C. Y-Axis:** Auto-scale with ~10% padding. Do not normalize. The ~10km delta between FM1 (512km) and BB1 (502km) is visible and meaningful.

## CLAUDE (turn 2)

I agree with date-aligned + absolute values as the default. The temporal truth matters for correlating with space weather events. The `3M` default is a good call — it frames the "current era" where FM1 exists.

But I want to push harder on the UX. Gabriel's ask is bigger than fixing the broken axis. He wants this page to be **world-class** — matching the best platforms, outstanding enough that SpaceMob members screenshot it and post it on socials. The telemetry portal needs to be a destination, not just a data view.

### Specific challenges I need your help thinking through:

**1. Chart readability at scale.** The current chart is a single white line on void black with minimal axis labels. When you add 7 satellites × 2 series each (apogee + avg altitude), that's 14 overlapping lines. How do we make multi-line comparison legible? Reference platforms: TradingView's multi-symbol overlay, Bloomberg Terminal's comparative analytics.

**2. Social shareability.** Members want to screenshot the chart and post it on X/Reddit. That means:
- The chart needs to be self-documenting (title, metric name, satellite names, date range — all visible in screenshot)
- The visual style needs to be distinctive and premium (people should recognize "that's Short Gravity")
- We already have `SGChart.exportToBlob()` for high-DPI share frames. Should we integrate a share/export button directly in the portal?

**3. Interaction design.** What hover/crosshair behavior makes sense for multi-satellite overlay? TradingView shows all values at the crosshair timestamp. Bloomberg shows a floating tooltip per series. What's the right pattern for 7 orbital tracks?

**4. Chart annotation potential.** Maneuver markers (▲ raise / ▼ lower) are already detected. Should we also overlay:
- Space weather events (geomagnetic storms) as background bands?
- Launch dates as vertical markers?
- FCC/regulatory milestones?
This could make the chart the single most information-dense view in the platform.

**5. The "hero chart" question.** Should the default view optimize for the most common use case (single satellite deep-dive, e.g. "show me FM1's orbit history") or the comparison use case (fleet overlay)? These have different optimal layouts.

Think about this from the SpaceMob member perspective — someone who follows ASTS closely, tracks satellite health, and wants to share insights. What makes this chart the one they come back to every day? What makes them screenshot it and post "look at this B* spike on FM1"?

Spec the full interaction model and visual hierarchy.

## GEMINI (turn 2)

### Philosophy: Data is the Art

The goal isn't just to visualize TLEs; it's to tell the story of the spacecraft's life in a hostile environment. SpaceMob members want to say, "Look how well FM1 held up against that X-class flare compared to BW3." We are building a **Forensic Orbital Tool**, not a generic line chart.

### 1. Visual Hierarchy & Modes

**Focus Mode (single sat):** Mean Altitude white 2px, Apogee/Perigee as grey dashed bounds (shows eccentricity breathing), maneuvers in orange. Y-axis auto-scaled to micro-movements.

**Fleet Mode (>1 sat):** Strip Apogee/Perigee, show mean altitude only. "Hero" satellite stays white 2px, peers in muted colors at 1px. Hero always on top (z-index).

### 2. Environmental Context ("The Alpha Layer")

Toggleable background bands for geomagnetic storms (Kp > 5 = red-orange shading). Users correlate storm bands with altitude drops. **This is the screenshot moment** — proving the atmosphere caused the drop, not a problem with the satellite.

### 3. Interaction: TradingView-style Statutory Legend

Fixed top-left of chart. Idle: shows latest values. Hover: updates to crosshair position. Click: freezes crosshair for inspection/screenshot. Format:
```
FM1  ALT: 512.4km  INC: 53.0°  ECC: 0.0001  [MANEUVER DETECTED]
BB1  ALT: 502.1km  (Δ -10.3km)
```

### 4. Social Shareability: "The Intel Card"

Dedicated Share/Export button → generates PNG (2:1 aspect). Watermark: "SHORT GRAVITY // ORBITAL INTELLIGENCE" top-left, dynamic title top-right, date range + source bottom. True black background, crisp lines.

### 5. Implementation Priority

1. Fix axis (epoch → ms timestamp, maneuver markers)
2. Statutory legend + crosshair
3. Multi-sat styling (hero vs peers, hide bounds in fleet mode)
4. Solar data overlay support (chart "regions" for Kp bands)

## CLAUDE (turn 3)

Strong spec. I agree with almost everything. A few pushbacks and refinements:

**On Focus vs Fleet mode:** I agree with the auto-switch logic. But we already have per-satellite colors in `SAT_COLOR_MAP` (FM1=white, BB1-5=orange gradient, BW3=cyan). In Fleet Mode, rather than greying out peers to `#444`, I'd use the existing color palette but dim peers to ~0.4 opacity while the hero gets full opacity. This preserves satellite identity when screenshotted — viewers can tell BB3 from BB5 by color even without the legend.

**On the Statutory Legend:** Love the TradingView pattern. But our chart is Canvas-rendered. We have two options:
- (a) HTML overlay positioned absolutely over the canvas (easier, crisper text)
- (b) Render the legend directly in Canvas (consistent with export/screenshot)

I lean toward (a) for the live view + (b) for the export frame. The export system already renders titles/stats into the canvas. For the live legend, HTML gives us better text rendering and interaction.

**On chart export:** We already have `ref.current.exportToBlob({ title, subtitle, stats, aspect })` wired up. The portal just needs to expose the ref and add a button. This is quick.

**On the environmental overlay:** We already have `spaceWeather` data in the TerminalDataProvider (F10.7, Kp, Ap daily). The data is there. We just need to map it to background bands. I'd implement this as a new overlay type in SGChart: `{ type: 'regions', data: [{ start, end, color, label }] }`.

**One thing missing from your spec:** What about the time range controls? We already have 7D/30D/90D/ALL buttons. Should we replace those with your 1M/3M/6M/YTD/ALL, or keep the current set? I think 7D is too narrow for orbital data (TLEs update every few hours, you'd see like 20 points). My proposal: **30D / 90D / 1Y / ALL** — four options, clean, covers all meaningful windows. 30D = "recent ops window", 90D = "quarterly review" (and shows FM1's full life), 1Y = "annual perspective", ALL = "full history including BW3."

**Implementation plan I'm proposing:**

**Phase 1 (now):** Fix the broken axis + maneuver markers. Switch time ranges to 30D/90D/1Y/ALL. Auto-strip apogee/perigee in fleet mode. This alone fixes the screenshot from "broken" to "correct."

**Phase 2 (this session if time allows):** Statutory legend as HTML overlay (top-left, updates on hover). Share/export button in header. Hero vs peer styling.

**Phase 3 (next session):** Space weather background bands. Click-to-freeze crosshair.

Does this implementation order work? Any objection to the 30D/90D/1Y/ALL range set?

## GEMINI (turn 3)

**Approvals:** All approved. Specific constraints:

1. **Time ranges:** 30D/90D/1Y/ALL. Default **90D** (frames FM1's entire lifespan).
2. **Fleet mode:** Opacity over greyscale. Hero = 100% opacity z-index 10. Peers = 40% opacity z-index 1. Hovering a peer boosts to 100% + z-index 9 temporarily.
3. **Statutory legend:** HTML overlay approved. Handle "no data" gracefully (dash, not NaN).
4. **Maneuver markers:** Snap to exact epoch of TLE where maneuver detected.

**Green light on Phase 1.** Fix axis, fix markers, update ranges to 30D/90D/1Y/ALL (default 90D), auto-strip bounds in fleet mode. Validate before moving to legend/export.

## Converged Spec

**Phase 1 (now):** Fix broken X-axis (epoch→ms), fix maneuver markers, time ranges 30D/90D/1Y/ALL (default 90D), auto-strip apogee/perigee in fleet mode, hero/peer opacity model.
**Phase 2 (this session):** Statutory legend (HTML overlay), share/export button, hover interaction.
**Phase 3 (next session):** Space weather background bands, click-to-freeze crosshair, chart regions overlay type.
