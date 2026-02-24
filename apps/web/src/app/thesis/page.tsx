'use client'

import { useState, useCallback, useEffect } from 'react'
import { Muted } from '@shortgravity/ui'
import { useTheses, useCreateThesis } from '@/lib/hooks/useTheses'
import type { Thesis } from '@/lib/hooks/useTheses'

const STATUS_COLORS: Record<string, string> = {
  complete: 'text-green-400 border-green-400/20',
  generating: 'text-amber-400 border-amber-400/20',
  failed: 'text-red-400 border-red-400/20',
}

function getSessionId(): string {
  if (typeof window === 'undefined') return crypto.randomUUID()
  let id = localStorage.getItem('sg_session_id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('sg_session_id', id)
  }
  return id
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function ThesisCard({ thesis }: { thesis: Thesis }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border border-white/[0.06] rounded-lg px-4 py-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-sm text-white/80 leading-snug text-left hover:text-white transition-colors flex-1"
        >
          &ldquo;{thesis.statement}&rdquo;
        </button>
        <span
          className={`text-[9px] font-bold px-1.5 py-0.5 rounded border shrink-0 ${
            STATUS_COLORS[thesis.status] ?? 'text-white/40 border-white/10'
          }`}
        >
          {thesis.status.toUpperCase()}
        </span>
      </div>
      <div className="text-[10px] text-white/25">{formatDate(thesis.created_at)}</div>

      {/* Expanded content */}
      {expanded && thesis.status === 'complete' && (
        <div className="mt-4 space-y-4 border-t border-white/[0.06] pt-4">
          {/* Supporting */}
          {thesis.supporting_prose && (
            <div>
              <div className="text-[10px] text-green-400/70 tracking-wider mb-1.5">
                SUPPORTING CASE
              </div>
              <div className="text-xs text-white/50 leading-relaxed">
                {thesis.supporting_prose}
              </div>
              {thesis.supporting_sources?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {thesis.supporting_sources.map((s, i) => (
                    <span
                      key={i}
                      className="text-[9px] text-white/25 border border-white/[0.06] px-1.5 py-0.5 rounded"
                    >
                      {s.title || s.table}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Contradicting */}
          {thesis.contradicting_prose && (
            <div>
              <div className="text-[10px] text-red-400/70 tracking-wider mb-1.5">
                CONTRADICTING CASE
              </div>
              <div className="text-xs text-white/50 leading-relaxed">
                {thesis.contradicting_prose}
              </div>
              {thesis.contradicting_sources?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {thesis.contradicting_sources.map((s, i) => (
                    <span
                      key={i}
                      className="text-[9px] text-white/25 border border-white/[0.06] px-1.5 py-0.5 rounded"
                    >
                      {s.title || s.table}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Synthesis */}
          {thesis.synthesis_prose && (
            <div>
              <div className="text-[10px] text-[#FF6B35]/70 tracking-wider mb-1.5">SYNTHESIS</div>
              <div className="text-xs text-white/50 leading-relaxed">
                {thesis.synthesis_prose}
              </div>
              {thesis.synthesis_sources?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {thesis.synthesis_sources.map((s, i) => (
                    <span
                      key={i}
                      className="text-[9px] text-white/25 border border-white/[0.06] px-1.5 py-0.5 rounded"
                    >
                      {s.title || s.table}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {expanded && thesis.status === 'generating' && (
        <div className="mt-4 border-t border-white/[0.06] pt-4">
          <div className="text-xs text-amber-400/50">Analysis in progress...</div>
        </div>
      )}

      {expanded && thesis.status === 'failed' && (
        <div className="mt-4 border-t border-white/[0.06] pt-4">
          <div className="text-xs text-red-400/50">Analysis failed. Try submitting again.</div>
        </div>
      )}

      {!expanded && thesis.status === 'complete' && thesis.synthesis_prose && (
        <div className="mt-2 text-[11px] text-white/30 line-clamp-2">
          {thesis.synthesis_prose}
        </div>
      )}
    </div>
  )
}

export default function ThesisPage() {
  const [sessionId, setSessionId] = useState<string>('')
  const [statement, setStatement] = useState('')
  const [showForm, setShowForm] = useState(false)

  useEffect(() => {
    setSessionId(getSessionId())
  }, [])

  const { data, isLoading } = useTheses(sessionId || undefined)
  const createThesis = useCreateThesis()

  const handleSubmit = useCallback(() => {
    if (!statement.trim() || !sessionId) return
    createThesis.mutate(
      { session_id: sessionId, statement: statement.trim() },
      { onSuccess: () => { setStatement(''); setShowForm(false) } },
    )
  }, [statement, sessionId, createThesis])

  return (
    <div className="min-h-screen bg-[#030305] text-white font-mono">
      <div className="max-w-3xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="flex items-baseline justify-between mb-8">
          <div>
            <h1 className="text-2xl font-light tracking-wider">THESIS BUILDER</h1>
            <Muted className="text-xs mt-1">
              Submit a thesis statement — get AI-powered bull/bear analysis backed by our data
            </Muted>
          </div>
          {data && (
            <div className="text-right">
              <span className="text-3xl font-light tabular-nums">{data.count}</span>
              <Muted className="text-xs ml-2">THESES</Muted>
            </div>
          )}
        </div>

        {/* New thesis form */}
        {showForm ? (
          <div className="border border-white/10 rounded-lg px-4 py-4 mb-6">
            <div className="text-[11px] text-white/50 tracking-wider mb-3">NEW THESIS</div>
            <textarea
              value={statement}
              onChange={(e) => setStatement(e.target.value)}
              placeholder="Enter your thesis statement... e.g. &quot;AST SpaceMobile will achieve commercial service by Q4 2026&quot;"
              className="w-full bg-white/[0.03] border border-white/[0.08] rounded px-3 py-2.5 text-sm text-white/80 placeholder:text-white/20 focus:outline-none focus:border-white/20 resize-none font-mono"
              rows={3}
            />
            <div className="flex items-center justify-between mt-3">
              <Muted className="text-[10px]">
                Analysis draws from SEC filings, patents, earnings, and orbital data
              </Muted>
              <div className="flex gap-2">
                <button
                  onClick={() => { setShowForm(false); setStatement('') }}
                  className="text-[11px] text-white/30 hover:text-white/50 transition-colors px-3 py-1.5"
                >
                  CANCEL
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={!statement.trim() || createThesis.isPending}
                  className="text-[11px] text-[#030305] bg-white/80 hover:bg-white transition-colors px-4 py-1.5 rounded disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  {createThesis.isPending ? 'SUBMITTING...' : 'SUBMIT'}
                </button>
              </div>
            </div>
            {createThesis.isError && (
              <div className="text-xs text-red-400/70 mt-2">
                Failed to create thesis. Please try again.
              </div>
            )}
          </div>
        ) : (
          <button
            onClick={() => setShowForm(true)}
            className="w-full border border-dashed border-white/10 rounded-lg px-4 py-4 mb-6 text-[11px] text-white/30 hover:text-white/50 hover:border-white/20 transition-colors"
          >
            + NEW THESIS
          </button>
        )}

        {/* Loading state */}
        {isLoading && (
          <div className="text-white/30 text-sm py-20 text-center">LOADING...</div>
        )}

        {/* Empty state */}
        {!isLoading && data && data.data.length === 0 && (
          <div className="border border-white/[0.06] rounded-lg p-12 text-center">
            <div className="text-white/30 text-sm mb-2">No theses yet</div>
            <Muted className="text-xs">
              Submit a thesis statement to get AI-powered analysis with supporting and contradicting evidence.
            </Muted>
          </div>
        )}

        {/* Thesis list */}
        {data && data.data.length > 0 && (
          <div className="space-y-3">
            {data.data.map((thesis) => (
              <ThesisCard key={thesis.id} thesis={thesis} />
            ))}
          </div>
        )}

        {/* Back links */}
        <div className="mt-12 flex justify-center gap-6">
          <a
            href="/"
            className="text-[11px] text-white/30 hover:text-white/50 transition-colors"
          >
            BACK TO TERMINAL
          </a>
          <a
            href="/signals"
            className="text-[11px] text-white/30 hover:text-white/50 transition-colors"
          >
            SIGNALS
          </a>
          <a
            href="/research"
            className="text-[11px] text-white/30 hover:text-white/50 transition-colors"
          >
            RESEARCH
          </a>
        </div>
      </div>
    </div>
  )
}
