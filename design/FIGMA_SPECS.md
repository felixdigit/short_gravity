# Short Gravity — Figma Design Specs

Use these exact values in Figma to ensure 1:1 translation to code.

---

## Color Palette

### Backgrounds
| Name | Hex | Usage |
|------|-----|-------|
| Black | `#000000` | Page background, card backgrounds |
| Near Black | `#050505` | Nested containers, chart backgrounds |
| Dark Gray | `#0a0a0a` | Hover states, expanded rows |
| Border | `#1a1a1a` | All borders, dividers |
| Row Divider | `#111111` | Table row separators |

### Accent Colors
| Name | Hex | Usage |
|------|-----|-------|
| Amber | `#D4A574` | Headers, titles, active states |
| Green | `#5CB85C` | Live indicators, positive values, OK status |
| Green (30%) | `#5CB85C` @ 30% opacity | Live panel borders |
| Red | `#D9534F` | Errors, negative values |

### Text Grays
| Name | Hex | Usage |
|------|-----|-------|
| White | `#CCCCCC` | Primary text, values |
| Light Gray | `#999999` | Secondary text, body |
| Medium Gray | `#888888` | Data values |
| Gray | `#666666` | Labels, column headers |
| Dark Gray | `#444444` | Timestamps, sources, footnotes |
| Muted | `#333333` | Disabled, very subtle text |

---

## Typography

### Font
**JetBrains Mono** (monospace) — used for everything

### Scale
| Size | Usage |
|------|-------|
| 7px | Footnotes, chart labels |
| 8px | Sources, timestamps, column headers, status badges |
| 9px | Table data, secondary labels |
| 10px | Panel headers, loading states |
| 12px | Price changes, SMA values |
| 14px | Trend indicators |
| 18px | RSI value |
| 28px | Main price display |
| 32px | Hero numbers |

### Weights
- **400** (Regular) — Most text
- **500** (Medium) — Satellite names
- **700** (Bold) — Prices, status, trends

---

## Spacing

### Base Unit: 4px

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Tight spacing |
| sm | 8px | Icon gaps, inline spacing |
| md | 12px | Panel padding (px-3 py-2) |
| lg | 16px | Section gaps |
| xl | 24px | Panel margins |

### Common Patterns
- Panel padding: `12px horizontal, 8px vertical`
- Header padding: `12px horizontal, 8px vertical`
- Table cell padding: `8px horizontal, 4-6px vertical`
- Grid gap: `8px`

---

## Component Specs

### Panel (Card)

```
┌─────────────────────────────────────┐
│ HEADER TEXT              ● LIVE     │  ← Header: 10px amber, 8px green
├─────────────────────────────────────┤  ← Border: #1a1a1a
│                                     │
│            CONTENT                  │
│                                     │
├─────────────────────────────────────┤  ← Border: #1a1a1a
│         Footer / Source             │  ← 8px, #444
└─────────────────────────────────────┘
```

**Default Panel:**
- Background: `#000000`
- Border: `1px solid #1a1a1a`
- Border radius: `0px` (sharp corners)

**Live Panel (has real data):**
- Background: `#000000`
- Border: `1px solid rgba(92, 184, 92, 0.3)` (#5CB85C @ 30%)
- Header shows: `● LIVE` in green

### Header Bar
- Height: ~28px
- Padding: 12px horizontal, 8px vertical
- Left: Title in amber (#D4A574), 10px
- Right: Status badge (● LIVE) in green, 8px
- Border bottom: 1px #1a1a1a

### Live Indicator
- Text: `● LIVE` or `● REAL`
- Color: #5CB85C
- Size: 8px
- The bullet is a text character, not a separate element

### Table Row
- Height: ~24-28px
- Padding: 12px horizontal, 6px vertical
- Border bottom: 1px #111111
- Hover: background #111111
- Selected/Expanded: background #0a0a0a

### Footer
- Height: ~20px
- Padding: 12px horizontal, 4px vertical
- Text: 8px, #444444, centered
- Border top: 1px #1a1a1a

---

## Status Colors

| Status | Background | Text | Border |
|--------|------------|------|--------|
| Loading | — | #444444 | #1a1a1a |
| Error | — | #D9534F | #1a1a1a |
| Live/OK | — | #5CB85C | #5CB85C @ 30% |
| Positive | — | #5CB85C | — |
| Negative | — | #D9534F | — |
| Neutral | — | #888888 | — |

---

## Grid Layouts

### Terminal Page (1440px viewport)
```
┌──────────┬─────────────────┬──────────┐
│  480px   │      flex       │  340px   │  Row 1: ~calc(50% - 78px)
│  Earth   │                 │  Stock   │
│          │    News Feed    │          │
├──────────┤    (2 rows)     ├──────────┤  Row 2: ~calc(50% - 78px)
│  Telem   │                 │ Indicat  │
│          │                 │          │
├──────────┴─────────────────┴──────────┤  Row 3: 150px
│           Event Timeline              │
└───────────────────────────────────────┘

Gap: 8px
Padding: 8px (page padding)
```

### Experiments Page Grid
- 3 columns on xl (1280px+)
- 2 columns on md (768px+)
- 1 column on mobile
- Gap: 24px
- Card height: 200px content area

---

## Animation

### Pulse (Loading)
```css
animation: pulse 2s ease-in-out infinite;

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

### Glow (Live indicator nodes)
```css
box-shadow: 0 0 8px #5CB85C;  /* Green glow */
box-shadow: 0 0 8px #D4A574;  /* Amber glow */
```

---

## Figma Setup Tips

1. **Create Color Styles** for each hex value above
2. **Create Text Styles** for each size (7px through 32px, all JetBrains Mono)
3. **Use Auto Layout** with 4px base spacing
4. **Components**: Create base Panel, Header, Footer, Table Row
5. **Variants**: Default vs Live panel states

### Naming Convention
```
Colors/
  Background/Black
  Background/Border
  Accent/Amber
  Accent/Green
  Accent/Red
  Text/Primary
  Text/Secondary
  Text/Muted

Text/
  Header-10
  Body-9
  Label-8
  Footnote-7
  Price-28
  Hero-32
```

---

## Quick Reference

**Most Common Values:**
- Background: `#000000`
- Border: `#1a1a1a`
- Header text: `#D4A574` 10px
- Body text: `#999999` 9px
- Live badge: `#5CB85C` 8px
- Footer: `#444444` 8px
- Padding: 12px / 8px

**Live Panel Border:**
`1px solid rgba(92, 184, 92, 0.3)`

**Font:**
JetBrains Mono, all weights
