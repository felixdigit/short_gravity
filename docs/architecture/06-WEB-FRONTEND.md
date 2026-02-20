# Web Frontend Architecture

**Platform:** Web Terminal (Mission Control)  
**Framework:** Next.js 14+ (App Router)  
**Version:** 1.0

---

## Overview

The Web Terminal is the full-fidelity desktop experience for deep research, wide-screen orbital visualization, and comprehensive dashboards. Built with Next.js App Router for SSR, API routes, and optimal performance.

---

## Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Framework | Next.js (App Router) | 14.x |
| UI Library | React | 18.x |
| Styling | Tailwind CSS | 3.x |
| State | Zustand + TanStack Query | 4.x / 5.x |
| 3D Rendering | Three.js + React Three Fiber | 0.160+ |
| Charts | Recharts | 2.x |
| Auth | Supabase Auth | Latest |
| Realtime | Supabase Realtime | Latest |

---

## Project Structure

```
short-gravity-web/
├── app/
│   ├── (auth)/
│   │   ├── login/
│   │   │   └── page.tsx
│   │   ├── signup/
│   │   │   └── page.tsx
│   │   └── layout.tsx
│   │
│   ├── (dashboard)/
│   │   ├── layout.tsx              # Dashboard shell with sidebar
│   │   ├── page.tsx                # Home / Signal Feed
│   │   ├── cockpit/
│   │   │   └── page.tsx            # 3D Orbital View
│   │   ├── entities/
│   │   │   ├── page.tsx            # Entity List
│   │   │   └── [slug]/
│   │   │       └── page.tsx        # Entity Detail
│   │   ├── briefings/
│   │   │   ├── page.tsx            # Briefing List
│   │   │   └── [id]/
│   │   │       └── page.tsx        # Briefing Detail
│   │   ├── watchlist/
│   │   │   └── page.tsx            # User Watchlist
│   │   └── settings/
│   │       └── page.tsx            # User Preferences
│   │
│   ├── api/
│   │   └── [...] (if needed)
│   │
│   ├── layout.tsx                  # Root layout
│   ├── globals.css
│   └── providers.tsx               # Client providers
│
├── components/
│   ├── ui/                         # Primitive UI components
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Input.tsx
│   │   ├── Badge.tsx
│   │   └── ...
│   │
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   ├── MobileNav.tsx
│   │   └── CommandPalette.tsx      # Cmd+K search
│   │
│   ├── cockpit/                    # 3D visualization components
│   │   ├── CockpitCanvas.tsx
│   │   ├── Earth.tsx
│   │   ├── SatelliteMarker.tsx
│   │   ├── OrbitLine.tsx
│   │   ├── CoverageCone.tsx
│   │   ├── TimeControls.tsx
│   │   └── CockpitControls.tsx
│   │
│   ├── signals/
│   │   ├── SignalFeed.tsx
│   │   ├── SignalCard.tsx
│   │   └── SignalFilters.tsx
│   │
│   ├── briefings/
│   │   ├── BriefingCard.tsx
│   │   ├── BriefingReader.tsx
│   │   └── GenerateBriefingButton.tsx
│   │
│   ├── entities/
│   │   ├── EntityCard.tsx
│   │   ├── EntitySearch.tsx
│   │   ├── SatelliteDetail.tsx
│   │   └── CompanyDetail.tsx
│   │
│   └── watchlist/
│       ├── WatchlistTable.tsx
│       └── AddToWatchlistButton.tsx
│
├── lib/
│   ├── supabase/
│   │   ├── client.ts               # Browser client
│   │   ├── server.ts               # Server client
│   │   └── middleware.ts           # Auth middleware
│   │
│   ├── api/                        # API wrapper functions
│   │   ├── entities.ts
│   │   ├── signals.ts
│   │   ├── briefings.ts
│   │   ├── watchlist.ts
│   │   └── orbital.ts
│   │
│   ├── orbital/                    # Orbital mechanics
│   │   ├── propagate.ts
│   │   ├── coverage.ts
│   │   └── los.ts
│   │
│   ├── claude/                     # AI integration (if client-side)
│   │   └── client.ts
│   │
│   └── utils/
│       ├── formatting.ts
│       └── date.ts
│
├── hooks/
│   ├── useSignals.ts
│   ├── useBriefings.ts
│   ├── useWatchlist.ts
│   ├── useEntity.ts
│   ├── useCockpitTime.ts
│   └── useRealtime.ts
│
├── stores/
│   ├── cockpit.ts                  # Cockpit UI state (Zustand)
│   └── ui.ts                       # Global UI state
│
├── types/
│   └── index.ts                    # Shared TypeScript types
│
├── public/
│   ├── textures/                   # Earth textures for 3D
│   │   ├── earth_day.jpg
│   │   ├── earth_night.jpg
│   │   └── ...
│   └── ...
│
├── middleware.ts                   # Auth redirect middleware
├── next.config.js
├── tailwind.config.js
├── tsconfig.json
└── package.json
```

