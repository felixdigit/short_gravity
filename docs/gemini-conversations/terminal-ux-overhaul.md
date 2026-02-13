# Terminal UX Overhaul — Competing with the Best

## CLAUDE (turn 1)

### Context

Short Gravity is a space sector intelligence platform. The primary product is the **Spacemob Terminal** — a deep $ASTS (AST SpaceMobile) intelligence dashboard live at shortgravity.com. It serves a community of space sector investors called "Spacemob."

**What we have:**
- 13,000+ brain chunks (RAG over patents, SEC filings, FCC filings, earnings transcripts, press releases, X posts)
- Real-time satellite telemetry (TLE data, orbital positions, constellation health)
- Signal detection (cross-source anomaly detection)
- SEC filing summaries, FCC regulatory tracking across 6 dockets
- Patent explorer (307 patents across 6 jurisdictions)
- Earnings command center with transcript analysis, topic heatmaps, guidance tracking
- Short interest, cash position, launch countdown data
- Competitive intelligence (adversarial FCC filing tracking)
- Space weather data
- Brain search (hybrid vector + keyword with LLM reranking)

**The problem Gabriel identified after 9 build threads:**
> "We greatly expanded the surface, BUT we didn't add much value. Too many pages, confusing to navigate, not even readable in some cases."

After a first pass at cleanup (reducing sidebar to 4 items, adding a Vault), Gabriel's verdict is still harsh:
1. **Brain is hidden** — The AI search/RAG capability is the crown jewel, but it's buried behind a nav item. Users should feel the intelligence layer everywhere, not have to navigate to a separate page.
2. **Too many pages** — Even with 4 core nav items, the secondary pages (Signals, Horizon, Thesis, Patents, Orbital, Regulatory, Competitive) feel disconnected. A Spacemob member shouldn't have to figure out which of 10+ pages has the answer.
3. **Terminal widgets are too compact** — The right-panel widgets (Short Interest, Cash Position, etc.) are tiny, poorly laid out, and don't surface the depth of data we have. They feel like afterthoughts, not intelligence.
4. **Not sophisticated enough** — We're competing with Bloomberg Terminal, Koyfin, Stratechery, Orbital Insight, and the best financial intelligence platforms. Our UX needs to feel like a command center, not a collection of small cards.

**Tech stack:** Next.js 14, Tailwind, Three.js (3D globe), custom Canvas charting engine, Supabase (PostgreSQL + pgvector), Zustand state management.

**Current terminal structure:** 3D globe in center, left panel (constellation matrix, signal feed, regulatory status), right panel (short interest, cash position, next event, earnings ledger). Sidebar with 4 items. Command palette (Cmd+K).

### The Ask

**Research the world's best intelligence/financial platforms and tell me how Spacemob Terminal should be structured.** Specifically:

1. **Study the best-in-class platforms** — Bloomberg Terminal, Koyfin, FactSet, Palantir Gotham/Foundry, Orbital Insight, Visible Alpha, Tegus, AlphaSense, Stratechery, The Information, Sentieo. What makes their UX work? How do they handle information density vs. clarity? How do they surface search/AI? How do they handle navigation when they have dozens of data domains?

2. **How should Brain (AI search) be surfaced?** — It's our biggest differentiator. 13,000+ chunks across patents, filings, transcripts. Should it be a persistent sidebar? A floating panel? Integrated into every page? How do the best platforms handle AI/search? Look at how Perplexity, Glean, AlphaSense, and Bloomberg's AI integrations work.

3. **How should the terminal consolidate pages?** — We have 10+ distinct data domains. Should they be tabs within the terminal? Panels that expand? A single scrollable dashboard? How do Bloomberg and Koyfin handle having hundreds of data views without making users navigate away?

4. **How should widgets evolve?** — Our widgets are tiny stat cards. Should they be expandable into full views? Should they have drill-down? How do the best dashboards handle progressive disclosure — showing a summary but allowing depth without leaving context?

5. **What's the information hierarchy?** — When a Spacemob member opens the terminal, what should hit them first? Price? Signals? The globe? Brain? What's the optimal layout for an investor intelligence platform?

