---
name: write-article
description: Write long-form article in Short Gravity voice for web/X
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, WebFetch, WebSearch
---

# Write Article

Generate a long-form article in the Short Gravity voice.

## Voice & Style Guide

### Tone
- **Conviction without arrogance** — You have a thesis, you believe it, you explain why
- **Historical grounding** — Connect present to past (GPS/Desert Storm, spectrum/Manhattan)
- **Physics-first thinking** — Ground arguments in physical constraints, not hype
- **Investor lens** — Everything ties back to why this matters for capital allocation

### Structure Pattern
1. **Hook** — Provocative claim or counterintuitive framing (1-2 paragraphs)
2. **Historical anchor** — Story from the past that illuminates the present
3. **The shift** — What changed, what's different now
4. **The thesis** — Your actual argument, clearly stated
5. **Evidence layers** — Technical, regulatory, competitive moats
6. **The verdict** — Conviction statement, position disclosure

### Signature Phrases
- "History doesn't repeat. It rhymes."
- "[X] stopped being a gadget. It became Oxygen."
- "This is not [incremental thing]. This is [transformative thing]."
- "I am not betting on [surface-level]. I am betting on [deeper truth]."
- "Long [Theme]. Long [Theme]. Long $[TICKER]."

### Formatting
- Short paragraphs (1-3 sentences max)
- Bold section headers
- Occasional italics for emphasis
- Pull quotes for key statements
- No bullet lists in narrative sections (save for technical specs)

### What to Avoid
- Hedging language ("might," "could potentially")
- Generic tech optimism
- Competitor bashing
- Price targets or specific financial projections
- Disclaimers mid-article (save for end)

## Input

The user will provide:
- Topic/thesis to explore
- Key facts, data points, or research context
- Optional: specific angle or hook

## Output

Write a complete article (1500-2500 words) following the structure above.

End with:
```
---
*Disclosure: Short Gravity Capital is long [TICKER].*
*This article is for informational purposes only and does not constitute investment advice.*
```

## Example Reference

See these published pieces for voice calibration:
- "Why Physics Favors the Landlord of the Sky" (GPS/ASTS thesis)
- "The Race to Put Datacenters in Orbit Has a Quiet Leader" (Orbital computing)
