# Short Gravity — Design System

This folder contains the design specifications and references for the Short Gravity web application.

## Structure

```
design/
├── 00-shell/           # Global HUD (header, effects)
│   ├── BUILD_SPEC.md   # Complete implementation spec
│   └── REFERENCE.md    # Reference notes
├── 01-intel/           # Intel/Signal Feed section
├── 02-terminal/        # Terminal/Cockpit section
└── 03-supply/          # Supply/Briefing section
```

## Implementation Status

✅ **00. THE SHELL (Global HUD)**
- Fixed header with backdrop blur
- JetBrains Mono font for logo
- Tab navigation (01. INTEL / 02. TERMINAL / 03. SUPPLY)
- Status ticker (BTC, GAS, UTC, SYS.ONLINE)
- Scanline animation (8s loop)
- Vignette overlay
- Grain texture (5% opacity)
- Active tab indicator (glowing dot)
- Hover states on logo brackets

## Design Principles

1. **Terminal Aesthetic**: Mission control / radar interface
2. **Monospace Typography**: JetBrains Mono for data/code
3. **Dark Mode Only**: #0A0A0A background
4. **Subtle Effects**: Scanlines, vignette, grain for CRT feel
5. **Color Coding**: 
   - Orange (#F97316) for accents
   - Blue (#3B82F6) for time/data
   - Green (#22C55E) for system status
   - Grey (#666) for inactive states

## Fonts

- **Logo/Data**: JetBrains Mono (700 Bold)
- **Navigation**: Geist Sans (500 Medium)
- **Body**: Geist Sans (400 Regular)

## Next Sections to Design

1. **01. INTEL** - Signal Feed layout
2. **02. TERMINAL** - Cockpit 3D view
3. **03. SUPPLY** - Briefing reader
