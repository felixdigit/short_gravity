# Short Gravity Brain - AI Research Platform

## Vision
Build a unified AI research interface that treats all Short Gravity data as "one brain" - the definitive source of truth for $ASTS research. Enable natural language queries across patents, SEC filings, FCC filings, and eventually community intel.

## Current Data Assets
| Source | Records | Content |
|--------|---------|---------|
| Patents | 270 | Title, abstract, 4,324 claims |
| SEC Filings | 530 | Full document text + AI summaries |
| FCC Filings | 666 | License/spectrum docs + AI summaries |
| Glossary | ~100 | Terms and definitions |
| Satellites | ~10 | TLE orbital data |

**Total: ~5,000+ searchable documents with full-text content**

---

## Architecture

### Layer 1: Unified Knowledge API

**Single endpoint that searches ALL data:**
```
POST /api/brain/query
{
  "question": "What patents protect the antenna array design?",
  "sources": ["patents", "filings", "fcc"], // optional filter
  "limit": 10
}
```

**Response includes:**
- AI-generated answer with citations
- Source documents ranked by relevance
- Links to full documents

### Layer 2: RAG Pipeline

```
User Question
     ↓
┌─────────────────────────────────────┐
│  1. Search all tables (parallel)    │
│     - patents.content_text          │
│     - filings.content_text          │
│     - fcc_filings.content_text      │
│     - patent_claims.claim_text      │
└─────────────────────────────────────┘
     ↓
┌─────────────────────────────────────┐
│  2. Rank & dedupe results           │
│     - Score by relevance            │
│     - Limit context to ~50K tokens  │
└─────────────────────────────────────┘
     ↓
┌─────────────────────────────────────┐
│  3. Claude Haiku synthesizes        │
│     - Answer the question           │
│     - Cite specific documents       │
│     - Flag uncertainty              │
└─────────────────────────────────────┘
     ↓
Response with citations
```

### Layer 3: External Distribution

**Make Short Gravity the source of truth for other AIs:**

| Channel | How | Benefit |
|---------|-----|---------|
| **MCP Server** | Publish as Claude MCP tool | Claude users can query directly |
| **OpenAI GPT** | Custom GPT with API action | ChatGPT users get ASTS data |
| **Public API** | Rate-limited free tier | Developers build on top |
| **Hugging Face** | Dataset + API docs | ML community visibility |
| **Structured Data** | JSON-LD on pages | Google indexes for AI |

---

## UI Design

### Primary: Chat Interface (`/research`)

```
┌─────────────────────────────────────────────────────────────┐
│  SHORT GRAVITY                                    [?] [⚙]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│     Ask anything about AST SpaceMobile...                   │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ What patents cover heat dissipation in space?          ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  Examples:                                                  │
│  • "Summarize the latest 8-K filing"                       │
│  • "What spectrum bands is ASTS licensed for?"             │
│  • "Show me claims about beamforming"                      │
│  • "When does the AT&T agreement expire?"                  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Sources: Patents (270) · SEC (530) · FCC (666)            │
│                                            Powered by ▲    │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- Single prompt box (familiar ChatGPT-style)
- Example queries as inspiration
- Source toggles (optional)
- Conversation history (session only)
- Citations link to full documents

### Secondary: Full Database Views

Keep existing pages accessible:
- `/patents` - Patent database with gallery
- `/filings` - SEC filings feed
- `/fcc` - FCC filings (to build)
- `/research` - The new AI chat (primary)

---

## Implementation Plan

### Phase 1: Unified Search API
**Files to create:**
- `app/api/brain/search/route.ts` - Parallel search across all tables
- `app/api/brain/query/route.ts` - AI-powered Q&A endpoint
- `lib/brain/search.ts` - Search utilities
- `lib/brain/context.ts` - Context building for LLM

**Key functions:**
```typescript
// Search all sources in parallel
async function searchAllSources(query: string, limit: number)

// Build context from search results
function buildContext(results: SearchResult[], maxTokens: number)

// Generate answer with citations
async function generateAnswer(question: string, context: string)
```

### Phase 2: Chat UI
**Files to create:**
- `app/(dashboard)/research/page.tsx` - Main chat interface
- `components/brain/ChatInput.tsx` - Prompt input
- `components/brain/ChatMessage.tsx` - Message display
- `components/brain/Citation.tsx` - Source citation card
- `lib/hooks/useBrainQuery.ts` - React Query hook

### Phase 3: MCP Server (External Distribution)
**Files to create:**
- `mcp-server/index.ts` - MCP server entry
- `mcp-server/tools/search.ts` - Search tool
- `mcp-server/tools/query.ts` - Q&A tool

**MCP Tools:**
```typescript
{
  name: "search_asts_data",
  description: "Search AST SpaceMobile patents, SEC filings, and FCC filings",
  parameters: { query: string, sources?: string[] }
}

