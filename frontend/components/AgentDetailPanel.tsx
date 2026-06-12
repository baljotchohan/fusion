// components/AgentDetailPanel.tsx — Diligence Binders: expandable partner report cards.
'use client'

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, Check, Circle, Loader2 } from 'lucide-react'
import { AGENTS, AgentMeta } from '../lib/agents'
import { AgentStatus } from '../hooks/useAgentWebSocket'

/* ------------------------------------------------------------------ */
/*  Status badge config                                                */
/* ------------------------------------------------------------------ */

const STATUS_BADGE: Record<AgentStatus, { label: string; bg: string; text: string; dot: string }> = {
  idle:    { label: 'Standby',  bg: 'bg-bg-muted',       text: 'text-text-muted',  dot: 'bg-text-muted' },
  working: { label: 'Auditing', bg: 'bg-warning-soft',   text: 'text-warning',     dot: 'bg-warning animate-pulse' },
  done:    { label: 'Complete', bg: 'bg-success-soft',   text: 'text-success',     dot: 'bg-success' },
  alert:   { label: 'Alert',    bg: 'bg-danger-soft',    text: 'text-danger',      dot: 'bg-danger animate-pulse' },
}

/* ------------------------------------------------------------------ */
/*  Left-border accent color per agent name                            */
/* ------------------------------------------------------------------ */

const AGENT_ACCENT: Record<string, string> = {
  managing_partner:  'border-l-blue-500',
  financial_partner: 'border-l-purple-500',
  legal_partner:     'border-l-amber-500',
  technical_partner: 'border-l-cyan-500',
  market_partner:    'border-l-emerald-500',
}

const AGENT_ICON_BG: Record<string, string> = {
  managing_partner:  'bg-blue-500/10',
  financial_partner: 'bg-purple-500/10',
  legal_partner:     'bg-amber-500/10',
  technical_partner: 'bg-cyan-500/10',
  market_partner:    'bg-emerald-500/10',
}

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */

interface AgentDetailPanelProps {
  agentStates: Record<string, AgentStatus>
  agentOutputs: Record<string, Record<string, any>>
  devMode: boolean
}

/* ------------------------------------------------------------------ */
/*  Report formatter — converts raw output into readable paragraphs    */
/* ------------------------------------------------------------------ */

function parseBold(str: string): React.ReactNode {
  const parts: React.ReactNode[] = []
  let lastIndex = 0
  const regex = /\*\*([^*]+)\*\*/g
  let match
  while ((match = regex.exec(str)) !== null) {
    if (match.index > lastIndex) {
      parts.push(str.substring(lastIndex, match.index))
    }
    parts.push(
      <strong key={match.index} className="font-bold text-text-primary dark:text-white">
        {match[1]}
      </strong>
    )
    lastIndex = regex.lastIndex
  }
  if (lastIndex < str.length) {
    parts.push(str.substring(lastIndex))
  }
  return parts.length > 0 ? <>{parts}</> : str
}

