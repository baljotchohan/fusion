// components/DealIntel.tsx — Deal Intelligence: the diligence engine's full
// deterministic output (GET /api/v1/deal-intel). Every number here is pure
// arithmetic over pitch evidence — no LLM generates or embellishes anything.
'use client'

import React, { useEffect, useState, useCallback } from 'react'
import { RefreshCw, AlertTriangle, HelpCircle, ListChecks, TrendingDown } from 'lucide-react'
import { apiFetch } from '@/lib/apiFetch'
import { API_BASE } from '@/lib/agents'

interface DealIntelData {
  incident_id?: string
  company?: string
  scores: { financial?: number; legal?: number; technical?: number; market?: number; weighted?: number }
  verdict?: string
  verdict_confidence?: number
  evidence_quality_score?: number
  deal_readiness_score?: number
  deal_readiness_status?: string
  scenario?: {
    client_name?: string; concentration_pct?: number; churn_revenue_loss?: number
    current_valuation?: number; new_valuation?: number; new_runway?: number
    new_monthly_burn?: number; survival_classification?: string
  } | null
  contradictions: { message?: string; severity?: string; domain?: string }[]
  missing_gaps: (string | { message?: string })[]
  questions: Record<string, string[]>
  diligence_priorities: { priority?: string; owner?: string; action?: string; domain?: string }[]
  override_reasons: string[]
}

const fmtMoney = (n?: number) =>
  n == null ? '—' : n >= 1e6 ? `$${(n / 1e6).toFixed(n >= 1e7 ? 0 : 1)}M` : n >= 1e3 ? `$${Math.round(n / 1e3)}K` : `$${n}`

/* Severity mapping for a RISK meter (higher = worse). Fill carries severity;
   track is a lighter step of the same ramp so state reads across the bar. */
function riskTone(score: number) {
  if (score >= 7) return { fill: 'bg-danger', track: 'bg-danger/15' }
  if (score >= 5) return { fill: 'bg-warning', track: 'bg-warning/15' }
  return { fill: 'bg-success', track: 'bg-success/15' }
}

function StatTile({ label, value, suffix, chip, chipTone }: {
  label: string; value: string | number; suffix?: string
  chip?: string; chipTone?: 'danger' | 'warning' | 'success' | 'muted'
}) {
  const tones = {
    danger: 'bg-danger-soft text-danger', warning: 'bg-warning-soft text-warning',
    success: 'bg-success-soft text-success', muted: 'bg-bg-muted text-text-muted',
  }
  return (
    <div className="rounded-xl bg-bg-card border border-border p-3.5">
      <p className="text-[10px] font-medium text-text-muted mb-1">{label}</p>
      <div className="flex items-baseline gap-1.5 flex-wrap">
        <span className="text-[22px] font-semibold text-text-primary leading-none">{value}</span>
        {suffix && <span className="text-[11px] text-text-muted">{suffix}</span>}
        {chip && (
          <span className={`ml-auto px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider ${tones[chipTone || 'muted']}`}>
            {chip}
          </span>
        )}
      </div>
    </div>
  )
}

function RiskMeter({ label, weight, score }: { label: string; weight: string; score?: number }) {
  if (score == null) return null
  const tone = riskTone(score)
  return (
    <div title={`${label}: risk ${score.toFixed(1)} of 10 (weight ${weight})`}>
      <div className="flex items-baseline justify-between mb-1">
        <span className="text-[11px] font-medium text-text-secondary">
          {label} <span className="text-[9px] font-mono text-text-muted">({weight})</span>
        </span>
        <span className="text-[11px] font-semibold text-text-primary">{score.toFixed(1)}<span className="text-text-muted font-normal">/10</span></span>
      </div>
      <div className={`h-2 rounded-full overflow-hidden ${tone.track}`}>
        <div className={`h-full rounded-r-[4px] ${tone.fill} transition-all duration-700`} style={{ width: `${score * 10}%` }} />
      </div>
    </div>
  )
}

