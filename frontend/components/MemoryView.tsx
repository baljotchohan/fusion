// components/MemoryView.tsx — insights & intelligence view.
import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Lightbulb, ShieldAlert } from 'lucide-react'

/* ── Sub-tab type ── */
type Tab = 'findings' | 'patterns'

/* ── Severity / Category colour maps ── */
const SEVERITY_STYLE: Record<string, string> = {
  High:   'bg-danger-soft text-danger',
  Medium: 'bg-warning-soft text-warning',
  Low:    'bg-success-soft text-success',
}

const CATEGORY_STYLE: Record<string, string> = {
  Financial:  'bg-accent-amber-soft  text-accent-amber',
  Legal:      'bg-accent-purple-soft text-accent-purple',
  Technical:  'bg-accent-cyan-soft   text-accent-cyan',
  Market:     'bg-accent-green-soft  text-accent-green',
}

/* ── Mock data — Key Findings ── */
interface Insight {
  id: number
  category: 'Financial' | 'Legal' | 'Technical' | 'Market'
  title: string
  description: string
  severity: 'High' | 'Medium' | 'Low'
}

const INSIGHTS: Insight[] = [
  {
    id: 1,
    category: 'Financial',
    title: 'Revenue Concentration Risk',
    description: 'Top 3 clients account for over 68% of total ARR, creating significant dependency.',
    severity: 'High',
  },
  {
    id: 2,
    category: 'Legal',
    title: 'Pending Regulatory Review',
    description: 'State-level money transmitter license application still under review in 4 jurisdictions.',
    severity: 'High',
  },
  {
    id: 3,
    category: 'Technical',
    title: 'Infrastructure Scalability',
    description: 'Current architecture supports up to 50K concurrent users; growth plan targets 200K.',
    severity: 'Medium',
  },
  {
    id: 4,
    category: 'Market',
    title: 'Emerging Competitor Pressure',
    description: 'Two well-funded entrants raised Series B rounds in the same vertical this quarter.',
    severity: 'Medium',
  },
  {
    id: 5,
    category: 'Financial',
    title: 'Gross Margin Compression',
    description: 'Margins declined 8 points YoY due to increased cloud infrastructure costs.',
    severity: 'Medium',
  },
  {
    id: 6,
    category: 'Legal',
    title: 'IP Assignment Gaps',
    description: 'Two early contractor agreements lack formal IP assignment clauses.',
    severity: 'Low',
  },
]

/* ── Mock data — Risk Patterns ── */
interface Pattern {
  id: number
  name: string
  frequency: number
  description: string
}

const PATTERNS: Pattern[] = [
  {
    id: 1,
    name: 'Customer Concentration',
    frequency: 14,
    description: 'Repeatedly flagged when a small number of clients drive the majority of revenue.',
  },
  {
    id: 2,
    name: 'Regulatory Timing Risk',
    frequency: 9,
    description: 'Deals in fintech and health-tech often stall due to unresolved licensing timelines.',
  },
  {
    id: 3,
    name: 'Founder Vesting Gaps',
    frequency: 7,
    description: 'Incomplete vesting schedules or single-trigger acceleration clauses surface frequently.',
  },
  {
    id: 4,
    name: 'Burn Rate Overrun',
    frequency: 11,
    description: 'Companies projecting 18-month runway frequently fall short due to underestimated OpEx.',
  },
  {
    id: 5,
    name: 'TAM Inflation',
    frequency: 6,
    description: 'Founder-reported TAM figures consistently exceed independent third-party estimates.',
  },
]

/* ── Animation ── */
const listVariants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.05 } },
}
const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  show:   { opacity: 1, y: 0, transition: { duration: 0.3 } },
}

interface MemoryViewProps {
  defaultTab?: 'findings' | 'patterns' | 'incidents'
}

/* ── Component ── */
export default function MemoryView({ defaultTab = 'findings' }: MemoryViewProps) {
  const [tab, setTab] = useState<Tab>(defaultTab === 'incidents' ? 'findings' : defaultTab)

  return (
    <div className="h-full overflow-y-auto px-6 py-8 max-w-3xl mx-auto space-y-8">
      {/* ── Header ── */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
        <h1 className="text-[22px] font-bold text-text-primary tracking-tight">
          Insights &amp; Intelligence
        </h1>
        <p className="text-[13px] text-text-secondary mt-1">
          Accumulated knowledge from past evaluations
        </p>
      </motion.div>

      {/* ── Sub-tabs ── */}
      <div className="flex gap-2">
        {([
          { key: 'findings' as Tab, label: 'Key Findings',  Icon: Lightbulb },
          { key: 'patterns' as Tab, label: 'Risk Patterns', Icon: ShieldAlert },
        ]).map(({ key, label, Icon }) => {
          const active = tab === key
          return (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`
                inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-[12px] font-semibold
                transition-all duration-200 border
                ${active
                  ? 'bg-accent text-white border-accent shadow-sm'
                  : 'bg-bg-card text-text-secondary border-border hover:bg-bg-subtle'}
              `}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </button>
          )
        })}
      </div>

      {/* ── Content ── */}
      <AnimatePresence mode="wait">
        {tab === 'findings' ? (
          <motion.div
            key="findings"
            variants={listVariants}
            initial="hidden"
            animate="show"
            exit={{ opacity: 0 }}
            className="space-y-3"
          >
            {INSIGHTS.map(insight => (
              <motion.div
                key={insight.id}
                variants={itemVariants}
                className="rounded-xl bg-bg-card border border-border shadow-sm p-5 flex flex-col gap-2
                           hover:shadow-md transition-shadow"
              >
                {/* top row — badges */}
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${CATEGORY_STYLE[insight.category]}`}>
                    {insight.category}
                  </span>
                  <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${SEVERITY_STYLE[insight.severity]}`}>
                    {insight.severity}
                  </span>
                </div>

                {/* title + description */}
                <p className="text-[14px] font-semibold text-text-primary leading-snug">
                  {insight.title}
                </p>
                <p className="text-[12px] text-text-secondary leading-relaxed">
                  {insight.description}
                </p>
              </motion.div>
            ))}
          </motion.div>
        ) : (
          <motion.div
            key="patterns"
            variants={listVariants}
            initial="hidden"
            animate="show"
            exit={{ opacity: 0 }}
            className="space-y-3"
          >
            {PATTERNS.map(pattern => (
              <motion.div
                key={pattern.id}
                variants={itemVariants}
                className="rounded-xl bg-bg-card border border-border shadow-sm p-5
                           hover:shadow-md transition-shadow"
              >
                <div className="flex items-center justify-between mb-2">
                  <p className="text-[14px] font-semibold text-text-primary">
                    {pattern.name}
                  </p>
                  <span className="text-[11px] font-bold text-accent bg-accent-soft px-2.5 py-0.5 rounded-full">
                    {pattern.frequency} occurrences
                  </span>
                </div>
                <p className="text-[12px] text-text-secondary leading-relaxed">
                  {pattern.description}
                </p>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* bottom breathing room */}
      <div className="h-4" />
    </div>
  )
}
