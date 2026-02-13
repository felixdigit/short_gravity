# Public Beta Strategy: Core vs Experimental Split + Terminal Refinement

## CLAUDE (turn 1)

### Context

We've built 9 GOLDEN threads across 9 major pages + the terminal. Gabriel's verdict after the experiment:

> "Overall it's decent results, we have greatly expanded the surface, BUT we didn't add much value to the platform. There are way too many pages right now and it's confusing to navigate. In some cases it's not even readable, content too small and lack of contrast. Now we want to make a distinction between experimental pages and CORE pages for public beta. We will focus on refining the main ASTS terminal view and make it as dynamic, pretty, and useful as possible."

### Current Page Inventory (29+ pages)

**Terminal** (`/asts`) — Immersive 3D globe + floating widget panels + portal drawers. Composition:
- Left panel: Constellation Matrix, Environment Strip, FM1 Monitor, Ground Track Map
- Right panel: Short Interest, Cash Position, Launch Countdown, Activity Feed
- Portal drawers: Telemetry (T key), Intel (I key) — full deep-dive views
- 3D globe background with 7,500 satellite markers
- Brain search overlay, satellite detail cards, welcome briefing

**Intelligence pages** (built in Threads 001-009):
- `/signals` — Signal cards + detail panel + brain search + document viewer
- `/horizon` — Future event timeline from 7 sources
- `/thesis` — Three-section thesis builder (FOR/AGAINST/SYNTHESIS)
- `/regulatory` — FCC docket battlemap + adversarial matrix
- `/orbital` — Constellation health + space weather
- `/competitive` — D2C competitive landscape + Tale of the Tape
- `/earnings` — Transcript viewer + topic matrix + guidance ledger
- `/briefing` — Cross-thread situation report
- `/patents` — 307 patents, table/gallery/stats views
- `/research` — Brain/RAG search interface
- `/satellite/[id]` — Per-satellite telemetry + asset logbook

**Dev pages**: 13+ pages under `/dev/*`, `/experiments`, `/asts/experimental`

### Problems Identified

1. **Too many top-level nav items** — Sidebar has 8 items. Landing page EXPLORE grid has 10 items. Users don't know where to go.
2. **Typography/contrast issues** — Many pages use 7-9px text with white/20-35 opacity. Readable on a developer's 5K monitor, not on a laptop.
3. **No information architecture** — Pages feel like a collection of tools, not a cohesive product. Each page was built as a standalone thread.
4. **Terminal is the product but doesn't surface the other pages' data** — The terminal has its own widget system but doesn't show signals, regulatory threats, earnings countdown, or competitor moves unless you know to press T or I.
5. **Undiscoverable features** — T/I portal keyboard shortcuts, brain search (Cmd+K), preset switching — no visual hints.

### The Terminal's Architecture (what we're working with)

The terminal is well-architected for refinement:
- **Widget system** with registry, manifests, presets — we can add/remove/rearrange widgets without touching the page
- **TerminalDataProvider** — shared context, widgets don't fetch their own data
- **Preset system** — named configurations (default, launch-day, post-unfold, earnings-week)
- **Portal drawers** — full-height deep-dive panels (Telemetry left, Intel right)
- **HUDLayout** compound component — Canvas, LeftPanel, RightPanel, BottomCenter, etc.
- **SGChart engine** — custom Canvas 2D charts, configuration-driven
- **13 registered widgets**: telemetry-feed, constellation-progress, constellation-matrix, environment-strip, fm1-monitor, fm1-watch, mercator-map, short-interest, cash-position, launch-countdown, activity-feed, signal-feed, regulatory-status

### What Needs Deciding

1. **Core pages for public beta** — What 3-4 pages ship? What happens to the rest?
2. **Terminal refinement scope** — What widgets should the terminal show by default? What new widgets would make it more dynamic/useful? Should data from other threads (signals, regulatory, earnings, competitors) be surfaced as terminal widgets?
3. **Navigation simplification** — How do we reduce from 8 sidebar items to 3-4 without losing discoverability?
4. **Typography/contrast overhaul** — Global CSS changes or per-page fixes? What's the minimum viable readability pass?
5. **The intelligence pages we built** — Do they become portal views inside the terminal? Standalone but secondary? Or hidden entirely?

### Constraints

- Solo operator. Can't redesign everything.
- Platform is live. Don't break what works.
- March 2 earnings call is 17 days away — earnings page must remain functional.
- Patreon monetization — need a compelling public beta experience.
- $SPACE is next but not yet started.

### The Question

How should we restructure for public beta? Specifically:
1. What are the CORE pages (max 4)?
2. How should the terminal be refined to be the "one page that matters"?
3. What happens to the 9 thread pages — terminal widgets, portal views, secondary nav, or hidden?
4. What's the right typography/contrast floor for public readability?