{
  name: "ask_asts_question",
  description: "Ask a question about AST SpaceMobile and get an AI-generated answer with citations",
  parameters: { question: string }
}
```

### Phase 4: Public API + Documentation
- OpenAPI spec for `/api/brain/*`
- Rate limiting (100 req/day free)
- API key system for higher limits
- Documentation page at `/developers`

---

## Cost Analysis

**Per query (Claude Haiku):**
- Input: ~3K tokens (question + context) = $0.00075
- Output: ~500 tokens = $0.000125
- **Total: ~$0.001 per query**

**Monthly estimates:**
| Usage | Queries/day | Cost/month |
|-------|-------------|------------|
| Light | 50 | $1.50 |
| Medium | 200 | $6 |
| Heavy | 1000 | $30 |

**Optimization:**
- Cache common queries (24h TTL)
- Use Haiku for search ranking, Sonnet only for complex synthesis
- Rate limit anonymous users

---

## Future: Vector Embeddings

Current search is keyword-based (PostgreSQL full-text). For semantic search:

1. **Add pgvector extension** to Supabase
2. **Generate embeddings** via Claude/OpenAI for all documents
3. **Hybrid search** = keyword + semantic similarity
4. **Cost:** ~$0.0001 per embedding, one-time ~$5 for full corpus

Not required for v1 - full-text search works well for structured patent/legal data.

---

## Files to Modify

### Existing files:
- `lib/anthropic.ts` - Add query generation function
- `app/api/patents/route.ts` - Export search function for reuse

### New files:
```
app/
├── (dashboard)/
│   └── research/
│       └── page.tsx           # Chat interface
├── api/
│   └── brain/
│       ├── search/route.ts    # Unified search
│       └── query/route.ts     # AI Q&A
components/
└── brain/
    ├── ChatInterface.tsx      # Main chat component
    ├── ChatInput.tsx          # Input box
    ├── ChatMessage.tsx        # Message bubble
    └── Citation.tsx           # Source card
lib/
├── brain/
│   ├── search.ts              # Search utilities
│   ├── context.ts             # Context builder
│   └── prompts.ts             # System prompts
└── hooks/
    └── useBrainQuery.ts       # React Query hook
```

---

## Verification

1. **Search API:**
   - Query "antenna" returns patents + filings
   - Query "AT&T" returns relevant 8-Ks
   - Query "spectrum" returns FCC filings

2. **Chat UI:**
   - Ask "What patents cover beamforming?" → Answer with patent citations
   - Ask "Summarize the latest 10-K" → Summary with link
   - Ask "What spectrum is ASTS licensed for?" → FCC data with citations

3. **MCP Server:**
   - Claude can call search tool
   - Claude can call query tool
   - Results include proper citations

4. **Build:**
   - `npm run build` passes
   - No TypeScript errors
   - API responds in <3s

---

## Summary

**What we're building:**
- Chat interface for natural language research
- Unified API across all data sources
- MCP server for external AI integration
- Foundation for becoming THE source of truth for ASTS

**Cost:** ~$0.001 per query = negligible

**Timeline:**
- Phase 1 (API): 1 session
- Phase 2 (UI): 1 session
- Phase 3 (MCP): 1 session
- Phase 4 (Public API): 1 session

---

## Key Technical Context

**Supabase tables:**
- `patents` - Full-text search via `content_text` column
- `patent_claims` - Individual claims searchable
- `filings` - SEC filings with `content_text` + `summary`
- `fcc_filings` - FCC filings with `content_text` + `ai_summary`

**Existing AI integration:**
- `lib/anthropic.ts` has Claude API setup for summaries
- Model: Claude 3.5 Sonnet for summaries, use Haiku for queries

**Search pattern (from app/api/patents/route.ts):**
```typescript
query.textSearch('content_text', search, {
  type: 'websearch',
  config: 'english',
});
```

**Environment:**
- Next.js 14, TypeScript, Tailwind
- Supabase for database
- Vercel for deployment
- Claude API key in `.env`