---

## Key Pages

### Home / Signal Feed (`app/(dashboard)/page.tsx`)

Primary dashboard showing real-time signal feed with filters.

```tsx
// app/(dashboard)/page.tsx
import { SignalFeed } from '@/components/signals/SignalFeed';
import { SignalFilters } from '@/components/signals/SignalFilters';
import { WatchlistSummary } from '@/components/watchlist/WatchlistSummary';

export default function HomePage() {
  return (
    <div className="grid grid-cols-12 gap-6">
      {/* Main feed */}
      <div className="col-span-8">
        <SignalFilters />
        <SignalFeed />
      </div>
      
      {/* Sidebar */}
      <div className="col-span-4">
        <WatchlistSummary />
        <RecentBriefings />
      </div>
    </div>
  );
}
```

### Cockpit (`app/(dashboard)/cockpit/page.tsx`)

Full-screen 3D orbital visualization.

```tsx
// app/(dashboard)/cockpit/page.tsx
'use client';

import { Suspense } from 'react';
import { CockpitCanvas } from '@/components/cockpit/CockpitCanvas';
import { CockpitControls } from '@/components/cockpit/CockpitControls';
import { TimeControls } from '@/components/cockpit/TimeControls';
import { SatellitePanel } from '@/components/cockpit/SatellitePanel';

export default function CockpitPage() {
  return (
    <div className="h-[calc(100vh-64px)] relative">
      {/* 3D Canvas */}
      <Suspense fallback={<CockpitLoader />}>
        <CockpitCanvas />
      </Suspense>
      
      {/* Overlay controls */}
      <div className="absolute top-4 left-4">
        <CockpitControls />
      </div>
      
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2">
        <TimeControls />
      </div>
      
      {/* Right panel */}
      <div className="absolute top-4 right-4 w-80">
        <SatellitePanel />
      </div>
    </div>
  );
}
```

### Entity Detail (`app/(dashboard)/entities/[slug]/page.tsx`)

```tsx
// app/(dashboard)/entities/[slug]/page.tsx
import { notFound } from 'next/navigation';
import { createServerClient } from '@/lib/supabase/server';
import { SatelliteDetail } from '@/components/entities/SatelliteDetail';
import { CompanyDetail } from '@/components/entities/CompanyDetail';

export default async function EntityPage({ 
  params 
}: { 
  params: { slug: string } 
}) {
  const supabase = createServerClient();
  
  const { data: entity, error } = await supabase
    .from('entities')
    .select(`*, satellites(*), companies(*), signals(*)`)
    .eq('slug', params.slug)
    .single();
  
  if (error || !entity) {
    notFound();
  }
  
  return (
    <div>
      {entity.type === 'satellite' && <SatelliteDetail entity={entity} />}
      {entity.type === 'company' && <CompanyDetail entity={entity} />}
    </div>
  );
}
```

---

## State Management

### Zustand Store (Cockpit UI State)

```typescript
// stores/cockpit.ts
import { create } from 'zustand';

interface CockpitState {
  // Time
  currentTime: Date;
  playbackSpeed: number;
  isPaused: boolean;
  mode: 'realtime' | 'historical' | 'future';
  
  // Selection
  selectedSatelliteIds: string[];
  hoveredSatelliteId: string | null;
  
  // Display options
  showOrbits: boolean;
  showCoverage: boolean;
  showLabels: boolean;
  showGroundTrack: boolean;
  
  // Actions
  setCurrentTime: (time: Date) => void;
  setPlaybackSpeed: (speed: number) => void;
  togglePause: () => void;
  selectSatellite: (id: string) => void;
  deselectSatellite: (id: string) => void;
  clearSelection: () => void;
  setHoveredSatellite: (id: string | null) => void;
  toggleOrbits: () => void;
  toggleCoverage: () => void;
}

export const useCockpitStore = create<CockpitState>((set) => ({
  currentTime: new Date(),
  playbackSpeed: 1,
  isPaused: false,
  mode: 'realtime',
  selectedSatelliteIds: [],
  hoveredSatelliteId: null,
  showOrbits: true,
  showCoverage: false,
  showLabels: true,
  showGroundTrack: false,
  
  setCurrentTime: (time) => set({ currentTime: time }),
  setPlaybackSpeed: (speed) => set({ playbackSpeed: speed }),
  togglePause: () => set((state) => ({ isPaused: !state.isPaused })),
  selectSatellite: (id) => set((state) => ({
    selectedSatelliteIds: [...state.selectedSatelliteIds, id],
  })),
  deselectSatellite: (id) => set((state) => ({
    selectedSatelliteIds: state.selectedSatelliteIds.filter((s) => s !== id),
  })),
  clearSelection: () => set({ selectedSatelliteIds: [] }),
  setHoveredSatellite: (id) => set({ hoveredSatelliteId: id }),
  toggleOrbits: () => set((state) => ({ showOrbits: !state.showOrbits })),
  toggleCoverage: () => set((state) => ({ showCoverage: !state.showCoverage })),
}));
```