## GEMINI (turn 1)

# Spec Update: Public Beta Structure & Terminal Consolidation

We are pivoting from a "website with many pages" to a "platform with a central operating system." The Terminal is the OS. Everything else is a utility.

Here is the architectural definition for the Public Beta.

### 1. The Core Hierarchy

We will drastically reduce the primary surface area. The user should feel like they have entered a cockpit, not a directory.

**Primary Navigation (Sidebar)**
Only 3 items exist at the top level.

1.  **TERMINAL** (`/asts`) — The live operating picture. Real-time data, orbit tracking, signal feeds. The "Home" screen.
2.  **BRIEFING** (`/briefing`) — The synthesis. Narrative reports, daily summaries, catch-up reading. The "Morning Paper."
3.  **BRAIN** (`/research`) — The oracle. Search, chat, and RAG operations. The "Search Engine."

*Everything else* (`/signals`, `/regulatory`, `/patents`, `/earnings`, `/thesis`, `/competitive`, `/horizon`) is moved to a **secondary "Intelligence Vault"** menu (a single sidebar icon that opens a drawer or modal list), or accessed contextually via Terminal widgets.

### 2. Terminal Refinement: "The One Page That Matters"

The Terminal currently feels isolated from the rich data we built in the threads. We will fix this by **converting page summaries into Terminal Widgets**.

The Terminal must answer: "What is happening *right now*?" and "What is *about to happen*?"

**New/Refined Widgets (The "Dashboard" Preset)**
We will update the default Terminal layout to surface data from the hidden pages.

| Widget | Source Page | Function |
| :--- | :--- | :--- |
| **Signal Ticker** | `/signals` | A compact, scrolling list of the last 5 high-impact signals. Clicking one opens the Signal detail view (portal or page). |
| **Countdown Block** | `/horizon` | Prominent countdown to the *single next critical event* (e.g., Launch, Earnings, FCC ruling). |
| **Threat Level** | `/regulatory` | A simple traffic-light indicator of FCC status (e.g., "Active Docket: SCS-23-42"). |
| **Sentiment Gauge** | `/thesis` | Visual aggregate of the Bull/Bear synthesis. |
| **Earnings Ledger** | `/earnings` | (Visible only <30 days to earnings) Mini-table of consensus vs. whisper numbers. |

**Architectural Change:**
The `TerminalDataProvider` must now fetch a lightweight "Situation Report" payload that includes the top-line summary data from Signals, Horizon, and Regulatory, so these widgets function without loading the heavy full pages.

### 3. The "Intel Portal" Strategy

We have two Portal Drawers in the Terminal (Telemetry `T` and Intel `I`). We will repurpose the **Intel Portal (Right Drawer)**.

*   **Current State:** It's a placeholder or specific view.
*   **New State:** The Intel Portal becomes the "Quick Look" wrapper for our deep pages.
*   **Behavior:** When a user clicks the "Signal Ticker" widget, it opens the **Intel Portal** with the Signals view loaded inside it.
*   **Benefit:** Users stay in the immersive 3D context while accessing deep data. They don't navigate away (`router.push`) unless they explicitly choose "Full View."

### 4. Visual Overhaul: The "Legibility Floor"

We are failing the "Laptop Test." We will enforce a strict visual standard for the Public Beta.

1.  **No Opacity for Text:** Stop using `text-white/40`. Use specific Zinc/Slate shades (e.g., `text-zinc-500`) to ensure proper sub-pixel rendering.
    *   *Hero:* `#FFFFFF` (White)
    *   *Primary:* `#E4E4E7` (Zinc-200)
    *   *Secondary:* `#A1A1AA` (Zinc-400)
    *   *Tertiary/Label:* `#71717A` (Zinc-500)
2.  **Minimum Font Size:**
    *   Absolute floor: `11px` (UPPERCASE only, tabular nums).
    *   Standard Body: `13px` or `14px`.
    *   Current 9px labels must be bumped to 11px or removed if they don't fit.
3.  **Contrast Ratios:** All actionable text must pass WCAG AA against the background `#030305`.

### 5. Execution Plan

**Step 1: Sidebar & Routing (Clean up the house)**
- Modify `Sidebar.tsx`.
- Hide deep links behind a "Library" or "Vault" icon.
- Ensure `/asts`, `/briefing`, and `/research` are the heroes.

**Step 2: Data Aggregation (Connect the pipes)**
- Update the `useTerminalData` hook to fetch summary stats from Signals/Regulatory/Horizon tables.

**Step 3: Widget Implementation (The Dashboard)**
- Create `SignalTickerWidget`.
- Create `NextEventWidget`.
- Update the Default Preset to include these, replacing lower-value widgets (like purely static environment strips) to make room.

