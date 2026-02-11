---
paths:
  - "short-gravity-web/**/*.ts"
  - "short-gravity-web/**/*.tsx"
---

# TypeScript Rules

- Strict mode, no `any` unless absolutely necessary
- Explicit return types on exported functions
- Interface over type for object shapes
- Types in `types/index.ts` for shared definitions
- Use `cn()` from `@/lib/utils/cn` for conditional classes
