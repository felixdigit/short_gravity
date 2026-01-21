# Short Gravity - Architecture Map

**Last Updated**: January 21, 2026
**Purpose**: Complete map of where everything lives in the codebase

---

## 🎯 Quick Navigation

Jump to section:
- [Project Structure](#-project-structure)
- [Tech Stack](#-tech-stack)
- [File Locations](#-file-locations-where-everything-lives)
- [Features Status](#-features--implementation-status)
- [Data Flow](#-data-flow-architecture)
- [Design System](#-design-system)

---

## 📁 Project Structure

```
short_gravity/
│
├── 🌐 short-gravity-web/              # Main Next.js application
│   ├── app/                           # Next.js App Router (pages & API routes)
│   ├── components/                    # React components
│   ├── lib/                          # Utilities, hooks, helpers
│   ├── types/                        # TypeScript type definitions
│   ├── public/                       # Static assets
│   └── package.json                  # Dependencies & scripts
│
├── 📐 short-gravity-architecture/     # Architecture documentation (10 files)
│   ├── 00-ARCHITECTURE-OVERVIEW.md
│   ├── 01-SIGNAL-ENGINE.md
│   ├── 02-COCKPIT.md
│   └── ... (see Architecture Docs section)
│
├── 🎨 design/                         # Design system documentation
│   ├── README.md
│   └── 00-shell/
│       ├── BUILD_SPEC.md
│       └── REFERENCE.md
│
├── 🔧 scripts/                        # Utility scripts
│   └── setup-vercel-env.sh
│
├── 📦 components/                     # Shared components (root level)
├── 📚 lib/                           # Shared utilities (root level)
│
└── 📄 Configuration & Docs
    ├── .env.example                  # Environment variable template
    ├── .env.local                    # Your secrets (gitignored)
    ├── ENV_SETUP_GUIDE.md           # Environment setup guide
    ├── QUICK_START.md               # Quick start guide
    ├── IMPLEMENTATION_LOG.md        # Implementation history
    └── vercel.json                  # Vercel configuration
```

---

## 🛠 Tech Stack

### Frontend
- **Framework**: Next.js 16.1.4 (App Router)
- **React**: 19.2.3
- **TypeScript**: 5.x
- **Styling**: Tailwind CSS v4
- **State**: Zustand 5.0.10
- **Data Fetching**: TanStack React Query 5.90.19
- **Icons**: Lucide React

### Backend
- **Planned**: Supabase (PostgreSQL + Realtime)
- **APIs**: X (Twitter), Space-Track.org, Claude AI

### Development
- **Build**: Next.js with React Compiler
- **Linting**: ESLint 9.x
- **Fonts**: Geist Sans/Mono, JetBrains Mono

---

## 📍 File Locations (Where Everything Lives)

### 🎨 Pages (App Router)

```
app/
│
├── layout.tsx                        # Root layout (fonts, metadata)
├── globals.css                       # Global styles
│
├── (dashboard)/                      # Dashboard route group
│   ├── layout.tsx                    # Dashboard container with sidebar
│   ├── page.tsx                      # 🏠 HOME: Signal Feed (01. INTEL)
│   │
│   ├── cockpit/
│   │   └── page.tsx                  # 🚀 Cockpit (02. TERMINAL)
│   │
│   ├── briefings/
│   │   └── page.tsx                  # 📋 Briefings (03. SUPPLY)
│   │
│   ├── watchlist/
│   │   └── page.tsx                  # ⭐ Watchlist (placeholder)
│   │
│   └── settings/
│       └── page.tsx                  # ⚙️ Settings (placeholder)
│
└── api/
    └── x/
        └── route.ts                  # X (Twitter) API endpoint
```

**Absolute Paths**:
- Signal Feed: `/Users/gabriel/Desktop/short_gravity/short-gravity-web/app/(dashboard)/page.tsx`
- Cockpit: `/Users/gabriel/Desktop/short_gravity/short-gravity-web/app/(dashboard)/cockpit/page.tsx`
- Briefings: `/Users/gabriel/Desktop/short_gravity/short-gravity-web/app/(dashboard)/briefings/page.tsx`

---

### 🧩 Components

```
components/
│
├── 🎯 layout/                        # Layout components
│   ├── GlobalHeader.tsx              # Top navigation bar with status ticker
│   ├── Sidebar.tsx                   # Sidebar navigation
│   └── TerminalEffects.tsx           # Scanlines, vignette, grain effects
│
├── 🔔 signals/                       # Signal Feed components
│   ├── SignalFeed.tsx                # Signal list container
│   └── SignalCard.tsx                # Individual signal card
│
├── 🚀 cockpit/                       # Cockpit components
│   └── CockpitCanvas.tsx             # 3D visualization container
│
├── 📋 briefings/                     # Briefing components
│   ├── BriefingList.tsx              # Briefing list container
│   └── BriefingCard.tsx              # Individual briefing card
│
└── 🎨 ui/                            # Base UI components
    ├── Card.tsx                      # Card, CardHeader, CardTitle, CardContent
    └── Badge.tsx                     # Severity badges (critical/high/medium/low)
```

**Absolute Paths**:
- Global Header: `/Users/gabriel/Desktop/short_gravity/short-gravity-web/components/layout/GlobalHeader.tsx`
- Signal Components: `/Users/gabriel/Desktop/short_gravity/short-gravity-web/components/signals/`
- Terminal Effects: `/Users/gabriel/Desktop/short_gravity/short-gravity-web/components/layout/TerminalEffects.tsx`

---

### 📚 Utilities & Helpers

```
lib/
│
├── env.ts                            # 🔐 Type-safe environment variables
│
├── hooks/
│   └── useXApi.ts                    # 🐦 React hook for X API calls
│
├── utils/
│   └── cn.ts                         # 🎨 ClassName merging utility
│
└── mock-data.ts                      # 🎭 Mock data (entities, signals, briefings)
```

**What Each File Does**:

| File | Purpose |
|------|---------|
| `env.ts` | Type-safe access to environment variables (server & client) |
| `useXApi.ts` | Client-side hook for secure X API calls via server route |
| `cn.ts` | Utility to merge Tailwind classes (clsx + tailwind-merge) |
| `mock-data.ts` | Mock entities, signals, briefings, satellites for development |

**Absolute Paths**:
- Environment Config: `/Users/gabriel/Desktop/short_gravity/short-gravity-web/lib/env.ts`
- X API Hook: `/Users/gabriel/Desktop/short_gravity/short-gravity-web/lib/hooks/useXApi.ts`
- Mock Data: `/Users/gabriel/Desktop/short_gravity/short-gravity-web/lib/mock-data.ts`

---

### 📐 Type Definitions

```
types/
└── index.ts                          # All TypeScript types
```

**Defined Types**:
- `EntityType`: 'satellite' | 'company' | 'constellation' | 'ground_station'
- `Entity`: Space entity (satellite, company, etc.)
- `Signal`: Anomaly detection signal with severity
- `Briefing`: AI-generated intelligence report
- `Satellite`: Satellite with orbital parameters
- `OrbitType`: 'LEO' | 'MEO' | 'GEO' | 'HEO' | 'SSO' | 'MOLNIYA'

**Absolute Path**: `/Users/gabriel/Desktop/short_gravity/short-gravity-web/types/index.ts`

---

### 📖 Documentation

```
short-gravity-architecture/          # System architecture docs
├── 00-ARCHITECTURE-OVERVIEW.md      # High-level system design
├── 01-SIGNAL-ENGINE.md              # Anomaly detection logic
├── 02-COCKPIT.md                    # 3D visualization specs
├── 03-BRIEFING.md                   # AI synthesis engine
├── 04-DATA-MODEL.md                 # Database schema
├── 05-API-CONTRACTS.md              # API endpoint specs
├── 06-WEB-FRONTEND.md               # Frontend implementation
├── 07-IOS-APP.md                    # iOS app specs
├── 08-DEPLOYMENT.md                 # DevOps details
└── 09-SECURITY.md                   # Security protocols

design/                               # Design system docs
├── README.md                         # Design system overview
└── 00-shell/
    ├── BUILD_SPEC.md                 # Global header implementation
    └── REFERENCE.md                  # Design references
```

**Absolute Paths**:
- Architecture: `/Users/gabriel/Desktop/short_gravity/short-gravity-architecture/`
- Design: `/Users/gabriel/Desktop/short_gravity/design/`

---

## ✅ Features & Implementation Status

### 🟢 Fully Implemented

| Feature | Location | Description |
|---------|----------|-------------|
| **Signal Feed** | `app/(dashboard)/page.tsx` | Anomaly detection display with severity filtering |
| **Global Header** | `components/layout/GlobalHeader.tsx` | Navigation + status ticker (BTC, GAS, UTC, system) |
| **Terminal Effects** | `components/layout/TerminalEffects.tsx` | Scanlines, vignette, grain overlay |
| **Briefing List** | `app/(dashboard)/briefings/page.tsx` | AI report display with type indicators |
| **Component System** | `components/ui/` | Base UI components (Card, Badge) |
| **Type System** | `types/index.ts` | Complete TypeScript definitions |
| **Mock Data** | `lib/mock-data.ts` | Development data for all features |
| **Environment Config** | `lib/env.ts` | Type-safe env variable access |
| **X API Integration** | `app/api/x/route.ts` + `lib/hooks/useXApi.ts` | Secure server-side X API calls |

### 🟡 Partially Implemented

| Feature | Location | Status |
|---------|----------|--------|
| **Cockpit** | `app/(dashboard)/cockpit/page.tsx` | UI structure ready, needs Three.js integration |
| **Watchlist** | `app/(dashboard)/watchlist/page.tsx` | Route created, needs data binding |
| **Settings** | `app/(dashboard)/settings/page.tsx` | Route created, needs feature implementation |

### 🔴 Not Yet Implemented

- Supabase integration (database, realtime)
- Three.js orbital visualization
- Claude AI briefing generation
- Space-Track.org TLE ingestion
- User authentication
- iOS app

---

## 🔄 Data Flow Architecture

### Current (Mock Data Flow)
```
┌─────────────────────────────────────────────┐
│         React Components (Client)            │
│  ┌─────────────────────────────────────┐    │
│  │  Signal Feed / Briefings / Cockpit  │    │
│  └──────────────┬──────────────────────┘    │
│                 │                            │
│                 ▼                            │
│       lib/mock-data.ts                       │
│       - getRecentSignals()                   │
│       - getUnreadBriefings()                 │
└─────────────────────────────────────────────┘
```

### Planned (Production Flow)
```
┌──────────────────────────────────────────────────────┐
│              Browser (Client Components)              │
│  ┌────────────────────────────────────────────────┐  │
│  │ Signal Feed / Briefings / Cockpit              │  │
│  │ - Uses React Query for data fetching           │  │
│  │ - Uses Zustand for global state                │  │
│  └───────────────────┬────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
                       │ fetch('/api/...')
                       ▼
┌──────────────────────────────────────────────────────┐
│           Next.js API Routes (Server)                 │
│  ┌────────────────────────────────────────────────┐  │
│  │ /api/signals - Fetch anomaly signals           │  │
│  │ /api/briefings - Fetch/generate briefings      │  │
│  │ /api/satellites - Fetch satellite data         │  │
│  │ /api/x - X (Twitter) API integration           │  │
│  └───────────────────┬────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│                  Supabase Backend                     │
│  ┌────────────────────────────────────────────────┐  │
│  │ PostgreSQL Database                             │  │
│  │ - entities, signals, briefings, satellites      │  │
│  │                                                  │  │
│  │ Realtime Subscriptions                          │  │
│  │ - Live updates for new signals/briefings        │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│               External APIs                           │
│  - Space-Track.org (TLE data)                        │
│  - Claude AI (briefing generation)                   │
│  - X API (social sharing)                            │
└──────────────────────────────────────────────────────┘
```

### X API Security Flow
```
Browser Component
    ↓
useXApi() hook (client-side)
    ↓ fetch('/api/x')
/api/x route (server-side)
    ↓ uses serverEnv.x.apiKey()
X (Twitter) API
```

**Why?** Keeps API credentials secure on server, never exposed to browser.

---

## 🎨 Design System

### Color Palette
```css
/* Core Colors */
--background: #0A0A0A;        /* Deep black */
--accent: #F97316;            /* Orange - primary accent */
--data: #3B82F6;              /* Blue - data/time */
--system: #22C55E;            /* Green - system status */

/* Text */
--text-primary: #FFFFFF;
--text-secondary: #888888;
--text-tertiary: #666666;

/* Severity Colors */
--critical: #EF4444;          /* Red */
--high: #FB923C;              /* Orange */
--medium: #FBBF24;            /* Yellow */
--low: #60A5FA;               /* Blue */
```

### Typography
```
Logo/Data: JetBrains Mono (400, 500, 700)
Navigation: Geist Sans 500 Medium
Body: Geist Sans 400 Regular
```

### Component Hierarchy
```
GlobalHeader (fixed top)
    ↓
Dashboard Layout
    ↓
┌─────────────┬──────────────────────────┐
│  Sidebar    │  Main Content Area       │
│             │  - Signal Feed           │
│             │  - Cockpit               │
│             │  - Briefings             │
│             │  - Watchlist             │
│             │  - Settings              │
└─────────────┴──────────────────────────┘
    ↓
TerminalEffects (overlay)
```

### Terminal Effects
- **Scanline**: 2px white line, 8s animation, 2% opacity
- **Vignette**: Radial gradient from center
- **Grain**: 5% opacity noise texture

---

## 🔑 Key Architectural Decisions

1. **Next.js App Router**: Modern routing with server components
2. **Monorepo Structure**: Root-level shared code + main app
3. **Type-First Development**: Comprehensive TypeScript types
4. **Component Isolation**: Each feature has its own components directory
5. **Mock Data First**: Development without backend dependency
6. **Environment Security**: Server-side secrets, type-safe access
7. **Terminal Aesthetic**: CRT effects, monospace fonts, dark theme

---

## 🚀 Next Implementation Steps

Based on the current state, here's the logical order for building features:

1. **Supabase Integration** (highest priority)
   - Set up database schema from `04-DATA-MODEL.md`
   - Replace mock data with real queries
   - Add realtime subscriptions

2. **Three.js Cockpit** (visual impact)
   - Integrate Three.js for 3D Earth globe
   - Render satellite positions
   - Add orbital path visualization

3. **Claude AI Integration** (intelligence layer)
   - Implement briefing generation
   - Add signal analysis
   - Create summary reports

4. **Space-Track Integration** (real data)
   - Fetch TLE data
   - Update satellite positions
   - Track orbital parameters

5. **User Authentication** (production readiness)
   - Add Supabase Auth
   - Implement user sessions
   - Add per-user watchlists

---

## 📞 Questions While Working?

**Need to find something?**
- Components: `short-gravity-web/components/`
- Pages: `short-gravity-web/app/(dashboard)/`
- Types: `short-gravity-web/types/index.ts`
- Mock Data: `short-gravity-web/lib/mock-data.ts`

**Need to understand how something works?**
- Architecture: `short-gravity-architecture/`
- Design System: `design/`
- Environment Setup: `ENV_SETUP_GUIDE.md`

**Need to add a new feature?**
1. Define types in `types/index.ts`
2. Create components in `components/[feature]/`
3. Add page in `app/(dashboard)/[feature]/page.tsx`
4. Add mock data in `lib/mock-data.ts` (if needed)
5. Update this map!

---

**Last Updated**: January 21, 2026
**Maintainer**: Keep this document updated as architecture evolves!