function formatReport(output?: Record<string, any>): React.ReactNode | null {
  if (!output) return null

  // If there's a "report" string, parse it into sections
  if (output.report && typeof output.report === 'string') {
    const raw = output.report as string
    const lines = raw.split('\n')
    const elements: React.ReactNode[] = []

    lines.forEach((line, i) => {
      const trimmed = line.trim()
      if (!trimmed) {
        elements.push(<div key={i} className="h-2" />)
      } else if (/^#{1,3}\s/.test(trimmed) || /^[A-Z][A-Z\s&/:—-]{4,}$/.test(trimmed)) {
        // Section header
        const heading = trimmed.replace(/^#{1,3}\s*/, '').replace(/[*_`]/g, '')
        elements.push(
          <h4 key={i} className="text-[11px] font-bold text-text-primary tracking-wide uppercase mt-3 mb-1 first:mt-0">
            {heading}
          </h4>
        )
      } else if (/^[-•*]\s/.test(trimmed)) {
        // Bullet point
        const content = trimmed.replace(/^[-•*]\s*/, '')
        elements.push(
          <div key={i} className="flex items-start gap-2 py-0.5">
            <span className="text-accent mt-0.5 shrink-0">•</span>
            <span className="text-[10.5px] text-text-secondary leading-relaxed">{parseBold(content)}</span>
          </div>
        )
      } else {
        // Regular paragraph
        elements.push(
          <p key={i} className="text-[10.5px] text-text-secondary leading-relaxed">
            {parseBold(trimmed)}
          </p>
        )
      }
    })

    return <>{elements}</>
  }

  // If there's a current_action field (working state)
  if (output.current_action) {
    return (
      <p className="text-[10.5px] text-text-secondary leading-relaxed italic">
        Currently analyzing: {output.current_action}
      </p>
    )
  }

  // If there's an error
  if (output.error) {
    return (
      <div className="rounded-lg bg-danger-soft p-3">
        <p className="text-[10.5px] text-danger font-medium">
          Review blocked: {output.error}
        </p>
      </div>
    )
  }

  // Fallback: iterate over keys and render as clean sections
  const keys = Object.keys(output).filter(k => k !== 'timestamp')
  if (keys.length === 0) return null

  return (
    <>
      {keys.map(key => {
        const value = output[key]
        const heading = key
          .replace(/_/g, ' ')
          .replace(/\b\w/g, c => c.toUpperCase())

        if (typeof value === 'string') {
          return (
            <div key={key} className="mb-2">
              <h4 className="text-[11px] font-bold text-text-primary tracking-wide uppercase mb-1">{heading}</h4>
              <p className="text-[10.5px] text-text-secondary leading-relaxed">{parseBold(value)}</p>
            </div>
          )
        }

        if (Array.isArray(value)) {
          return (
            <div key={key} className="mb-2">
              <h4 className="text-[11px] font-bold text-text-primary tracking-wide uppercase mb-1">{heading}</h4>
              {value.map((item, i) => (
                <div key={i} className="flex items-start gap-2 py-0.5">
                  <span className="text-accent mt-0.5 shrink-0">•</span>
                  <span className="text-[10.5px] text-text-secondary leading-relaxed">
                    {typeof item === 'string' ? parseBold(item) : JSON.stringify(item)}
                  </span>
                </div>
              ))}
            </div>
          )
        }

        return null
      })}
    </>
  )
}

/* ------------------------------------------------------------------ */
/*  Checklist Item                                                     */
/* ------------------------------------------------------------------ */

function ChecklistItem({ label, status }: { label: string; status: AgentStatus }) {
  return (
    <div className="flex items-center gap-2.5 py-1">
      {status === 'done' ? (
        <div className="w-4 h-4 rounded-full bg-success/15 flex items-center justify-center shrink-0">
          <Check className="w-2.5 h-2.5 text-success" strokeWidth={3} />
        </div>
      ) : status === 'working' ? (
        <Loader2 className="w-4 h-4 text-warning animate-spin shrink-0" strokeWidth={2.5} />
      ) : (
        <Circle className="w-4 h-4 text-text-muted shrink-0" strokeWidth={1.5} />
      )}
      <span
        className={`text-[10.5px] leading-snug ${
          status === 'done'
            ? 'text-text-primary font-medium'
            : status === 'working'
            ? 'text-text-secondary'
            : 'text-text-muted'
        }`}
      >
        {label}
      </span>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Single Binder Card                                                 */
/* ------------------------------------------------------------------ */

function BinderCard({
  agent,
  status,
  output,
  devMode,
  isExpanded,
  onToggle,
}: {
  agent: AgentMeta
  status: AgentStatus
  output?: Record<string, any>
  devMode: boolean
  isExpanded: boolean
  onToggle: () => void
}) {
  const badge = STATUS_BADGE[status] || STATUS_BADGE.idle
  const accent = AGENT_ACCENT[agent.name] || 'border-l-slate-400'
  const iconBg = AGENT_ICON_BG[agent.name] || 'bg-bg-muted'
  const report = formatReport(output)

  return (
    <div
      className={`rounded-xl bg-bg-card border border-border shadow-sm overflow-hidden border-l-4 ${accent} transition-shadow hover:shadow-md`}
    >
      {/* Header — always visible */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3.5 px-4 py-3.5 cursor-pointer group text-left"
      >
        {/* Agent Icon */}
        <div className={`w-10 h-10 rounded-full ${iconBg} flex items-center justify-center shrink-0 text-lg select-none`}>
          {agent.icon}
        </div>

        {/* Name + Role */}
        <div className="flex-1 min-w-0">
          <h3 className="text-[13px] font-semibold text-text-primary truncate tracking-tight">
            {agent.displayName}
          </h3>
          <p className="text-[10px] text-text-muted font-mono truncate">
            {agent.role}
          </p>
        </div>

        {/* Status Badge */}
        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full shrink-0 ${badge.bg}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${badge.dot}`} />
          <span className={`text-[9px] font-bold font-mono uppercase tracking-wider ${badge.text}`}>
            {badge.label}
          </span>
        </div>

        {/* Chevron */}
        <motion.div
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="shrink-0"
        >
          <ChevronDown className="w-4 h-4 text-text-muted group-hover:text-text-secondary transition-colors" />
        </motion.div>
      </button>

      {/* Expandable body */}
      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 pt-1 border-t border-border space-y-4">
              {/* Diligence Checklist */}
              {agent.checklist.length > 0 && (
                <div>
                  <span className="text-[9px] font-bold font-mono tracking-widest text-text-muted uppercase block mb-1.5">
                    Diligence Checklist
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4">
                    {agent.checklist.map((item, idx) => (
                      <ChecklistItem key={idx} label={item} status={status} />
                    ))}
                  </div>
                </div>
              )}

              {/* Report Output */}
              {report && (
                <div>
                  <span className="text-[9px] font-bold font-mono tracking-widest text-text-muted uppercase block mb-2">
                    Audit Report
                  </span>
                  <div className="rounded-xl bg-bg-subtle border border-border p-4 max-h-72 overflow-y-auto">
                    {report}
                  </div>
                </div>
              )}

              {/* No output yet */}
              {!report && status === 'idle' && (
                <p className="text-[10.5px] text-text-muted italic">
                  Awaiting pitch deck ingest to begin diligence…
                </p>
              )}

              {/* Dev mode: raw JSON */}
              {devMode && output && (
                <div>
                  <span className="text-[9px] font-bold font-mono tracking-widest text-text-muted uppercase block mb-1.5">
                    Raw Output
                  </span>
                  <pre className="text-[9px] font-mono bg-bg-muted text-accent-cyan p-3 rounded-xl overflow-auto max-h-36 border border-border">
                    {JSON.stringify(output, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Main Panel                                                         */
/* ------------------------------------------------------------------ */

export function AgentDetailPanel({ agentStates, agentOutputs, devMode }: AgentDetailPanelProps) {
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null)

  function toggle(name: string) {
    setExpandedAgent(prev => (prev === name ? null : name))
  }

  return (
    <div className="flex flex-col gap-3">
      {AGENTS.map(agent => {
        const status = agentStates[agent.name] || 'idle'
        const output = agentOutputs[agent.name]
        const isExpanded = expandedAgent === agent.name

        return (
          <BinderCard
            key={agent.name}
            agent={agent}
            status={status}
            output={output}
            devMode={devMode}
            isExpanded={isExpanded}
            onToggle={() => toggle(agent.name)}
          />
        )
      })}
    </div>
  )
}

export default AgentDetailPanel
