# Left Column Redesign — High-Signal Constellation Monitor

## CLAUDE (turn 1) — Context + Design Brief

We just completed a major design overhaul of Short Gravity's terminal (`/asts`). We added a global persistent frame (sidebar nav + top bar) and stripped the terminal of chrome — it's now a pure workspace: 3D globe + two floating widget columns. The columns have no borders or backgrounds — they float transparently over the globe.

Gabriel's brief for this loop: **"Fill the left column with the right constellation monitoring data. It must be high signal and dense, bloomberg style but in our own sauce."**

### What We Need From You

1. **Widget set design** — What data should the left column show for someone monitoring the ASTS SpaceMobile constellation? What's the right information hierarchy? Think Bloomberg terminal meets SpaceX mission control — every pixel earns its place.

2. **Data density philosophy** — How do we make this dense without being cluttered? Bloomberg is dense because every cell means something. What's the visual grammar?

3. **Specific widget specs** — For each widget you recommend, give me: name, what data it shows, visual layout (sketch in text), and what makes it high-signal.

---

### Current State

**Platform:** Short Gravity — autonomous space sector intelligence for $ASTS investors.

**Terminal page (`/asts`):** Fullscreen 3D globe with 7 tracked ASTS SpaceMobile satellites. Two floating columns of widgets (no borders, transparent background). Global frame provides nav sidebar (hidden on terminal) + top bar with search + stock ticker.

**Current left column widgets (default preset):**
1. **TELEMETRY FEED** — Table showing all 7 satellites: name, lat, lon, altitude, velocity. Click to select on globe. Shows TLE freshness, source divergence (CelesTrak vs Space-Track).
2. **CONSTELLATION** — Big number "7" + "SATELLITES IN ORBIT" + satellite image. Simple progress indicator.
3. **FM1 WATCH** — B* drag coefficient chart for FM1 (BlueBird 7, the Block 2 prototype). Shows drag history since launch, source filter (CelesTrak/Space-Track/All), change percentage. Currently broken (returns null when data loading — being fixed).
4. **GROUND TRACK** — Mercator projection map showing satellite ground tracks with orbit paths and coverage zones. Expandable to 70vw.

**Current right column widgets:**
1. Short Interest (financial)
2. Cash Position (financial)
3. Launch Countdown
4. Activity Feed (signals, news, filings)

**Available data in the database:**
- `satellites` table — norad_id, name, altitude, inclination, eccentricity, period, bstar, epoch, tle_line1/2
- `tle_history` — Full TLE history per satellite per source (CelesTrak + Space-Track). ~50k records.
- `space_weather` — Daily solar flux (F10.7), Kp index, Ap index, sunspot number. 25k+ records.
- `conjunctions` — SOCRATES conjunction/close approach data for tracked satellites
- `signals` — Cross-source anomaly detection (altitude drops, drag spikes, stale TLEs, unusual filing activity)
- `daily_prices` — ASTS stock OHLCV data
- Drag history API — B* trends over configurable time ranges, per source
- TLE freshness API — Age of latest TLE per satellite
- Source divergence API — CelesTrak vs Space-Track B* delta per satellite
- Satellite position propagation — Real-time lat/lon/alt/velocity via satellite.js from TLE data (updates every 500ms)

**Available satellite data (the ASTS SpaceMobile constellation):**
- FM1 (67232) — Block 2 prototype, launched 2025-12-24 (most important satellite)
- BB1-BB5 (61045-61049) — Block 1 test satellites, launched 2024-09-12
- BW3 (53807) — BlueWalker 3 test vehicle, launched 2022-09-10

**Design constraints:**
- Column width: ~256px (w-64), floating with no background
- Font: Inter for labels/text, JetBrains Mono for data values
- Color: void-black bg, white data, orange for active/selected only (5% usage), green/red for deltas
- Each widget uses the Primitive system: Panel, Stat, Text, Label, Value, StatusDot
- Widgets must read from TerminalDataProvider context (no direct API calls)
- FocusPanel wrapper for expandable widgets

**What Gabriel does NOT want:**
- Marketing CTAs (email signup, Patreon) — already killed
- Decorative overlays (targeting reticle, corner brackets) — already killed
- Fluff or padding — every element must justify its screen real estate

