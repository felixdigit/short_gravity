# Short Gravity

## Project Overview
Space sector intelligence platform focused on $ASTS. Web app (Terminal), data workers, research tools.

**Purpose:** Enable Gabriel to research, visualize, and deploy intuitively—fetch complete data, generate alpha insights, produce content for X/shortgravity.com.

## Gabriel
Solo operator. Research, writing, content, visuals, code.
- Works intuitively, no hand-holding
- Space sector investor, focused on $ASTS
- **Execute. Don't over-explain. Don't ask unnecessary questions.**

## Tech Stack
- **Frontend:** Next.js 14, TypeScript, Tailwind CSS, Three.js
- **Backend:** Python 3, Playwright
- **Database:** Supabase
- **APIs:** Space-Track.org, SEC EDGAR, Finnhub, Alpha Vantage, Claude API
- **Deploy:** Vercel

## Directory Structure

```
short_gravity/
├── short-gravity-web/           # Next.js app
│   ├── app/
│   │   ├── (dashboard)/terminal # Main terminal
│   │   ├── (immersive)/         # Fullscreen layouts
│   │   ├── dev/hud-v2/          # Clean HUD (use this)
│   │   └── api/                 # API routes
│   ├── components/
│   │   ├── primitives/          # Atomic UI (Text, Stat, Panel, etc.)
│   │   ├── hud/                 # HUD layout + widgets
│   │   ├── earth/               # 3D globe, satellites
│   │   └── cockpit/             # Legacy terminal components
│   └── lib/
│       ├── hooks/               # React Query data hooks
│       ├── data/                # Static data (satellites, catalysts)
│       └── stores/              # Zustand stores
├── scripts/data-fetchers/       # Python workers
├── design/                      # Style guide, Figma specs
├── docs/                        # Consolidated documentation
├── research/                    # Alpha nuggets, notes
└── short-gravity-architecture/  # Database schema
```

## Documentation

| Doc | Purpose |
|-----|---------|
| `INSIGHTS.md` | **Read first** — Compounding knowledge, architectural decisions, alpha edges |
| `globals.css` | **UI source of truth** — CSS variables, colors, typography |
| `docs/UI_ARCHITECTURE.md` | Component system — primitives, HUD layout, widgets |
| `docs/DATA_SOURCES.md` | API setup — Space-Track, Finnhub, Supabase, SEC |
| `docs/COMPONENTS.md` | Component inventory with data source mapping |
| `docs/TERMINAL.md` | Terminal layout and composition |

## Commands

```bash
# Dev server
cd short-gravity-web && npm run dev

# Production build
cd short-gravity-web && npm run build

# Filing worker
cd scripts/data-fetchers && export $(grep -v '^#' .env | xargs) && python3 filing_worker.py
```

## Git & Deployment

**CRITICAL: Never auto-commit or auto-push.** Only commit/push when Gabriel explicitly asks.

**Branches:**
- `development` — default working branch. All work happens here.
- `main` — production. Push to main auto-deploys to Vercel.

**Workflow:**
1. Work on `development` branch (always)
2. Gabriel says "commit" → commit to `development`
3. Gabriel says "push" or "deploy" → merge `development` → `main` and push
4. Never push to `main` without explicit instruction

```bash
# Dev workflow
git checkout development       # Always work here
npm run dev                    # Test locally

# When Gabriel says "commit"
git add <files> && git commit -m "description"

# When Gabriel says "deploy" or "push to prod"
git checkout main && git merge development && git push
git checkout development       # Back to dev
```

**DO NOT** use `vercel --prod` directly. Let GitHub handle deployments.
**DO NOT** commit or push unless explicitly told to.

## UI Design

**Source of truth:** `short-gravity-web/app/globals.css`

### Color Philosophy — Tactical HUD
- **White is the hero** — crisp on true black, let it pop
- **Orange is surgical** — selection/active states ONLY (5% of UI)
- No decorative color. No muddy grays.

### Key Variables
```css
--void-black: #030305;        /* Page background */
--asts-orange: #FF6B35;       /* Selection, active — USE SPARINGLY */
--text-primary: #FFFFFF;      /* Key data */
--text-secondary: #E5E7EB;    /* Secondary */
--text-muted: #71717A;        /* Timestamps */
```

### Typography
- **Everything:** JetBrains Mono, uppercase labels, tracking-wider
- **Large values:** font-light (300 weight)

### Rules
- Dark mode only
- Panel headers: white/gray, NOT orange
- Chart lines: white
- Selection: orange (the only pop of color)
- Hover: subtle white border increase

## Code Conventions
- Read before modifying
- Follow existing patterns exactly
- TypeScript strict mode
- No over-engineering
- No unnecessary comments

## Environment Variables

### Web App (`.env.local`)
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=
FINNHUB_API_KEY=
ALPHA_VANTAGE_API_KEY=
SPACE_TRACK_USERNAME=
SPACE_TRACK_PASSWORD=
```

### Python Workers (`scripts/data-fetchers/.env`)
```
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
ANTHROPIC_API_KEY=
```

## Key Integrations

| Source | Purpose | Rate Limits |
|--------|---------|-------------|
| Space-Track.org | Satellite TLE data | 30/min, 300/hr |
| Finnhub | Stock prices | 60/min |
| SEC EDGAR | Filings | None (public) |
| EPO OPS | Patents (global) | 20/min |
| Supabase | Database | PostgreSQL |

## Research Archive (RAG)

**4,000+ searchable records** for research and citations.

| Table | Count | Content |
|-------|-------|---------|
| `filings` (SEC) | 530 | Full document text (10-K, 8-K, S-1, etc.) |
| `fcc_filings` | 666 | Structured metadata + context |
| `patents` | 307 | Global patent portfolio (29 families, 7 jurisdictions) |
| `patent_claims` | 2,482 | Individual claim text with type (target: 3,800) |

### Quick Query (from scripts/data-fetchers)
```bash
export $(grep -v '^#' .env | xargs)

