# Components

All React components and their data source dependencies.

---

## Architecture

```
Terminal Page (Immersive Layout)
    │
    ├── ClientGlobe3D ────────── Space-Track API (TLE → satellite.js)
    │   ├── Globe3D
    │   ├── CellGrid (coverage)
    │   └── BlueBirdSatellite (3D models)
    │
    ├── ClientGroundTrackMap ─── Same satellite data (2D projection)
    │
    ├── Stock Price ──────────── Finnhub API
    │
    ├── TLE Freshness ────────── /api/satellites/batch-tle
    │
    └── SEC Filings ──────────── /api/filings
```

---

## Earth Components

Located in `components/earth/`.

### Globe3D

**File**: `Globe3D.tsx`
**Wrapper**: `ClientGlobe3D.tsx` (dynamic import, no SSR)
**Data Source**: Space-Track via `useSatellites` hook

Features:
- Photorealistic Earth texture
- Real-time satellite markers (dots or 3D models)
- Orbital path visualization (TLE propagation)
- Coverage hexgrid (CellGrid component)
- OrbitControls for rotation/zoom
- Click satellite to select

```typescript
<ClientGlobe3D
  satellites={sats}
  selectedSatellite={selected}
  onSelectSatellite={handleSelect}
  showOrbits={true}
  showCoverage={true}
  useDotMarkers={false}  // false = 3D satellite models
/>
```

### CellGrid

**File**: `CellGrid.tsx`
**Purpose**: Hexagonal coverage visualization on globe surface

Features:
- Geodesic hexagonal tessellation (hexasphere.js)
- Shader-based visibility (only shows within satellite coverage)
- Fades at coverage edges
- Based on FCC 23-65: 48km diameter ground cells

```typescript
<CellGrid
  satellites={satellitePositions}
  globeRadius={1}
  detailLevel="HIGH"
  cellColor="#FF6B35"
  opacity={0.8}
/>
```

### BlueBirdSatellite / BlueBirdSatelliteV2

**Files**: `BlueBirdSatellite.tsx`, `BlueBirdSatelliteV2.tsx`
**Purpose**: 3D satellite models for visualization

Generations:
- `bluewalker3`: Original test satellite (64 m²)
- `block1`: BB1-BB5 production satellites (64 m²)
- `block2`: FM1 larger satellite (223 m²)

Features:
- Accurate panel geometry
- Copper trim details
- Selection glow effect

### GroundTrackMap

**File**: `GroundTrackMap.tsx`
**Wrapper**: `ClientGroundTrackMap.tsx`
**Purpose**: 2D Mercator projection with ground tracks

Features:
- SVG-based rendering
- Landmass outlines (points + coastlines)
- Satellite markers with labels
- Orbital ground tracks
- Coverage circles (optional)
- Click to select/deselect
- Expandable to full overlay

```typescript
<ClientGroundTrackMap
  satellites={satellites}
  selectedSatellite={selected}
  onSelectSatellite={handleSelect}
  showOrbits={true}
  showCoverage={true}
  showLegend={true}
/>
```

### Supporting Files

| File | Purpose |
|------|---------|
| `satellite-colors.ts` | Color palette and labels for each satellite |
| `landmass-points.ts` | Coordinate data for continent rendering |
| `shaders/cellVisibility.ts` | Coverage calculation utilities |
| `satellite/config.ts` | Satellite dimensions and specs |

---

## Cockpit Components

Located in `components/cockpit/`. Legacy components from grid-based layout.

| Component | Status | Notes |
|-----------|--------|-------|
| `LiveTelemetryFeed` | Active | Used in DENSE mode sidebar |
| `StockPricePanel` | Active | Top-right price display |
| `SatelliteDetailModal` | Active | Popup on satellite select |
| `DragHistoryChart` | Active | B* coefficient trends |
| `Earth3D` | Deprecated | Replaced by Globe3D |
| `NewsFeed` | Deprecated | Was static mock data |
| `EventTimeline` | Deprecated | Was static mock data |
| `TechnicalIndicators` | Inactive | Not in current Terminal |

---

## Filings Components

Located in `components/filings/`.

| Component | Purpose |
|-----------|---------|
| `FilingCard` | Single filing display |
| `FilingsFeed` | List of recent filings |
| `FilingDetailModal` | Full filing view |

---

## Experiments

Located in `components/experiments/`. Prototype components:

- `RealFilingsFeed` - Live filings integration
- `RealSatelliteMap` - Early map prototype
- `RealPriceTicker` - Stock ticker
- `RealTelemetry` - Telemetry display
- Various UI widgets (Gauge, Sparkline, etc.)

---

## Gallery Components

Located in `components/gallery/`. Modular UI components for future use:

### Stock
- `PriceTicker`, `PriceSparkline`, `PriceStats`
- `DayRangeBar`, `YTDPerformance`

### Telemetry
- `SatelliteCard`, `TelemetryTable`
- `ConstellationGrid`, `ConstellationProgress`
- `OrbitalParamsCard`, `DragComparisonChart`

### Content
- `FilingCard`, `SignalCard`
- `UnifiedInbox`, `EarningsTimeline`
- `LatestByCategory`, `PendingMilestones`

---

## Component → Data Source Map

| Component | Hook | API Route | Update |
|-----------|------|-----------|--------|
| Globe3D | `useSatellites` | `/api/satellites/batch-tle` | 1s client |
| GroundTrackMap | (same data) | - | - |
| Stock Price | `useStockPrice` | `/api/stock/ASTS` | 60s |
| TLE Freshness | `useTLEFreshness` | `/api/satellites/batch-tle` | 1min |
| Filings | `useFilings` | `/api/filings` | 5min |
| Drag History | `useDragHistory` | `/api/satellites/[id]/drag-history` | On open |

---

## Creating New Components

1. **Identify data source** → Check `docs/DATA_SOURCES.md`
2. **Create hook** if needed → `lib/hooks/use[Feature].ts`
3. **Create component** → `components/[category]/[Name].tsx`
4. **Follow style guide** → Check `globals.css` for colors/typography
5. **Add to Terminal** → `app/(dashboard)/terminal/page.tsx`

### Style Guidelines

```typescript
// Colors (from globals.css)
'bg-[#030305]'      // void-black background
'text-white/90'     // primary text
'text-white/50'     // secondary text
'text-white/30'     // muted text
'border-white/15'   // subtle borders
'text-asts-orange'  // selection only (#FF6B35)

// Typography
'font-mono'
'text-[10px]'       // base size
'text-[8px]'        // small labels
'tracking-wider'
'uppercase'
```

---

## Performance Notes

### Three.js (Globe3D)
- Dynamically imported via `next/dynamic` (no SSR)
- Coverage grid uses GPU shaders
- 3D satellite models only render when zoomed in
- Client-side position calculation (satellite.js)

### Real-time Updates
- Satellite positions: 1s interval via `setInterval` + satellite.js
- Stock price: 60s polling via React Query
- TLE data: 1min staleTime, refetches on window focus

### Bundle Size
Three.js and satellite.js are code-split via dynamic imports.
