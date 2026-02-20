# Design Philosophy Loop — Terminal Layout, Page Architecture, Visual Language

## CLAUDE (turn 1) — Current State + Design Brief

We're about to expand Short Gravity from $ASTS-only to multi-ticker ($SPACE), but before we do, Gabriel wants to nail the UI foundation. The concern: we built fast and the layout/design might not be exactly right. We need to study the best, critique what we have, and define the layout philosophy that scales.

### What We Need From You

1. **Reference brand analysis** — Study the design philosophy of: SpaceX/Starlink dashboards, Robinhood, Bloomberg Terminal, TradingView, Unusual Whales, Palantir Foundry. What makes each one work? What are the design principles that make financial/aerospace dashboards feel authoritative?

2. **Critical review of our current design** — Given the current state below, what works and what doesn't? Be brutal. Where does the design language break down? Where is it inconsistent?

3. **Terminal dashboard rethink** — Is the current widget set what a SpaceMob member actually wants to monitor? What's missing? What should be removed? What's the information hierarchy?

4. **Layout philosophy** — Should every page follow the same structure? Or should different pages have different layout patterns? What's the right layout system for a platform that has an immersive terminal, data pages (signals, horizon, patents), and tool pages (thesis, research)?

5. **Design language refinement** — The current palette is void-black + white + surgical orange. Is this right? What's missing? Should we evolve it?

---

### Current Platform State

#### Terminal (`/asts`) — The Flagship Page

**Layout:** Fullscreen 3D globe as canvas, with floating widget panels on left and right sides. Decorative overlay (targeting reticle, corner brackets). Brain search bar at bottom center.

**Default preset widgets:**

LEFT PANEL (w-60):
1. TELEMETRY FEED — Live satellite data table
2. CONSTELLATION PROGRESS — Deployment progress bar
3. FM1 WATCH — First satellite dashboard (expandable)
4. GROUND TRACK — 2D Mercator map (expandable)

RIGHT PANEL (w-56):
1. SHORT INTEREST — Short interest chart
2. CASH POSITION — Cash runway chart
3. LAUNCH COUNTDOWN — Next launch timer
4. INTEL LINK — Navigation to SIGNALS/HORIZON/THESIS
5. EMAIL SIGNUP — Email capture
6. PATREON — CTA strip
7. ACTIVITY FEED — Multi-source activity stream (flexible, fills remaining space)

**Other presets:**
- Launch Day: telemetry, constellation, map / launch countdown, FM1, signals
- Post Unfold: telemetry, FM1, map / signals, regulatory, activity
- Earnings Week: telemetry, constellation, map / short interest, cash, activity

**Modes:** Dense (both panels) vs Minimal (panels hidden, large sat count center)

#### Design Tokens (from globals.css)

```
Backgrounds:
  --void-black: #030305       (page bg)
  --space-dark: #0A0A0F       (primary surface)
  --nebula-depth: #0D1117     (card bg)
  --cosmic-gray: #161B22      (elevated)
  --stellar-mist: #21262D     (hover)

Brand:
  --asts-orange: #FF6B35      (active states — used sparingly)
  --origin-blue: #0077C8      (secondary, links)

Status:
  --status-nominal: #22C55E   (green)
  --status-warning: #EAB308   (yellow)
  --status-critical: #EF4444  (red)

Text hierarchy:
  --text-primary: #FFFFFF
  --text-secondary: #E5E7EB
  --text-tertiary: #A1A1AA
  --text-muted: #71717A
  --text-dim: #52525B

Typography: JetBrains Mono, uppercase labels, tracking-wider
Large values: font-light (300), tabular-nums
Labels: 8px uppercase tracking-wider
```

#### Page Layouts (non-terminal)

**Landing (`/`):** Centered vertical. Brand → value prop → 2-col product grid (ASTS live / SPACE coming) → 3-col explore nav → email signup → footer with data source credits.

**Signals (`/signals`):** Full-width. Price chart with signal markers at top → filter controls → scrollable signal cards → brain search panel. Fixed right sidebar (360px) for signal detail. DocumentViewer modal.

