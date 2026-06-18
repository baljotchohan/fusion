// components/MemoryView.tsx — real deal history & learned-pattern intelligence.
// All data is fetched live from the backend memory graph. Nothing is mocked:
// if the team has not evaluated any deals yet, the view shows an empty state.
import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Lightbulb, ShieldAlert, Inbox, X, Download, FileText, Eye, ChevronRight } from 'lucide-react'
import { API_BASE, AGENTS } from '../lib/agents'
import { apiFetch, logActivity } from '../lib/apiFetch'

type Tab = 'findings' | 'patterns'

/* ── Verdict colour map ── */
const VERDICT_STYLE: Record<string, string> = {
  PASS:        'bg-danger-soft text-danger',
  CONDITIONAL: 'bg-warning-soft text-warning',
  INVEST:      'bg-success-soft text-success',
  INSUFFICIENT_EVIDENCE: 'bg-bg-subtle text-text-secondary',
}

interface Incident {
  incident_id: string
  company: string
  verdict: string | null
  trigger?: string
  findings: number
  final_decision: string | null
  created_at: string | null
}

interface MemoryViewProps {
  defaultTab?: 'findings' | 'patterns' | 'incidents'
}

const listVariants = { hidden: {}, show: { transition: { staggerChildren: 0.05 } } }
const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
}

function fmtDate(iso: string | null): string {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  } catch { return iso }
}

function EmptyState({ icon: Icon, title, hint }: { icon: typeof Inbox; title: string; hint: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center text-center py-20 gap-3"
    >
      <div className="w-12 h-12 rounded-full bg-bg-subtle flex items-center justify-center">
        <Icon className="w-6 h-6 text-text-secondary" />
      </div>
      <p className="text-[14px] font-semibold text-text-primary">{title}</p>
      <p className="text-[12px] text-text-secondary max-w-xs leading-relaxed">{hint}</p>
    </motion.div>
  )
}

