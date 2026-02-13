# Thread 001: Signal-to-Source — GAP 5

## CLAUDE (turn 1) — THE TRACE

Thread 001 continuation. GAP 1 (signal evidence → DocumentViewer) is closed. The primary path works. Now closing the secondary path: brain search citations.

### The GAP

Brain search citations across the platform don't open DocumentViewer. Two manifestations:

**On /signals page:** Brain search panel renders sources as plain text:
```tsx
{lastAssistant.sources.slice(0, 5).map((src, i) => (
  <Text key={i} variant="dim" size="xs" className="text-white/15 py-0.5">
    [{src.source}] {src.title || src.source}
  </Text>
))}
```
No click handler. No Citation component. Just text.

**In ChatMessage (full brain panel):** Uses `Citation` component, which wraps in `<a href={result.url}>` if URL exists, otherwise renders a static non-clickable card. Most internal documents (filings, patents, FCC docs) DON'T have external URLs — so most citations are dead ends.

### What exists

- `SearchResult` has `source` (type: 'filing', 'patent', 'fcc_filing', etc.) and `id` (natural key: accession_number, patent_number, file_number)
- DocumentViewer accepts `sourceTable` + `sourceRef` (built in GAP 1)
- Citation component has the data it needs but doesn't use it for internal navigation

### Source type → table mapping needed

```
'filing'              → 'filings'
'patent'              → 'patents'
'patent_claim'        → 'patents' (strip claim suffix from id)
'fcc_filing'          → 'fcc_filings'
'press_release'       → 'press_releases'
'x_post'              → 'x_posts'
'earnings_transcript' → 'earnings_transcripts'
'signal'              → 'signals'
'glossary'            → null (no document to view)
'cash_position'       → null
'short_interest'      → null
```

### What I need from you

1. Should Citation trigger DocumentViewer directly (managing its own state), or should it call a callback prop that the parent manages? The parent could be ChatMessage, BrainSearch overlay, or the /signals page brain panel — three different contexts.

2. Should the /signals page brain panel use the full Citation component grid, or keep the compact text format with click-through? Space is tight in that panel.

3. Any other considerations for this transition?

## GEMINI (turn 1)

Recommended: Lift state via `onSelect` callback on Citation. Parent components manage DocumentViewer state. Add a `getDocumentViewerParams()` utility to map SearchResult source types to table names. /signals page gets compact inline citation links. ChatMessage gets full Citation cards with onSelect.

## Implementation Note (Claude)

Simplifying Gemini's spec — no new Zustand store, no InlineCitationLink component. Citation gets `onSelect` prop. Parents use local `useState` for DocumentViewer. Utility function lives in `lib/brain/search.ts` alongside existing types.
