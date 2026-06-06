// components/AgentCard.tsx
import React from 'react'
import { AgentStatus } from '../hooks/useAgentWebSocket'

const STATUS_CONFIGS = {
  idle: {
    colorClass: 'border-slate-800 bg-slate-900/60 text-slate-400',
    indicatorClass: 'bg-slate-700 shadow-slate-900/40',
    label: 'Idle',
    icon: '○'
  },
  working: {
    colorClass: 'border-amber-500/50 bg-amber-950/20 text-amber-300 shadow-[0_0_15px_rgba(245,158,11,0.1)]',
    indicatorClass: 'bg-amber-500 shadow-amber-500/50 animate-ping',
    label: 'Working',
    icon: '◉'
  },
  done: {
    colorClass: 'border-emerald-500/40 bg-emerald-950/25 text-emerald-300',
    indicatorClass: 'bg-emerald-500 shadow-emerald-500/50',
    label: 'Done',
    icon: '●'
  },
  alert: {
    colorClass: 'border-red-500/50 bg-red-950/30 text-red-300 shadow-[0_0_15px_rgba(239,68,68,0.15)] animate-pulse',
    indicatorClass: 'bg-red-500 shadow-red-500/50',
    label: 'Escalated',
    icon: '⚠'
  }
}

interface AgentCardProps {
  name: string
  displayName: string
  status: AgentStatus
  description: string
}

export function AgentCard({ name, displayName, status, description }: AgentCardProps) {
  const config = STATUS_CONFIGS[status] || STATUS_CONFIGS.idle

  return (
    <div className={`border rounded-xl p-4 transition-all duration-500 backdrop-blur-md ${config.colorClass}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold text-sm tracking-wide text-white">{displayName}</span>
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${status === 'working' ? 'bg-amber-400' : 'hidden'}`}></span>
            <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${config.indicatorClass}`}></span>
          </span>
          <span className="text-[10px] uppercase font-bold tracking-widest opacity-80">{config.label}</span>
        </div>
      </div>
      <p className="text-xs text-slate-400 leading-relaxed font-sans">{description}</p>
    </div>
  )
}
export default AgentCard;
