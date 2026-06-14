// components/MemoryView.tsx — real deal history & learned-pattern intelligence.
// All data is fetched live from the backend memory graph. Nothing is mocked:
// if the team has not evaluated any deals yet, the view shows an empty state.
import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Lightbulb, ShieldAlert, Inbox } from 'lucide-react'
import { API_BASE } from '../lib/agents'

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

  useEffect(() => {
    let alive = true
    async function load() {
      setLoading(true)
      try {
        const [incRes, statRes] = await Promise.all([
          fetch(`${API_BASE}/api/v1/incidents`).then(r => r.json()).catch(() => null),
          fetch(`${API_BASE}/api/v1/memory/stats`).then(r => r.json()).catch(() => null),
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
            <button key={key} onClick={() => setTab(key)}
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
                <motion.div key={inc.incident_id} variants={itemVariants}
                  className="rounded-xl bg-bg-card border border-border shadow-sm p-5 flex flex-col gap-2 hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-[14px] font-semibold text-text-primary leading-snug">{inc.company || 'Unknown Company'}</p>
                    {inc.verdict && (
                      <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${VERDICT_STYLE[inc.verdict] || 'bg-bg-subtle text-text-secondary'}`}>
                        {inc.verdict.replace(/_/g, ' ')}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-[11px] text-text-secondary">
                    <span>{fmtDate(inc.created_at)}</span>
                    <span>·</span>
                    <span>{inc.findings} partner {inc.findings === 1 ? 'report' : 'reports'}</span>
                  </div>
                  {inc.final_decision && (
                    <pre className="text-[11px] font-mono text-text-secondary whitespace-pre bg-bg-subtle p-3 rounded-lg border border-border mt-2 overflow-x-auto leading-normal">
                      {inc.final_decision.replace(/^```\n?/, '').replace(/\n?```$/, '')}
                    </pre>
                  )}
                </motion.div>
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

      <div className="h-4" />
    </div>
  )
}
