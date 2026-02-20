# Extraction Report — `@shortgravity/ui`

**23 files** written. **0 Next.js/Supabase/fetch references.** TypeScript compiles with zero errors.

## Foundation

| File | What |
|------|------|
| `src/lib/utils.ts` | `cn()` — clsx + tailwind-merge |
| `src/types.ts` | `SignalSeverity`, `Signal`, `WidgetManifest` |
| `tsconfig.json` | TypeScript config (ESNext, bundler resolution) |

## Layer 1 — Primitives (`src/components/primitives/`)

| Component | Props | Notes |
|-----------|-------|-------|
| `Panel` | `blur`, `border`, `className` | Compound: `.Header`, `.Content`, `.Divider`, `.Section` |
| `Text` | `variant` (7), `size` (8), `mono`, `uppercase`, `tracking`, `tabular`, `as` | + convenience: `Label`, `Value`, `Muted` |
| `Stat` | `value`, `label`, `sublabel`, `delta`, `variant` (5), `size` (4) | Hero numbers with directional deltas |
| `StatusDot` | `variant` (5), `size` (3), `pulse` | Animated status indicator |
| `LoadingState` | `text`, `size` (3) | + `Skeleton` for placeholder blocks |
| `ProgressBar` | `value`, `max`, `variant` (4), `size`, `showLabel` | Gradient fill bar |

## Chart Primitives (`src/components/primitives/chart/`)

| Component | Use |
|-----------|-----|
| `Crosshair` | SVG crosshair reticle |
| `HairlinePath` | Thin SVG data line |
| `ValueReadout` | SVG text readout |
| `CornerBrackets` | SVG corner decoration |
| `Baseline` | SVG reference line |
| `GhostTrend` | SVG dashed trend line |

## Layer 2 — UI Components (`src/components/ui/`)

| Component | Notes |
|-----------|-------|
| `Badge` | Severity-colored pill (critical/high/medium/low) |
| `Card` / `CardHeader` / `CardTitle` / `CardContent` | Standard card layout |
| `ErrorBoundary` | Class component with retry button |
| `FocusPanelProvider` / `useFocusPanelContext` | Focus management context |
| `WidgetHost` | Widget wrapper with ErrorBoundary + sizing logic |

## Layout & Brand

| Component | Notes |
|-----------|-------|
| `HUDLayout` | Full HUD shell — 11 compound slots (Canvas, TopLeft, TopRight, LeftPanel, RightPanel, BottomLeft, BottomRight, BottomCenter, Center, Overlay, Attribution) + `useHUDLayout` hook |
| `LogoMark` | Pure SVG planet-orbit-satellite icon |

## Domain — Signals

| Component | Notes |
|-----------|-------|
| `SignalCard` | Intelligence signal card — severity dots, category labels, price impact, time-ago. Pure props, zero data fetching |

## Surgical Scrub Checklist

- [x] `next/link` — **removed** (0 references)
- [x] `next/navigation` / `useRouter` / `usePathname` — **removed** (0 references)
- [x] `useSWR` / `@tanstack/react-query` — **removed** (0 references)
- [x] `fetch()` calls — **removed** (0 references)
- [x] Supabase — **removed** (0 references)
- [x] `@/lib/utils` alias — **replaced** with relative imports
- [x] `@/types` — **replaced** with local `types.ts`
- [x] Custom CSS variables (`alert-critical`, `nebula-depth`) — **replaced** with standard Tailwind colors

## Not Extracted (by design)

- **FocusPanel** — depends on `framer-motion` + `html-to-image` + portal rendering (heavy, app-layer concern)
- **All data-fetching widgets** (TelemetryFeed, ShortInterest, CashPosition, etc.) — coupled to React Query + Zustand stores
- **Sidebar** — coupled to `next/link` + `usePathname` routing
- **SatelliteInfoCard** — coupled to `useRouter`
