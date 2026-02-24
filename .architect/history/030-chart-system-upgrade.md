TARGET: apps/web
---
MISSION:
Upgrade the three stub/basic chart components: DragChart (sparkline → interactive), SGChart (basic polyline → multi-series), and FocusPanel (inline → expandable modal).

DIRECTIVES:

## 1. Upgrade DragChart

Read `src/components/hud/widgets/DragChart.tsx` to understand current implementation.

The current DragChart renders a basic SVG sparkline of B* values. Upgrade it to show:
- SVG chart with proper axes (time on X, B* on Y)
- Axis labels (dates on bottom, B* values on left)
- Data points as small circles
- Hover/tooltip showing exact values
- Chart line in orange (#FF6B35)
- Optional secondary Y-axis for altitude if data available

Key approach: Use pure SVG (no chart library). The chart receives data points with `{ epoch: string, bstar: number, avgAltitude?: number }`.

```tsx
// Simplified interactive chart structure:
// 1. Calculate min/max for axes
// 2. Map data points to SVG coordinates
// 3. Draw path + circles
// 4. Add hover interaction with useState for active point
// 5. Show value tooltip near active point
```

Keep the component self-contained. The data comes in as props (dataPoints array from the parent widget). Don't add external chart dependencies.

Add:
- X-axis labels (dates, every N points to avoid overlap)
- Y-axis labels (B* values in exponential notation)
- Hover state: when user hovers a data point, show a tooltip with exact epoch + B* + altitude
- Responsive: chart fills its container

## 2. Upgrade SGChart

Read `src/lib/charts/index.tsx` to understand the current stub.

The current SGChart renders a basic polyline for the first series. Upgrade to support:
- Multiple series (each with its own color and label)
- Proper axes with labels
- Legend showing series names + colors
- Hover interaction showing values for all series at the hovered X position
- Grid lines for readability

Keep it SVG-based, no external dependencies. The chart API should be:

```tsx
interface SGChartProps {
  series: Array<{
    name: string
    data: Array<{ x: number | string; y: number }>
    color: string
  }>
  xLabel?: string
  yLabel?: string
  height?: number
}
```

## 3. Upgrade FocusPanel

Read `src/components/ui/FocusPanel.tsx` to understand the current stub.

The current FocusPanel renders children inline with no expand/collapse. Upgrade to:
- Collapsed state: shows a compact summary (children rendered normally)
- Expand button: small "EXPAND" text button in the corner
- Expanded state: renders as a larger overlay/modal with more room
- Close button to collapse back
- Optional: animate transition if framer-motion is available, otherwise use CSS transition

```tsx
interface FocusPanelProps {
  children: React.ReactNode
  title?: string
  expandable?: boolean
}
```

When expanded:
- Render a semi-transparent backdrop
- Show children in a larger centered panel
- Close on Escape key or clicking backdrop
- Close button in top-right

When collapsed (default):
- Render children normally
- Show small expand icon/button

If framer-motion is available (check package.json), use it for smooth transitions. Otherwise, use CSS opacity/transform transitions.

## 4. Run `npx tsc --noEmit`
