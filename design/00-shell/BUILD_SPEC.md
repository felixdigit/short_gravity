# 00. THE SHELL (Global HUD) // BUILD SPEC

**The Logic:** This is not a "Header." It is the frame of the monitor. It stays fixed at the top (z-index: 999) while the content scrolls behind it.

## 1. The Container (The Glass)

- **Position:** Fixed (Top: 0, Left: 0, Right: 0)
- **Height:** 48px (Keep it tight. 64px is too "web 2.0")
- **Background:** #0A0A0A at 85% Opacity + Backdrop Blur (12px)
- **Effect:** When you scroll past text, it blurs out behind the header like a frosted cockpit glass
- **Border:** Bottom border only. 1px solid #1F1F1F

## 2. The Logo (Top Left)

- **Font:** JetBrains Mono (700 Bold)
- **Text:** `[ SHORT GRAVITY ]` (Include the brackets)
- **Size:** 14px
- **Tracking (Letter Spacing):** -0.02em (Tight)
- **Color:** #FFFFFF
- **Interaction:** On hover, the brackets turn Neon Orange (#F97316)

## 3. The Navigation (Center)

**Style:** These are "Tabs," not links

- **Font:** Inter or Geist Sans (500 Medium)
- **Size:** 13px
- **Text Transform:** Uppercase
- **Spacing:** 32px gap between items

**Items:**
- // 01 INTEL
- // 02 TERMINAL
- // 03 SUPPLY

**Active State:** Text is White (#FFF). A small glowing dot • appears below the active tab
**Inactive State:** Text is Grey (#666)

## 4. The Status Ticker (Top Right)

**Vibe:** Financial Telemetry

- **Font:** JetBrains Mono
- **Size:** 11px (Micro-text)
- **Layout:** Flex row, gap 16px

**Data Points:**
- `BTC: $97,420` (Color: #FFF)
- `GAS: 12 GWEI` (Color: #888)
- `UTC: 14:05:22 Z` (Color: #3B82F6 - Make this clock tick)

**Decorator:** Add a small flashing green circle 🟢 (4px size) at the far right. Label it `SYS.ONLINE`

---

## The "Extra" Polish (The Texture)

### 1. The Scanline (CSS Animation)

Create a div that covers the entire screen (pointer-events: none)

- **Visual:** A horizontal line, 2px height, white color, 2% opacity
- **Animation:** It travels from top: 0 to top: 100vh every 8 seconds. Loop infinite
- **Why:** It creates that subtle "refresh rate" flicker

### 2. The Vignette

Add a radial-gradient overlay on the corners of the screen

- **Code:** `background: radial-gradient(circle, transparent 70%, rgba(0,0,0,0.6) 100%);`
- **Why:** It darkens the edges, forcing the eye to the center

---

## Mobile Adaptation (The "Mobile HUD")

- **Top Bar:** Shrinks to 44px
- **Right Ticker:** Hide everything except the SYS.ONLINE dot
- **Navigation:** Move to a bottom bar (thumb zone) or a "hamburger" menu that opens a full-screen terminal list
- **Recommendation:** Bottom Bar is more "App-like"
