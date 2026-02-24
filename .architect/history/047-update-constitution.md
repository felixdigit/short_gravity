TARGET: .architect
---

MISSION:
Update the NEXOD Constitution to reflect the actual state of the monorepo. The constitution is missing documentation for `apps/sync`, `packages/database`, and the infrastructure directories (`scripts/`, `.github/`). A constitution that doesn't match reality is entropy.

DIRECTIVES:

1. Read the current `NEXOD_CONSTITUTION.md` file.

2. Update Section 2 (THE THERMODYNAMICS OF CODE) to include ALL rooms. Replace the current room list with:
   ```markdown
   - **The Rooms (Workspaces):** Individual domains.
     - `packages/ui`: Pure visual primitives and math (WebGL, Tailwind). Amnesiac. No data fetching. No APIs. No imports from `@shortgravity/core` or `@shortgravity/database`.
     - `packages/core`: Pure data schemas, physics calculations, and processing logic. No UI code. No React. No API calls.
     - `packages/database`: Database schemas (Drizzle ORM) and client configuration. No UI code. No React. No business logic.
     - `apps/web`: The Application Router. Fetches data and acts as an Anti-Corruption Layer (ACL) to translate data for the UI. The ONLY package that may import from both `@shortgravity/ui` and `@shortgravity/database`. Responsible for all data fetching, API routes, and state management.
     - `apps/sync`: Background data synchronization workers. Consumes `@shortgravity/core` and `@shortgravity/database`. No UI code. No React.
   ```

3. Add a new Section 4 — THE UNGOVERNED TERRITORIES:
   ```markdown
   ## 4. THE UNGOVERNED TERRITORIES
   These directories exist outside the Microkernel system. They are infrastructure, not application code. Agents working in these directories receive no local CLAUDE.md constraints — they operate under mandate instructions only.

   - `scripts/data-fetchers/`: Python data collection workers. Invoked by GitHub Actions. Write to Supabase via REST API. Stdlib-only (no `requests`).
   - `.github/workflows/`: GitHub Actions YAML definitions. Schedule and invoke Python workers.
   - `.architect/`: The orchestration layer. Contains Lingot (`lingot.mjs`), the mandate queue, history, and the Architect's workbench.
   - `docs/`: Project documentation. Read-only reference material.
   - `_ARCHIVE_V1/`: The V1 application archive. Read-only. Source of truth for migration reference. Never modify.
   ```

4. Add a new Section 5 — THE IMPORT GRAPH (enforces the dependency direction):
   ```markdown
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
   ```

5. Verify the updated constitution is valid Markdown and reads coherently as a single document.