# Search SEC filings by keyword
curl -s -G -H "apikey: $SUPABASE_SERVICE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  "$SUPABASE_URL/rest/v1/filings" \
  --data-urlencode "select=form,filing_date,content_text" \
  --data-urlencode "content_text=ilike.*KEYWORD*" \
  --data-urlencode "order=filing_date.desc" \
  --data-urlencode "limit=5"

# Search FCC filings
curl -s -G -H "apikey: $SUPABASE_SERVICE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  "$SUPABASE_URL/rest/v1/fcc_filings" \
  --data-urlencode "select=file_number,title,application_status,filed_date" \
  --data-urlencode "content_text=ilike.*KEYWORD*" \
  --data-urlencode "order=filed_date.desc"

# Search patents by country
curl -s -G -H "apikey: $SUPABASE_SERVICE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  "$SUPABASE_URL/rest/v1/patents" \
  --data-urlencode "select=patent_number,title,status,source" \
  --data-urlencode "patent_number=like.EP*" \
  --data-urlencode "order=patent_number.asc"
```

Use `/research-filings` skill for comprehensive queries with citations.

## Behavior Rules

1. **Just do it** — If a follow-up action is obvious (run a worker, start a server, execute a migration), do it. Don't tell Gabriel to do it himself.
2. **Git: suggest, never act** — Never auto-commit or auto-push. But proactively suggest commits and deploys at the right moments:
   - **Suggest commit** when: a feature works end-to-end, a bug is fixed, before switching to a different task, after a batch of related changes, before risky refactors (save point)
   - **Suggest deploy** when: multiple commits are stacked on `development` and stable, a user-facing feature is complete and tested, a critical fix is ready
   - Keep it brief: "Good checkpoint — commit?" or "That's stable, deploy to prod?"
   - Gabriel says yes → do it. Gabriel says no or ignores → move on.
3. **Never rely on conversation history** — Context compaction loses data
4. **Historical completeness** — Fetch ALL data, never stop early
5. **When Gabriel provides credentials** → Write to `.env` immediately
6. **Error resilience** — Retry 3x with exponential backoff
7. **Before complex tasks** — Use `claude-code-guide` agent to check docs
8. **Follow official patterns** — When unsure how to implement something (skills, hooks, agents, workflows), check Claude Code docs via `claude-code-guide` agent BEFORE guessing. Use documented patterns, not improvisation.
9. **Always start the dev server** — When testing UI changes, start `npm run dev` in background automatically. Never ask Gabriel to do it.

## Content Workflows

Gabriel's typical patterns for content production:

### Research → Article → Visual
1. `/research-filings [topic]` — gather citations from RAG
2. `/write-article` — draft using research context
3. `/nano-banana` or `/gemini-generate` — create visual

### Quick X Post
1. Provide thesis or context
2. `/write-x-post single` or `/write-x-post thread`
3. `/nano-banana` for accompanying image if needed

### Research Only
- `/research-filings [question]` — returns citations, no content generation

### Skills Architecture
- Skills are atomic capabilities, not pipelines
- Chain skills conversationally: invoke one, use output, invoke next
- Skills cannot call other skills — orchestration happens in conversation

## Debugging Rules

**Isolate before fixing.** When debugging visual/3D/UI issues:
1. **Create or use an isolated test page** (e.g., `/bluebird-demo`, `/dev/3d`)
2. **Render the component alone** — no other elements, no complex scene
3. **Identify the root cause visually** before writing code
4. **Fix once** — don't iterate blindly in production

Test pages:
- `/dev/hud-v2` — **Current HUD** (clean architecture)
- `/dev/hud-experiment` — Legacy HUD (1000+ line monolith)
- `/bluebird-demo` — Satellite 3D model isolation
- `/dev/3d` — Three.js experiments
- `/dev/globe` — Globe isolation

## UI Placement Rules

**Check existing elements before placing new ones.** When adding UI controls:
1. **Read the component you're modifying** — identify existing positioned elements (legends, labels, controls)
2. **Check for overlaps** — new elements must not obscure existing content
3. **Respect the hierarchy** — controls should not compete with data display
4. **Test in context** — verify placement in both collapsed and expanded states

## CRITICAL: Real Data Only

**THIS IS NOT A TOY. NO APPROXIMATIONS.**

### Satellite Tracking
- **ALL satellite visualization MUST use TLE data propagated via satellite.js**
- Orbits: Propagate TLE over one orbital period, plot actual positions
- Positions: Use `satellite.propagate()` with real TLE lines
- Coverage: Calculate from actual altitude and antenna specs
- **NEVER use geometric approximations** (fake great circles, estimated inclinations)
- The TLE contains everything: inclination, RAAN, eccentricity, mean motion, epoch
- Use `satellite.twoline2satrec()` → `satellite.propagate()` → `satellite.eciToGeodetic()`

### Financial Data
- Stock prices from Finnhub/Alpha Vantage APIs only
- SEC filings from EDGAR only
- No mock data, no placeholders in production

## Bash Guidelines

```bash
# BAD: Causes buffering
git log | head -10

# GOOD: Use command flags
git log -n 10
```

Don't pipe through `head`, `tail`, `less`. Let commands complete.
