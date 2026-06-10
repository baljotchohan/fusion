// components/AgentDetailPanel.tsx — structured, expandable specialist cards.
import React, { useState } from 'react'
import { AGENTS } from '../lib/agents'
import { AgentStatus } from '../hooks/useAgentWebSocket'

const STATUS_META: Record<AgentStatus, { label: string; dot: string; text: string }> = {
  idle:    { label: 'Standby',  dot: 'bg-slate-300 dark:bg-slate-600', text: 'text-slate-400 dark:text-slate-500' },
  working: { label: 'Working',  dot: 'bg-amber-500 animate-pulse',      text: 'text-amber-600 dark:text-amber-400' },
  done:    { label: 'Complete', dot: 'bg-emerald-500',                  text: 'text-emerald-600 dark:text-emerald-400' },
  alert:   { label: 'Error',    dot: 'bg-red-500 animate-pulse',        text: 'text-red-600 dark:text-red-400' },
}

interface AgentDetailPanelProps {
  agentStates: Record<string, AgentStatus>
  agentOutputs: Record<string, Record<string, any>>
  devMode: boolean
}

function reportText(out?: Record<string, any>): string | null {
  if (!out) return null
  if (out.report) return String(out.report)
  if (out.current_action) return `▸ ${out.current_action}`
  if (out.error) return `⚠ ${out.error}`
  return null
}

export function AgentDetailPanel({ agentStates, agentOutputs, devMode }: AgentDetailPanelProps) {
  const [expanded, setExpanded] = useState<string | null>(null)

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 auto-rows-fr">
      {AGENTS.map(agent => {
        const status = agentStates[agent.name] || 'idle'
        const sm = STATUS_META[status]
        const report = reportText(agentOutputs[agent.name])
        const isOpen = expanded === agent.name
        return (
          <div
            key={agent.name}
            className={`rounded-xl border bg-white/60 dark:bg-slate-900/40 transition-all flex flex-col ${
              status === 'working' ? 'border-amber-400/50 shadow-[0_0_0_1px_rgba(251,191,36,0.15)]'
              : status === 'done' ? 'border-emerald-400/40'
              : status === 'alert' ? 'border-red-400/50'
              : 'border-slate-200/60 dark:border-slate-800/60'
            }`}
          >
            <div className="p-3.5 flex flex-col flex-1">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2.5 min-w-0">
                  <span className="text-lg shrink-0">{agent.icon}</span>
                  <div className="min-w-0">
                    <h3 className="text-[12px] font-bold text-slate-800 dark:text-slate-100 truncate">{agent.displayName}</h3>
                    <p className="text-[9px] font-mono text-slate-400 dark:text-slate-500 truncate">{agent.role}</p>
                  </div>
                </div>
                <span className={`flex items-center gap-1.5 text-[9px] font-mono uppercase tracking-wider shrink-0 ${sm.text}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${sm.dot}`} /> {sm.label}
                </span>
              </div>

              <p className="mt-2.5 text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">{agent.plain}</p>

              {agent.mitre.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {agent.mitre.map(t => (
                    <span key={t} className="text-[8.5px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800/70 text-slate-500 dark:text-slate-400">{t}</span>
                  ))}
                </div>
              )}

              {report ? (
                <button
                  onClick={() => setExpanded(isOpen ? null : agent.name)}
                  className="mt-auto pt-2.5 self-start text-[10px] font-mono text-cyan-600 dark:text-cyan-400 hover:underline"
                >
                  {isOpen ? '▾ Hide report' : '▸ View report'}
                </button>
              ) : (
                <span className="mt-auto pt-2.5 text-[10px] font-mono text-slate-300 dark:text-slate-600">awaiting tasking</span>
              )}
            </div>

            {isOpen && report && (
              <div className="px-3.5 pb-3.5">
                <pre className="text-[10px] leading-relaxed whitespace-pre-wrap font-mono bg-slate-50 dark:bg-slate-950/70 border border-slate-200/60 dark:border-slate-800 rounded-lg p-3 text-slate-600 dark:text-slate-300 max-h-64 overflow-auto">
                  {report}
                </pre>
                {devMode && (
                  <pre className="mt-2 text-[9px] font-mono bg-slate-950 text-emerald-400/90 p-2 rounded-lg overflow-auto max-h-32 border border-slate-800">
                    {JSON.stringify(agentOutputs[agent.name], null, 2)}
                  </pre>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default AgentDetailPanel
