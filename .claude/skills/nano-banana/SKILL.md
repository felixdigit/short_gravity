---
name: nano-banana
description: Generate Gemini image prompts for Short Gravity visual assets
user-invocable: true
allowed-tools: Read, Write
---

# Nano Banana Prompt Generator

Generate professional image prompts optimized for Gemini (Nano Banana) image generation.

## Reference

Full guide: `design/NANO_BANANA_GUIDE.md`

## Prompt Formula

```
Subject + Action + Environment + Art Style + Lighting + Details
```

## Short Gravity Style Defaults

Apply these unless user specifies otherwise:

### Colors
- Background: Deep black (#0A0A0A)
- Primary accent: Cyan (#06B6D4)
- Secondary accent: Orange (#F97316)
- Text: White (#FFFFFF)

### Aesthetics
- Bloomberg terminal density
- Monospace typography (JetBrains Mono style)
- Technical/aerospace engineering feel
- Dark mode only
- Subtle CRT scanlines (optional)
- Cyan glow on active elements
- Orange highlights on selected/important elements

## Aspect Ratios

| Ratio | Pixels | Use |
|-------|--------|-----|
| 1:1 | 1024x1024 | Social icons |
| 16:9 | 1536x864 | Dashboard, widescreen |
| 9:16 | 864x1536 | Mobile/vertical |
| 5:2 | ~1536x614 | Wide banners |
| 21:9 | 1536x672 | Ultrawide cinematic |

## Input Options

User provides:
- **Subject**: What to generate (dashboard, satellite, banner, etc.)
- **Aspect ratio**: Required dimension
- **Reference images**: Optional style/content references
- **Context**: What it's for (X header, website banner, UI mockup)

## Output

Return a complete, copy-paste ready prompt formatted as:

```
[ASPECT: ratio]

[Detailed prompt following the formula]

Context: [What this image is for]
```

## Best Practices

1. **Be hyper-specific** — "cyan #06B6D4" not "blue"
2. **Describe scenes** — Not keyword soup
3. **Use photographic language** — Lens, angle, lighting terms
4. **Numbered lists** for complex compositions
5. **Positive framing** — Describe what you want, not what to avoid

## Multi-Image Composites

When user provides reference images:
- Describe how to blend/combine them
- Specify which elements to extract from each
- Define the final composition layout