**Step 4: Legibility Pass (The Polish)**
- Global CSS variable audit for text colors.
- "squint test" on the Terminal. If you can't read it from 3 feet back, bump the size.

This structure respects the work done (nothing is deleted) but focuses the user experience (everything is discovered through the Terminal).

## CLAUDE (turn 2)

### Agreements

Strong alignment on the core structure. Terminal as OS, 3 primary nav items, thread pages demoted. The "Intelligence Vault" pattern is clean. The legibility floor is overdue.

### Pushback & Refinements

**1. Sidebar: 3 items → 4. Earnings must be primary.**

March 2 earnings call is 17 days away. The `/earnings` page has a transcript viewer, topic matrix, and guidance ledger — that's not widget-reducible data. During earnings season, this is the second most important page after the terminal. Proposal:

- **TERMINAL** (`/asts`) — always
- **BRIEFING** (`/briefing`) — always
- **EARNINGS** (`/earnings`) — always (or at minimum, promoted during earnings season)
- **BRAIN** (`/research`) — always

4 items is still clean. The earnings page has too much depth (full transcripts, topic-by-topic analysis) to live inside a portal drawer or a widget.

**2. "Sentiment Gauge" widget — skip it.**

The thesis system is session-based — users build arguments manually. There's no persistent aggregate sentiment to display. A "Bull/Bear gauge" with no real data behind it is exactly the kind of hollow widget that Gabriel said "didn't add much value." Cut it from the widget list. If we want sentiment later, it needs a real signal pipeline behind it, not a UI wrapper around empty state.

**3. Intel Portal repurposing — too ambitious for this phase.**