**Horizon (`/horizon`):** Full-width. Header with stats → type filter pills + range selector → events grouped by month with severity dots, countdowns, type badges.

**Thesis (`/thesis`):** Centered (max-w-1000px). Input state vs results state. Input: textarea + suggestions + saved theses. Results: thesis statement + progress tracker + 3 stacked section panels (supporting/contradicting/synthesis).

**Patents (`/patents`):** Full-width. Header → view mode tabs (database/gallery/stats) → search + filters → stats bar → content area varies by view mode.

**Research (`/research`):** Fullscreen centered empty state → transitions to chat mode with scrollable messages + fixed bottom input.

#### HUD Layout Zones (available to any immersive page)
Canvas (z-0), Overlay (z-1), TopLeft (z-10), TopRight (z-20), LeftPanel (z-10, w-60), RightPanel (z-10, w-56), BottomLeft (z-10), BottomRight (z-10), BottomCenter (z-30), Center (z-50), Attribution.

#### Widget System
13 registered widgets. Each has a manifest (id, name, category, sizing, panel preference). Widgets read from TerminalDataProvider context, not their own fetches. Presets define which widgets go in which panel.

---

### Questions for Gemini

1. **What design principles from SpaceX/Starlink, Robinhood, Bloomberg, TradingView, Unusual Whales, and Palantir make their dashboards feel authoritative?** What can we steal?

2. **Looking at our terminal — is this what a retail space investor actually wants to see on their main dashboard?** The current default has: satellite telemetry, constellation progress, FM1 watch, ground track, short interest, cash position, launch countdown, activity feed. Is this the right hierarchy? What's missing that matters? What's there that doesn't?

3. **Our non-terminal pages (signals, horizon, thesis, patents, research) each have their own layout.** Should there be a unifying layout philosophy? Or is variety appropriate?

4. **The design language:** void-black + white + orange. JetBrains Mono everywhere. 8px uppercase labels. Is this actually working? Is it too cold? Too monotonous? Does it need a warmer human element? Or should it lean harder into the tactical/aerospace aesthetic?

5. **What's the one design decision we're getting wrong that we should fix before expanding to multi-ticker?**

Be specific. Reference the actual widgets, pages, and tokens. Don't give generic "consider user needs" advice — tell us what to change and why.

---

## GEMINI (turn 1) — Gemini 2.5 Pro — Design Teardown

### 1. Reference Brand Analysis: Deconstructing Authority

*   **SpaceX/Starlink: Cinematic Focus.** Ruthlessly curated mission control. Only the most critical telemetry for the current mission phase. Authority from **narrative clarity**. Color with extreme prejudice—green nominal, red off-nominal.
    *   **Steal:** "Mission phases." Presets should radically change what's on screen, not re-order widgets. During a launch, financial data is noise. During earnings, satellite telemetry is noise. Be more ruthless.

*   **Bloomberg Terminal: Information Supremacy.** Authority from raw data density. Brutally efficient for power users. Keyboard-driven (`<EQUITY> GO`) makes the user feel like a pilot.
    *   **Steal:** The command bar. "Brain" is the seed. Should be the primary way to navigate and pull up data. Don't bury navigation in widgets like "INTEL LINK". User should type `ASTS SI` and see short interest, or `/h` to go to Horizon.

*   **TradingView/Unusual Whales: The Chart is the Canvas.** Authority from making complex feel interactive. Chart is centerpiece, all modules contextualize it. Unusual Whales turns raw data into narrative ("Here's what smart money is doing").
    *   **Steal:** The narrative layer. Activity Feed should be an *intelligence* stream. Group related events. "FCC Filing Published → Stock Price +2% → 3 Analyst Mentions." Connect the dots.

*   **Robinhood: Radical Simplicity.** Authority from making a terrifying domain feel accessible. Massive fonts for key numbers, clear hierarchy. You know exactly what your portfolio is worth in a single glance.
    *   **Steal:** The "single most important number." On the terminal, what is it? Satellite count? Stock price? Next launch? Right now everything has equal visual weight. Decide what matters most.

*   **Palantir Foundry: The Ontology.** Authority from visualizing hidden connections between disparate data types. Person, place, transaction, satellite—all "objects." Power is showing the web of relationships.
    *   **Steal:** Think in objects. Click a satellite → see every patent, filing, and news event related to it. Dashboard → intelligence platform.