export default function MemoryView({ defaultTab = 'findings' }: MemoryViewProps) {
  const [tab, setTab] = useState<Tab>(defaultTab === 'incidents' ? 'findings' : defaultTab)
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [patterns, setPatterns] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    async function load() {
      setLoading(true)
      try {
        const [incRes, statRes] = await Promise.all([
          apiFetch(`${API_BASE}/api/v1/incidents`).then(r => r.json()).catch(() => null),
          apiFetch(`${API_BASE}/api/v1/memory/stats`).then(r => r.json()).catch(() => null),
        ])
        if (!alive) return
        if (incRes && Array.isArray(incRes.incidents)) setIncidents(incRes.incidents)
        if (statRes && statRes.learned_patterns) setPatterns(statRes.learned_patterns)
      } finally {
        if (alive) setLoading(false)
      }
    }
    load()
    return () => { alive = false }
  }, [])

  const patternEntries = Object.entries(patterns).filter(([, n]) => (n as number) > 0)

  return (
    <div className="h-full overflow-y-auto px-6 py-8 max-w-3xl mx-auto space-y-8">
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
        <h1 className="text-[22px] font-bold text-text-primary tracking-tight">Insights &amp; Intelligence</h1>
        <p className="text-[13px] text-text-secondary mt-1">Accumulated from deals this committee has actually evaluated</p>
      </motion.div>

      <div className="flex gap-2">
        {([
          { key: 'findings' as Tab, label: 'Deal History',   Icon: Lightbulb },
          { key: 'patterns' as Tab, label: 'Risk Patterns',  Icon: ShieldAlert },
        ]).map(({ key, label, Icon }) => {
          const active = tab === key
          return (
            <button key={key} onClick={() => { setTab(key); logActivity('memory_tab_switched', { tab: key }) }}
              className={`inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-[12px] font-semibold transition-all duration-200 border
                ${active ? 'bg-accent text-white border-accent shadow-sm' : 'bg-bg-card text-text-secondary border-border hover:bg-bg-subtle'}`}>
              <Icon className="w-3.5 h-3.5" />{label}
            </button>
          )
        })}
      </div>

      {loading ? (
        <div className="text-[13px] text-text-secondary py-16 text-center">Loading…</div>
      ) : (
        <AnimatePresence mode="wait">
          {tab === 'findings' ? (
            <motion.div key="findings" variants={listVariants} initial="hidden" animate="show" exit={{ opacity: 0 }} className="space-y-3">
              {incidents.length === 0 ? (
                <EmptyState icon={Inbox} title="No deals evaluated yet"
                  hint="Upload a pitch or trigger a deal. Every committee verdict is recorded here with its risk profile." />
              ) : incidents.map(inc => (
                <motion.button key={inc.incident_id} variants={itemVariants}
                  onClick={() => { setSelectedId(inc.incident_id); logActivity('memory_deal_clicked', { incidentId: inc.incident_id, company: inc.company }) }}
                  className="w-full text-left rounded-xl bg-bg-card border border-border shadow-sm p-5 flex flex-col gap-2 hover:shadow-md hover:border-accent/40 transition-all cursor-pointer group">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-[14px] font-semibold text-text-primary leading-snug">{inc.company || 'Unknown Company'}</p>
                    <div className="flex items-center gap-2 shrink-0">
                      {inc.verdict && (
                        <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${VERDICT_STYLE[inc.verdict] || 'bg-bg-subtle text-text-secondary'}`}>
                          {inc.verdict.replace(/_/g, ' ')}
                        </span>
                      )}
                      <ChevronRight className="w-4 h-4 text-text-muted group-hover:text-accent transition-colors" />
                    </div>
                  </div>
                  <div className="flex items-center gap-3 text-[11px] text-text-secondary">
                    <span>{fmtDate(inc.created_at)}</span>
                    <span>·</span>
                    <span>{inc.findings} partner {inc.findings === 1 ? 'report' : 'reports'}</span>
                    <span>·</span>
                    <span className="text-accent font-medium">View details</span>
                  </div>
                  {inc.final_decision && (
                    <pre className="text-[11px] font-mono text-text-secondary whitespace-pre bg-bg-subtle p-3 rounded-lg border border-border mt-2 overflow-x-auto leading-normal">
                      {inc.final_decision.replace(/^```\n?/, '').replace(/\n?```$/, '')}
                    </pre>
                  )}
                </motion.button>
              ))}
            </motion.div>
          ) : (
            <motion.div key="patterns" variants={listVariants} initial="hidden" animate="show" exit={{ opacity: 0 }} className="space-y-3">
              {patternEntries.length === 0 ? (
                <EmptyState icon={ShieldAlert} title="No risk patterns learned yet"
                  hint="As the committee evaluates more deals, recurring red-flag patterns it learns will appear here." />
              ) : patternEntries.map(([name, freq]) => (
                <motion.div key={name} variants={itemVariants}
                  className="rounded-xl bg-bg-card border border-border shadow-sm p-5 hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-[14px] font-semibold text-text-primary capitalize">{name.replace(/_/g, ' ')}</p>
                    <span className="text-[11px] font-bold text-accent bg-accent-soft px-2.5 py-0.5 rounded-full">
                      {freq as number} {(freq as number) === 1 ? 'occurrence' : 'occurrences'}
                    </span>
                  </div>
                  <p className="text-[12px] text-text-secondary leading-relaxed">
                    Recurring risk pattern the committee has flagged across evaluated deals.
                  </p>
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      )}

      <AnimatePresence>
        {selectedId && (
          <HistoryDetail incidentId={selectedId} onClose={() => setSelectedId(null)} />
        )}
      </AnimatePresence>

      <div className="h-4" />
    </div>
  )
}

/* ── Agent metadata lookup for the detail view ── */
const AGENT_META: Record<string, { displayName: string; icon: string }> = Object.fromEntries(
  AGENTS.map(a => [a.name, { displayName: a.displayName, icon: a.icon }])
)
function agentLabel(key: string) {
  return AGENT_META[key]?.displayName || key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}
function agentIcon(key: string) {
  return AGENT_META[key]?.icon || '•'
}

function parseVerdict(text: string | null): string | null {
  const m = /decision\s*\*?\*?\s*:\s*\*?\*?\s*([a-z_]+)/i.exec(text || '')
  return m ? m[1].toUpperCase() : null
}

interface IncidentDetail {
  metadata?: Record<string, any>
  timeline?: { agent: string; finding: string; severity?: number; timestamp?: string }[]
  final_decision?: string | null
  created_at?: string | null
}

function HistoryDetail({ incidentId, onClose }: { incidentId: string; onClose: () => void }) {
  const [data, setData] = useState<IncidentDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [preview, setPreview] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  useEffect(() => {
    let alive = true
    setLoading(true)
    apiFetch(`${API_BASE}/api/v1/incident/${incidentId}`)
      .then(r => r.json())
      .then(d => { if (alive) setData(d) })
      .catch(() => { if (alive) setData(null) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [incidentId])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const meta = data?.metadata || {}
  const rawCo = meta.company
  const company = typeof rawCo === 'object' && rawCo ? (rawCo.value || rawCo.name || 'Unknown') : (rawCo || 'Unknown')
  const verdict = parseVerdict(data?.final_decision || null)

  const reportUrl = (fmt: 'md' | 'pdf') => `${API_BASE}/api/v1/generate-report?incident_id=${incidentId}&format=${fmt}`
  const download = (fmt: 'md' | 'pdf') => {
    logActivity('memory_report_download_clicked', { incidentId, company, format: fmt })
    window.open(reportUrl(fmt), '_blank')
  }
  const loadPreview = async () => {
    if (preview) { setPreview(null); return }
    setPreviewLoading(true)
    try {
      logActivity('memory_report_preview_clicked', { incidentId, company })
      const r = await apiFetch(reportUrl('md'))
      setPreview(await r.text())
    } catch { setPreview('Could not load the report preview.') }
    finally { setPreviewLoading(false) }
  }
  const timeline = Array.isArray(data?.timeline) ? data!.timeline! : []

  // Group findings per partner for the "research" section.
  const byAgent = new Map<string, typeof timeline>()
  for (const ev of timeline) {
    const k = ev.agent || 'unknown'
    if (!byAgent.has(k)) byAgent.set(k, [])
    byAgent.get(k)!.push(ev)
  }

  return (
    <motion.div
      className="fixed inset-0 z-50 flex"
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
    >
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative ml-auto h-full w-full sm:max-w-2xl bg-bg-base border-l border-border shadow-2xl flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-border shrink-0">
          <div className="flex-1 min-w-0">
            <p className="text-[15px] font-bold text-text-primary truncate">{company}</p>
            <p className="text-[11px] text-text-muted">{fmtDate(data?.created_at || null)} · {timeline.length} partner {timeline.length === 1 ? 'report' : 'reports'}</p>
          </div>
          {verdict && (
            <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${VERDICT_STYLE[verdict] || 'bg-bg-subtle text-text-secondary'}`}>
              {verdict.replace(/_/g, ' ')}
            </span>
          )}
          <button onClick={onClose} className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-bg-muted text-text-muted shrink-0">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-6">
          {loading ? (
            <div className="text-[13px] text-text-secondary py-16 text-center">Loading deal record…</div>
          ) : !data ? (
            <div className="text-[13px] text-text-secondary py-16 text-center">Could not load this deal.</div>
          ) : (
            <>
              {/* Downloads */}
              <div className="flex flex-wrap gap-2">
                <button onClick={loadPreview}
                  className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-border bg-bg-card hover:bg-bg-muted text-text-primary text-[12px] font-semibold transition">
                  <Eye className="w-3.5 h-3.5 text-text-muted" />{preview ? 'Hide preview' : (previewLoading ? 'Loading…' : 'Preview report')}
                </button>
                <button onClick={() => download('pdf')}
                  className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-accent text-white hover:bg-accent/90 text-[12px] font-semibold shadow-sm transition">
                  <Download className="w-3.5 h-3.5" />Download PDF
                </button>
                <button onClick={() => download('md')}
                  className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-border bg-bg-card hover:bg-bg-muted text-text-primary text-[12px] font-semibold transition">
                  <FileText className="w-3.5 h-3.5 text-text-muted" />Download Markdown
                </button>
              </div>

              {preview && (
                <pre className="text-[11px] font-mono text-text-secondary whitespace-pre-wrap bg-bg-subtle p-4 rounded-xl border border-border max-h-[360px] overflow-y-auto leading-normal">
                  {preview}
                </pre>
              )}

              {/* Per-partner research */}
              <section>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-3">Partner Research & Findings</p>
                {byAgent.size === 0 ? (
                  <p className="text-[12px] text-text-secondary">No partner findings recorded for this deal.</p>
                ) : (
                  <div className="space-y-3">
                    {[...byAgent.entries()].map(([agent, evs]) => {
                      const latest = evs[evs.length - 1]
                      return (
                        <div key={agent} className="rounded-xl bg-bg-card border border-border p-4">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="text-[16px] leading-none">{agentIcon(agent)}</span>
                            <p className="text-[13px] font-semibold text-text-primary">{agentLabel(agent)}</p>
                            {typeof latest.severity === 'number' && (
                              <span className="ml-auto text-[10px] font-semibold text-text-muted">Severity {latest.severity}/10</span>
                            )}
                          </div>
                          <p className="text-[12px] text-text-secondary whitespace-pre-wrap leading-relaxed">{latest.finding}</p>
                        </div>
                      )
                    })}
                  </div>
                )}
              </section>

              {/* Debate / collaboration timeline */}
              <section>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-3">Committee Timeline</p>
                <ol className="relative border-l border-border ml-2 space-y-4">
                  {timeline.map((ev, i) => (
                    <li key={i} className="ml-4">
                      <span className="absolute -left-[5px] mt-1.5 w-2.5 h-2.5 rounded-full bg-accent" />
                      <div className="flex items-center gap-2">
                        <span className="text-[13px] leading-none">{agentIcon(ev.agent)}</span>
                        <p className="text-[12px] font-semibold text-text-primary">{agentLabel(ev.agent)}</p>
                        <span className="text-[10px] text-text-muted">{fmtDate(ev.timestamp || null)}</span>
                      </div>
                      <p className="text-[11.5px] text-text-secondary mt-1 line-clamp-3 leading-relaxed">{ev.finding}</p>
                    </li>
                  ))}
                </ol>
              </section>

              {/* Verdict memo */}
              {data.final_decision && (
                <section>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-3">Committee Verdict Memo</p>
                  <pre className="text-[11px] font-mono text-text-secondary whitespace-pre-wrap bg-bg-subtle p-4 rounded-xl border border-border overflow-x-auto leading-normal">
                    {data.final_decision.replace(/^```\n?/, '').replace(/\n?```$/, '')}
                  </pre>
                </section>
              )}
            </>
          )}
        </div>
      </div>
    </motion.div>
  )
}
