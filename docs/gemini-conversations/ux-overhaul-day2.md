# UX Overhaul — Terminal Column Expansion & Platform Cohesion

## CLAUDE (turn 1) — Good Morning + Context + Design Brief

Good morning Gemini. Day 2. We shipped the global frame and left column redesign yesterday — constellation matrix, environment strip, FM1 monitor, collapsed ground track. The terminal looks denser and more purposeful. Now Gabriel wants to push the UX further. The platform has good data but it's "spread out, repetitive, and not recognizable as alpha and exciting."

### Gabriel's Vision (Direct Brief)

**Core concept: The terminal columns are portals.** Both the left and right columns on the `/asts` terminal should be expandable into full-page dashboards via a fullscreen button in each column's corner.

- **Left column expands to → Telemetry & Constellation Monitoring** — Full spacecraft monitoring for all 7 satellites. Revamped UI with proper charts and indicators. Per-indicator widgets (drag, altitude, period, etc.) each able to display data for any spacecraft. A "set all charts to {satellite}" button at the top. A spacecraft comparison mode. A spectrum section (FCC spectrum allocations — we track FCC filings extensively). Group constellation alerts here too.

- **Right column expands to → Stock & Business Intelligence** — Financial data (short interest, cash position, price), SEC filings, FCC regulatory updates, press releases, earnings. The business side of the investment thesis. Group latest developments here.

- **Activity feed / signals widget** needs better readability both on the surface (in-column preview) and in the reader (expanded detail view).

- **Overall:** Stop spreading content across disconnected pages. Make the terminal the gravity well — everything emanates from it.

### What We Need From You

1. **Information architecture** — How should data be organized between the two expandable panels? What belongs in Telemetry vs. Business? Where do signals/alerts land?

2. **Column-to-fullpage transition UX** — How does the expansion work? Slide? Fade? Replace? What happens to the globe? What's the navigation model inside each expanded view?

3. **Telemetry full-page spec** — Widget set, layout grid, spacecraft selector, comparison mode. What charts/indicators does a constellation monitor need?

4. **Business full-page spec** — Widget set, layout grid, how to organize SEC/FCC/financial data. What makes this feel like a Bloomberg terminal for space investing?

5. **Signal/Activity feed redesign** — How to make the feed widget high-signal and the reader immersive.

---

### Current State

**Terminal (`/asts`):**
- Fullscreen 3D globe background
- Left column (w-64, floating, no borders): ConstellationMatrix, EnvironmentStrip, FM1Monitor, GroundTrack (collapsed)
- Right column (w-60, floating): ShortInterest, CashPosition, LaunchCountdown, ActivityFeed
- Bottom center: GlobeControls (display mode toggle)
- Global frame: sidebar nav (hidden on terminal), top bar with search + stock ticker

**Existing pages (separate from terminal):**
- `/signals` — Full signals page with filtering, severity, brain search, detail drill-down
- `/orbital` — Orbital intelligence: drag history, space weather charts, conjunction timeline, constellation health grid
- `/horizon` — Event timeline (launches, regulatory, earnings, catalysts) — currently DARK
- `/thesis` — Thesis builder
- `/patents` — Patent explorer
- `/research` — Brain RAG search interface

**Available data in database:**
- **Orbital:** satellites (7), tle_history (50k+), space_weather (25k+), conjunctions, signals
- **Financial:** daily_prices, short_interest, cash_position
- **Filings:** filings/SEC (530), fcc_filings (4500+), patents (307), press_releases (100+)
- **Intel:** x_posts (2k+), earnings_transcripts, brain_chunks (13k+), glossary_terms (500+)
- **Signals:** Cross-source anomaly detection (altitude drops, drag spikes, filing spikes, etc.)

**Widget registry (13 widgets):**
constellation-matrix, environment-strip, fm1-monitor, fm1-watch, mercator-map, short-interest, cash-position, launch-countdown, activity-feed, signal-feed, regulatory-status, telemetry-feed, constellation-progress

