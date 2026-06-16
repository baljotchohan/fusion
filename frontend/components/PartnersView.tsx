// components/PartnersView.tsx — AI Partner Profiles
import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { ChevronDown, CheckCircle2 } from 'lucide-react'
import { AGENTS } from '../lib/agents'

const AGENT_COLORS: Record<string, { bg: string; border: string }> = {
  managing_partner: { bg: 'bg-accent-soft', border: 'border-l-accent' },
  financial_partner: { bg: 'bg-accent-purple-soft', border: 'border-l-accent-purple' },
  legal_partner: { bg: 'bg-accent-amber-soft', border: 'border-l-accent-amber' },
  technical_partner: { bg: 'bg-accent-cyan-soft', border: 'border-l-accent-cyan' },
  market_partner: { bg: 'bg-accent-green-soft', border: 'border-l-accent-green' },
}

const GROUP_LABELS: Record<string, string> = {
  intake: 'Intake',
  analysis: 'Analysis',
  command: 'Command',
  executive: 'Executive',
}

export function PartnersView() {
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null)

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary tracking-tight">Investment Partners</h1>
        <p className="text-text-secondary mt-1">Your AI-powered due diligence team</p>
      </div>

      {/* Partner Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {AGENTS.map((agent, idx) => {
          const colors = AGENT_COLORS[agent.name] || { bg: 'bg-bg-muted', border: 'border-l-border' }
          const isExpanded = expandedAgent === agent.name

          return (
            <motion.div
              key={agent.name}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.08 }}
              className={`rounded-xl bg-bg-card border border-border border-l-4 ${colors.border} shadow-sm overflow-hidden`}
            >
              {/* Header */}
              <div className="p-5">
                <div className="flex items-start gap-4">
                  <div className={`w-12 h-12 rounded-xl ${colors.bg} flex items-center justify-center text-2xl shrink-0`}>
                    {agent.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <h3 className="text-[15px] font-bold text-text-primary">{agent.displayName}</h3>
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-bg-muted text-text-muted">
                        {GROUP_LABELS[agent.group] || agent.group}
                      </span>
                    </div>
                    <p className="text-[12px] text-text-secondary font-medium">{agent.role}</p>
                    <p className="text-[12px] text-text-muted mt-2 leading-relaxed">{agent.plain}</p>
                  </div>
                </div>
              </div>

              {/* Expandable Checklist */}
              <div className="border-t border-border">
                <button
                  onClick={() => setExpandedAgent(isExpanded ? null : agent.name)}
                  className="w-full flex items-center justify-between px-5 py-3 hover:bg-bg-subtle transition-colors"
                >
                  <span className="text-[11px] font-semibold text-text-muted uppercase tracking-wider">Due Diligence Checklist</span>
                  <ChevronDown className={`w-4 h-4 text-text-muted transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`} />
                </button>

                {isExpanded && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="px-5 pb-5"
                  >
                    <ul className="grid grid-cols-2 gap-2">
                      {agent.checklist.map((item, i) => (
                        <li key={i} className="flex items-center gap-2 text-[12px] text-text-secondary">
                          <CheckCircle2 className="w-3.5 h-3.5 text-accent-green shrink-0" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </motion.div>
                )}
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
