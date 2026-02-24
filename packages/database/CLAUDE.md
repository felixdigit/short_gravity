# MICROKERNEL: @shortgravity/database
You are isolated in `packages/database`.

YOUR LAWS OF PHYSICS:
1. LEAF NODE: This package is a dependency leaf. Do NOT import from any other `@shortgravity/*` package (`@shortgravity/core`, `@shortgravity/ui`, etc.).
2. DB ONLY: You ONLY write database schemas, types, and Supabase client exports. No UI. No React.
3. EXPORTS: All public types and clients must be exported in `src/index.ts`.
