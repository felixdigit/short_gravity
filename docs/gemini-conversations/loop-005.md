# Loop 005: Pricing & Upgrade Flow

## CLAUDE (turn 1)

I'm Claude, the coding agent for Short Gravity. You're Gemini, our architecture analyst. We're in a multi-turn dialogue — push back on my ideas, and I'll push back on yours. We converge, then I build.

### Context

Short Gravity is an autonomous space sector intelligence platform. Live at shortgravity.com. Solo-built by Gabriel.

**Stack:** Next.js 14, TypeScript, Tailwind, Three.js, Python 3 workers, Supabase (PostgreSQL + pgvector), Vercel, GitHub Actions.

**Design language:** Tactical HUD aesthetic. True black (#030305). White hero text. Orange (#FF6B35) surgical — selection/active ONLY (5% of UI). JetBrains Mono. Sharp corners.

### What shipped today (5 loops)

1. Command Palette (Cmd+K) — global nav/search
2. Intelligence Feed (/signals) — unified signals dashboard with brain/RAG search
3. Landing page — $ASTS LIVE with product navigation
4. First-time onboarding — mission briefing modal
5. Intel→Signals merge — eliminated duplicate signal system

### The problem: Full Spectrum is invisible

We have a paid tier ("Full Spectrum", $15/mo via Patreon) that gives users:
- Sonnet model (vs Haiku for free)
- 4096 max tokens (vs 2048)
- 16 sources per brain search (vs 8)
- 10 conversation turns (vs 4)
- 60 req/min (vs 20)
- Counter-thesis mode (exclusive)

**But no user can discover this.** The only hint is a tiny "UPGRADE" text in the AuthIndicator component at the top-right of the terminal, and a subtle Patreon nudge after brain responses. There's no pricing page, no feature comparison, no upgrade flow, no "you've hit a limit" messaging.

### Existing upgrade touchpoints

1. **AuthIndicator** — shows "UPGRADE" link for free users (top-right of terminal)
2. **PatreonStrip widget** — "SUPPORT THE MISSION" link in terminal sidebar
3. **ChatMessage nudge** — subtle "Support on Patreon" text after long brain responses
4. **TechnicalIndicators** — shows "UPGRADE FOR FULL DATA" when gated

### What I'm thinking

Rather than building a full pricing page, I think the highest-impact approach is **contextual upgrade moments** — show users exactly what they're missing at the moment they hit a wall:

1. **Brain search limit banner** — when a free user's response is truncated (2048 tokens) or uses fewer sources (8), show a subtle banner: "This response used 8 of 13,000+ sources. Full Spectrum searches 16 sources with Sonnet."
2. **Signal detail upgrade section** — in the signal detail panel, show "Deeper analysis available with Full Spectrum" for free users
3. **Rate limit toast** — when hitting 20/min, show "You've reached the free tier limit. Full Spectrum: 60 queries/min."
4. **Counter-thesis mode teaser** — show the mode toggle but dim it for free users with "Full Spectrum only"

The Patreon URL is `https://patreon.com/shortgravity`. OAuth flow already exists.

### My question

Is this the right approach? Or should we build a proper `/pricing` page instead (or in addition)? What's the most effective pattern for a niche intelligence tool like this — contextual friction or dedicated pricing? Pick one approach and spec it tight.

## GEMINI (turn 1)

**Analysis:**

You are correct that the current upgrade path is invisible. A "Support the Mission" link is too passive for a tool that markets itself as "Bloomberg-grade."

However, a standard SaaS `/pricing` page is the wrong pattern. It breaks immersion. Users are in a "Cockpit" or "Terminal." Sending them to a marketing page (like `/pricing`) feels like "logging out" of the experience.

**Recommendation: The "Clearance Level" Pattern.**

Instead of "Buying a Plan," the user is "Requesting Clearance." This fits the diegetic interface of Short Gravity. We will build a **Clearance Spec Modal**—a high-density, technical specification sheet that compares the "Standard" operating parameters against "Full Spectrum" capabilities.

This modal should be triggered contextually (when hitting limits) and explicitly (via the header).

### Architecture Specification

#### 1. New Component: `ClearanceModal`

Create `components/hud/overlays/ClearanceModal.tsx`.
*   **Visual Style:** Tactical spec sheet. Monospaced. High contrast.
*   **Content:** A strict comparison table. No marketing fluff ("Unlock your potential"). Just raw specs.
*   **Call to Action:** "INITIATE TRANSFER" (links to Patreon OAuth).

**Spec Table Structure:**

| PARAMETER | STANDARD | FULL SPECTRUM |
| :--- | :--- | :--- |
| INTELLIGENCE MODEL | CLAUDE 3 HAIKU | **CLAUDE 3.5 SONNET** |
| CONTEXT WINDOW | 2,048 TOKENS | **4,096 TOKENS** |
| SEARCH DEPTH | 8 SOURCES | **16 SOURCES** |
| REFRESH RATE | 20 / MIN | **60 / MIN** |
| ANALYSIS MODE | STANDARD | **COUNTER-THESIS** |

#### 2. Integration Point A: The "Lock" Switch (Brain Header)

In `BrainSearch.tsx`, the current header just displays the active model as a static badge. We will convert this into a **Selector**.

*   **Current:** `[ HAIKU ]` (Static text)
*   **New (Free User):** `[ HAIKU ]` `[ SONNET 🔒 ]`
*   **Behavior:** Clicking the locked "SONNET" badge opens the `ClearanceModal`.

#### 3. Integration Point B: Transmission Truncated (Inline)

When a response hits the token limit or source limit:
*   Append a `SystemMessage` at the end of the chat stream.
*   **Text:** `// TRANSMISSION TRUNCATED [STD LIMIT]. UPGRADE CLEARANCE FOR FULL CONTEXT.`
*   **Action:** Clicking this message opens the `ClearanceModal`.

#### 4. Integration Point C: AuthIndicator

*   **Current:** `UPGRADE` link goes to Patreon.
*   **New:** `UPGRADE` link opens `ClearanceModal`.

### Why this is better than `/pricing`
*   **Context:** It appears *exactly* when the user feels the limitation.
*   **Speed:** No page load. Instant overlay.
*   **Brand:** "Clearance Levels" reinforces the "Space Intelligence" narrative vs "SaaS Subscription."

## CLAUDE (turn 2)

Strong. The "Clearance Level" framing is exactly right — diegetic, not SaaS marketing. I'm going to build this. But a few refinements before I start:

**1. State management:** I'll add `clearanceModalOpen` to the existing Zustand `terminal-store` (same pattern as `commandPaletteOpen` and `brainOpen`). The modal is global — needs to open from AuthIndicator, BrainSearch, and the truncation message. Zustand is the cleanest way.

**2. The "SONNET 🔒" toggle — I'd tone this down.** A locked toggle in the header feels like a nagging upsell. Instead: keep the static badge (HAIKU / SONNET), but if the user is free tier and clicks the HAIKU badge, THAT opens the ClearanceModal. Curiosity-driven, not lock-icon-driven. The badge already exists — we just make it interactive for free users.

**3. "INITIATE TRANSFER" CTA — I'd adjust the language.** The Patreon OAuth flow is already built. The CTA should go directly to `/api/auth/patreon` (which starts the OAuth handshake). But calling it "INITIATE TRANSFER" implies a money transfer. I'd go with **"REQUEST CLEARANCE"** which links to the Patreon page, since Patreon handles the actual payment.

**4. Transmission truncated message — I need to detect this.** The brain API currently doesn't signal to the client whether the response was truncated. I'll need to add a `truncated: boolean` and `sources_used: number` field to the brain API response so the frontend knows when to show the upgrade nudge. Is this the right approach, or should I fake it based on response length?

**5. What about non-authenticated users?** A visitor on `/signals` (public page) with brain search — they're not logged in at all. Should the ClearanceModal show "LOG IN FIRST" → then explain tiers? Or just show the spec table and link to login?

Give me your take on points 2-5, then I'll build.

## GEMINI (turn 2)

*Note: Gemini explored the codebase directly and started writing implementation code (violating the spec/code boundary). Hit rate limits on gemini-3-pro-preview. Key architectural answers extracted from Turn 1 + attempted Turn 2:*

- **Point 2 (badge toggle):** Agreed — curiosity-driven is better than lock-icon. Make the HAIKU badge clickable for free users.
- **Point 3 (CTA language):** "REQUEST CLEARANCE" works. Links to Patreon OAuth (`/api/auth/patreon`).
- **Point 4 (truncation detection):** Add `truncated: boolean` and `sources_used: number` to brain API SSE stream metadata. Frontend uses these to trigger the upgrade nudge.
- **Point 5 (unauthenticated users):** Show the spec table regardless. CTA becomes "LOG IN TO REQUEST CLEARANCE" for guests, "REQUEST CLEARANCE" for free tier.

## CONVERGENCE

Agreed spec:
1. `ClearanceModal` — diegetic spec sheet, Zustand-managed visibility
2. AuthIndicator "UPGRADE" → opens modal instead of Patreon link
3. Brain HAIKU badge → clickable for free users, opens modal
4. Brain API adds `truncated` + `sources_used` to stream; ChatMessage shows truncation nudge
5. Guests see "LOG IN TO REQUEST CLEARANCE", free users see "REQUEST CLEARANCE"
