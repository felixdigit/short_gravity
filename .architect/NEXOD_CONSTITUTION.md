# NEXOD / LINGOT: THE EPISTEMIC MONOREPO CONSTITUTION

## 1. THE GLOBAL MISSION
We are building Lingot: an autonomous orchestration layer for AI software development. The goal is to eliminate "context bleed." Instead of passing a massive global context to an LLM, Lingot physically traps AI agents inside specific, constrained directories (Micro-Environments) and forces them to perform isolated work.

## 2. THE THERMODYNAMICS OF CODE
Codebases heat up and decay when agents are given too much context. To prevent this, we enforce strict physical boundaries:
- **The Cathedral (The Monorepo):** The overarching structure (`apps/`, `packages/`).
- **The Rooms (Workspaces):** Individual domains.
  - `packages/ui`: Pure visual primitives and math (WebGL, Tailwind). Amnesiac. No data fetching. No APIs. No imports from `@shortgravity/core` or `@shortgravity/database`.
  - `packages/core`: Pure data schemas, physics calculations, and processing logic. No UI code. No React. No API calls.
  - `packages/database`: Database schemas (Drizzle ORM) and client configuration. No UI code. No React. No business logic.
  - `apps/web`: The Application Router. Fetches data and acts as an Anti-Corruption Layer (ACL) to translate data for the UI. The ONLY package that may import from both `@shortgravity/ui` and `@shortgravity/database`. Responsible for all data fetching, API routes, and state management.
  - `apps/sync`: Background data synchronization workers. Consumes `@shortgravity/core` and `@shortgravity/database`. No UI code. No React.
- **The Local Physics (Microkernels):** Each room contains a `CLAUDE.md` file dictating what an agent can and cannot do inside that specific folder.

## 3. MAXWELL'S DEMON (The Orchestrator)
A Node.js script (`.architect/lingot.mjs`) reads Work Orders (Mandates) from a queue. It autonomously spawns a local AI CLI (like Claude Code) inside a target room, completely locking its context to that directory.
- **YOLO Mode:** The agent runs headlessly. It does not ask for permission to write files or install dependencies.
- **The Circuit Breaker:** After the agent works, Lingot runs the TypeScript compiler natively in the room (`tsc --noEmit`). If it passes, the mandate is archived. If it fails, the assembly line halts. No human intervention.

## 4. THE UNGOVERNED TERRITORIES
These directories exist outside the Microkernel system. They are infrastructure, not application code. Agents working in these directories receive no local CLAUDE.md constraints — they operate under mandate instructions only.

- `scripts/data-fetchers/`: Python data collection workers. Invoked by GitHub Actions. Write to Supabase via REST API. Stdlib-only (no `requests`).
- `.github/workflows/`: GitHub Actions YAML definitions. Schedule and invoke Python workers.
- `.architect/`: The orchestration layer. Contains Lingot (`lingot.mjs`), the mandate queue, history, and the Architect's workbench.
- `docs/`: Project documentation. Read-only reference material.
- `_ARCHIVE_V1/`: The V1 application archive. Read-only. Source of truth for migration reference. Never modify.

## 5. THE IMPORT GRAPH
Dependencies flow in ONE direction. Violations are structural compromise.

```
packages/ui ←── apps/web ──→ packages/database
                    │
                    ↓
               packages/core
```

**Allowed imports:**
- `apps/web` → `@shortgravity/ui`, `@shortgravity/core`, `@shortgravity/database`
- `apps/sync` → `@shortgravity/core`, `@shortgravity/database`

**Forbidden imports:**
- `packages/ui` → `@shortgravity/core` (UI must not know about data domains)
- `packages/ui` → `@shortgravity/database` (UI must never touch the database)
- `packages/core` → `@shortgravity/ui` (Logic must not know about presentation)
- `packages/core` → `@shortgravity/database` (Logic operates on pure data, not DB clients)
- `packages/database` → anything else (Database is a leaf node)