Don't just describe these platforms abstractly — give me specific UX patterns, layout strategies, and a concrete recommendation for how Spacemob Terminal should be restructured. Be opinionated. We're building for sophisticated investors who want depth AND clarity.

## GEMINI (turn 1)

### Architecture Analysis

The current terminal suffers from "feature isolation." We have built powerful vertical engines (Orbit, RAG/Brain, Filings, Patents) but trap them in separate rooms. The user has to *go to* the Patents page to see patents, or *go to* the Brain page to search.

**Best-in-class terminals (Bloomberg, Koyfin, Palantir) do not work this way.** They are **workspace-centric**, not page-centric. They don't force you to leave your market monitor to check a filing; they let you bring the filing *into* your workspace.

**The Verdict:**
1. **Kill "Clean vs. Dense" Modes:** This is a false dichotomy. Sophisticated users want organized density, not emptiness.
2. **The Globe is a Widget, Not the Wallpaper:** Currently, the 3D globe forces all other data to be "overlays" or floating panels, limiting their density and utility. The globe should be a premier "Tile" that can be maximized, but it shouldn't dictate the layout of a text-heavy reading experience like SEC filings.
3. **Brain is Infrastructure, Not a Destination:** It must be omnipresent. A side-panel "Co-pilot" pattern (AlphaSense style) + a Global Command Palette (Perplexity/Arc style) is the winning combination.

### Spec Recommendation: The Workspace System

#### 1. The Shell: Command & Control
Instead of a "navbar," we move to a **Global Shell**.

* **Global Command Palette (`Cmd+K`):** The primary navigation engine. Inspired by Raycast/Arc.
  * *Search:* "Latest 8-K", "Orbit parameters", "Patents regarding antennas".
  * *Actions:* "Toggle globe", "Open earnings workspace", "Switch to $SPACE".
  * *Context:* It knows where you are. If you are looking at a filing, `Cmd+K` > "Summarize this" works instantly.
* **The Brain Panel (Right Sidebar):** A collapsible, persistent intelligence pane.
  * *Always available:* Click a button or hit `Cmd+B`.
  * *Context-aware:* "What does this patent imply for the spectrum application?" (It reads the active tile).
  * *Chat interface:* Multi-turn conversations (like Perplexity threads) that don't block the view of the data.

#### 2. The Workspace Engine (Layouts)
The Terminal is no longer a single page. It is a collection of **Workspaces** (tabs).

**Default Workspaces:**
1. **MISSION (The current "Terminal"):**
   * *Hero:* 3D Cockpit (Satellites/Orbit) - Top/Center.
   * *Support:* Signal Feed (Bottom Left), Ticker/Price (Top Right), Next Event (Bottom Right).
   * *Goal:* Situational awareness. The "Screensaver" mode lives here.
2. **INTEL (The "Bloomberg" view):**
   * *Layout:* Grid of dense data tiles. No 3D globe background.
   * *Tiles:* SEC Filings list, Earnings Transcript viewer, News/X Feed, Patent list.
   * *Goal:* Reading and analysis.
3. **MARKET (Financials):**
   * *Tiles:* Full-screen Charting (TradingView style but custom SG engine), Order Book (if avail), Short Interest, Cash Position.

#### 3. The Tile System (Widget Evolution)
Widgets evolve into **Tiles**.

* **States:**
  * *Standard:* The default box in the grid.
  * *Maximized:* Expands to fill the workspace (except for sidebars).
  * *Mini:* Minimized to a status bar or icon.
* **Drill-Down:**
  * *In-Tile Navigation:* Don't link away. A filing list tile should let you click a filing and read it *inside the tile* (Master-Detail pattern).

## CLAUDE (turn 2)

### What I Agree With

1. **"Feature isolation" is the right diagnosis.** We built 10+ powerful vertical engines and put them in 10+ separate rooms. The user has to navigate between them instead of composing them. This is the root cause of Gabriel's frustration.

2. **Brain as infrastructure, not destination — 100%.** The current `/research` page makes Brain feel like a feature you visit. It should be a layer you invoke from anywhere. The `Cmd+B` persistent right sidebar is the right pattern. AlphaSense and Perplexity both prove this works.

3. **Globe as widget, not wallpaper — agreed.** The immersive 3D globe looks impressive but it forces everything else into cramped floating overlays. When a Spacemob member wants to read a filing, the globe is noise.

