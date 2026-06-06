// components/LiveLog.tsx
import React, { useState } from 'react'
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
  working: 'text-amber-500 dark:text-amber-400',
  done: 'text-emerald-600 dark:text-emerald-400',
  alert: 'text-red-600 dark:text-red-400',
  idle: 'text-slate-400 dark:text-slate-500'
}

export function LiveLog({ events }: LiveLogProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [clearedTimestamp, setClearedTimestamp] = useState<number | null>(null)

  const handleClear = () => {
    setClearedTimestamp(Date.now())
  }

  const handleCopy = () => {
    const visibleEvents = getActiveEvents()
    if (visibleEvents.length === 0) return
    
    const logText = visibleEvents.map(event => {
      const name = AGENT_DISPLAY_NAMES[event.agent] || event.agent
      const text = event.output?.report || event.output?.event || JSON.stringify(event.output)
      return `[${event.timestamp}] [${name.toUpperCase()}] [${event.status.toUpperCase()}]: ${text}`
    }).join('\n')

    navigator.clipboard.writeText(logText)
      .then(() => alert('Logs copied to clipboard'))
      .catch(err => console.error('Failed to copy logs:', err))
  }

  const getActiveEvents = () => {
    let filtered = events
    if (clearedTimestamp) {
      filtered = filtered.filter(e => new Date(e.timestamp).getTime() > clearedTimestamp)
    }
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(e => {
        const name = (AGENT_DISPLAY_NAMES[e.agent] || e.agent).toLowerCase()
        const text = (e.output?.report || e.output?.event || JSON.stringify(e.output) || '').toLowerCase()
        return name.includes(query) || text.includes(query)
      })
    }
    return filtered
  }

  const activeEvents = getActiveEvents()

  return (
    <div className="w-full flex flex-col rounded-xl overflow-hidden border border-slate-200/80 dark:border-slate-800/80 bg-slate-900 text-slate-100 shadow-md">
      {/* macOS Header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-950/70 border-b border-slate-950/80 backdrop-blur-md">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#ff5f56] border border-[#e0443e]"></span>
          <span className="w-2.5 h-2.5 rounded-full bg-[#ffbd2e] border border-[#dea123]"></span>
          <span className="w-2.5 h-2.5 rounded-full bg-[#27c93f] border border-[#1aab29]"></span>
        </div>
        <span className="text-[10px] font-mono text-slate-400 font-medium">bash - telemetry@argus</span>
        <div className="flex items-center gap-2">
          <button 
            onClick={handleCopy}
            className="text-[9px] font-mono text-slate-400 hover:text-white transition px-1.5 py-0.5 rounded hover:bg-slate-800"
            title="Copy all logs"
            disabled={activeEvents.length === 0}
          >
            COPY
          </button>
          <button 
            onClick={handleClear}
            className="text-[9px] font-mono text-slate-400 hover:text-white transition px-1.5 py-0.5 rounded hover:bg-slate-800"
            title="Clear logs locally"
          >
            CLEAR
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="px-3 py-1.5 bg-slate-950/20 border-b border-slate-950/30 flex items-center">
        <span className="text-[9.5px] font-mono text-slate-500 mr-2">FILTER:</span>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search logs by agent or keyword..."
          className="flex-1 bg-transparent text-[10px] font-mono text-slate-200 placeholder-slate-600 outline-none border-none p-0"
        />
        {searchQuery && (
          <button 
            onClick={() => setSearchQuery('')}
            className="text-[9px] text-slate-500 hover:text-slate-300 ml-1 font-mono"
          >
            ✕
          </button>
        )}
      </div>

      {/* Logs View */}
      <div className="h-[270px] overflow-y-auto font-mono text-[10.5px] space-y-3 p-4 bg-slate-950/90 scrollbar-thin">
        {activeEvents.length === 0 ? (
          <div className="flex h-full items-center justify-center text-slate-600 text-[10px] font-mono italic">
            &gt;_ NO LOGS MATCHING SEARCH OR LOGS CLEARED
          </div>
        ) : (
          activeEvents.map((event, index) => {
            const agentName = AGENT_DISPLAY_NAMES[event.agent] || event.agent
            const colorClass = LOG_COLOR_MAP[event.status] || 'text-slate-300'
            const logContent = event.output?.report || event.output?.event || JSON.stringify(event.output)
            const timeStr = event.timestamp.includes('T') 
              ? event.timestamp.split('T')[1].replace('Z', '').substring(0, 8)
              : event.timestamp

            return (
              <div key={index} className="border-b border-slate-900/50 pb-2.5 last:border-0 last:pb-0">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <span className="text-slate-500">[{timeStr}]</span>
                  <span className="text-blue-400 font-bold uppercase tracking-wider text-[9px]">{agentName}</span>
                  <span className={`px-1 py-[0.5px] rounded-[3px] text-[7.5px] font-extrabold uppercase bg-slate-900 border border-slate-800 ${colorClass}`}>
                    {event.status}
                  </span>
                </div>
                <p className="text-slate-300 whitespace-pre-wrap leading-relaxed pl-2.5 border-l border-slate-800 font-light">
                  {logContent}
                </p>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

export default LiveLog;
