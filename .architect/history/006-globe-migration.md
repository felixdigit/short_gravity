TARGET: .
---
MISSION:
Migrate the full Globe3D visual system from the V1 archive into the NEXOD monorepo, respecting strict room boundaries. Pure math goes to `packages/core`. Visual/WebGL code goes to `packages/ui`. The ACL layer in `apps/web` wires data to the Globe. After this mandate, `turbo run typecheck` passes across all workspaces and the Globe3D component is importable.

DIRECTIVES:

## PHASE 1: Core Math Layer (packages/core)

1. Create `packages/core/src/satellite-coverage.ts` by copying `_ARCHIVE_V1/short-gravity-web/lib/satellite-coverage.ts` EXACTLY as-is. This file has zero external dependencies — pure math only.

2. Create `packages/core/src/orbital.ts` with the `propagateOrbitPath` function extracted from `_ARCHIVE_V1/short-gravity-web/components/earth/Globe3D.tsx` (lines 63-108). This function takes two TLE strings and returns `{lat, lon, alt}[]`. Copy it exactly, including the `satellite.js` import it requires.

3. Add `satellite.js` to `packages/core/package.json` dependencies:
   ```
   "satellite.js": "^5.0.0"
   ```
   Check the version used in `_ARCHIVE_V1/short-gravity-web/package.json` and match it.

4. Export the new modules from `packages/core/src/index.ts`. Add:
   ```ts
   export { getCoverageRadiusKm, calculateCoverageGeometry, formatSurfaceArea, getASTSCoverageGeometry, calculateCoverageRings } from './satellite-coverage'
   export type { CoverageParams, CoverageGeometry } from './satellite-coverage'
   export { propagateOrbitPath } from './orbital'
   ```

## PHASE 2: Visual Layer (packages/ui)

5. Create the directory structure:
   ```
   packages/ui/src/components/earth/
   packages/ui/src/components/earth/satellite/
   packages/ui/src/components/earth/shaders/
   packages/ui/src/lib/
   ```

6. Copy the following files from the V1 archive to packages/ui. Use `cp` for exact copies:
   ```
   _ARCHIVE_V1/short-gravity-web/components/earth/landmass-data.ts       → packages/ui/src/components/earth/landmass-data.ts
   _ARCHIVE_V1/short-gravity-web/components/earth/landmass-points.json   → packages/ui/src/components/earth/landmass-points.json
   _ARCHIVE_V1/short-gravity-web/components/earth/satellite-colors.ts    → packages/ui/src/components/earth/satellite-colors.ts
   _ARCHIVE_V1/short-gravity-web/components/earth/satellite/config.ts    → packages/ui/src/components/earth/satellite/config.ts
   _ARCHIVE_V1/short-gravity-web/components/earth/shaders/cellVisibility.ts → packages/ui/src/components/earth/shaders/cellVisibility.ts
   _ARCHIVE_V1/short-gravity-web/components/earth/CellGrid.tsx           → packages/ui/src/components/earth/CellGrid.tsx
   _ARCHIVE_V1/short-gravity-web/components/earth/Globe3D.tsx            → packages/ui/src/components/earth/Globe3D.tsx
   _ARCHIVE_V1/short-gravity-web/lib/hexasphere-grid.ts                  → packages/ui/src/lib/hexasphere-grid.ts
   ```

7. CRITICAL — Rewrite imports in the copied files:

   **Globe3D.tsx** — make these exact changes:
   - REMOVE `import * as satellite from 'satellite.js'` (no longer needed here)
   - REMOVE the entire `propagateOrbitPath` function definition (lines 63-108 of the original)
   - CHANGE `import { getCoverageRadiusKm } from '@/lib/satellite-coverage'` → `import { getCoverageRadiusKm, propagateOrbitPath } from '@shortgravity/core'`
   - All other imports (`./landmass-data`, `./satellite-colors`, `./satellite/config`, `./CellGrid`) stay as-is — they are now local within packages/ui

   **CellGrid.tsx** — make this exact change:
   - CHANGE `import { ... } from '@/lib/hexasphere-grid'` → `import { ... } from '../../lib/hexasphere-grid'`

   **hexasphere-grid.ts** — no import changes needed (it only imports `three` and `hexasphere.js`)

   **All other copied files** — no import changes needed. Verify no `@/` path aliases exist in any of them. If they do, resolve them to relative paths or `@shortgravity/core` imports as appropriate.

8. Add dependencies to `packages/ui/package.json`:
   ```
   "@react-three/drei": "^9.120.0"      (dependencies — check V1 package.json for exact version range)
   "hexasphere.js": "^0.1.0"            (dependencies — check V1 package.json for exact version range)
   "@shortgravity/core": "workspace:*"  (dependencies)
   ```
   Match the version ranges from `_ARCHIVE_V1/short-gravity-web/package.json`. Do NOT guess versions — read the V1 package.json.

9. Update `packages/ui/src/index.ts` — update the Globe comment and add the Globe3D export:
   - Change the bottom comment about Globe to reference Globe3D
   - Add: `export { Globe3D } from './components/earth/Globe3D'`
   - Add: `export type { SatelliteData } from './components/earth/Globe3D'`
   - Keep or remove the old `Globe` component at your discretion — Globe3D replaces it

## PHASE 3: Application Layer (apps/web)

10. Update `apps/web/src/components/dashboard/GlobeWidget.tsx`:
    - Replace the import of `Globe` with `Globe3D` from `@shortgravity/ui`
    - The dynamic import should now point to `@shortgravity/ui/components/earth/Globe3D`
    - Update the component usage: `Globe3D` takes `satellites` (array of `SatelliteData`) instead of `signals`
    - For now, if the real satellite hook doesn't exist, render `Globe3D` with no props (empty globe) so it at least mounts
    - The old `GlobeSignal` type is no longer needed

## PHASE 4: Install & Verify

11. Run `pnpm install` from the monorepo root. Verify exit 0.

12. Run `turbo run typecheck` from the monorepo root. Capture full output.
    - If there are type errors in the files you just created/modified, FIX THEM.
    - If there are type errors in files you did NOT touch, IGNORE THEM and note them in your output.
    - Common issues to watch for: `@react-three/drei` types needing `@types/three` alignment, `hexasphere.js` having no types (use `@ts-expect-error`), path alias resolution.

13. Do NOT run `pnpm dev` or any persistent process.

CONTEXT FOR THE AGENT:
- The V1 archive is at `_ARCHIVE_V1/short-gravity-web/`. All source files are in `components/` and `lib/` (no `src/` prefix in V1).
- `packages/ui` already has `three@^0.183.1` and `@react-three/fiber@^8.17.10` as dependencies.
- `packages/ui` already has `@types/three` in devDependencies.
- `packages/core` already depends on `@shortgravity/database` (workspace:*) and `zod`.
- The `landmass-points.json` file is 356KB single-line JSON. Use `cp`, do not try to read/rewrite it.
- `hexasphere.js` has no TypeScript definitions. Use `@ts-expect-error` on its import.
- The root Circuit Breaker uses `files: []` so it passes trivially. Quality gate is `turbo run typecheck` in step 12.
- `@react-three/drei` version must be compatible with `@react-three/fiber@^8.17.10` (R3F v8, NOT v9). Use the drei version from the V1 archive.
- Globe3D.tsx has `'use client'` directive at the top — preserve it.
- Do NOT modify any files not listed in these directives.