### Where I Push Back

1. **Three workspace tabs is premature abstraction.** We don't have the content density to justify MISSION vs INTEL vs MARKET as three separate contexts yet. Bloomberg can do this because each workspace has 50+ data types. We have ~10 data domains. A single flexible layout with a composable tile grid is simpler and more powerful. Let the user maximize a tile to "enter" that context — don't force them to switch tabs.

2. **"Tile system with drag-and-drop" is over-engineered for our stage.** Palantir can build a tiling window manager because they have 200 engineers. We need a simpler version: **fixed grid layouts with expandable tiles.** Think Koyfin's approach — predefined layouts where clicking a tile expands it inline, not a fully customizable drag-and-drop grid.

3. **The Command Palette needs to become the Brain.** Right now Cmd+K is for navigation commands. Gemini suggests keeping them separate (Cmd+K for commands, Cmd+B for Brain). I think they should MERGE. One input: type a navigation command ("go to earnings") and it navigates. Type a question ("what did the last 10-K say about cash") and Brain answers. This is exactly how Perplexity works — one input, intelligent routing. Two separate hotkeys is cognitive overhead.

### My Counter-Proposal: The Single-Page Terminal

**One page. One URL. `/asts`.** Everything lives here.

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ [SG Logo]  [$ASTS $XX.XX +X%]  [═══ Brain Search ═══]  │  ← Top Bar (always visible)
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐      │
│  │ CONSTELLATION│ │  SIGNALS    │ │ SEC FILINGS │      │  ← Tile Grid (2-3 cols)
│  │ (Globe mini) │ │  (Feed)     │ │ (List+Read) │      │
│  └─────────────┘ └─────────────┘ └─────────────┘      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐      │
│  │ SHORT INT   │ │ REGULATORY  │ │ EARNINGS    │      │
│  │ (Chart+Stat)│ │ (Docket Map)│ │ (Guidance)  │      │
│  └─────────────┘ └─────────────┘ └─────────────┘      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐      │
│  │ PATENTS     │ │ CASH/BURN   │ │ HORIZON     │      │
│  │ (Explorer)  │ │ (Runway)    │ │ (Timeline)  │      │
│  └─────────────┘ └─────────────┘ └─────────────┘      │
│                                                         │
│                    [Brain Panel ────────────────]  →    │  ← Slides in from right on Cmd+K
└─────────────────────────────────────────────────────────┘
```

**Key differences from Gemini's proposal:**
- **No workspace tabs.** One grid, one page. Tiles expand inline.
- **Brain IS the command palette.** One input (`Cmd+K`), intelligent routing.
- **Globe is a tile**, not the background. Can be maximized for the immersive orbital view.
- **Every data domain is a tile** — not a page. Filings, Patents, Earnings, Regulatory, Signals, Horizon — all live as tiles in the grid.
- **Tiles have master-detail** — clicking a filing in the Filings tile opens it inline. No page navigation.

### Questions for Gemini (turn 2)

1. **How should tiles handle density at different viewport sizes?** On a 27" monitor you could show 9 tiles. On a 13" laptop you can show maybe 4. Should tiles collapse to a vertical scroll? Should there be a "priority" system where less important tiles hide below the fold?

2. **How should the Brain panel interact with tiles?** If I ask "summarize the latest 8-K" in the Brain panel, should the answer appear in the Brain panel only? Or should it also highlight/navigate to the relevant filing tile?

3. **What's the right tile size?** Bloomberg tiles are dense — small text, lots of data. Koyfin tiles are medium — charts with clear labels. Our current widgets are too small. What's the minimum useful tile size for each data type?

4. **Should tiles be fully contained or should some data types still warrant a full-page view?** Earnings transcripts are 10,000+ words. Patents have complex claim trees. Can these really work as tiles, or do they need a maximize-to-fullscreen mode?

## GEMINI (turn 2)

### The Pivot: Unifying the Vision

Claude is right to push back on the workspace abstraction. At our current scale (10 domains), forcing users to switch tabs is unnecessary friction. A single, composable glass pane is superior.

However, a "scrollable dashboard" is a trap. It encourages passive consumption. A **Terminal** is an active workspace.

We will adopt a **Bento Grid System** (inspired by linear.app and Apple's finest UIs) that balances density with focus. It is a single page, but it is not a static feed. It is a dynamic surface where tiles breathe, expand, and interact.

### 1. The Architecture: Bento Grid + Focus Mode

We abandon the "Tabs" concept for a **Single Page View (`/asts`)** but implement strict layout rules.

**The Grid Engine:**
* **Base Unit:** The screen is divided into a 12-column grid.
* **Tile Types:**
  * **1x1 (Status):** Ticker, Countdown, Weather.
  * **2x2 (Standard):** Charts, Signals Feed, Filings List.
  * **4x2 (Wide):** Timeline, Regulatory Map.
  * **Max (Focus):** Fullscreen overlay.

**The "Focus Mode" Pattern:**
* **Default State:** The Earnings Tile shows a summary: "Q3 Earnings: Missed rev by 2%. Guidance raised." + a mini sparkline.
* **Interaction:** User clicks the "Expand" icon on the tile.
* **Focus State:** The tile animates to fill 90% of the viewport (modal overlay with blurred background). The content *transforms* from summary to full transcript reader.
* **Result:** You stay on the same URL, in the same context, but get the deep reading experience of a dedicated page.

### 2. The Interaction: Merged Command & Brain (Omnibox)

One input to rule them all.

* **Trigger:** `Cmd+K`.
* **Visual:** A centered modal input.
* **Logic:**
  * **Prefix Matching:** "/go" → Navigation. "?" → Force Brain mode.
  * **Intelligent Routing (No prefix):** "Cash" → shows both "Open Cash Tile" (Nav) and "Ask Brain: What is the current cash position?" (AI).

**Brain Output Location:** It must do both. If you ask "What is the cash burn?", the Brain Panel slides out with the text answer AND it scrolls to the Cash Position Tile with a momentary orange highlight. Trust = AI synthesis + raw data proof.

### 3. Responsiveness & Tile Sizing

* **Desktop (1920px+):** 4-column Bento layout.
* **Laptop (1280px):** 3-column.
* **Tablet:** 2-column.
* **Minimum tile:** `300px x 300px`. Standard: `600px x 400px`.
* **Priority System:** `hidden-mobile` class for non-critical tiles (globe) to keep mobile focused on hard data.

### 4. Master-Detail for Heavy Content

* **Transcripts/Patents cannot be read in a small tile.**
* **Solution:** Click item in list tile → triggers Focus Mode (90% viewport overlay). Zero page loads, instant transitions, context preservation.

## CLAUDE (turn 3) — Convergence Summary

We've converged on the core architecture in 2 turns. Here's what we agree on:

### The Agreed Spec

1. **Single Page Terminal (`/asts`)** — No workspace tabs, no multi-page navigation. Everything lives on one surface.

2. **Bento Grid of Tiles** — Each data domain (Signals, Filings, Patents, Earnings, Regulatory, Constellation, Short Interest, Cash, Horizon) is a tile in a responsive grid. Not tiny stat cards — substantial tiles with real content.

3. **Focus Mode** — Any tile can expand to 90% viewport for deep content (transcripts, patent details, filing readers). Stays on same URL. Modal overlay with blur.

4. **Brain = Omnibox** — `Cmd+K` unifies navigation + AI search. No separate Brain page. Brain answers appear in a right sidebar panel AND highlight relevant tiles.

5. **Globe is a tile** — Not the wallpaper. Can be maximized for immersive view but doesn't constrain the layout.

6. **No sidebar navigation** — The Omnibox (`Cmd+K`) handles all navigation. The left sidebar goes away entirely. Top bar has: logo, ticker, Omnibox trigger, Brain toggle.

### What This Means for Implementation

This is a significant architectural shift — not a widget reshuffle. It requires:
- New `Tile` primitive component (replaces current Widget system)
- New `BentoGrid` layout component (replaces HUDLayout)
- New `FocusMode` system (Zustand store + overlay)
- Merging Brain into the Command Palette (Omnibox)
- Converting every existing page into a tile with summary + focus views
- Removing the sidebar entirely

**This is Gabriel's call.** The spec is ready. The implementation is a multi-session effort.
