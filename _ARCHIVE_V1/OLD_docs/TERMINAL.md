# Terminal

The main product interface — a globe-centric mission control dashboard.

---

## Overview

The Terminal (`/terminal`) is a full-viewport immersive view with the 3D globe as background and floating overlay panels for data. Two modes: CLEAN (minimal) and DENSE (full data).

**URL**: `/terminal`
**File**: `app/(dashboard)/terminal/page.tsx`

---

## Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  SHORT GRAVITY              [Glossary]    ASTS $XX.XX    TLE: XXh   │
│  ASTS CONSTELLATION MONITOR                                         │
│  [timestamp]                                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│                                                                     │
│                         3D GLOBE                                    │
│                    (full background)                                │
│                                                                     │
│                                                                     │
│  ┌──────────┐                                       ┌─────────────┐ │
│  │ Mercator │                                       │ SEC Filings │ │
│  │   Map    │                                       │    Feed     │ │
│  └──────────┘                                       └─────────────┘ │
│                                                                     │
│              [ CLEAN | DENSE ] [ ORBITS | COVERAGE ] [ DOTS | 3D ]  │
│                          SPACE-TRACK · FINNHUB · SEC                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Modes

### CLEAN Mode
- Globe only with satellites
- Minimal UI overlays
- Best for presentations/screenshots

### DENSE Mode (default)
Shows all panels:
- Top left: Branding, timestamp, glossary button
- Top right: Stock price, TLE age badge
- Right sidebar: Satellite list with telemetry
- Bottom left: Mercator mini-map (expandable)
- Bottom right: SEC filings feed
- Bottom center: Control toggles

---

## Key Components

### Globe (`ClientGlobe3D`)
- Full-bleed 3D Earth with photorealistic texture
- Satellite markers (dots or 3D models)
- Orbital paths (toggle)
- Coverage hexgrid (toggle)
- Click satellite to select

### Mercator Map (`ClientGroundTrackMap`)
- 2D projection with ground tracks
- Expandable to 70% viewport
- Click to select/deselect satellites
- Shows orbits and coverage when expanded

### Satellite List
- All 7 ASTS satellites
- Real-time lat/lon/alt
- Click to select and show detail card

### SEC Filings Feed
- Recent filings with form type
- Click to open filing

---

## Controls

Bottom control bar (DENSE mode only):

| Toggle | Options | Default |
|--------|---------|---------|
| Mode | CLEAN / DENSE | DENSE |
| Visualization | ORBITS / COVERAGE | Off |
| Markers | DOTS / 3D | DOTS |

---

## Data Flow

```
Terminal Page
    │
    ├── ClientGlobe3D
    │   └── useSatellites() → /api/satellites/batch-tle
    │       └── Real-time position via satellite.js (client-side)
    │
    ├── ClientGroundTrackMap
    │   └── Same satellite data, 2D projection
    │
    ├── Stock Price
    │   └── useStockPrice('ASTS') → /api/stock/ASTS
    │
    ├── TLE Freshness
    │   └── useTLEFreshness() → /api/satellites/batch-tle
    │
    └── SEC Filings
        └── useFilings() → /api/filings
```

---

## Z-Index Layers

| Layer | Z-Index | Content |
|-------|---------|---------|
| Globe | z-0 | 3D canvas background |
| Panels | z-10 | Mercator, filings, satellite list |
| Controls | z-30 | Bottom toggle bar |
| Mercator focused | z-40 | Expanded map overlay |
| Backdrop | z-30 | Dark overlay when map expanded |

---

## Files

```
app/(dashboard)/terminal/page.tsx     # Main page
components/earth/ClientGlobe3D.tsx    # 3D globe wrapper
components/earth/Globe3D.tsx          # Globe implementation
components/earth/ClientGroundTrackMap.tsx  # Mercator wrapper
components/earth/GroundTrackMap.tsx   # Mercator implementation
components/earth/CellGrid.tsx         # Hexagonal coverage grid
components/earth/BlueBirdSatellite.tsx    # 3D satellite model
```
