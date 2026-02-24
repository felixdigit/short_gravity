TARGET: apps/web
---
MISSION:
Replace the ClearanceModal stub with a functional component, and fix all dead navigation links across the app to prevent users hitting 404s.

DIRECTIVES:

## 1. Replace ClearanceModal stub

File: `src/components/hud/overlays/ClearanceModal.tsx`

Read the archive version at `../../_ARCHIVE_V1/short-gravity-web/components/hud/overlays/ClearanceModal.tsx` (or search for ClearanceModal in the archive).

The ClearanceModal is a tier comparison / upgrade prompt that shows:
- Current tier (free vs full_spectrum)
- Feature comparison between tiers
- CTA to upgrade via Patreon
- Discord invite link

Replace the stub with a functional implementation. If the archive version is complex, build a clean minimal version:

```tsx
'use client'

import { useEffect } from 'react'

interface ClearanceModalProps {
  open: boolean
  onClose: () => void
}

export function ClearanceModal({ open, onClose }: ClearanceModalProps) {
  // Close on Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) onClose()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 bg-[#0a0f14]/95 border border-white/[0.08] rounded-xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
          <h2 className="text-sm font-mono text-white/70 tracking-wider">CLEARANCE LEVEL</h2>
          <button
            onClick={onClose}
            className="text-white/30 hover:text-white/50 transition-colors text-lg"
          >
            &times;
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-6 space-y-6">
          {/* Current tier */}
          <div className="text-center">
            <div className="text-[10px] text-white/30 tracking-widest mb-1">CURRENT TIER</div>
            <div className="text-lg font-mono text-white/60">FREE</div>
          </div>

          {/* Tier comparison */}
          <div className="grid grid-cols-2 gap-4">
            <div className="border border-white/[0.06] rounded-lg p-4">
              <div className="text-[11px] font-mono text-white/40 mb-3">FREE</div>
              <ul className="space-y-2 text-[11px] text-white/50">
                <li>Live constellation tracking</li>
                <li>Public filings feed</li>
                <li>Basic orbital data</li>
                <li>Signal feed (delayed)</li>
              </ul>
            </div>
            <div className="border border-[#FF6B35]/20 rounded-lg p-4 bg-[#FF6B35]/[0.03]">
              <div className="text-[11px] font-mono text-[#FF6B35] mb-3">FULL SPECTRUM</div>
              <ul className="space-y-2 text-[11px] text-white/70">
                <li>Everything in Free</li>
                <li>Brain AI search (13K+ docs)</li>
                <li>Real-time signal alerts</li>
                <li>Daily intelligence briefing</li>
                <li>Drag analysis & alerts</li>
                <li>Source divergence tracking</li>
              </ul>
            </div>
          </div>

          {/* CTAs */}
          <div className="space-y-3">
            <a
              href="https://www.patreon.com/shortgravity"
              target="_blank"
              rel="noopener noreferrer"
              className="block w-full text-center py-3 bg-[#FF6B35]/10 border border-[#FF6B35]/30 rounded-lg text-sm font-mono text-[#FF6B35] hover:bg-[#FF6B35]/20 transition-colors"
            >
              UPGRADE ON PATREON
            </a>
            {process.env.NEXT_PUBLIC_DISCORD_INVITE_URL && (
              <a
                href={process.env.NEXT_PUBLIC_DISCORD_INVITE_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="block w-full text-center py-2.5 border border-white/[0.06] rounded-lg text-[11px] font-mono text-white/40 hover:text-white/60 transition-colors"
              >
                JOIN DISCORD
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
```

IMPORTANT: Check how the ClearanceModal is currently mounted. Read `src/app/layout.tsx` or search for `<ClearanceModal` to see where it's rendered and what props it receives. Match the props interface. It likely receives `open` and `onClose` from the terminal store:
```tsx
<ClearanceModal
  open={store.clearanceModalOpen}
  onClose={() => store.setClearanceModalOpen(false)}
/>
```

## 2. Fix dead navigation links

Multiple components link to pages that don't exist. Fix them to prevent users hitting 404s.

### Strategy: For pages that don't exist yet, either:
- Remove the link entirely
- Change to a non-clickable "coming soon" state
- Redirect to the closest existing page

### Files to fix:

**Landing page: `src/app/page.tsx`**

Read the file and find the navigation grid. For each link, check if the target page exists:
- `/asts` → EXISTS ✓
- `/signals` → EXISTS ✓
- `/orbital` → EXISTS ✓
- `/briefing` → MISSING — change link to `/signals` or disable
- `/horizon` → MISSING — change link to `/orbital` or disable
- `/thesis` → MISSING — disable
- `/patents` → MISSING — disable
- `/research` → MISSING — disable (or link to `/asts` with brain open)
- `/competitive` → MISSING — disable
- `/earnings` → MISSING — disable
- `/regulatory` → MISSING — change to `/orbital` or disable
- `/login` → MISSING — disable

For disabled links, change them to non-clickable elements:
```tsx
// Instead of: <a href="/patents">PATENTS</a>
// Use: <span className="text-white/20 cursor-default">PATENTS <span className="text-[9px]">SOON</span></span>
```

**Sidebar: `src/components/frame/Sidebar.tsx`**

Same approach — disable links to non-existent pages. Keep working links to /asts, /signals, /orbital.

**Widget links:**

Check these widgets for broken "VIEW ALL" or detail links:
- `src/components/hud/widgets/EarningsLedger.tsx` — if it links to `/earnings`, disable or remove
- `src/components/hud/widgets/RegulatoryStatus.tsx` — if it links to `/regulatory`, disable or change to `/orbital`
- `src/components/hud/widgets/NextEvent.tsx` — if it links to `/horizon`, disable or change to `/orbital`
- `src/components/hud/widgets/LaunchCountdown.tsx` — if it links to `/horizon`, disable or change to `/orbital`
- `src/components/hud/widgets/SignalFeed.tsx` — links to `/signals` → EXISTS ✓

For each widget link pointing to a missing page, either:
- Remove the link
- Replace with "#" and add `cursor-default text-white/20` styling
- Or redirect to the closest working page

## 3. Run `npx tsc --noEmit`
