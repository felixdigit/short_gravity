# CLAUDE.md Draft Updates — Round 1

These sections are proposed additions/replacements for CLAUDE.md, based on Gemini's analysis filtered through codebase verification.

---

## UPDATE 1: Replace existing "Charting Engine" section

### Charting Engine

**One engine, one theme, every chart.** Charting is platform infrastructure. Short Gravity uses a custom Canvas 2D rendering engine (`lib/charts/`) — configuration-driven, not composition-driven. Every chart in the app is a configuration of this engine.

- **Recharts and lightweight-charts are legacy.** Migrate to the SG engine when touched. No new charts using third-party libraries.

#### The API: `<SGChart />`

SGChart takes a flat `ChartConfig` object — not JSX children. This is intentional: Canvas rendering requires batched, coordinated draw passes that a composition model can't guarantee.

```typescript
<SGChart
  series={[
    { id: 'price', type: 'line', data: priceData, color: 'white', strokeWidth: 1.5 },
    { id: 'volume', type: 'area', data: volumeData, axis: 'y2', fillOpacity: 0.05 },
  ]}
  overlays={[
    { type: 'trend', seriesId: 'price' },
    { type: 'reference-line', axis: 'y', value: 100, label: 'SMA(20)' },
    { type: 'markers', data: [{ time: '2024-01-15', color: '#FF6B35' }] },
  ]}
  axes={{ x: 'time', y: { format: v => `$${v.toFixed(2)}` } }}
  crosshair
  animate
  height={300}
/>
```

#### Series Types

| Type | Data Shape | Notes |
|------|-----------|-------|
| `line` | `TimeSeriesPoint[]` | Monotone cubic interpolation by default. No overshoot. |
| `area` | `TimeSeriesPoint[]` | Line + gradient fill. `fillOpacity` default 0.08. |
| `bar` | `TimeSeriesPoint[]` or `BarPoint[]` | Auto-detects: time-based or categorical/diverging. |
| `candlestick` | `OHLCPoint[]` | OHLC candles + optional volume bars on y2. |
| `sparkline` | `TimeSeriesPoint[]` | Minimal inline chart. No axes, no animation. |

#### Overlay Types

| Type | Purpose |
|------|---------|
| `trend` | Linear regression line computed from a series. |
| `reference-line` | Static horizontal or vertical reference (SMA, target price, event date). |
| `markers` | Vertical lines at specific timestamps (earnings, filings, launches). |

#### Key Types

```typescript
interface TimeSeriesPoint { time: number | string | Date; value: number }
interface OHLCPoint { time: number | string | Date; open: number; high: number; low: number; close: number; volume?: number }
interface BarPoint { label: string; value: number; color?: string }
```

#### Chart Theme

Defined once in `lib/charts/theme.ts`, consumed by every chart:

```
Background: #030305 (void black)
Lines/strokes: white, 0.75px hairline default
Grid: rgba(255,255,255, 0.02) — barely visible
Accent: #FF6B35 — crosshair vertical line only
Up: #22C55E | Down: #EF4444 | Warning: #EAB308
Text: JetBrains Mono, 9-10px, white/40
Tooltip: bg black/95, border white/10
```

#### Export

SGChart supports share-frame export via ref handle: `ref.current.exportToBlob({ title, subtitle, source, aspect: '16:9', stats })`. Renders high-DPI static image with header, chart, footer, and stat boxes. Use for X posts, reports, and shareable visuals.

#### Engine Internals (for reference, not modification)

`ChartEngine` class manages: Canvas init → DPR scaling → Scale computation → Render passes (background → grid → series → overlays → crosshair) → Animation (300ms easeOut on data change) → Interaction (mouse tracking, nearest-point snap within 40px). `ScaleManager` handles domain→pixel mapping for time, linear, log, index, and category scales. Monotone cubic Hermite interpolation (`lib/charts/spline.ts`) matches D3's `curveMonotoneX` — preserves monotonicity, no overshoot.

---

## UPDATE 2: New section after "Architecture Principle: One Engine Per Domain"

### Data Flow: Terminal Provider & Widget Contracts

The terminal page data flow is: **Provider fetches → Context distributes → Widgets render.**

#### `TerminalDataProvider` (`lib/providers/TerminalDataProvider.tsx`)

Single provider at page level. Composes internal hooks, exposes a typed context. Widgets consume via `useTerminalData()`. Widgets MUST NOT fetch their own data — they read from context or accept prop overrides.

**Current context shape** (satellite/orbital focused — will expand for $SPACE):

