// components/DemoDeals.tsx
// Preset demo deals shown on the idle dashboard. Clicking a card expands a
// preview panel with the full raw pitch data, then "Run Committee" kicks off
// the agentic flow for THAT company.
import React, { useEffect, useState } from 'react'
import { API_BASE } from '@/lib/agents'
import { ChevronDown, Play, Building2, Loader2 } from 'lucide-react'

interface DemoMeta {
  id: string
  company_name: string
  sector: string
  stage: string
  raise_amount: string
  tagline: string
  expected_verdict: string
  accent: string
}

interface DemoDetail {
  meta: DemoMeta
  pitch: Record<string, unknown>
  preview: {
    verdict?: string
    weighted_score?: number
    coverage_score?: number
    scores?: Record<string, number | null>
    override_reasons?: string[]
    company_name?: string
    raise_amount?: string
    valuation?: string
  } | null
}

const verdictStyle = (v?: string) => {
  const x = (v || '').toUpperCase()
  if (x === 'INVEST') return 'bg-emerald-500/12 text-emerald-500 border-emerald-500/30'
  if (x === 'CONDITIONAL') return 'bg-amber-500/12 text-amber-500 border-amber-500/30'
  if (x === 'PASS') return 'bg-rose-500/12 text-rose-500 border-rose-500/30'
  return 'bg-bg-muted text-text-muted border-border'
}

// Recursively render any nested pitch value so ALL raw data is visible.
function RawValue({ value, depth = 0 }: { value: unknown; depth?: number }) {
  if (value === null || value === undefined || value === '') {
    return <span className="text-text-muted italic">—</span>
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-text-muted italic">none</span>
    return (
      <div className="space-y-1.5">
        {value.map((item, i) => (
          <div key={i} className="pl-2 border-l border-border-strong/60">
            <RawValue value={item} depth={depth + 1} />
          </div>
        ))}
      </div>
    )
  }
  if (typeof value === 'object') {
    return (
      <div className="space-y-1">
        {Object.entries(value as Record<string, unknown>).map(([k, v]) => (
          <div key={k} className="grid grid-cols-[minmax(110px,170px)_1fr] gap-2 items-start">
            <span className="text-[11px] font-semibold text-text-secondary capitalize pt-px">
              {k.replace(/_/g, ' ')}
            </span>
            <div className="text-[11.5px] text-text-primary min-w-0 break-words">
              <RawValue value={v} depth={depth + 1} />
            </div>
          </div>
        ))}
      </div>
    )
  }
  return <span className="break-words">{String(value)}</span>
}

const SECTION_LABELS: Record<string, string> = {
  company: 'Company',
  pitch_claims: 'Pitch Claims',
  financials: 'Financials',
  legal: 'Legal & Compliance',
  technical: 'Technical & Security',
  market: 'Market',
  team: 'Team',
  deal_summary: 'Deal Summary',
}

