// components/LiveLog.tsx
import React from 'react'
import { AgentUpdate } from '../hooks/useAgentWebSocket'

interface LiveLogProps {
  events: AgentUpdate[]
}

const AGENT_DISPLAY_NAMES: Record<string, string> = {
  threat_intel_agent: 'Threat Intel',
  recon_agent: 'Recon',
  red_team_agent: 'Red Team',
  attack_path_agent: 'Attack Path',
  detection_agent: 'Detection',
  malware_agent: 'Malware Inv',
  blue_team_agent: 'Blue Team',
  incident_commander: 'Inc Commander',
  executive_decision: 'Executive Board',
}

const LOG_COLOR_MAP: Record<string, string> = {
  working: 'text-amber-400',
  done: 'text-emerald-400',
  alert: 'text-red-400',
  idle: 'text-slate-500'
}

export function LiveLog({ events }: LiveLogProps) {
  if (events.length === 0) {
    return (
      <div className="flex h-[320px] items-center justify-center text-slate-600 text-xs font-mono border border-slate-900 bg-slate-950/40 rounded-xl">
        &gt;_ NO LOGS STREAMING (WAITING FOR INCIDENT RUN)
      </div>
    )
  }

  return (
    <div className="flex flex-col h-[320px] overflow-y-auto font-mono text-[10px] space-y-1.5 p-3 border border-slate-900 bg-slate-950 rounded-xl scrollbar-thin scrollbar-thumb-slate-800">
      {events.map((event, index) => {
        const agentName = AGENT_DISPLAY_NAMES[event.agent] || event.agent
        const colorClass = LOG_COLOR_MAP[event.status] || 'text-slate-300'
        const logContent = event.output?.report || event.output?.event || JSON.stringify(event.output)
        
        return (
          <div key={index} className="border-b border-slate-900/50 pb-1.5 last:border-0">
            <div className="flex items-center gap-1.5 mb-0.5">
              <span className="text-slate-500">[{event.timestamp.split('T')[1].replace('Z', '')}]</span>
              <span className="text-blue-400 font-bold uppercase">{agentName}</span>
              <span className={`px-1 py-[1px] rounded-[3px] text-[8px] font-bold uppercase bg-slate-900 ${colorClass}`}>
                {event.status}
              </span>
            </div>
            <p className="text-slate-300 whitespace-pre-wrap leading-relaxed pl-2 border-l border-slate-800">
              {logContent}
            </p>
          </div>
        )
      })}
    </div>
  )
}
export default LiveLog;
