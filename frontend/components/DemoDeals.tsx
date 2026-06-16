// components/DemoDeals.tsx
// Preset demo deals on the idle dashboard. A card expands a polished deal-sheet
// preview (key metrics, highlights, per-domain facts, + full raw JSON on demand),
// then "Run Committee" kicks off the agentic flow for THAT company.
import React, { useEffect, useState } from 'react'
import { API_BASE } from '@/lib/agents'
import {
  ChevronDown, Play, Building2, Loader2, DollarSign, TrendingUp, Flame,
  Timer, Percent, Landmark, AlertTriangle, CheckCircle2, Scale, Cpu, Globe2, Users,
} from 'lucide-react'

interface DemoMeta {
  id: string; company_name: string; sector: string; stage: string
  raise_amount: string; tagline: string; expected_verdict: string; accent: string
}
interface DemoDetail {
  meta: DemoMeta
  pitch: Record<string, unknown>
  preview: {
    verdict?: string; weighted_score?: number; coverage_score?: number
    scores?: Record<string, number | null>; override_reasons?: string[]
    company_name?: string; raise_amount?: string; valuation?: string
  } | null
}

const verdictStyle = (v?: string) => {
  const x = (v || '').toUpperCase()
  if (x === 'INVEST') return 'bg-emerald-500/12 text-emerald-500 border-emerald-500/30'
  if (x === 'CONDITIONAL') return 'bg-amber-500/12 text-amber-500 border-amber-500/30'
  if (x === 'PASS') return 'bg-rose-500/12 text-rose-500 border-rose-500/30'
  return 'bg-bg-muted text-text-muted border-border'
}

