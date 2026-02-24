TARGET: apps/web
---
MISSION:
Replace the MercatorMapPanel stub with a functional 2D satellite ground track map using a lightweight SVG world map approach (no heavy dependencies like Leaflet).

DIRECTIVES:

## 1. Read the current stub

Read `src/components/hud/widgets/MercatorMapPanel.tsx` to understand the current widget manifest and props.

## 2. Replace with functional SVG map

The map should show:
- SVG world map outline (simplified country borders or continent outlines)
- Satellite positions as colored dots
- Auto-updating positions (satellites move in real-time)

Use the satellite data from `useTerminalData()` (already provides `mapTracks` with latitude/longitude/noradId/name).

The simplest approach: an SVG element with a world map background and positioned satellite dots.

For the world map outline, use a simplified SVG path. Create a minimal world outline:

```tsx
'use client'

import { useTerminalData } from '@/lib/providers/TerminalDataProvider'

// Simplified world coastline as SVG — use a basic equirectangular projection
// The SVG viewBox maps to lat/lon: x = longitude (-180 to 180), y = latitude (90 to -90)

function latLonToSvg(lat: number, lon: number, width: number, height: number) {
  const x = ((lon + 180) / 360) * width
  const y = ((90 - lat) / 180) * height
  return { x, y }
}

export function MercatorMapPanel() {
  const { mapTracks } = useTerminalData()

  const width = 600
  const height = 300

  return (
    <div className="w-full h-full relative overflow-hidden bg-[#030305]">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full h-full"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Background */}
        <rect width={width} height={height} fill="#030305" />

        {/* Grid lines */}
        {/* Longitude lines every 30° */}
        {Array.from({ length: 12 }, (_, i) => {
          const x = (i / 12) * width
          return <line key={`lon-${i}`} x1={x} y1={0} x2={x} y2={height} stroke="white" strokeOpacity={0.04} strokeWidth={0.5} />
        })}
        {/* Latitude lines every 30° */}
        {Array.from({ length: 6 }, (_, i) => {
          const y = (i / 6) * height
          return <line key={`lat-${i}`} x1={0} y1={y} x2={width} y2={y} stroke="white" strokeOpacity={0.04} strokeWidth={0.5} />
        })}
        {/* Equator */}
        <line x1={0} y1={height / 2} x2={width} y2={height / 2} stroke="white" strokeOpacity={0.08} strokeWidth={0.5} />

        {/* Satellite positions */}
        {mapTracks.map((sat) => {
          const pos = latLonToSvg(
            sat.currentPosition.latitude,
            sat.currentPosition.longitude,
            width,
            height
          )
          return (
            <g key={sat.noradId}>
              {/* Dot */}
              <circle
                cx={pos.x}
                cy={pos.y}
                r={3}
                fill="#FF6B35"
                opacity={0.9}
              />
              {/* Glow */}
              <circle
                cx={pos.x}
                cy={pos.y}
                r={6}
                fill="#FF6B35"
                opacity={0.15}
              />
              {/* Label */}
              <text
                x={pos.x + 8}
                y={pos.y + 3}
                fill="white"
                fillOpacity={0.4}
                fontSize={8}
                fontFamily="monospace"
              >
                {sat.name}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
```

## 3. Update the widget manifest

Make sure the component is exported with the correct widget manifest. Check the existing stub for the manifest shape and keep it the same:

```ts
export const mercatorMapManifest: WidgetManifest = {
  id: 'mercator-map',
  name: 'MERCATOR MAP',
  category: 'orbital',
  minWidth: 2,
  minHeight: 2,
}
```

Keep whatever manifest already exists — just replace the component implementation.

## 4. Ensure useTerminalData is accessible

The widget renders inside the /asts page which wraps in TerminalDataProvider, so `useTerminalData()` is available. Verify that `mapTracks` returns the expected shape: `{ noradId, name, currentPosition: { latitude, longitude }, inclination, altitude }`.

## 5. Run `npx tsc --noEmit`