---

### My Take (Claude's Initial Thinking)

I think the current left column has the right structure but wrong density. Here's what I'd propose, but I want your critique:

1. **CONSTELLATION STATUS** — Replace the big "7" with a compact status grid. Each satellite as a row: name, status dot (nominal/warning/critical), altitude, B* trend arrow, TLE age. Think a flight arrivals board but for satellites. Dense, scannable, actionable.

2. **FM1 FOCUS** — Keep the drag chart but make it denser. Add altitude overlay. Show key orbital parameters inline: period, inclination, eccentricity, apogee/perigee. This is the money satellite — it deserves its own section.

3. **ORBITAL HEALTH** — New widget. Aggregate health metrics: avg constellation altitude, TLE freshness summary, any active conjunction warnings, source divergence alerts. One-glance constellation health.

4. **SPACE WEATHER** — Solar flux and geomagnetic indices matter for LEO satellites. Show current F10.7, Kp, Ap with trend indicators. Affects drag prediction accuracy.

5. **GROUND TRACK** — Keep mercator map but make it more compact when collapsed. Primary value is spatial awareness.

Total: 5 widgets, all data-driven, all from existing database tables. No new APIs needed.

Questions for you:
- Is this the right information hierarchy? What am I missing?
- How should we handle the dense table layout — should each satellite row be its own mini-dashboard, or is tabular better?
- What's the Bloomberg grammar for this? Ticker tape? Blotter? Matrix?
- Any SpaceX/mission control patterns we should steal?

## GEMINI (turn 1) — Constellation Health Monitor Spec

Claude's initial thinking is on the right track, but we can push the density and signal-to-noise ratio further by refining the information hierarchy and adopting a more rigorous visual grammar.

My recommendations are grounded in the principle that the left column should function as a real-time **constellation health monitor**. It must answer three questions in order of priority:
1. **Is the system nominal?** (Executive Summary)
2. **How is each asset performing?** (Detailed View)
3. **What external factors are at play?** (Context)

This leads to a specific widget set and hierarchy. The `GROUND TRACK` is a spatial awareness tool, not a core health monitor, and should be de-emphasized. The `FM1 WATCH` is a specialized deep-dive tool.

### 1. Data Density Philosophy: The "Blotter" Grammar

To achieve Bloomberg-level density, we will adopt the visual grammar of a trading blotter or an engineering status matrix. Every pixel must convey information.

- **Structure:** Purely tabular. Data is organized in aligned columns. No "cards" or decorative containers.
- **Typography:**
  - **Labels:** `text-neutral-400`, uppercase, `Inter`, tracking-wide. They are signposts, not content.
  - **Values:** `text-white`, `JetBrains Mono`. The data is the hero.
- **Micro-visualizations:** We will use symbols and inline graphics to replace text where possible.
  - **Status:** `●` (Green/Yellow/Red) for Nominal/Warning/Critical states.
  - **Trends:** `▲` `▼` for positive/negative deltas. Use color (`green`/`red`) sparingly for emphasis on change.
  - **History:** Inline sparklines (`__/\_`) for recent performance at a glance.
- **Interaction:** Hovering a row or data point can reveal a tooltip with more detail (e.g., exact timestamp, parameter definition). Clicking a satellite's row in any widget selects it globally.

### 2. Recommended Widget Set & Hierarchy

This hierarchy moves from a high-level summary down to specific asset details and contextual factors.

#### Widget 1: `CONSTELLATION HEALTH`

- **Purpose:** An executive summary of the entire constellation's status. It answers "Is everything okay?" in under three seconds.
- **Data Points:**
  - **Overall Status:** A single `NOMINAL`, `WARNING`, or `CRITICAL` value derived from the signals engine.
  - **TLE Freshness:** The status of the most out-of-date TLE in the constellation (e.g., `STALE: BB3 (4.5d)`).
  - **Conjunctions:** A count of active high-risk conjunction warnings from SOCRATES.
  - **Source Divergence:** The highest B* divergence percentage between CelesTrak and Space-Track for any single satellite.
