TARGET: apps/web
---

MISSION:
Fix the constitutional boundary violation where `packages/ui` imports from `@shortgravity/core`. The constitution mandates that `packages/ui` is "pure visual primitives and math — amnesiac, no data fetching, no APIs." The ACL translation layer is `apps/web`. Move the orbital computation out of the UI package and into the web ACL layer.

DIRECTIVES:

1. Read `../../packages/ui/src/components/earth/Globe3D.tsx`. Find the import:
   ```typescript
   import { getCoverageRadiusKm, propagateOrbitPath } from '@shortgravity/core'
   ```
   Identify exactly where these functions are called and what data they consume/produce.

2. Read `../../packages/core/src/satellite-coverage.ts` and `../../packages/core/src/orbital.ts` to understand the function signatures:
   - `getCoverageRadiusKm(altitudeKm: number): number` — pure math (geometry)
   - `propagateOrbitPath(tle, startTime, points): {lat, lng, alt}[]` — TLE propagation

3. The fix: Move the computation into `apps/web`'s ACL layer. Modify `src/components/dashboard/GlobeWidget.tsx` to:
   a. Import `getCoverageRadiusKm` and `propagateOrbitPath` from `@shortgravity/core` (web CAN import from core — it's the ACL)
   b. Pre-compute coverage radii and orbit paths for each satellite
   c. Pass the pre-computed data as props to `Globe3D`

4. Modify the `Globe3D` component props interface (in `packages/ui`) to accept pre-computed data instead of computing it internally:
   - Add `coverageRadii?: Record<string, number>` prop (noradId → radius in km)
   - Add `orbitPaths?: Record<string, {lat: number, lng: number, alt: number}[]>` prop
   - Remove the `@shortgravity/core` import entirely

5. Update `Globe3D.tsx` to use the pre-computed props instead of calling core functions directly. Where it currently calls `getCoverageRadiusKm(satellite.altitude)`, use `coverageRadii?.[satellite.noradId]` with a fallback. Where it calls `propagateOrbitPath(...)`, use `orbitPaths?.[satellite.noradId]`.

6. Verify the `@shortgravity/core` dependency is removed from `packages/ui/package.json`. If `@shortgravity/core` is listed in dependencies, remove it. Run `cd ../.. && pnpm install` to update the lockfile.

7. Run `pnpm typecheck` in BOTH `packages/ui/` and `apps/web/` to verify zero type errors in both rooms.

8. Verify no other file in `packages/ui/src/` imports from `@shortgravity/core`. Run a search for `@shortgravity/core` across all files in `packages/ui/src/`. There should be ZERO matches after this fix.