### TanStack Query (Server State)

```typescript
// hooks/useSignals.ts
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase/client';
import { useEffect } from 'react';

export function useSignals(entityIds?: string[]) {
  const queryClient = useQueryClient();
  
  // Fetch signals
  const query = useQuery({
    queryKey: ['signals', entityIds],
    queryFn: async () => {
      let q = supabase
        .from('signals')
        .select('*')
        .order('detected_at', { ascending: false })
        .limit(50);
      
      if (entityIds?.length) {
        q = q.in('entity_id', entityIds);
      }
      
      const { data, error } = await q;
      if (error) throw error;
      return data;
    },
  });
  
  // Real-time subscription
  useEffect(() => {
    const channel = supabase
      .channel('signals-realtime')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'signals' },
        (payload) => {
          // Optimistically add to cache
          queryClient.setQueryData(['signals', entityIds], (old: any) => {
            return old ? [payload.new, ...old] : [payload.new];
          });
        }
      )
      .subscribe();
    
    return () => {
      supabase.removeChannel(channel);
    };
  }, [entityIds, queryClient]);
  
  return query;
}
```

---

## Authentication

### Middleware

```typescript
// middleware.ts
import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs';
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export async function middleware(req: NextRequest) {
  const res = NextResponse.next();
  const supabase = createMiddlewareClient({ req, res });
  
  const {
    data: { session },
  } = await supabase.auth.getSession();
  
  // Protect dashboard routes
  if (req.nextUrl.pathname.startsWith('/(dashboard)') && !session) {
    return NextResponse.redirect(new URL('/login', req.url));
  }
  
  // Redirect authenticated users away from auth pages
  if (req.nextUrl.pathname.startsWith('/(auth)') && session) {
    return NextResponse.redirect(new URL('/', req.url));
  }
  
  return res;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
```

### Supabase Clients

```typescript
// lib/supabase/client.ts
import { createBrowserClient } from '@supabase/ssr';

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}

export const supabase = createClient();
```

```typescript
// lib/supabase/server.ts
import { createServerClient as createSSRClient } from '@supabase/ssr';
import { cookies } from 'next/headers';

export function createServerClient() {
  const cookieStore = cookies();
  
  return createSSRClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          return cookieStore.get(name)?.value;
        },
      },
    }
  );
}
```

---

## Responsive Design

The Web Terminal adapts to screen sizes:

| Breakpoint | Layout |
|------------|--------|
| Desktop (1280px+) | Full sidebar, wide cockpit, multi-column |
| Tablet (768-1279px) | Collapsible sidebar, stacked panels |
| Mobile (<768px) | Bottom nav, single column, simplified cockpit |

```tsx
// components/layout/DashboardLayout.tsx
export function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-950">
      {/* Desktop sidebar */}
      <aside className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
        <Sidebar />
      </aside>
      
      {/* Mobile header */}
      <div className="lg:hidden sticky top-0 z-40">
        <MobileHeader />
      </div>
      
      {/* Main content */}
      <main className="lg:pl-64">
        <div className="px-4 py-6 lg:px-8">
          {children}
        </div>
      </main>
      
      {/* Mobile bottom nav */}
      <nav className="lg:hidden fixed bottom-0 inset-x-0">
        <MobileNav />
      </nav>
    </div>
  );
}
```

---

## Performance Optimization

1. **3D Rendering**
   - Use `frameloop="demand"` when cockpit is idle
   - Instanced meshes for large constellations
   - LOD (Level of Detail) for distant satellites
   - Web Worker for orbital propagation

2. **Data Fetching**
   - TanStack Query for caching and deduplication
   - Infinite scroll for signal feed
   - Prefetch entity data on hover

3. **Bundle Size**
   - Dynamic imports for cockpit (`next/dynamic`)
   - Tree-shaking unused Three.js features
   - Image optimization via `next/image`

```tsx
// Dynamic import for cockpit
import dynamic from 'next/dynamic';

const CockpitCanvas = dynamic(
  () => import('@/components/cockpit/CockpitCanvas'),
  { 
    ssr: false,
    loading: () => <CockpitLoader />,
  }
);
```

---

## Environment Variables

```env
# .env.local
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

---

## Deployment

- **Platform:** Vercel
- **Build:** `next build`
- **Preview:** Automatic for PRs
- **Production:** Auto-deploy from `main` branch

```json
// vercel.json
{
  "framework": "nextjs",
  "regions": ["iad1"],
  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        { "key": "Cache-Control", "value": "no-store" }
      ]
    }
  ]
}
```