- **Visual Spec:**
  ```
  CONSTELLATION HEALTH
  STATUS               NOMINAL ●
  TLE AGE (MAX)        1.2d (BB1)
  CONJUNCTIONS         0 ACTIVE
  SOURCE DIVERGENCE    2.1% (FM1)
  ```
- **High-Signal Rationale:** This is the top-level stoplight. If all fields are nominal, the user can be confident in the constellation's baseline health without scanning every satellite. It aggregates the most urgent, system-wide failure modes.

#### Widget 2: `ORBITAL STATUS`

- **Purpose:** A dense, scannable data matrix of every satellite in orbit. This is the core of the monitoring system, replacing the old `TELEMETRY FEED`.
- **Data Points (per satellite row):**
  - **Status:** `●` derived from all available signals for that asset (stale TLE, altitude drop, conjunction risk, etc.).
  - **Name:** e.g., `FM1`, `BW3`.
  - **Altitude (km):** Current altitude.
  - **Altitude 24h Change (m):** e.g., `-110m`. A direct measure of orbital decay.
  - **B* Drag:** The B* drag term from the latest TLE.
  - **B* Trend (7d):** A 7-day sparkline of the B* value plus a net percentage change.
- **Visual Spec:**
  ```
  ORBITAL STATUS
  SAT    ALT(KM) Δ24H    B*        B* TREND 7D
  ● FM1  528.1   -10m    .1234E-04 __/\_ +2.1%
  ● BW3  510.5   -30m    .5432E-04 _/-\_ +8.4%
  ● BB1  511.2   -20m    .5811E-04 \__/- -3.0%
  ○ BB3  498.9   -110m   .9876E-04 /---- +11.7%
  ```
- **High-Signal Rationale:** This is the "blotter." It provides direct, comparable performance metrics for every asset. The 24h altitude change is a more immediate indicator of drag effects than B* alone. The sparkline provides crucial historical context for the current B* value.

#### Widget 3: `SPACE ENVIRONMENT`

- **Purpose:** Displays key space weather data that directly influences LEO orbital drag. Provides the external context for changes seen in the `ORBITAL STATUS` widget.
- **Data Points:**
  - **Solar Flux (F10.7):** Current value and 24h trend (`▲`/`▼`).
  - **Ap Index:** Current value and 24h trend (`▲`/`▼`).
  - **Kp Index:** Current value, presented as a numeric value and a simple bar visualization for at-a-glance magnitude.
- **Visual Spec:**
  ```
  SPACE ENVIRONMENT
  SOLAR FLUX (F10.7)    182 ▲
  AP INDEX              15  ▼
  KP INDEX (PLANETARY)  3   [|||.....]
  ```
- **High-Signal Rationale:** Space weather is the primary driver of atmospheric density changes in LEO. Displaying it is essential for interpreting B* trends. An increase in solar flux will precede an increase in drag; this widget explains the "why."

#### Widget 4: `FM1 MONITOR`

- **Purpose:** A dedicated deep-dive widget for the mission-critical Block 2 prototype satellite. It keeps the essential chart but enriches it with key orbital parameters.
- **Data Points:**
  - **Chart:** The existing B* drag chart, but with a second line overlaying Altitude. The inverse correlation between drag and altitude becomes immediately visible.
  - **Key Parameters (displayed below chart):** Apogee, Perigee, Inclination, Period, Eccentricity.
- **Visual Spec:**
  ```
  FM1 MONITOR: B* & ALTITUDE
  [   Chart: B* (white), Altitude (dim)   ]

  APOGEE    528.4 km   INCLINATION   53.0°
  PERIGEE   527.8 km   PERIOD        95.1 min
  ECCENTRICITY   .0000431
  ```
- **High-Signal Rationale:** FM1 is the single most important asset. Its performance is a proxy for the entire program's viability. This widget provides the deepest view of its orbital mechanics and health, visualizing the direct relationship between drag and altitude decay.

### 3. De-prioritized Widgets

- **`GROUND TRACK`:** This is a spatial awareness tool, not a data-dense monitor. It should be collapsed by default to a single line with an "[EXPAND]" button. When expanded, it can take over the column or open in a modal, but its default state should be minimal to save space for the data widgets.
- **`CONSTELLATION` (the big "7"):** Removed entirely. The satellite count is implicit in the `ORBITAL STATUS` widget, which provides far more useful information.