export default function DemoDeals({ onRun }: { onRun: (companyName: string) => void }) {
  const [demos, setDemos] = useState<DemoMeta[]>([])
  const [openId, setOpenId] = useState<string | null>(null)
  const [detail, setDetail] = useState<DemoDetail | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/demos`)
      .then(r => r.json())
      .then(d => setDemos(Array.isArray(d.demos) ? d.demos : []))
      .catch(() => {})
  }, [])

  const openDemo = async (id: string) => {
    if (openId === id) { setOpenId(null); setDetail(null); return }
    setOpenId(id); setDetail(null); setLoading(true)
    try {
      const r = await fetch(`${API_BASE}/api/v1/demos/${id}`)
      const d = await r.json()
      setDetail(d)
    } catch { /* ignore */ } finally { setLoading(false) }
  }

  if (!demos.length) return null

  const sectionOrder = (pitch: Record<string, unknown>) => {
    const known = Object.keys(SECTION_LABELS).filter(k => k in pitch)
    const rest = Object.keys(pitch).filter(k => !(k in SECTION_LABELS))
    return [...known, ...rest]
  }

  return (
    <div className="w-full space-y-3">
      <div className="flex items-center gap-2">
        <div className="h-px flex-1 bg-border" />
        <span className="text-[11px] font-semibold text-text-muted uppercase tracking-wide">Or explore a demo deal</span>
        <div className="h-px flex-1 bg-border" />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {demos.map(d => {
          const isOpen = openId === d.id
          return (
            <button
              key={d.id}
              onClick={() => openDemo(d.id)}
              className={`text-left rounded-xl border p-3.5 transition group ${isOpen ? 'border-accent bg-accent-soft' : 'border-border hover:border-accent/50 hover:bg-bg-subtle'}`}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <div className="w-7 h-7 rounded-lg bg-bg-muted flex items-center justify-center shrink-0">
                    <Building2 className="w-3.5 h-3.5 text-text-secondary" />
                  </div>
                  <div className="min-w-0">
                    <h4 className="text-[13px] font-bold text-text-primary truncate">{d.company_name}</h4>
                    <p className="text-[10.5px] text-text-muted truncate">{d.sector}</p>
                  </div>
                </div>
                <span className={`text-[9.5px] font-bold px-1.5 py-0.5 rounded border shrink-0 ${verdictStyle(d.expected_verdict)}`}>
                  {d.expected_verdict}
                </span>
              </div>
              <p className="text-[11px] text-text-secondary mt-2 leading-snug line-clamp-2">{d.tagline}</p>
              <div className="flex items-center justify-between mt-2.5">
                <span className="text-[10px] text-text-muted">{d.stage} · {d.raise_amount}</span>
                <span className="text-[10.5px] font-semibold text-accent flex items-center gap-0.5">
                  {isOpen ? 'Hide' : 'View deal'}
                  <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                </span>
              </div>
            </button>
          )
        })}
      </div>

      {/* Expandable preview panel */}
      {openId && (
        <div className="rounded-xl border border-border bg-bg-card overflow-hidden">
          {loading && (
            <div className="flex items-center justify-center gap-2 py-10 text-text-muted">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-[12px]">Loading deal data…</span>
            </div>
          )}
          {!loading && detail && (
            <div>
              {/* panel header */}
              <div className="flex items-center justify-between gap-3 p-4 border-b border-border bg-bg-subtle">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-[15px] font-bold text-text-primary">{detail.meta.company_name}</h3>
                    {detail.preview?.verdict && (
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${verdictStyle(detail.preview.verdict)}`}>
                        Engine preview: {detail.preview.verdict}
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-text-muted mt-0.5">
                    {detail.meta.sector} · {detail.meta.stage} · {detail.meta.raise_amount} raise
                    {detail.preview?.weighted_score != null && <> · risk {detail.preview.weighted_score}/10</>}
                  </p>
                </div>
                <button
                  onClick={() => onRun(detail.meta.company_name)}
                  className="shrink-0 flex items-center gap-1.5 bg-accent text-white text-[12px] font-semibold px-3.5 py-2 rounded-lg hover:opacity-90 transition">
                  <Play className="w-3.5 h-3.5" />
                  Run Committee
                </button>
              </div>

              {/* domain score chips */}
              {detail.preview?.scores && (
                <div className="flex flex-wrap gap-2 px-4 pt-3">
                  {Object.entries(detail.preview.scores).map(([k, v]) => (
                    <span key={k} className="text-[10.5px] px-2 py-1 rounded-lg bg-bg-muted text-text-secondary">
                      <span className="capitalize">{k}</span> risk: <span className="font-semibold text-text-primary">{v == null ? 'N/A' : `${v}/10`}</span>
                    </span>
                  ))}
                </div>
              )}

              {/* raw data — all sections */}
              <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[440px] overflow-y-auto">
                {sectionOrder(detail.pitch).map(key => (
                  <div key={key} className="rounded-lg border border-border bg-bg-subtle p-3">
                    <h5 className="text-[11px] font-bold text-text-primary uppercase tracking-wide mb-2">
                      {SECTION_LABELS[key] || key.replace(/_/g, ' ')}
                    </h5>
                    <RawValue value={detail.pitch[key]} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
