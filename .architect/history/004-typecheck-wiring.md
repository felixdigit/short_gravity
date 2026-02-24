TARGET: .
---
MISSION:
Wire up `turbo run typecheck` across all workspaces. Every workspace needs a `typecheck` script, and workspaces missing `typescript` as a devDependency need it added. After this mandate, `turbo run typecheck` is runnable from the root. Type errors in application code are expected and NOT your problem — report them but do not fix them.

DIRECTIVES:

1. Add a `typecheck` script to `apps/web/package.json` inside the existing `scripts` block:
   ```
   "typecheck": "tsc --noEmit"
   ```

2. Add a `scripts` block with a `typecheck` script to `packages/ui/package.json`:
   ```
   "scripts": {
     "typecheck": "tsc --noEmit"
   }
   ```

3. Add a `scripts` block with a `typecheck` script to `packages/core/package.json`, AND add `typescript` to its `devDependencies` (it is currently missing):
   ```
   "scripts": {
     "typecheck": "tsc --noEmit"
   }
   ```
   ```
   "devDependencies": {
     "@types/node": "^20.0.0",
     "typescript": "^5.0.0"
   }
   ```

4. Add a `scripts` block with a `typecheck` script to `packages/database/package.json`, AND add a `devDependencies` block with `typescript` (it currently has no devDependencies at all):
   ```
   "scripts": {
     "typecheck": "tsc --noEmit"
   }
   ```
   ```
   "devDependencies": {
     "typescript": "^5.0.0"
   }
   ```

5. Run `pnpm install` from the monorepo root to link the newly declared dependencies.

6. Run `turbo run typecheck` from the monorepo root. Capture the full output. Type errors in workspace source files are EXPECTED at this stage — they are NOT failures of this mandate. Your job is only to verify the command is runnable (tsc is found in every workspace and executes). If any workspace fails because `tsc` is not found, THAT is a real failure — fix it. If workspaces fail with TS compilation errors, simply note them and move on.

CONTEXT FOR THE AGENT:
- Root `turbo.json` already defines a `typecheck` task with `"dependsOn": ["^build"]`.
- `apps/web` already has a `scripts` block — ADD to it, do not replace it.
- `packages/ui` already has `typescript` in devDependencies — do not duplicate it.
- `packages/core` already has a `devDependencies` block with `@types/node` — ADD typescript to it, do not replace the block.
- `packages/database` has NO `devDependencies` block — create one.
- Do NOT modify any `.ts` or `.tsx` source files. Do NOT fix type errors. This mandate is purely structural wiring.
- Do NOT run `pnpm dev` or any persistent process.
