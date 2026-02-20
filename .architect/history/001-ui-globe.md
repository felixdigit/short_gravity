TARGET: packages/ui
---
MISSION:
Replace the "3D Globe not yet wired" grey stub in `src/components/Globe.tsx` with a structural 3D WebGL implementation.

DIRECTIVES:
1. Run package manager commands to install dependencies strictly inside your package: `pnpm add three @react-three/fiber` and `pnpm add -D @types/three`.
2. Update `Globe.tsx` to render a `<Canvas>` from `@react-three/fiber`.
3. Inside the canvas, render a 3D `<mesh>` sphere to represent Earth. Give it a basic wireframe material (`wireframe={true}`) matching our dark theme (e.g., `#3b82f6`).
4. Add a slow auto-rotation to the mesh using `useFrame`.
5. Define a generic interface inside the file: `export interface GlobeSignal { id: string; lat: number; lng: number; severity: string; }`. The component should accept an optional `signals?: GlobeSignal[]` prop.
6. Display a pure HTML/Tailwind overlay absolutely positioned over the canvas showing `{signals?.length || 0} ACTIVE TRACKS`.
7. DO NOT fetch data. DO NOT map to `@shortgravity/core` types. Follow your Microkernel rules.
