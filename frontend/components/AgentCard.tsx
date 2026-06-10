// components/AgentCard.tsx
import React from 'react'
import { AgentStatus } from '../hooks/useAgentWebSocket'

const STATUS_CONFIGS = {
  idle: {
    colorClass: 'border-slate-200/60 bg-white/40 text-slate-500 dark:border-slate-850/50 dark:bg-slate-900/10 dark:text-slate-400',
    indicatorClass: 'bg-slate-300 dark:bg-slate-700',
    label: 'Standby',
  },
  working: {
    colorClass: 'border-amber-400/80 bg-amber-500/5 text-amber-700 dark:border-amber-500/40 dark:bg-amber-500/5 dark:text-amber-400 shadow-[0_0_15px_rgba(245,158,11,0.06)]',
    indicatorClass: 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.6)] animate-pulse',
    label: 'Active',
  },
  done: {
    colorClass: 'border-emerald-400 bg-emerald-500/5 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/5 dark:text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.04)]',
    indicatorClass: 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]',
    label: 'Complete',
  },
  alert: {
    colorClass: 'border-red-500 bg-red-500/5 text-red-700 dark:border-red-500/40 dark:bg-red-500/5 dark:text-red-400 shadow-[0_0_20px_rgba(239,68,68,0.1)] dark:shadow-[0_0_25px_rgba(239,68,68,0.15)] animate-pulse',
    indicatorClass: 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]',
    label: 'Escalated',
  }
}

interface AgentCardProps {
  name: string
  displayName: string
  status: AgentStatus
  description: string
  llm: string
  room: string
  devMode?: boolean
  lastOutput?: Record<string, any> | null
}

// Plain-English status line for non-technical viewers (normal mode)
function plainEnglish(status: AgentStatus, lastOutput?: Record<string, any> | null): string {
  if (status === 'working') return lastOutput?.current_action || 'Analyzing the situation…'
  if (status === 'done') {
    const report: string = lastOutput?.report || ''
    return report ? report.replace(/[-—#*`]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 110) + '…' : 'Finished — report delivered to the team.'
  }
  if (status === 'alert') return 'Needs attention — something went wrong.'
  return 'Waiting for an incident…'
}

export function AgentCard({ name, displayName, status, description, llm, room, devMode = false, lastOutput = null }: AgentCardProps) {
  const config = STATUS_CONFIGS[status] || STATUS_CONFIGS.idle

  return (
    <div className={`glassmorphic border rounded-xl p-4 flex flex-col justify-between h-[185px] transition-all duration-500 ${config.colorClass}`}>
      <div className="min-h-0 flex-1">
        <div className="flex items-center justify-between mb-2">
          <span className="font-semibold text-xs tracking-tight text-slate-800 dark:text-slate-100">{displayName}</span>
          <div className="flex items-center gap-1.5 bg-slate-100/50 dark:bg-slate-900/50 border border-slate-200/50 dark:border-slate-800/80 px-2 py-0.5 rounded-full">
            <span className="relative flex h-1.5 w-1.5">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${status === 'working' ? 'bg-amber-400' : 'hidden'}`}></span>
              <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${config.indicatorClass}`}></span>
            </span>
            <span className="text-[8px] uppercase font-bold tracking-wider opacity-85 text-slate-500 dark:text-slate-400">{config.label}</span>
          </div>
        </div>
        {devMode ? (
          /* Dev mode: raw event JSON for hackers */
          <pre className="text-[8px] font-mono bg-slate-950 text-emerald-400/90 p-2 rounded-md overflow-auto max-h-[88px] border border-slate-800">
            {JSON.stringify({ agent: name, status, output: lastOutput || {} }, null, 1)}
          </pre>
        ) : status === 'idle' ? (
          <p className="text-[10.5px] text-slate-500 dark:text-slate-400 leading-relaxed font-sans line-clamp-3">
            {description}
          </p>
        ) : (
          /* Normal mode: plain English for non-technical viewers */
          <p className="text-[10.5px] text-slate-500 dark:text-slate-400 leading-relaxed font-sans line-clamp-4">
            {plainEnglish(status, lastOutput)}
          </p>
        )}
      </div>

      <div className="mt-3 pt-2 border-t border-slate-200/50 dark:border-slate-800/60 flex flex-col gap-0.5 text-[9px] font-mono">
        <div className="flex items-center justify-between">
          <span className="text-slate-400 dark:text-slate-500 uppercase tracking-wider text-[8px]">LLM:</span>
          <span className="text-slate-600 dark:text-slate-350 font-medium">{llm}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400 dark:text-slate-500 uppercase tracking-wider text-[8px]">Room:</span>
          <span className="text-slate-600 dark:text-slate-350 font-medium max-w-[120px] truncate" title={room}>{room}</span>
        </div>
      </div>
    </div>
  )
}

export default AgentCard;