This specification provides a clear, opinionated, and actionable plan for Claude to implement. It aligns with the project's design language while dramatically increasing the density and utility of the interface.

## GEMINI 3 PRO (turn 2) — Refinement & Final Spec

I've reviewed the dialogue. **Gemini Turn 1 is 80% there but suffers from "Dashboard Drift."**

The critique:
1. **Too much summary, not enough raw data.** The `CONSTELLATION HEALTH` widget in Turn 1 is a "manager's view" (Status: NOMINAL). A Terminal user (analyst/trader) needs the *engineer's view*. They don't want to be told it's "Nominal"; they want to see the `0.00043` eccentricity variance that proves it.
2. **Wasted vertical space.** "Status" text fields (e.g., "NOMINAL") are low-density. Use color states on values instead.
3. **Missing Temporal Context.** The "Blotter" needs to explicitly show *Time of Last Contact* (Epoch Age). In LEO monitoring, data staleness is the #1 silent killer.

Here is the **Final Specification**. It pushes the "Bloomberg" density harder and aligns strictly with the Short Gravity "Tactical HUD" aesthetic.

### 1. Design Philosophy: "The Tape"

We are moving from a "Widget" model to a **"Tape" model**.
- **No containers.** The left column is a single continuous stream of data.
- **Headerless data.** Context comes from the column headers of the matrix, not individual widget titles.
- **Exception-based coloring.** Everything is White/Grey. Orange (#FF6B35) appears *only* when a value deviates from the baseline (e.g., TLE age > 12h, drag spike > 5%).

### 2. The Left Column Structure

#### Section A: THE CONSTELLATION MATRIX (Top Priority)
Replaces `ORBITAL STATUS` and `CONSTELLATION HEALTH`. This is the primary view. It merges status, identity, and physics into one dense grid.

**Columns:**
1. `SAT`: Identifier (FM1, BB1..5, BW3).
2. `AGE`: TLE Age (e.g., `0.4h`, `1.2d`). **High Signal:** If > 24h, text turns Orange. This replaces the "Freshness" widget.
3. `ALT`: Km (1 decimal).
4. `Δ24`: Altitude change in meters (e.g., `-45`). **High Signal:** This is the "heartbeat" of orbital decay.
5. `B*`: Drag term (Scientific notation, truncated: `.12-4`).
6. `SRC`: Source divergence indicator. A simple `Δ` symbol if CelesTrak and Space-Track differ by > 5%.

**Visual Spec (Monospace Grid):**
```
SAT  AGE   ALT    Δ24   B*      SRC
FM1  0.2h  528.1  -12   .43-4   -
BB1  1.4d  511.2  -20   .12-4   Δ
BB2  0.2h  511.4  -18   .12-4   -
...
```
*Interaction:* Hover row to see full TLE details. Click to lock Globe camera to satellite.

#### Section B: ENVIRONMENT STRIP (Context)
Replaces `SPACE WEATHER`. Collapse this into a highly condensed "ticker" strip immediately below the Matrix. It does not need a full panel.

**Layout:** Single row or tight 2-row grid.
**Data:**
- `F10.7`: Solar Flux (The "Input" energy).
- `Ap`: Geomagnetic Index (The "Reaction").
- `Dst`: Disturbance Storm Time (if available, otherwise Kp).

**Visual Spec:**
```
ENV:  F10.7 182▲   Ap 15▼   Kp 3
```

#### Section C: FM1 TELEMETRY (Deep Dive)
This satellite is the proxy for the stock price. It gets the only chart in the column.

**Data:**
- **Primary Visualization:** Dual-axis chart.
    - Axis Left: **Mean Altitude** (Linear descent).
    - Axis Right: **B* Drag Term** (Volatile spikes).
    - *Insight:* Users watch this to see if a drag spike (solar storm) causes a "step down" in altitude.
- **Key Stats (Inline below chart):**
    - `INC`: Inclination (e.g., `53.00°`).
    - `ECC`: Eccentricity (e.g., `.0004`).
    - `PER`: Period (e.g., `95.1m`).

### 3. Implementation Directives

1. **Data Source:** Use the existing `useTerminalData` hook. Do **not** create new fetchers.
   - Matrix derives from `satellites` joined with `tle_history` (latest).
   - Environment derives from `space_weather` (latest).
2. **Typography:**
   - Headers: `text-[10px] tracking-widest text-neutral-500 uppercase font-sans`.
   - Data: `text-xs text-white font-mono`.
   - "Orange": `text-[#FF6B35]` for `AGE > 24h` or `Active Selection`.
3. **Styling:**
   - Background: Transparent (`bg-transparent`).
   - Spacing: `gap-y-1` between rows. `gap-y-6` between Sections.
   - Borders: None. Alignment is the only structure.

### 4. Why This Wins
This specification removes the "editorial layer" (words like "Nominal") and gives the user the raw telemetry. It trusts the user to know that `Age: 1.4d` is bad, or highlights it in orange to teach them. It fits 7 satellites, space weather, and a deep-dive chart into the same pixel budget as the previous "Telemetry Feed" list.

## CLAUDE (turn 2) — Pushback & Convergence

Strong spec. The "Tape" model and exception-based coloring are right. I'm buying the core thesis: raw data > editorial summary, dense grid > cards, engineer's view > manager's view. Here's where I push back:

### 1. The Constellation Matrix — Data Availability Problem

The spec calls for `Δ24` (24h altitude change in meters). This is the highest-signal column — I agree — but we can't derive it from what we currently have. Our `tle_history` table stores TLE snapshots, not continuous altitude measurements. We propagate positions client-side from TLEs using satellite.js, which gives us *current* altitude but not historical altitude deltas.

**Options:**
- (A) Compute `Δ24` by comparing the current propagated altitude vs the altitude propagated from the TLE closest to 24h ago. This requires fetching 2 TLEs per satellite and running 2 propagations. Doable client-side but computationally heavy for 7 satellites at 500ms refresh.
- (B) Drop `Δ24` and replace with `PER` (orbital period in minutes). Period decay is a direct proxy for altitude decay and we already have it from the TLE. Less intuitive but zero new computation.
- (C) Pre-compute altitude history server-side (new API endpoint). Most accurate but breaks the "no new fetchers" directive.

**My recommendation:** (B) for v1. Period is in every TLE, it's the professional's metric for orbital decay, and it keeps us in the "existing data only" lane. We can add `Δ24` later as a server-side computed field.

### 2. B* Display Format

The spec shows `.43-4` as truncated scientific notation. This is clever but nonstandard — even Bloomberg wouldn't invent a new number format. The standard TLE convention is `.43210-4` (5-digit mantissa, power). I propose we keep standard scientific notation but compact: `4.3e-5`. Users who read TLEs will recognize it. Users who don't will still see relative magnitude.

### 3. Source Divergence Column

A binary `Δ` flag is too coarse. If CelesTrak and Space-Track disagree on B* by 2% that's noise; by 200% that's a signal. I'd keep the column but show the actual delta percentage when it exceeds threshold: blank when < 5%, orange percentage when ≥ 5% (e.g., `12%`). This turns an on/off indicator into a gradient of concern.

### 4. Environment Strip — What About Conjunction Count?

The Gemini 2.5 spec had active conjunction count from SOCRATES. That's dropped in your spec. I think it belongs in the environment strip: `F10.7 182▲  Ap 15▼  Kp 3  CDM 0`. A conjunction warning is arguably higher priority than Kp for our users — it's the one thing that could kill a satellite today.

### 5. FM1 Telemetry — Chart Engine Constraint

The dual-axis chart (Altitude left, B* right) is the right visualization. But I want to flag: our charting engine (`SGChart`) supports dual Y-axes via the `y2` axis config, so this is feasible. However, we need to feed it historical altitude data, which goes back to the Δ24 problem. For the drag chart, we already fetch B* history from `/api/satellites/[noradId]/drag-history` — that response includes `avgAltitude` per data point. So the FM1 chart CAN show both B* and altitude. Good.

### 6. Ground Track De-prioritization

Agree. The mercator map is spatial awareness, not monitoring. I'd keep it as the last item in the left column, collapsed to just its header line with expand button. When expanded, it opens in the FocusPanel modal. Zero vertical space cost in the default view.

### Questions for convergence:

1. On `Δ24` vs `PER`: Which approach? I'm leaning (B) — period as proxy.
2. On sparklines vs trend arrows for B* 7d trend: The 256px column is tight. A 60px sparkline + percentage would need ~100px total for the last two columns. Feasible but tight. Alternatively: just the percentage with color (green for decreasing drag, red for increasing) and save the sparkline for the expanded/hover state.
3. On widget architecture: Should I implement these as 3 separate widgets registered in the registry (ConstellationMatrix, EnvironmentStrip, FM1Monitor)? Or literally as one monolithic "LeftColumnTape" component that renders all three sections? The Tape concept suggests monolithic, but the widget system's ErrorBoundary isolation and preset flexibility suggest keeping them separate.

## GEMINI 3 PRO (turn 3) — Final Architecture Decision

I agree with the "Tape" philosophy, but I'm overruling the implementation detail on the monolith. We need modularity for the future, even if the visual output looks monolithic.

Here is the final specification for the **Left Column Redesign**. Execute this plan.

### 1. Architecture: Modular Tape

Do **not** build a monolithic `LeftColumnTape` component.
- Build 4 separate widgets: `ConstellationMatrix`, `EnvironmentStrip`, `FM1Monitor`, `GroundTrack`.
- Register them individually in the widget registry.
- Achieve the "Tape" look via the **layout configuration**:
    - Remove all standard widget padding/margins in the column container for this preset.
    - Ensure widgets have transparent backgrounds.
    - Use `gap-y-6` (24px) spacing *between* widgets, defined in the layout renderer, not the widgets themselves.

**Why:** If we need to inject a "Launch Countdown" widget between the Matrix and FM1 next week, a monolith blocks us. A registry does not.

### 2. The Constellation Matrix (Revised)

We will accept the compromise on `Δ24` for V1 to avoid new data fetchers, but we will strictly format the columns to fit 256px.

**Columns (Strict Widths):**
1. **`SAT`**: `w-12` (Fixed). Name (e.g., `FM1`).
2. **`AGE`**: `w-12` (Fixed). TLE Age (e.g., `0.4h`). **Color:** Orange if > 24h.
3. **`ALT`**: `flex-1`. Altitude in km (e.g., `528.1`).
4. **`PER`**: `w-14`. Period in mins (e.g., `95.12`). *Proxy for decay.*
5. **`B*`**: `w-16`. Drag term. **Format:** Standard `4.3e-5`. Use `text-neutral-500` for the exponent to reduce visual noise.
6. **`SRC`**: `w-8` (Right align). Source Divergence. **Logic:** Empty if < 5%. Orange `%` integer if ≥ 5% (e.g., `12`).

**Header:**
`SAT  AGE  ALT    PER    B*      SRC`

### 3. Environment Strip (with Conjunctions)

CDM (Conjunction Data Message) is critical context. It belongs here.

**Layout:** Single dense row or tight 2x2 grid depending on width.
**Data:**
- `F10.7`: Solar Flux.
- `Ap`: Geomagnetic Index.
- `Kp`: Planetary Index.
- `CDM`: Active Conjunctions (Count). **Color:** Red if > 0.

**Visual:**
```
ENV: F10.7 182▲  Ap 15▼  Kp 3  CDM 0
```

### 4. FM1 Monitor

- **Chart:** Dual Y-axis. Left=Altitude (Linear), Right=B* (Log/Linear).
- **Data Source:** Use `/api/satellites/[noradId]/drag-history` as confirmed. It has `avgAltitude`.
- **Legend:** Minimal inline text. `Alt (White) / Drag (Orange)`.

### 5. Ground Track

- **State:** Collapsed by default.
- **Visual:** A simple button-like row: `[+] GROUND TRACK MAP`.
- **Behavior:** Clicking expands via FocusPanel modal. Default state is 1 row height.

---

**Summary Checklist for Implementation:**
1. Scaffold 4 new widgets in `components/hud/widgets/`.
2. Update the default preset for `/asts` to use this stack.
3. Implement `ConstellationMatrix` using `useTerminalData`.
4. Implement `EnvironmentStrip` — needs new data (space weather + conjunctions).
5. Implement `FM1Monitor` with `SGChart` dual-axis config.
6. Verify 256px fit.
