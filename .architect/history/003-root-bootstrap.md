TARGET: .
---
MISSION:
Restore the monorepo root to a bootable state. The root package.json is a bare skeleton missing Turborepo, there is no turbo.json, no root tsconfig.json, and zombie processes may be squatting on port 3000. After this mandate, `pnpm install` succeeds, `turbo.json` exists, `tsc --noEmit` passes at the root, and the monorepo is ready for `pnpm dev`.

DIRECTIVES:

1. Kill any processes holding port 3000:
   ```
   lsof -ti :3000 | xargs kill -9 2>/dev/null || true
   ```

2. Overwrite the root `package.json` with the following exact content:
   ```json
   {
     "name": "short-gravity",
     "private": true,
     "packageManager": "pnpm@9.10.0",
     "scripts": {
       "dev": "turbo run dev",
       "build": "turbo run build",
       "typecheck": "turbo run typecheck",
       "lint": "turbo run lint"
     },
     "devDependencies": {
       "turbo": "^2.8.0",
       "typescript": "^5.0.0"
     }
   }
   ```

3. Create `turbo.json` at the monorepo root with the following exact content:
   ```json
   {
     "$schema": "https://turbo.build/schema.json",
     "tasks": {
       "build": {
         "dependsOn": ["^build"],
         "outputs": [".next/**", "dist/**"]
       },
       "dev": {
         "cache": false,
         "persistent": true
       },
       "lint": {},
       "typecheck": {
         "dependsOn": ["^build"]
       }
     }
   }
   ```

4. Create `tsconfig.json` at the monorepo root with the following exact content:
   ```json
   {
     "compilerOptions": {
       "target": "ES2022",
       "module": "ESNext",
       "moduleResolution": "bundler",
       "strict": true,
       "skipLibCheck": true,
       "noEmit": true,
       "esModuleInterop": true,
       "isolatedModules": true,
       "resolveJsonModule": true
     },
     "files": [],
     "references": [
       { "path": "apps/web" },
       { "path": "packages/ui" },
       { "path": "packages/core" },
       { "path": "packages/database" }
     ]
   }
   ```
   IMPORTANT: `"files": []` is deliberate. The root has no source files. This ensures `tsc --noEmit` exits 0 at the root (the Lingot Circuit Breaker depends on this). The `references` are for documentation and future `tsc -b` support.

5. Run a clean install from the monorepo root:
   ```
   pnpm install
   ```
   Verify it exits 0 and all workspace packages link correctly.

6. Verify the install is sound (non-persistent — must exit cleanly):
   ```
   pnpm ls --depth 0
   ```
   Confirm `turbo` and `typescript` appear in root devDependencies, and that workspace packages (`@shortgravity/web`, `@shortgravity/ui`, `@shortgravity/core`, `@shortgravity/database`) are linked. Do NOT run `pnpm dev` or any persistent/long-running process — the human will verify the dev server manually.

CONTEXT FOR THE AGENT:
- pnpm 9.10.0, Node 22.8.0, turbo 2.8.10 (global) are available.
- `pnpm-workspace.yaml` already exists and is correct: `packages/*` + `apps/*`.
- Four workspace packages exist: `@shortgravity/web`, `@shortgravity/ui`, `@shortgravity/core`, `@shortgravity/database`.
- `apps/sync` is a placeholder with no package.json — ignore it.
- Do NOT delete `pnpm-lock.yaml`. Let pnpm update it naturally.
- The Lingot Circuit Breaker runs `tsc --noEmit` at the TARGET directory after the agent finishes. Step 4 exists specifically to satisfy this check. Do NOT remove or modify the `"files": []` field.
