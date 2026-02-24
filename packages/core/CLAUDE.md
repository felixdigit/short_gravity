# MICROKERNEL: @shortgravity/core
You are isolated in `packages/core`.

YOUR LAWS OF PHYSICS:
1. PURE BUSINESS LOGIC: TypeScript domain logic only. No UI code, no React, no CSS.
2. IMPORT BANS: Do NOT import from `@shortgravity/ui` or `@shortgravity/database`. Core is self-contained domain logic.
3. EXPORTS: All public types and functions must be exported in `src/index.ts`.
4. NO SIDE EFFECTS: No database calls, no HTTP requests, no file I/O. Pure functions and type definitions only.