### 2. Critical Review: The `/asts` Terminal

**What Works:**
*   The Globe — immersive, immediately communicates the domain. Single best asset.
*   The Dark Theme — appropriate for finance + aerospace. `void-black` base is solid.
*   Real-time Data — TELEMETRY FEED and CONSTELLATION PROGRESS make platform feel alive.

**What's Broken:**

1.  **Marketing CTAs in the Cockpit.** EMAIL SIGNUP and PATREON widgets are catastrophic. Like pop-up ads on a fighter jet's HUD. Instantly shatters the illusion. **Remove them immediately.** Place on landing page or global footer.

2.  **Navigation as a Widget.** INTEL LINK is a crutch — navigation masquerading as content. Platform lacks coherent global navigation.

3.  **Decorative Overlays.** Targeting reticle and corner brackets serve no purpose. Visual noise. **Remove or make functional.**

4.  **Redundant Information.** GROUND TRACK 2D map is redundant when 3D globe shows the same thing. Kill it. If users need 2D, make it a mode of the globe.

5.  **Widget Hierarchy:**
    *   Left (Aerospace): Telemetry table is lazy — needs sparklines/gauges. FM1 WATCH too specific — should be "Selected Satellite" or "Watchlist".
    *   Right (Finance/Intel): SHORT INTEREST and CASH POSITION essential. LAUNCH COUNTDOWN great. But ACTIVITY FEED too generic. Where are SEC filings? Analyst ratings? Social sentiment? The intel feels shallow.

### 3. Layout Philosophy: Consistency is Authority

Every non-terminal page having its own bespoke layout is a red flag. Variety signals lack of coherent vision.

**Core problem: absence of a global application shell.**

**Recommendation: "Persistent Frame" Layout.**

1.  **Slim, icon-based Left Sidebar** — global navigation: Terminal, Signals, Horizon, Patents, Thesis/Research, Settings.

2.  **Global Top Bar** with:
    *   **Ticker Selector:** dropdown for ASTS, SPACE, etc. Most important element for scaling.
    *   **Brain Search Bar:** moved from terminal bottom-center to global top-center. Accessible from every page. True command bar à la Bloomberg.
    *   Global actions (notifications, profile).

3.  **Content Canvas Patterns:**
    *   **Immersive Canvas** (`/terminal`): full-bleed globe, side panels, frame can auto-hide.
    *   **Data Canvas** (`/signals`, `/horizon`, `/patents`): full-width for tables, feeds, dense data.
    *   **Focused Canvas** (`/thesis`, `/research`): centered with max-width for readability.

### 4. Design Language Refinement

*   **Color:** Palette is powerful but application is too vague.
    *   `--brand-accent`: orange for **interactive elements only** (buttons, active tabs, focused inputs)
    *   `--data-viz-primary`: `origin-blue` for charts/visualizations
    *   Status colors: use them more. Tag the data — is cash runway nominal or warning?

*   **Typography: JetBrains Mono for everything is a critical mistake.** Monospaced fonts are for code and tabular data. Fatiguing to read in paragraphs. Makes app feel like a dev side project.
    *   **Introduce a sans-serif** (Inter or Satoshi) for UI copy: labels, buttons, navigation, page titles, body text.
    *   Reserve JetBrains Mono for: numerical data, tables, charts, timestamps, telemetry.
    *   This hierarchy will instantly make the app feel more polished and professional.

*   **Labels:** `8px uppercase tracking-wider` is a good signature but overused. Works for widget titles. Fails for scannability. Use deliberately for headers, not every label.

### 5. The One Decision to Fix Before Scaling

**Build a global, persistent layout frame.**

1.  Solves multi-ticker problem (where does ticker switcher live?)
2.  Fixes navigation (kills INTEL LINK widget, declutters terminal)
3.  Centralizes command bar (Brain becomes universal Bloomberg-style tool)
4.  Creates cohesive platform (single product, not loosely related dashboards)

**Do not write a single line of code for $SPACE until you have built the house that both tickers will live in.**
