TARGET: apps/web
---
MISSION:
Wire the new 3D `<Globe>` from `@shortgravity/ui` into the dashboard using an Anti-Corruption Layer (ACL).

DIRECTIVES:
1. Create a new Client Component at `src/components/dashboard/GlobeWidget.tsx` (must have `"use client";` at the top).
2. Import `useSignals` from `@/hooks/useSignals`.
3. Import `dynamic` from `next/dynamic`.
4. Dynamically import the `Globe` component from `@shortgravity/ui` with SSR disabled to prevent WebGL server errors:
   `const Globe = dynamic(() => import('@shortgravity/ui').then(mod => mod.Globe as any), { ssr: false });`
5. Inside `GlobeWidget`, call `useSignals()` to get the `data` array.
6. Translate the signals into the generic array expected by the Globe. Since our mock API doesn't have lat/lng yet, generate random coordinates: `{ id: signal.id, lat: (Math.random() - 0.5) * 180, lng: (Math.random() - 0.5) * 360, severity: signal.signal_type }`.
7. Render `<Globe signals={translatedSignals} />` (return null or a skeleton if `!data`).
8. Update `src/app/page.tsx`: Remove the direct import of `Globe` from `@shortgravity/ui`. Import your new `GlobeWidget` and replace the `<Globe />` instance in the main grid with `<GlobeWidget />`.
