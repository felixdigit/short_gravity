# Short Gravity — Bloomberg-Inspired Design Reference

**Last Updated**: January 25, 2026

---

## Core Philosophy

**"NASA Mission Control meets Bloomberg Terminal"**

A professional intelligence tool for Spacemob. Dense, data-rich, multi-panel. Not a consumer app — a power tool for investors watching $ASTS unfold in real-time.

---

## Visual DNA: Bloomberg Terminal

### What Makes Bloomberg Work

1. **Information density** — Multiple data streams visible simultaneously
2. **Color-coded semantics** — Green=positive, red=negative, orange=alerts
3. **Monospace data** — All numbers, timestamps, IDs in mono font
4. **Panel hierarchy** — Primary (large), secondary (data streams), tertiary (metadata)
5. **Live tickers** — Scrolling status bars with real-time updates
6. **Dense tables** — Tight row spacing, precise alignment
7. **Terminal modals** — Drill-down detail views with bordered frames

### Bloomberg Layout Patterns

```
┌─────────────────────────────────────────────────────────────────┐
│ GLOBAL STATUS TICKER (scrolling data, system health)           │
├──────┬──────────────────────────────────────────────────────────┤
│      │  ┌─────────────────┬─────────────────┐                  │
│ SIDE │  │  DATA PANEL 1   │  DATA PANEL 2   │                  │
│ BAR  │  │  (live feed)    │  (metrics)      │                  │
│      │  ├─────────────────┴─────────────────┤                  │
│ Nav  │  │  PRIMARY VISUALIZATION            │                  │
│  +   │  │  (3D, charts, timeline)           │                  │
│ Meta │  │                                   │                  │
│      │  └───────────────────────────────────┘                  │
│      │  ┌───────────────────────────────────────────────────┐  │
│      │  │  SECONDARY DATA STREAM / READOUTS                 │  │
└──────┴──┴───────────────────────────────────────────────────┴──┘
```

---

## Panel Components

### Data Panel (Bloomberg-style)

```
┌─ SIGNAL FEED ─────────────────────────── LIVE ──┐
│                                                  │
│  ID       ENTITY           Z-SCORE   TIME       │
│  ─────────────────────────────────────────────  │
│  SIG-001  BlueWalker 3       4.2    12:34:56   │
│  SIG-002  ASTS-Corp          3.8    12:33:12   │
│  SIG-003  BlueBird 6         2.9    12:31:45   │
│                                                  │
├──────────────────────────────────────────────────┤
│  156 SIGNALS              UPDATED 12:34:56      │
└──────────────────────────────────────────────────┘
```

### Status Ticker (Top Banner)

```
│ BW3: 519.8km ▲ │ ASTS: $24.52 ▼ -2.3% │ BB6: NOMINAL │ UTC: 14:05:22Z │ SYS.ONLINE ●
```

### Terminal Modal (Drill-down)

```
┌────────────────────────────────────────────────┐
│ [X] SIGNAL DETAIL · ID: SIG-2847               │
├────────────────────────────────────────────────┤
│                                                │
│  ENTITY:    BlueWalker 3                       │
│  SEVERITY:  HIGH                               │
│  DETECTED:  2026-01-21T14:32:15Z               │
│                                                │
│  Z-SCORE:   3.42                               │
│  METRIC:    orbital_velocity_kms               │
│                                                │
│  SOURCE DATA ──────────────────────────────    │
│  > Tweet by @SpaceMobVoice                     │
│  > Filed SEC 8-K on 2026-01-20                 │
│                                                │
│  [VIEW SOURCE]  [DISMISS]                      │
└────────────────────────────────────────────────┘
```

---

## Color System (Bloomberg-aligned)

| Use | Color | Hex |
|-----|-------|-----|
| Primary accent | Cyan | `#06B6D4` |
| Highlight/selection | Orange | `#F97316` |
| Positive/gains | Green | `#22C55E` |
| Negative/losses | Red | `#EF4444` |
| Warning/alerts | Orange | `#F97316` |
| Background | Deep black | `#0A0A0A` |
| Panel bg | Slightly lighter | `#0D0D0D` |
| Primary text | White | `#FFFFFF` |
| Secondary text | Gray | `#A1A1AA` |
| Borders | Cyan at 20% | `rgba(6, 182, 212, 0.2)` |

---

## Typography (Terminal-style)

| Use | Font | Style |
|-----|------|-------|
| All data/numbers | JetBrains Mono | Normal |
| Labels/headers | JetBrains Mono | UPPERCASE, tracking-wider |
| Prose/descriptions | Geist Sans | Normal case |

**Size scale** (dense terminal):
- 9px: Micro labels, timestamps
- 10px: Data labels
- 11px: Secondary text
- 12px: Body text
- 14px: Standard content
- 16px: Section headers

---

## Key Interaction Patterns

### Hover States
- Border: `rgba(6, 182, 212, 0.5)` (brighter cyan)
- Background: `#1a1a1a` (slightly elevated)
- Glow: `box-shadow: 0 0 15px rgba(6, 182, 212, 0.15)`

### Selection States
- Border: `#F97316` (orange)
- Background: `rgba(249, 115, 22, 0.05)`
- Glow: `box-shadow: 0 0 20px rgba(249, 115, 22, 0.2)`

### Data Updates
- Brief cyan pulse when data refreshes
- Stagger animations for new entries
- Odometer-style number transitions

---

## What NOT to Do

- Single-column layouts (too basic)
- Excessive whitespace (not dense enough)
- Consumer app styling (rounded corners, soft shadows)
- Decorative elements (unnecessary visual noise)
- Slow animations (terminal feels instant)

---

## Implementation Reference

See `DESIGN_SYSTEM_V2.md` for complete technical specs.

---

*"Dense, data-rich, professional. Like sitting at a Bloomberg terminal watching the $ASTS story unfold."*