Loading full page views inside the portal drawer means we need to:
- Extract page content into standalone components (currently they're full `page.tsx` files with their own data fetching)
- Handle scroll, keyboard focus, and state management inside a drawer context
- Deal with the fact that portal drawers have fixed-width constraints

This is a good v2 idea but it's a significant refactor. For public beta, simpler: widgets link out to the full page. The pages still exist at their routes — they're just not in primary nav. Users who click "View all signals" from the Signal Ticker widget navigate to `/signals`. That's fine.

**4. Typography: I agree on the floor, but disagree on killing opacity entirely.**

Opacity-based text is core to the HUD aesthetic. `text-white/70` on `#030305` renders at approximately `#B3B3B3` which is perfectly readable. The problem isn't opacity itself — it's that we went too low (`white/20`, `white/25`, `white/30`). Proposal:

- **Floor:** `white/50` minimum for any readable text (≈ `#808080` on void black)
- **Labels/headers:** `white/70` minimum
- **Hero values:** `white` or `white/90`
- **Decorative/divider text:** `white/40` allowed but ONLY for non-essential decoration
- Keep the opacity system. Don't switch to Zinc. Zinc doesn't match the void-black HUD language.

Font size floor: agree on 11px minimum. But I'd set the standard body at `12px` not `13-14px` — JetBrains Mono at 13px in uppercase tracking-wider gets chunky fast. 12px is the sweet spot for data-dense HUD panels.

**5. Widget replacement — what gets cut from the default preset?**

We're adding Signal Ticker, Next Event, Threat Level, and Earnings Ledger. The current default preset has 8 slots (4 left, 4 right). What gets removed? My suggestion:

**Keep:** Constellation Matrix (core orbital data), Short Interest (core financial), Cash Position (core financial), Launch Countdown (→ merge into Next Event?)
**Demote:** Environment Strip (low signal-to-noise), FM1 Monitor (specific to one satellite — niche), Activity Feed (replaced by Signal Ticker which is strictly better), Mercator Map (cool but redundant with the 3D globe)

**New default layout:**
- Left: Constellation Matrix, Signal Ticker, Threat Level
- Right: Short Interest, Cash Position, Next Event, Earnings Ledger (conditional)

**6. The landing page — what happens to it?**

You didn't address the landing page (`/`). Currently it has a big EXPLORE grid with 10 items. For public beta, should it:
- Redirect straight to `/asts` (terminal IS the product)?
- Remain as a minimal gateway with 3-4 cards pointing to the core pages?
- Something else?

### The Question for Turn 2

1. Do you agree on 4 sidebar items (adding Earnings)?
2. Confirm: skip Sentiment Gauge, defer Intel Portal repurposing?
3. Opacity floor vs Zinc switch — which direction?
4. Widget replacement: does the proposed default layout make sense?
5. Landing page strategy?

## GEMINI (turn 2)

# Spec Finalization: Public Beta Architecture

We have consensus. Your pragmatic constraints regarding the Portal refactor and the Earnings prominence are accepted. We will ship a dense, focused product, not a sprawling website.

Here is the **Final Specification** for the Public Beta refactor.

### 1. Navigation & Routing Structure

**The Sidebar (The "Core 4")**
We move from 8 items to 4. This is the persistent global navigation.

1.  **TERMINAL** (`/asts`) — The OS.
2.  **BRIEFING** (`/briefing`) — The Narrative.
3.  **EARNINGS** (`/earnings`) — The Financials. (Permanent fixture for Beta).
4.  **BRAIN** (`/research`) — The Oracle.

**The "Vault" (Secondary Navigation)**
How do users access `/signals`, `/regulatory`, `/patents`, `/horizon`, `/competitive`?
*   **Implementation:** A "Grid/Apps" icon at the bottom of the sidebar (above Settings/Profile).
*   **Action:** Opens a minimal **Command Palette / Modal** listing the secondary tools.
*   **Rationale:** Keeps the sidebar clean but keeps the tools accessible for power users without relying solely on widget clicks.

**The Landing Page (`/`)**
*   **Strategy:** Direct Entry.
*   **Behavior:** `/` redirects immediately to `/asts`.
*   **Rationale:** We are building a terminal, not a marketing site. The "wow" moment is the spinning globe, not a landing page hero section.

### 2. The Terminal Layout (Default Preset)

We adopt your proposed consolidation. This layout maximizes data density while removing "dead" pixels.

**Left Column (Orbital & Risk)**
1.  **Constellation Matrix** (Top, Tall) — The visual anchor for satellite status.
2.  **Signal Ticker** (Middle) — *NEW.* Replaces Activity Feed. Scrollable list of last 5 signals. Click -> Router Push to `/signals`.
3.  **Threat Level** (Bottom) — *NEW.* Minimal FCC/Regulatory status. Traffic light + Docket ID. Click -> Router Push to `/regulatory`.

**Right Column (Financial & Timeline)**
1.  **Short Interest** (Top) — Core financial metric.
2.  **Cash Position** (Upper Mid) — Core runway metric.
3.  **Next Event** (Lower Mid) — *NEW.* Merges "Launch Countdown" and "Horizon".
    *   *Logic:* If Launch confirmed < 14 days, show Launch. Else if Earnings < 30 days, show Earnings. Else show next major Horizon event.
4.  **Earnings Ledger** (Bottom) — *NEW.* Condensed view of the detailed ledger. Visible/Highlighted only when Earnings < 30 days.

**Removed/Demoted:**
*   *Environment Strip:* Gone.
*   *FM1 Monitor:* Gone (too specific).
*   *Mercator Map:* Gone (redundant).
*   *Activity Feed:* Replaced by Signal Ticker.

### 3. Visual System Update (The "HUD Standard")

We accept the "Opacity Preservation" argument but strictly enforce the floor.

**Typography Rules**
*   **Font:** JetBrains Mono (Global).
*   **Size Floor:** `11px` (Uppercase, Tracking-Wide). *Absolutely no 9px.*
*   **Body Standard:** `12px` (Regular).
*   **Headers:** `14px` (Bold/Medium).

**Color/Opacity Rules**
*   **Background:** `#030305` (Void).
*   **Hero/Value:** `text-white` (100% opacity).
*   **Label/Secondary:** `text-white/70` (Minimum for readability).
*   **Disabled/Placeholder:** `text-white/50` (The absolute floor).
*   **Banned:** `text-white/40` and below. If it's not important enough to be 50%, it shouldn't be on the screen.
*   **Accents:** Keep the Orange `#FF6B35` for active states/cursors only.

### 4. Implementation Priorities

**Phase 1: The Cleanup (1-2 Hours)**
1.  **Sidebar:** Update `Sidebar.tsx` to the "Core 4" + Vault Icon.
2.  **Redirect:** Set `next.config.mjs` or Middleware to route `/` to `/asts`.
3.  **CSS Audit:** Search and destroy `text-xs` (often 12px, check config) and `text-[9px]` or `text-[10px]`. Replace with `text-[11px]` class or custom utility. Search/Destroy `white/20`, `white/30`.

**Phase 2: The Widget Factory (2-3 Hours)**
1.  **Data Hook:** Update `useTerminalData` to fetch the "Situation Report" (Signals head, Next Event, Regulatory status).
2.  **Build Widgets:** Create `SignalTicker`, `ThreatLevel`, `NextEvent`.
3.  **Update Registry:** Register new widgets in `widget-registry.tsx`.

**Phase 3: The Assembly (1 Hour)**
1.  **Layout:** Update the default layout config in `terminal-state.ts`.
2.  **Verify:** Check the "Laptop Test" (resize window to 1366x768).

Let's begin with Phase 1. Clean the navigation and routing first.
