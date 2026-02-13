# Thread 003: Thesis Builder — GAP 1 (DARK → BROKEN)

## TRACE

Thread 003 is DARK — zero surface area for the user intent: "I have a theory about ASTS. Is there evidence to support or refute it?"

### What exists today

The brain search system is powerful but unstructured:
- `/api/brain/query` accepts question + optional mode (`default` or `counter-thesis`)
- Counter-thesis mode has a fully written system prompt that steelmans the bear case
- Brain searches 13,000+ embedded documents across 10 source tables
- Search pipeline: query expansion → embedding → keyword search → vector search → RRF fusion → LLM reranking → Claude synthesis
- Results stream as prose with `[1]`, `[2]` citations, then sources appended via `---SOURCES---` delimiter
- Conversations persist in `brain_conversations` table with full message history
- Tier gating: free gets Haiku/2048 tokens/8 sources/4 turns; full_spectrum gets Sonnet/4096 tokens/16 sources/10 turns
- `useBrainQuery()` hook manages state, streaming, conversation loading

### What's broken (the user journey)

```
[User has thesis: "Verizon deal will close in H1 2026"]
  → opens BrainSearch overlay (Cmd+K → brain, or panel on /signals)
  → types: "Will the Verizon definitive agreement close in H1 2026?"
  → gets streaming prose response with [1], [2] citations ✅
  → BUT: response is a flat narrative — no structure
  → cannot distinguish: what supports the thesis vs. what contradicts it
  → cannot see evidence strength — all citations weighted equally
  → no way to save the thesis as a persistent artifact
  → no way to compare bull vs bear arguments side by side
  → counter-thesis mode exists in config but NO UI to activate it
  → **DEAD END: user reads the narrative and closes the panel**

[Alternative: user tries to build a case manually]
  → searches brain for "Verizon agreement"
  → gets response
  → searches again for "Verizon risks"
  → gets separate response
  → no way to combine these into a structured argument
  → no for/against categorization
  → **DEAD END: information scattered across conversation turns**
```

### Gap analysis

1. **No structured output** — Brain returns flat prose. The thesis builder needs FOR/AGAINST evidence buckets with cited sources.
2. **No counter-thesis UI** — The mode exists in tier config and the system prompt is written, but no component surfaces it. Full_spectrum users can't access it.
3. **No thesis persistence** — Users can't save a thesis as a named artifact. Conversations exist but they're chat logs, not structured documents.
4. **No evidence scoring** — All citations appear equal. Rerank scores exist (0-10) but aren't surfaced to the user.

### Priority for Phase 1 (DARK → BROKEN)

We need the minimum viable thesis builder — a **new mode or page** that:
1. Accepts a thesis statement (not a question)
2. Runs brain search to find supporting AND contradicting evidence
3. Presents results in a structured layout: thesis statement, FOR evidence (with citations + scores), AGAINST evidence (with citations + scores), synthesis/verdict
4. Uses the existing counter-thesis system prompt for the AGAINST side

This should reuse existing infrastructure (brain search, streaming, citations, DocumentViewer) rather than building new AI pipelines.

---

## WEAVE REQUEST FOR GEMINI

Given:
- Brain search infrastructure (query expansion, hybrid search, LLM reranking, streaming Claude responses)
- Counter-thesis system prompt already written and working (steelmans bear case, rates risks by likelihood × severity)
- Existing `mode` parameter on `/api/brain/query` (default, counter-thesis)
- `useBrainQuery()` hook with conversation persistence
- DocumentViewer integration on citations (from Thread 001)
- Tier gating (counter-thesis requires full_spectrum)
- Current UI: BrainSearch overlay (fullscreen modal with sidebar + chat)

Question for Gemini:

**What's the minimum viable Thesis Builder that goes from DARK to BROKEN?**

Options I see:

**A. New `/thesis` page** — Dedicated page with thesis input, dual-column FOR/AGAINST layout. Makes two brain queries (one default, one counter-thesis). Structured output. New page, new component.

**B. Thesis mode on existing BrainSearch** — Add a "THESIS" mode toggle to BrainSearch overlay. When active, changes the prompt to produce structured output. Same overlay, extended. Less surface area.

**C. Hybrid: structured brain query + new output renderer** — Keep the same `/api/brain/query` endpoint but add a `thesis` mode that returns structured JSON (not streaming prose). New renderer component for the structured output. Could live on a page or in the overlay.

Constraints:
- Must work within existing search pipeline (no new embedding or ranking infrastructure)
- Must reuse DocumentViewer for source drill-down (Thread 001 infrastructure)
- Counter-thesis mode is full_spectrum only — thesis builder should have a free tier version too
- Should feel like a natural extension of the brain, not a separate product

What's the right architecture? Which option, or what hybrid? What should the structured output format look like?

---

## GEMINI RESPONSE

Gemini recommends: **New `/thesis` page powered by a new orchestrating API endpoint `/api/brain/thesis`.**

### Architecture

**API (`/api/brain/thesis`):**
- Lightweight orchestrator — makes two internal calls to existing brain search/synthesis:
  1. FOR query: brain with thesis statement + `mode: 'default'`
  2. AGAINST query: brain with thesis statement + `mode: 'counter-thesis'`
- Streams results sequentially with delimiters:
  - FOR prose → `---THESIS_AGAINST---` → AGAINST prose → `---THESIS_SYNTHESIS---` → synthesis
- Sources appended per section via existing `---SOURCES---` delimiter

**Frontend (`/thesis` page):**
- Large text input for thesis statement
- Three-section layout: Supporting Evidence, Contradicting Evidence, Synthesis
- `useThesisQuery` hook parses streaming response by delimiters
- Citation parsing and DocumentViewer integration reused as-is

**Tier gating:**
- Free tier: FOR query + Synthesis only. AGAINST section shows upgrade prompt.
- Full spectrum: complete FOR + AGAINST + SYNTHESIS

### Structured output

```typescript
interface ThesisResult {
  thesisStatement: string;
  supportingEvidence: { prose: string; sources: Source[]; };
  contradictingEvidence: { prose: string; sources: Source[]; };
  synthesis: { prose: string; };
}
```

### Phase 2 path (BROKEN → FRAYED → GOLDEN)
1. Single advanced prompt instead of two calls (halves cost/latency)
2. True structured JSON output with evidence scoring
3. Persistence to `theses` table with shareable URLs

---

## IMPLEMENTATION PLAN (Claude)

I'll simplify slightly from Gemini's spec:

1. **Skip the orchestrating API endpoint for now.** The `/thesis` page can make two fetch calls to the existing `/api/brain/query` directly — one with `mode: 'default'`, one with `mode: 'counter-thesis'`. No new backend code needed for MVP. The orchestrator can come in Phase 2 when we optimize to a single prompt.

2. **The page handles the dual-stream parsing.** Two parallel streams, each section renders independently as they arrive.

3. **Free tier:** Both queries run with `mode: 'default'` (since counter-thesis requires full_spectrum). The AGAINST section uses a tweaked question prompt instead ("What are the strongest arguments against: {thesis}?"). Not as good as the real counter-thesis prompt, but functional.

4. **Add to command palette + navigation.**

Files:
- CREATE: `app/thesis/page.tsx` — the thesis builder page
- CREATE: `lib/hooks/useThesisQuery.ts` — hook managing dual-stream state
- MODIFY: `components/command-palette/commands.ts` — add THESIS BUILDER nav
- MODIFY: `app/(landing)/page.tsx` — add to EXPLORE grid (if space permits)
- MODIFY: `THREADS.md` — update Thread 003 status