```typescript
interface TerminalDataContextValue {
  satellites: SatelliteData[]          // All tracked satellites with live positions
  fm1: SatelliteData | undefined       // Primary satellite (BlueBird 7)
  mapTracks: MapSatellite[]            // Simplified data for map visualization
  terminalContext: string | undefined  // Human-readable context string for brain queries
  tleFreshness: TLEFreshness | null    // Overall TLE age metrics
  perSatelliteFreshness: Record<string, PerSatelliteFreshness>  // Per-satellite TLE source/age
  divergenceData: DivergenceData[] | undefined  // CelesTrak vs Space-Track BSTAR delta
  dragHistory: DragHistoryResponse | null | undefined  // 45-day FM1 B* history
  dragLoading: boolean                 // Drag history loading state
}
```

**Data freshness:**

| Data | Source | Cadence | Cache |
|------|--------|---------|-------|
| TLE data | `/api/satellites/batch-tle` | On mount, 30min stale | React Query |
| Live positions | Local satellite.js propagation | 500ms interval | In-memory |
| Drag history | `/api/satellites/{id}/drag-history` | On mount, 1h refetch | React Query |
| Divergence | `/api/satellites/divergence` | On mount, refetch on focus | React Query 5min |

#### UI State: `useTerminalStore` (Zustand)

Separate from data. Manages: display mode (minimal/dense), globe toggles (orbits, coverage, dot markers), satellite selection, brain panel open/close, active preset. Only `activePreset` and `mode` persist to localStorage.

#### Widget data consumption pattern

Widgets accept optional prop overrides but default to context:

```typescript
const ctx = useTerminalData()
const satellites = propSatellites ?? ctx.satellites
```

This allows widgets to work standalone (with props) or composed (from provider). When adding a new data domain to the provider, extend the interface, add the internal hook, and memoize the output.

---

## UPDATE 3: Replace existing "Coverage Completeness" section

### CRITICAL: Coverage Completeness

Short Gravity is a source of truth. The truth is finite — every FCC filing, patent, SEC exhibit, and regulatory action exists out there. The job is to capture all of it, then keep it current. Not an endless process — a completable one.

#### Worker Lifecycle: Capture → Verify → Maintain

1. **Capture** — Backfill everything that exists historically. Don't stop at "recent." Go to the beginning.
2. **Verify** — The worker self-audits: compare what exists at the source against what's in Supabase. If the count doesn't match, the job isn't done.
3. **Maintain** — Once complete, the scheduled cron watches for new additions only. The hard part is already done.

#### Completeness Verification Standard

Every worker MUST implement a completeness check that answers: **"Source has X records. Database has Y. Gap is Z."**

The pattern:

```python
def verify_completeness(worker_name, table_name):
    source_count = query_source_total()        # e.g., SEC EDGAR total filings for CIK
    db_count = query_db_count(table_name)       # e.g., SELECT count(*) FROM filings WHERE company='ASTS'
    coverage_pct = (db_count / source_count * 100) if source_count > 0 else 0

    supabase_request("POST", "worker_completeness_audits", {
        "worker_name": worker_name,
        "table_name": table_name,
        "source_count": source_count,
        "db_count": db_count,
        "coverage_pct": round(coverage_pct, 2),
        "status": "complete" if db_count >= source_count else "incomplete"
    })
```

This runs at the END of every worker execution — both backfill and incremental modes.

#### Completeness infrastructure

- **`worker_runs` table** — Already exists. Logs every GH Actions execution with worker name, status, run URL.
- **`worker_completeness_audits` table** — NEW. Tracks source count vs DB count per worker per run. Schema: `(worker_name, table_name, source_count, db_count, coverage_pct, status, details JSONB, checked_at)`.
- **Health endpoint** (`/api/system/health`) — Already checks staleness. Extend to also surface completeness: "Patent Worker: 307/307 (100%)" vs "ECFS 23-65: 250/269 (93%)".
- **Staleness alert** (`.github/workflows/staleness-alert.yml`) — Already creates GitHub Issues for stale data. Extend to also flag incomplete workers.

#### Rules

- **Every worker must know if it's complete.** A worker that can't answer "have I captured everything?" is unfinished. Build in source-count checks, discovery queries, or coverage reports.
- **Discovery over hardcoding.** Don't just fetch a list of known docket numbers — search for the filer. Don't just fetch known patent numbers — query the assignee. Hardcoded lists miss what you don't know about yet.
- **When a gap is found, fix the worker** — don't just backfill. The gap means the capture logic has a hole. Patch the hole.
- **Coverage gaps are worse than stale data.** Stale data is visible. Missing data is invisible.
- **Local-only workers are incomplete.** `exhibit_backfill.py`, `fcc_attachment_worker.py`, and `patent_enricher.py` need GitHub Actions workflows. A worker without a cron schedule is not autonomous.