// ── safe readers (demo pitches follow the rich nested schema) ───────────────
const asStr = (v: unknown): string | null => {
  if (v == null || v === '') return null
  if (typeof v === 'object') {
    const o = v as Record<string, unknown>
    if ('value' in o) return asStr(o.value)
    return null
  }
  return String(v)
}
const money = (v: unknown): string | null => {
  const s = asStr(v); if (s == null) return null
  // Pull a numeric magnitude out of "$8,500,000", "8500000", "$420k", etc.
  const digits = s.replace(/[^0-9.]/g, '')
  const n = parseFloat(digits)
  if (Number.isNaN(n)) return s
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(n % 1_000_000 ? 1 : 0)}M`
  if (n >= 1_000) return `$${Math.round(n / 1000)}k`
  return `$${n}`
}
const get = (obj: unknown, path: string): unknown =>
  path.split('.').reduce<unknown>((a, k) => (a == null ? a : (a as Record<string, unknown>)[k]), obj)

interface Metric { icon: React.ComponentType<{ className?: string }>; label: string; value: string }
function buildMetrics(p: Record<string, unknown>): Metric[] {
  const out: Metric[] = []
  const push = (icon: Metric['icon'], label: string, v: string | null) => { if (v) out.push({ icon, label, value: v }) }
  push(DollarSign, 'ARR', money(get(p, 'pitch_claims.arr')) || money(get(p, 'financials.arr')))
  push(TrendingUp, 'Growth', asStr(get(p, 'pitch_claims.yoy_growth')))
  push(Flame, 'Burn / mo', money(get(p, 'financials.monthly_burn_usd')))
  const rw = asStr(get(p, 'financials.runway_months')); push(Timer, 'Runway', rw ? `${rw} mo` : null)
  const gm = asStr(get(p, 'financials.gross_margin_pct')); push(Percent, 'Gross margin', gm ? `${gm}%` : null)
  push(Landmark, 'Valuation', money(get(p, 'company.post_money_valuation')))
  return out.slice(0, 6)
}

function collectFlags(p: Record<string, unknown>): string[] {
  const flags: string[] = []
  for (const sec of ['financials', 'legal', 'technical', 'market']) {
    const f = get(p, `${sec}.red_flags`)
    if (Array.isArray(f)) for (const x of f) { const s = asStr(x); if (s) flags.push(s) }
  }
  return flags
}

// one compact fact row
const Fact = ({ k, v }: { k: string; v: string | null }) =>
  v ? (
    <div className="flex gap-2 text-[11.5px] leading-snug">
      <span className="text-text-muted shrink-0 w-[88px]">{k}</span>
      <span className="text-text-primary min-w-0 break-words">{v}</span>
    </div>
  ) : null

function domainCards(p: Record<string, unknown>) {
  const fin = (get(p, 'financials') as Record<string, unknown> | undefined) || {}
  const breakdown = fin.customer_revenue_breakdown
  const topCust = (Array.isArray(breakdown) ? breakdown[0] : null) as Record<string, unknown> | null
  const stack = get(p, 'technical.tech_stack') as Record<string, unknown> | undefined
  const stackStr = stack ? Object.values(stack).map(v => asStr(v)).filter(Boolean).slice(0, 4).join(' · ') : asStr(get(p, 'technical.stack'))
  const comps = get(p, 'market.competitors')
  const compStr = Array.isArray(comps)
    ? (comps as Array<Record<string, unknown>>).map(c => asStr(c?.name)).filter(Boolean).join(', ')
    : asStr(get(p, 'market.competition'))
  const pendingLit = get(p, 'legal.pending_litigation')
  const lit = asStr(get(p, 'legal.litigation')) ||
    (Array.isArray(pendingLit) && pendingLit.length === 0 ? 'No active lawsuits' : null)
  const comp = get(p, 'legal.regulatory_compliance') as Record<string, unknown> | undefined
  const compFacts = comp ? Object.values(comp).map(v => asStr(v)).filter(Boolean).slice(0, 2).join(' · ') : asStr(get(p, 'legal.compliance'))
  const sec = get(p, 'technical.security') as Record<string, unknown> | undefined
  const secStr = sec ? [asStr(sec.encryption_at_rest), asStr(sec.last_penetration_test)].filter(Boolean).slice(0, 2).join(' · ') : null

  return [
    {
      icon: DollarSign, title: 'Financials', facts: [
        ['ARR', money(get(p, 'pitch_claims.arr'))],
        ['Runway', asStr(fin?.runway_months) ? `${asStr(fin?.runway_months)} months` : null],
        ['Margin', asStr(fin?.gross_margin_pct) ? `${asStr(fin?.gross_margin_pct)}%` : null],
        ['Top client', topCust ? `${asStr(topCust.revenue_pct)}% — ${asStr(topCust.customer)}` : null],
      ] as [string, string | null][],
    },
    {
      icon: Scale, title: 'Legal & Compliance', facts: [
        ['Litigation', lit],
        ['Compliance', compFacts],
        ['IP', asStr(get(p, 'legal.ip_status'))],
      ] as [string, string | null][],
    },
    {
      icon: Cpu, title: 'Technical', facts: [
        ['Stack', stackStr],
        ['Security', secStr],
      ] as [string, string | null][],
    },
    {
      icon: Globe2, title: 'Market', facts: [
        ['Sector', asStr(get(p, 'market.sector'))],
        ['TAM', asStr(get(p, 'market.tam_claim'))],
        ['Competitors', compStr],
      ] as [string, string | null][],
    },
    {
      icon: Users, title: 'Team', facts: [
        ['CEO', [asStr(get(p, 'team.ceo.name')), asStr(get(p, 'team.ceo.previous_company'))].filter(Boolean).join(' — ') || null],
        ['CTO', [asStr(get(p, 'team.cto.name')), asStr(get(p, 'team.cto.previous'))].filter(Boolean).join(' — ') || null],
      ] as [string, string | null][],
    },
  ].filter(c => c.facts.some(([, v]) => v))
}

// recursive renderer for the collapsible "full raw data"
function RawValue({ value }: { value: unknown }) {
  if (value === null || value === undefined || value === '') return <span className="text-text-muted italic">—</span>
  if (Array.isArray(value)) {
    if (!value.length) return <span className="text-text-muted italic">none</span>
    return <div className="space-y-1">{value.map((it, i) => <div key={i} className="pl-2 border-l border-border-strong/50"><RawValue value={it} /></div>)}</div>
  }
  if (typeof value === 'object') {
    return <div className="space-y-0.5">{Object.entries(value as Record<string, unknown>).map(([k, v]) => (
      <div key={k} className="grid grid-cols-[minmax(96px,150px)_1fr] gap-2 items-start">
        <span className="text-[10.5px] font-medium text-text-secondary capitalize pt-px">{k.replace(/_/g, ' ')}</span>
        <div className="text-[11px] text-text-primary min-w-0 break-words"><RawValue value={v} /></div>
      </div>))}</div>
  }
  return <span className="break-words">{String(value)}</span>
}

export default function DemoDeals({ onRun }: { onRun: (companyName: string) => void }) {
  const [demos, setDemos] = useState<DemoMeta[]>([])
  const [openId, setOpenId] = useState<string | null>(null)
  const [detail, setDetail] = useState<DemoDetail | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/demos`).then(r => r.json())
      .then(d => setDemos(Array.isArray(d.demos) ? d.demos : [])).catch(() => {})
  }, [])

  const openDemo = async (id: string) => {
    if (openId === id) { setOpenId(null); setDetail(null); return }
    setOpenId(id); setDetail(null); setLoading(true)
    try { setDetail(await (await fetch(`${API_BASE}/api/v1/demos/${id}`)).json()) }
    catch { /* ignore */ } finally { setLoading(false) }
  }

  if (!demos.length) return null

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
            <button key={d.id} onClick={() => openDemo(d.id)}
              className={`text-left rounded-xl border p-3.5 transition ${isOpen ? 'border-accent bg-accent-soft' : 'border-border hover:border-accent/50 hover:bg-bg-subtle'}`}>
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
                <span className={`text-[9.5px] font-bold px-1.5 py-0.5 rounded border shrink-0 ${verdictStyle(d.expected_verdict)}`}>{d.expected_verdict}</span>
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

      {openId && (
        <div className="rounded-xl border border-border bg-bg-card overflow-hidden">
          {loading && (
            <div className="flex items-center justify-center gap-2 py-10 text-text-muted">
              <Loader2 className="w-4 h-4 animate-spin" /><span className="text-[12px]">Loading deal data…</span>
            </div>
          )}
          {!loading && detail && (() => {
            const p = detail.pitch
            const metrics = buildMetrics(p)
            const flags = collectFlags(p)
            const cards = domainCards(p)
            const desc = asStr(get(p, 'company.description'))
            return (
              <div>
                {/* header */}
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
                  <button onClick={() => onRun(detail.meta.company_name)}
                    className="shrink-0 flex items-center gap-1.5 bg-accent text-white text-[12px] font-semibold px-3.5 py-2 rounded-lg hover:opacity-90 transition">
                    <Play className="w-3.5 h-3.5" /> Run Committee
                  </button>
                </div>

                <div className="p-4 space-y-4 max-h-[60vh] overflow-y-auto">
                  {/* key metrics */}
                  {metrics.length > 0 && (
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
                      {metrics.map(m => (
                        <div key={m.label} className="rounded-lg border border-border bg-bg-subtle px-2.5 py-2">
                          <div className="flex items-center gap-1 text-text-muted"><m.icon className="w-3 h-3" /><span className="text-[9.5px] uppercase tracking-wide">{m.label}</span></div>
                          <div className="text-[13.5px] font-bold text-text-primary mt-0.5 truncate">{m.value}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  {desc && <p className="text-[12px] text-text-secondary leading-relaxed">{desc}</p>}

                  {/* domain score chips */}
                  {detail.preview?.scores && (
                    <div className="flex flex-wrap gap-1.5">
                      {Object.entries(detail.preview.scores).map(([k, v]) => (
                        <span key={k} className="text-[10px] px-2 py-1 rounded-md bg-bg-muted text-text-secondary">
                          <span className="capitalize">{k}</span> risk <span className="font-semibold text-text-primary">{v == null ? 'N/A' : `${v}/10`}</span>
                        </span>
                      ))}
                    </div>
                  )}

                  {/* highlights / red flags */}
                  <div className="rounded-lg border border-border bg-bg-subtle p-3">
                    <div className="flex items-center gap-1.5 mb-1.5">
                      {flags.length ? <AlertTriangle className="w-3.5 h-3.5 text-amber-500" /> : <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />}
                      <h5 className="text-[11px] font-bold text-text-primary uppercase tracking-wide">{flags.length ? `Red flags (${flags.length})` : 'Highlights'}</h5>
                    </div>
                    {flags.length ? (
                      <ul className="space-y-1">
                        {flags.slice(0, 6).map((f, i) => (
                          <li key={i} className="text-[11.5px] text-text-secondary flex gap-1.5"><span className="text-amber-500 shrink-0">•</span><span className="min-w-0">{f}</span></li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-[11.5px] text-text-secondary">No material red flags surfaced in the brief — strong, clean fundamentals.</p>
                    )}
                  </div>

                  {/* per-domain fact cards */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                    {cards.map(c => (
                      <div key={c.title} className="rounded-lg border border-border bg-bg-subtle p-3">
                        <div className="flex items-center gap-1.5 mb-2"><c.icon className="w-3.5 h-3.5 text-text-secondary" /><h5 className="text-[11px] font-bold text-text-primary uppercase tracking-wide">{c.title}</h5></div>
                        <div className="space-y-1.5">{c.facts.map(([k, v]) => <Fact key={k} k={k} v={v} />)}</div>
                      </div>
                    ))}
                  </div>

                  {/* full raw data — collapsed by default */}
                  <details className="rounded-lg border border-border bg-bg-subtle group">
                    <summary className="cursor-pointer select-none px-3 py-2 text-[11px] font-semibold text-text-secondary hover:text-text-primary flex items-center gap-1.5">
                      <ChevronDown className="w-3.5 h-3.5 transition-transform group-open:rotate-180" />
                      View full raw pitch data
                    </summary>
                    <div className="px-3 pb-3 grid grid-cols-1 md:grid-cols-2 gap-3 border-t border-border pt-3">
                      {Object.keys(p).map(key => (
                        <div key={key}>
                          <h6 className="text-[10px] font-bold text-text-muted uppercase tracking-wide mb-1">{key.replace(/_/g, ' ')}</h6>
                          <RawValue value={p[key]} />
                        </div>
                      ))}
                    </div>
                  </details>
                </div>
              </div>
            )
          })()}
        </div>
      )}
    </div>
  )
}
