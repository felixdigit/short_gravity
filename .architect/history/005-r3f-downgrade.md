TARGET: packages/ui
---
MISSION:
Fix the R3F runtime crash caused by a React version mismatch. `@react-three/fiber@9.5.0` bundles the React 19 reconciler, but this monorepo runs React 18. Downgrade R3F to the last v8 release, which is built for React 18. After this mandate, the Globe component initializes without a reconciler crash.

DIRECTIVES:

1. In `package.json`, change the `@react-three/fiber` dependency from `^9.5.0` to `^8.17.10`. Do NOT change `three` — version `^0.183.1` is compatible with R3F 8. Do NOT change `@types/three`.

2. In `package.json`, verify that `react` and `react-dom` peer dependencies are still `^18.2.0`. Do not change them.

3. Run `pnpm install` from the monorepo root to re-resolve the dependency tree:
   ```
   cd ../.. && pnpm install
   ```
   Verify it exits 0 with no peer dependency errors related to React or R3F.

4. Run `tsc --noEmit` from `packages/ui` to verify the Globe component still type-checks with R3F 8's API surface:
   ```
   pnpm typecheck
   ```
   The component uses `Canvas`, `useFrame`, and `Mesh` type — all stable across R3F 8.x. If there are type errors in Globe.tsx, fix them. Do NOT fix type errors in other files — only Globe.tsx is in scope.

CONTEXT FOR THE AGENT:
- You are isolated in `packages/ui`. Do NOT modify files outside this directory.
- The crash was: `TypeError: Cannot read properties of undefined (reading 'S')` — R3F 9's bundled reconciler reads `React.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE`, which is a React 19 internal. React 18 does not export it.
- The V1 archive used `@react-three/fiber@8.15.12` with React 18 — this pairing is known to work.
- `Globe.tsx` uses only basic R3F APIs: `Canvas`, `useFrame`, `useRef<Mesh>`, `sphereGeometry`, `meshBasicMaterial`. All of these exist in R3F 8.x.
- Do NOT run `pnpm dev` or any persistent process.