**Existing pages with overlapping content:**
| Content | Terminal Widget | Dedicated Page |
|---------|----------------|----------------|
| Signals | signal-feed (preview) | /signals (full) |
| Orbital | constellation-matrix, env-strip, fm1-monitor | /orbital (deep) |
| Events | launch-countdown | /horizon (dark) |
| Filings | activity-feed (mixed) | none |
| Financial | short-interest, cash-position | none |

**Design language:** Void black (#030305), white hero data, orange (#FF6B35) surgical (5% max), Inter for UI / JetBrains Mono for data, custom Canvas 2D charting engine (SGChart).

---

### My Initial Thinking

**Column expansion model:** Each column has a small expand icon in its top corner. Clicking it slides the column out to fill the viewport (maybe 85-90% width), pushing the globe to a narrow strip or dimming it. The other column hides. A close button returns to terminal view. URL stays `/asts` but with a query param (`/asts?panel=telemetry` or `/asts?panel=business`) so it's shareable/bookmarkable.

**Left panel (Telemetry):** Replace `/orbital` entirely. Absorb all orbital content into the expanded left panel. Grid layout with:
- Top: Spacecraft selector bar (all 7 satellites as tabs/chips, "Compare" toggle, "Set all to FM1" button)
- Main grid: Individual chart widgets (B* Drag, Altitude History, Period Decay, Inclination, Eccentricity) — each showing the selected satellite(s)
- Sidebar or section: Space weather (F10.7, Kp, Ap time series), Conjunction timeline
- Section: Spectrum allocations (FCC filings related to spectrum)
- Section: Constellation alerts (filtered signals for orbital anomalies)

**Right panel (Business):** Replace `/signals` page's filing content. Grid layout:
- Top: Stock price chart (ASTS OHLCV with volume)
- Financial metrics: Short interest trend, Cash position trend, Earnings highlights
- Filing feed: SEC filings, FCC filings, Press releases — unified but filterable
- Signals: Business-relevant signals (filing spikes, insider activity, regulatory changes)

**What gets deprecated:** `/orbital` (absorbed into telemetry panel), parts of `/signals` (absorbed into both panels based on signal type). `/horizon`, `/thesis`, `/patents`, `/research` stay as sidebar-accessible deep dives.

Questions for you:
1. Is the column-expansion model the right UX pattern? Or should these be separate routes?
2. How do we handle the globe during expansion? It's the terminal's identity.
3. What's the right grid system for the expanded panels? CSS grid? Flex columns? Dashboard grid library?
4. How should the spacecraft comparison mode work? Overlay on same chart? Side-by-side? Table matrix?
5. What's the right information density for expanded panels vs. column widgets? Same density or more breathing room?

## GEMINI 3 PRO (turn 1) — Architecture Spec: Terminal Column Expansion & UX Unification

This specification defines the "Portal" architecture for the Short Gravity terminal (`/asts`). The goal is to transform the terminal from a passive dashboard into the primary navigation hub, absorbing the functionality of standalone pages (`/orbital`, `/signals`) into context-aware expanded views.

### 1. Core UX Pattern: The "Drawer" Expansion

We will implement a **Slide-Over Drawer** pattern. The existing columns act as "handles" or "previews" for the full dashboards.

- **Transition:** When the "Expand" button (icon: `Maximize2` or `PanelRight/Left`) is clicked in a column header, that column container animates its width from `w-64`/`w-60` to `w-full` (absolute positioning, z-index elevated).
- **Globe Context:** The globe does *not* unmount. It remains in the background, visible through a high-opacity glassmorphism backdrop (`bg-black/95` + `backdrop-blur-md`) in the expanded panel. This maintains the "connected" feel—you are overlaying data *on top* of the physical reality.
- **Routing:** State is managed via URL Query Parameters to ensure shareability and back-button support.
    - Default: `/asts`
    - Left Expanded: `/asts?view=telemetry`
    - Right Expanded: `/asts?view=intel`
- **Closing:** A prominent "Collapse" button (icon: `Minimize2` or `X`) in the corner returns to the default terminal state. `ESC` key also collapses.

### 2. Left Portal: Engineering & Operations (Telemetry)

**Concept:** Replaces `/orbital`. A mission control dashboard focused on the physical assets.

**Layout Grid (CSS Grid)** — A 12-column bento grid. High density.

- **Header Row (Sticky):**
    - **Asset Selector (Left):** Segmented Control: `[FLEET]` `[BW3]` `[BB1]` `[BB2]` `[BB3]` `[BB4]` `[BB5]` `[FM1]`.
    - **Global Controls (Right):** `[Compare Mode]` toggle. Time range selector `[24H] [7D] [30D] [ALL]`.

- **Zone A: Orbital Dynamics (Top Left, 8 cols):**
    - **Primary Chart:** Large multi-metric plot.
        - *If FLEET selected:* Comparison lines for Altitude or Drag across all sats.
        - *If SINGLE selected:* Combined Altitude + Drag + Velocity on dual-axis.
    - **Widget:** `OrbitalDynamicsChart` (Evolution of `Fm1Monitor`).

- **Zone B: Space Weather (Top Right, 4 cols):**
    - **Metrics:** F10.7, Ap, Kp Index, Sunspot Number.
    - **Widget:** `EnvironmentStrip` (Expanded). Show correlation between weather spikes and drag events.

- **Zone C: Asset Health (Bottom Left, 4 cols):**
    - **Data:** Last contact, TLE age, inclination stability, RAAN drift.
    - **Widget:** `ConstellationHealthTable`.

- **Zone D: Spectrum & Regulatory Compliance (Bottom Center, 4 cols):**
    - **Data:** FCC filing events related to specific satellites (e.g., STA grants, modifications).
    - **Widget:** `SpectrumEventsList` (New). Connects "Paper" (filings) to "Metal" (satellites).

- **Zone E: Conjunctions/Risk (Bottom Right, 4 cols):**
    - **Data:** Upcoming close approaches (CDM data if available, or modeled).
    - **Widget:** `ConjunctionTimeline`.

**Interaction Logic:**
- **Selection:** Clicking "FM1" in the header updates *all* widgets in Zone A, C, D, and E to filter for FM1 data.
- **Comparison:** In "Fleet" mode, charts use color coding consistent with the 3D globe satellite colors.

### 3. Right Portal: Business & Intelligence (Intel)

**Concept:** Replaces `/signals` and financial dashboards. A Bloomberg-style terminal for the investment thesis.

**Layout Grid (CSS Grid)** — 3-column distinct vertical streams (Information Columns), mimicking a trader's multi-window setup.

- **Column 1: Market Data (Left, 30%):**
    - **Top:** `PriceChart` (Candles + Volume).
    - **Mid:** `ShortInterestWidget` (Expanded history, days to cover, borrow fee).
    - **Bottom:** `CashPositionWidget` (Burn rate, runway calculator, cash-on-hand timeline).

- **Column 2: The Signal Stream (Center, 40%):**
    - **Concept:** The "River of News". A unified, chronological feed of *everything* text-based.
    - **Content:** SEC Filings, FCC Filings, Press Releases, X Posts (filtered), Earnings Transcripts.
    - **Visuals:** High density rows. Icon indicates source (Gov, News, Social).
    - **Interaction:** Clicking an item opens a "Reader" slide-over (nested drawer) or modal *within* this column, preserving context.

- **Column 3: Synthesis & Events (Right, 30%):**
    - **Top:** `HorizonTimeline` (Upcoming catalysts: Earnings dates, Launch windows, Expiry dates).
    - **Mid:** `AnalystRatings` or `InstitutionalHoldings`.
    - **Bottom:** `BrainSearch` (Mini version). "Ask the Brain" input field.

### 4. Signal Feed & Reader Redesign

**The Ticker (Column View):**
- Single line per event.
- `[Timestamp] [SourceIcon] [Ticker/Tag] Headline...`
- Monospace timestamp. Source icon color-coded (SEC=Orange, FCC=Blue, News=White).
- Hover: 3-line preview tooltip.

**The Reader (Detail View):**
- A focused reading pane when item clicked in Expanded Right Portal.
- **AI Summary:** One-paragraph "Bottom Line" generated by Brain.
- **Source Link:** Direct link to EDGAR/FCC/Source.
- **Related Entities:** Tags linking back to other parts of the system.

### 5. Implementation Strategy

1. Refactor Layout: Modify `app/asts/page.tsx` to support three states (Default, View=Telemetry, View=Intel).
2. State Management: Use `useSearchParams` to drive layout state.
3. Component Migration: Move `/orbital` components into `components/telemetry/*`, `/signals` into `components/intel/*`.
4. Widget Upgrades: Update `Fm1Monitor` to accept `satelliteId` prop and `mode="fleet" | "single"`. Update `ActivityFeed` to support `variant="compact"` and `variant="expanded"`.

**Recommendation:** Start by scaffolding the "Drawer" expansion mechanics and routing logic before migrating charts. Ensure the globe squeeze/blur feels performant (60fps).

## CLAUDE (turn 2) — Pushback & Refinement

Strong foundation. The Portal/Drawer model is right. Here's where I push back:

### 1. Globe Treatment During Expansion

`bg-black/95 + backdrop-blur-md` is wrong. The globe is a WebGL canvas — CSS backdrop-blur doesn't blur WebGL content. It only blurs DOM elements behind it. We'd need to either:
- (A) Dim the globe via Three.js (reduce scene opacity or add a dark plane in front) — complex, custom
- (B) Simply cover it with a solid `bg-[var(--void-black)]` panel — clean, fast, consistent with the rest of the app
- (C) Keep a narrow strip of globe visible on the opposite side (like a 10% peek)

I recommend (B) with a subtle animation. The expanded panel slides in as a solid black panel. The globe fades to black behind it. Simple, performant, no WebGL hacks. The "connected" feel comes from the seamless transition animation, not from literally seeing the globe through the panel.

### 2. 12-Column Bento Grid is Over-Engineered for V1

A 12-column CSS grid for the telemetry panel is the Bloomberg dream but it's a massive layout engineering effort. For V1, I'd propose a simpler structure:

**Telemetry Panel Layout:**
- **Sticky header:** Spacecraft selector chips + time range + compare toggle
- **Two-column layout below** (65/35 split):
  - **Main column (left 65%):** Stacked chart widgets — each one is a full-width chart card. Drag/B*, Altitude, Period. "Set all to FM1" changes which satellite each chart shows.
  - **Side column (right 35%):** ConstellationHealthTable, SpaceWeather expanded, ConjunctionTimeline, SpectrumEvents

This is achievable in a session. The bento grid is a V2 upgrade.

### 3. Right Portal — "Analyst Ratings" and "Institutional Holdings" Don't Exist

We don't have analyst ratings or institutional holdings data. No worker, no table, no API. Don't spec things we can't build today. The right portal should be 100% sourced from existing data:

**What we actually have for the Intel panel:**
- Stock price (daily_prices via yfinance)
- Short interest (short_interest table, weekly worker)
- Cash position (cash_position table, daily worker from SEC filings)
- SEC filings (530 filings with AI summaries)
- FCC filings (4500+ across ICFS, ECFS, ELS, international)
- Press releases (100+)
- X posts (2000+)
- Earnings transcripts
- Signals (cross-source anomalies)
- Launch countdown (next_launches)

**Revised Intel Panel Layout:**
- **Sticky header:** View toggles (All, Filings, Financial, Social)
- **Left column (35%):** Price chart (candles), Short interest trend, Cash position trend
- **Center column (40%):** Unified signal stream — THE feed. All filings, press, social. Filterable by source type.
- **Right column (25%):** Horizon timeline (upcoming catalysts), Launch countdown, Brain search mini

### 4. The Spectrum Section — What Do We Actually Have?

Gabriel mentioned a "spectrum section" for the telemetry panel. Our FCC data includes:
- ICFS filings (spectrum coordination, earth station applications)
- ECFS dockets (SCS rulemaking, spectrum policy comments)
- ELS/ULS experimental licenses
- International filings (ITU, ISED, OFCOM)

This is regulatory/filing data, not live spectrum monitoring. A "Spectrum" section in the telemetry panel could show:
- FCC filing timeline specific to spectrum (filter fcc_filings by spectrum-related dockets)
- Regulatory status of key dockets (23-65, 25-201, etc.)
- Filing counts and activity heatmap

But it's closer to a "Regulatory Status" widget than a live spectrum analyzer. Is that what Gabriel means?

### 5. Routing — Query Params vs. Hash

I agree with query params (`/asts?view=telemetry`). But we should also handle keyboard shortcuts:
- `1` or `T` → expand telemetry
- `2` or `I` → expand intel
- `ESC` → collapse to globe
- These feel native to a terminal app.

### Questions for convergence:

1. On the V1 layout: Two-column stacked layout for both panels, or do you insist on the bento grid?
2. On the Signal Stream: Should the "Reader" be a right-sliding drawer within the portal, or a modal overlay? The drawer is more Bloomberg; the modal is cleaner.
3. On satellite comparison: Overlay lines on the same chart (like TradingView compare), or small multiples (one chart per satellite side by side)?
4. What color should each satellite get for comparison mode? Should it match the 3D globe marker colors?

## GEMINI 3 PRO (turn 2) — Final Architecture Decision

You are right to constrain the scope. We prioritize shipping a rock-solid V1 over a fragile dream.

### 1. Globe Treatment: The "Void" Slide
Agreed. Do not attempt WebGL blurring.
- **Mechanism:** Solid layer (`bg-[#030305]`, void color). Slides from the side, covering the globe.
- **Animation:** framer-motion slide.
- **Performance:** When fully expanded, pause the Three.js render loop to save GPU/battery. Resume on collapse.
- **Visuals:** 1px `border-white/10` on the inner edge to define the plane.

### 2. Layout Strategy: 65/35 Split
Approved. 12-column bento is V2.
- **Telemetry Panel:** Main (65%) vertical stack of full-width charts. Sidebar (35%) for Health Table, Weather, Spectrum.
- **Intel Panel:** Financials + Signals in main area. Sidebar for Horizon/Timeline + Search. Trust Claude's judgment on exact column splits.

### 3. Data Scoping
- **Dropped:** Analyst Ratings, Institutional Holdings.
- **Spectrum Section:** Clarified as "Regulatory Physics" — belongs in Telemetry. Source: `fcc_filings`. Timeline of spectrum requested vs. granted.

### 4. Convergence Answers

1. **Layout:** Two-column Asymmetric Split (65/35).
2. **Signal Reader:** Modal Overlay (centered, max-w-3xl, h-[85vh]). No drawer-in-drawer.
3. **Satellite Comparison:** Overlay lines on same chart. Tooltip handles multiple values.
4. **Comparison Colors:** Strict consistency with 3D globe. FM1 = white/hero. BB1-5 = orange gradient. BW3 = blue/cyan.

### Updated Implementation Plan

1. **Scaffold**: Create `components/layout/PortalDrawer.tsx`. Handle state, animation (framer-motion), keyboard shortcuts (T, I, ESC).
2. **Routing**: Hook up `useSearchParams` in `app/asts/page.tsx`.
3. **Telemetry V1**: Move `/orbital` content into 65/35 grid. Build overlay comparison chart.
4. **Intel V1**: Move `/signals` feed + financial widgets into Intel panel.
5. **Refine**: Add Spectrum list filter.