const SectionHead = ({ Icon, title }: { Icon: React.ElementType; title: string }) => (
  <div className="flex items-center gap-1.5 mb-2.5">
    <Icon className="w-3.5 h-3.5 text-text-muted" />
    <h3 className="text-[10px] font-bold font-mono uppercase tracking-widest text-text-muted">{title}</h3>
  </div>
)

const PRIORITY_TONE: Record<string, string> = {
  High: 'bg-danger-soft text-danger', Medium: 'bg-warning-soft text-warning', Low: 'bg-bg-muted text-text-muted',
}

const ROLE_LABELS: Record<string, string> = { ceo: 'For the CEO', cto: 'For the CTO', legal: 'For Legal Counsel', cfo: 'For the CFO' }

export function DealIntel({ incidentId }: { incidentId?: string | null }) {
  const [data, setData] = useState<DealIntelData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const q = incidentId ? `?incident_id=${encodeURIComponent(incidentId)}` : ''
      const res = await apiFetch(`${API_BASE}/api/v1/deal-intel${q}`)
      if (!res.ok) throw new Error(`${res.status}`)
      setData(await res.json())
    } catch {
      setError('Deal intelligence unavailable — is the FUSION backend running?')
    } finally { setLoading(false) }
  }, [incidentId])

  // Defer a tick so no setState runs synchronously inside the effect body.
  useEffect(() => { void Promise.resolve().then(load) }, [load])

  if (error) return <p className="text-[11.5px] text-text-muted italic py-8 text-center">{error}</p>
  if (!data) return <p className="text-[11.5px] text-text-muted italic py-8 text-center">Computing deal intelligence…</p>

  const s = data.scores || {}
  const verdictTone = data.verdict === 'INVEST' ? 'success' : data.verdict === 'CONDITIONAL' ? 'warning' : 'danger'
  const scen = data.scenario
  const questionRoles = Object.entries(data.questions || {}).filter(([, qs]) => qs?.length)

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-[11px] text-text-secondary">
          <span className="font-semibold text-text-primary">{data.company || 'Active deal'}</span>
          {' — '}computed deterministically from pitch evidence. No AI generation.
        </p>
        <button onClick={load} disabled={loading} title="Recompute"
          className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-bg-muted transition">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatTile label="Weighted risk" value={s.weighted?.toFixed(1) ?? '—'} suffix="/10"
          chip={data.verdict} chipTone={verdictTone} />
        <StatTile label="Verdict confidence" value={data.verdict_confidence != null ? Math.round(data.verdict_confidence) : '—'} suffix="%" />
        <StatTile label="Evidence quality" value={data.evidence_quality_score != null ? Math.round(data.evidence_quality_score) : '—'} suffix="%" />
        <StatTile label="IC readiness" value={data.deal_readiness_score != null ? Math.round(data.deal_readiness_score) : '—'} suffix="%"
          chip={data.deal_readiness_status} chipTone={data.deal_readiness_score != null && data.deal_readiness_score >= 70 ? 'success' : 'warning'} />
      </div>

      {/* Domain risk meters */}
      <div className="rounded-xl bg-bg-card border border-border p-4">
        <SectionHead Icon={ListChecks} title="Domain risk — committee weighting" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3.5">
          <RiskMeter label="Financial" weight="30%" score={s.financial} />
          <RiskMeter label="Legal" weight="25%" score={s.legal} />
          <RiskMeter label="Technical" weight="25%" score={s.technical} />
          <RiskMeter label="Market" weight="20%" score={s.market} />
        </div>
      </div>

      {/* Churn stress test */}
      {scen?.client_name && (
        <div className="rounded-xl bg-bg-card border border-border p-4">
          <SectionHead Icon={TrendingDown} title={`Stress test — ${scen.client_name} churns`} />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div>
              <p className="text-[9.5px] text-text-muted">Revenue at risk</p>
              <p className="text-[14px] font-semibold text-text-primary">{fmtMoney(scen.churn_revenue_loss)}
                <span className="text-[10px] text-text-muted font-normal"> ({scen.concentration_pct}% of ARR)</span></p>
            </div>
            <div>
              <p className="text-[9.5px] text-text-muted">Valuation impact</p>
              <p className="text-[14px] font-semibold text-text-primary">{fmtMoney(scen.current_valuation)} → {fmtMoney(scen.new_valuation)}</p>
            </div>
            <div>
              <p className="text-[9.5px] text-text-muted">Post-churn runway</p>
              <p className="text-[14px] font-semibold text-text-primary">{scen.new_runway?.toFixed(1)} <span className="text-[10px] text-text-muted font-normal">months</span></p>
            </div>
            <div>
              <p className="text-[9.5px] text-text-muted">Survival outlook</p>
              <span className={`inline-block mt-0.5 px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider ${
                scen.survival_classification === 'High Risk' ? 'bg-danger-soft text-danger' : 'bg-warning-soft text-warning'}`}>
                {scen.survival_classification}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Contradictions & gaps */}
      <div className="rounded-xl bg-bg-card border border-border p-4">
        <SectionHead Icon={AlertTriangle} title="Contradictions & evidence gaps" />
        {data.contradictions.length === 0 && data.missing_gaps.length === 0 ? (
          <p className="text-[11px] text-text-muted italic">None detected across the pitch evidence.</p>
        ) : (
          <div className="space-y-2">
            {data.contradictions.map((c, i) => (
              <div key={`c${i}`} className="flex items-start gap-2">
                <span className={`px-1.5 py-0.5 rounded text-[8.5px] font-bold uppercase shrink-0 mt-0.5 ${
                  c.severity === 'Critical' ? 'bg-danger-soft text-danger' : 'bg-warning-soft text-warning'}`}>
                  {c.severity || 'Flag'}
                </span>
                <p className="text-[11px] text-text-secondary leading-relaxed">{c.message}</p>
              </div>
            ))}
            {data.missing_gaps.map((g, i) => (
              <div key={`g${i}`} className="flex items-start gap-2">
                <span className="px-1.5 py-0.5 rounded text-[8.5px] font-bold uppercase bg-bg-muted text-text-muted shrink-0 mt-0.5">Gap</span>
                <p className="text-[11px] text-text-secondary leading-relaxed">{typeof g === 'string' ? g : g.message}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Auto-generated founder questions */}
      {questionRoles.length > 0 && (
        <div className="rounded-xl bg-bg-card border border-border p-4">
          <SectionHead Icon={HelpCircle} title="Questions for the founders" />
          <div className="space-y-3">
            {questionRoles.map(([role, qs]) => (
              <div key={role}>
                <p className="text-[9.5px] font-bold font-mono uppercase tracking-wider text-accent mb-1">{ROLE_LABELS[role] || role}</p>
                <ul className="space-y-1">
                  {qs.map((q, i) => (
                    <li key={i} className="flex items-start gap-2 text-[11px] text-text-secondary leading-relaxed">
                      <span className="text-accent shrink-0">•</span>{q}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Diligence priorities */}
      {data.diligence_priorities.length > 0 && (
        <div className="rounded-xl bg-bg-card border border-border p-4">
          <SectionHead Icon={ListChecks} title="Diligence priorities" />
          <div className="space-y-2">
            {data.diligence_priorities.map((p, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className={`px-1.5 py-0.5 rounded text-[8.5px] font-bold uppercase shrink-0 mt-0.5 ${PRIORITY_TONE[p.priority || 'Low'] || PRIORITY_TONE.Low}`}>
                  {p.priority}
                </span>
                <div className="min-w-0">
                  <p className="text-[11px] text-text-secondary leading-relaxed">{p.action}</p>
                  <p className="text-[9px] font-mono text-text-muted">{p.domain} · owner: {p.owner}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default DealIntel
