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
- **Database:** Supabase (PostgreSQL + pgvector)
- **Automation:** GitHub Actions (all workers run on cron schedules)
- **Deploy:** Vercel (auto-deploy on push to `main`)

## Directory Structure

```
short_gravity/
├── short-gravity-web/           # Next.js app (Vercel)
│   ├── app/                     # Pages + API routes
│   ├── components/              # UI components
│   ├── lib/                     # Hooks, stores, brain search
│   ├── scripts/data-fetchers/   # Workers deployed via GitHub Actions
│   └── .github/workflows/       # Cron schedules for all workers
├── scripts/data-fetchers/       # Local worker dev copies
├── .claude/rules/               # Auto-loaded context (architecture, workers, database)
├── docs/                        # Documentation + system-map.html
├── design/                      # Style guide, Figma specs
└── research/                    # Alpha nuggets, notes
```

## Commands

```bash
cd short-gravity-web && npm run dev      # Dev server
cd short-gravity-web && npm run build    # Production build
```

## Git & Deployment

**CRITICAL: Never auto-commit or auto-push.** Only commit/push when Gabriel explicitly asks.

- `main` — production. Push to main auto-deploys to Vercel.
- Work directly on `main` unless Gabriel specifies otherwise.

**DO NOT** use `vercel --prod` directly. Let GitHub handle deployments.
**DO NOT** commit or push unless explicitly told to.

## UI Design

**Source of truth:** `short-gravity-web/app/globals.css`

### Color Philosophy — Tactical HUD
- **White is the hero** — crisp on true black
- **Orange is surgical** — selection/active states ONLY (5% of UI)
- No decorative color. No muddy grays.

```css
--void-black: #030305;        /* Page background */
--asts-orange: #FF6B35;       /* Selection, active — USE SPARINGLY */
--text-primary: #FFFFFF;      /* Key data */
--text-secondary: #E5E7EB;    /* Secondary */
--text-muted: #71717A;        /* Timestamps */
```

### Typography
- JetBrains Mono, uppercase labels, tracking-wider
- Large values: font-light (300 weight)

### Rules
- Dark mode only. Panel headers: white/gray, NOT orange.
- Chart lines: white. Selection: orange (only pop of color).

## Code Conventions
- Read before modifying. Follow existing patterns exactly.
- TypeScript strict mode. No over-engineering. No unnecessary comments.

## Behavior Rules

1. **Just do it** — If a follow-up action is obvious, do it.
2. **Git: suggest, never act** — Never auto-commit/push. Suggest commits at good checkpoints.
3. **Historical completeness** — Fetch ALL data, never stop early.
4. **When Gabriel provides credentials** → Write to `.env` immediately.
5. **Error resilience** — Retry 3x with exponential backoff.
6. **Before complex tasks** — Use `claude-code-guide` agent to check docs.
7. **Always start the dev server** — When testing UI changes, start `npm run dev` in background.
8. **Automation = GitHub Actions** — Every worker must have a GitHub Actions workflow. `run_all.py` is a local convenience only, NOT the automation layer. A worker without a GH Actions workflow is not deployed.
9. **Worker deployment** — Workers run from `short-gravity-web/scripts/data-fetchers/`. When creating/modifying a worker, update BOTH copies (parent repo + web app repo) and ensure the GH Actions workflow exists.

## Content Workflows

- `/research-filings [topic]` — citations from RAG
- `/write-article` — draft using research
- `/write-x-post single` or `/write-x-post thread` — X content
- `/nano-banana` — visual generation

Skills are atomic — chain them conversationally.

## Debugging Rules

**Isolate before fixing.** Use test pages:
- `/dev/hud-v2` — Current HUD (clean architecture)
- `/bluebird-demo` — Satellite 3D model isolation
- `/dev/3d` — Three.js experiments
- `/dev/globe` — Globe isolation

## CRITICAL: Real Data Only

- **ALL satellite visualization MUST use TLE data propagated via satellite.js**
- Use `satellite.twoline2satrec()` → `satellite.propagate()` → `satellite.eciToGeodetic()`
- **NEVER use geometric approximations**
- Stock prices from Finnhub/Alpha Vantage only. SEC filings from EDGAR only.
- No mock data, no placeholders in production.

## UI Placement Rules

Before placing new UI elements: read the component, check for overlaps, test in context.

## Bash Guidelines

Don't pipe through `head`, `tail`, `less`. Use command flags (`git log -n 10`).
