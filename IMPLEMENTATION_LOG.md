# Short Gravity — Implementation Log

## 2026-01-20: Global Shell (HUD) Implementation

### ✅ Completed

**Global Header Component** (`components/layout/GlobalHeader.tsx`)
- Fixed position header (48px height)
- Background: #0A0A0A with 85% opacity + 12px backdrop blur
- Border: 1px solid #1F1F1F (bottom only)
- z-index: 999

**Logo** (Top Left)
- Font: JetBrains Mono, 700 weight, 14px
- Text: `[ SHORT GRAVITY ]` with brackets
- Letter spacing: -0.02em
- Hover: Brackets turn orange (#F97316)

**Navigation** (Center)
- Three tabs: "// 01. INTEL", "// 02. TERMINAL", "// 03. SUPPLY"
- Font: Geist Sans, 500 weight, 13px, uppercase
- Active state: White text + glowing dot below
- Inactive state: #666 grey
- Gap: 32px between tabs

**Status Ticker** (Top Right)
- Font: JetBrains Mono, 11px
- Live data:
  - BTC price (white, updates every 5s)
  - GAS in GWEI (grey #888)
  - UTC time (blue #3B82F6, updates every second)
  - SYS.ONLINE indicator (green pulsing dot)

**Terminal Effects** (`components/layout/TerminalEffects.tsx`)
- Scanline: 2px white line, 2% opacity, 8s loop animation
- Vignette: Radial gradient overlay, darkens edges
- Grain: 5% opacity noise texture

**Typography**
- Installed JetBrains Mono font from Google Fonts
- Updated globals.css to use it as default monospace
- Three font families available:
  - Geist Sans (body)
  - Geist Mono (fallback)
  - JetBrains Mono (primary mono)

**Layout Changes**
- Removed old sidebar navigation
- Added global header to root layout
- Added 48px top padding to content
- Simplified dashboard layout to just container

### Design Files Created

```
design/
├── 00-shell/
│   ├── BUILD_SPEC.md      # Complete spec from blueprint
│   └── REFERENCE.md       # Reference notes
├── 01-intel/              # (Empty - ready for next section)
├── 02-terminal/           # (Empty - ready for next section)
├── 03-supply/             # (Empty - ready for next section)
└── README.md              # Design system overview
```

### Code Files Modified/Created

**New:**
- `components/layout/GlobalHeader.tsx`
- `components/layout/TerminalEffects.tsx`
- `design/00-shell/BUILD_SPEC.md`
- `design/README.md`

**Modified:**
- `app/layout.tsx` - Added header, effects, JetBrains Mono
- `app/(dashboard)/layout.tsx` - Removed sidebar
- `app/globals.css` - Added scanline animation

### Technical Details

**Animations:**
- Scanline: CSS keyframe, linear 8s infinite
- Pulsing dot: Tailwind `animate-pulse`
- Clock: React useEffect, updates every 1000ms
- BTC price: Random fluctuation every 5000ms

**Responsive:**
- Mobile adaptation not yet implemented
- Blueprint specifies: 44px height, hide ticker except SYS.ONLINE

### Next Steps

1. Implement mobile header (44px, bottom nav)
2. Design and build "01. INTEL" section (Signal Feed)
3. Design and build "02. TERMINAL" section (Cockpit)
4. Design and build "03. SUPPLY" section (Briefing)

### Running the App

```bash
npm run dev
```

Visit http://localhost:3000

All pages work:
- `/` - Intel/Signal Feed (old design, pending update)
- `/cockpit` - Terminal (old design, pending update)
- `/briefings` - Supply (old design, pending update)
- `/watchlist` - Placeholder
- `/settings` - Placeholder

Global header is visible on all pages with proper navigation and effects.
