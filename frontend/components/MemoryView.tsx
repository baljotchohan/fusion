// components/MemoryView.tsx — incident history, learned defenses, chat history.
import React, { useEffect, useState, useCallback } from 'react'
import { API_BASE, AGENT_BY_NAME } from '../lib/agents'

interface IncidentRow {
  incident_id: string
  threat_level?: number
  trigger?: string
  findings: number
  final_decision?: string | null
  created_at?: string
}

interface MemStats {
  total_incidents: number
  total_findings: number
  learned_patterns: Record<string, number>
  agent_profiles: Record<string, any>
}

function Stat({ label, value, accent }: { label: string; value: React.ReactNode; accent?: string }) {
  return (
    <div className="glassmorphic border border-slate-200/60 dark:border-slate-800/60 rounded-xl p-4">
      <div className={`text-2xl font-bold ${accent || 'text-slate-800 dark:text-white'}`}>{value}</div>
      <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 dark:text-slate-500 mt-1">{label}</div>
    </div>
  )
}

export function MemoryView() {
  const [stats, setStats] = useState<MemStats | null>(null)
  const [incidents, setIncidents] = useState<IncidentRow[]>([])
  const [detail, setDetail] = useState<any | null>(null)
  const [chat, setChat] = useState<any[]>([])
  const [tab, setTab] = useState<'incidents' | 'patterns' | 'chat'>('incidents')

  const load = useCallback(() => {
    fetch(`${API_BASE}/api/v1/memory/stats`).then(r => r.json()).then(setStats).catch(() => {})
    fetch(`${API_BASE}/api/v1/incidents`).then(r => r.json()).then(d => setIncidents(d.incidents || [])).catch(() => {})
    fetch(`${API_BASE}/api/v1/chat/history?limit=60`).then(r => r.json()).then(d => setChat(d.history || [])).catch(() => {})
  }, [])

  useEffect(() => { load() }, [load])

  const openIncident = (id: string) => {
    fetch(`${API_BASE}/api/v1/incident/${id}`).then(r => r.json()).then(setDetail).catch(() => {})
  }

  const clearChat = () => {
    fetch(`${API_BASE}/api/v1/chat/history`, { method: 'DELETE' }).then(() => setChat([]))
  }

  const patterns = stats ? Object.entries(stats.learned_patterns) : []

  return (
    <div className="space-y-5">
      {/* stat row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Incidents handled" value={stats?.total_incidents ?? '—'} accent="text-cyan-600 dark:text-cyan-400" />
        <Stat label="Total findings logged" value={stats?.total_findings ?? '—'} />
        <Stat label="Defense recipes learned" value={patterns.length || '—'} accent="text-emerald-600 dark:text-emerald-400" />
        <Stat label="Active agents" value={stats ? Object.keys(stats.agent_profiles).length : '—'} />
      </div>

      {/* sub-tabs */}
      <div className="flex items-center gap-1 border-b border-slate-200/60 dark:border-slate-800/60">
        {(['incidents', 'patterns', 'chat'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-[11px] font-semibold capitalize transition border-b-2 ${
              tab === t ? 'border-cyan-500 text-cyan-600 dark:text-cyan-400' : 'border-transparent text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
            }`}
          >
            {t === 'chat' ? 'Chat history' : t}
          </button>
        ))}
        <button onClick={load} className="ml-auto text-[10px] font-mono text-slate-400 hover:text-cyan-500 px-2">↻ refresh</button>
      </div>

      {/* incidents */}
      {tab === 'incidents' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <div className="space-y-2 max-h-[460px] overflow-auto pr-1">
            {incidents.length === 0 && <p className="text-[11px] text-slate-400 font-mono p-4">No incidents recorded yet.</p>}
            {incidents.map(inc => (
              <button
                key={inc.incident_id}
                onClick={() => openIncident(inc.incident_id)}
                className={`w-full text-left rounded-xl border p-3 transition ${
                  detail?.incident_id === inc.incident_id
                    ? 'border-cyan-500/50 bg-cyan-500/5'
                    : 'border-slate-200/60 dark:border-slate-800/60 hover:border-cyan-500/30'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-mono font-bold text-slate-700 dark:text-slate-200">{inc.incident_id}</span>
                  <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${
                    (inc.threat_level || 0) >= 7 ? 'bg-red-500/10 text-red-600 dark:text-red-400' : 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                  }`}>THREAT {inc.threat_level ?? '?'}/10</span>
                </div>
                <div className="mt-1 flex items-center gap-2 text-[10px] text-slate-400 dark:text-slate-500 font-mono">
                  <span>{inc.trigger}</span>·<span>{inc.findings} findings</span>
                  {inc.final_decision && <span className="text-emerald-600 dark:text-emerald-400">✓ decided</span>}
                </div>
              </button>
            ))}
          </div>

          <div className="rounded-xl border border-slate-200/60 dark:border-slate-800/60 p-4 max-h-[460px] overflow-auto">
            {!detail && <p className="text-[11px] text-slate-400 font-mono">Select an incident to view its timeline.</p>}
            {detail && (
              <div className="space-y-3">
                <div>
                  <h3 className="text-[12px] font-bold text-slate-800 dark:text-slate-100">{detail.incident_id}</h3>
                  <p className="text-[10px] font-mono text-slate-400">{detail.created_at}</p>
                </div>
                {detail.final_decision && (
                  <div className="rounded-lg bg-emerald-500/5 border border-emerald-500/20 p-2.5 text-[11px] text-emerald-700 dark:text-emerald-300">
                    {detail.final_decision}
                  </div>
                )}
                <ol className="space-y-2">
                  {(detail.timeline || []).map((ev: any, i: number) => (
                    <li key={i} className="border-l-2 border-slate-200 dark:border-slate-800 pl-3">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-200">
                          {AGENT_BY_NAME[ev.agent]?.displayName || ev.agent}
                        </span>
                        <span className="text-[8.5px] font-mono text-slate-400">sev {ev.severity}</span>
                        {(ev.tags || []).map((t: string) => (
                          <span key={t} className="text-[8px] font-mono px-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-500">{t}</span>
                        ))}
                      </div>
                      <p className="text-[10.5px] text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-3 whitespace-pre-wrap">{ev.finding}</p>
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </div>
        </div>
      )}

      {/* learned patterns */}
      {tab === 'patterns' && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {patterns.length === 0 && <p className="text-[11px] text-slate-400 font-mono p-4">No defense recipes learned yet — run an incident through Blue Team.</p>}
          {patterns.map(([mitre, count]) => (
            <div key={mitre} className="rounded-xl border border-slate-200/60 dark:border-slate-800/60 p-3.5">
              <div className="flex items-center justify-between">
                <span className="text-[12px] font-mono font-bold text-emerald-600 dark:text-emerald-400">{mitre}</span>
                <span className="text-[9px] font-mono text-slate-400">{count} recipe{count === 1 ? '' : 's'}</span>
              </div>
              <p className="mt-1.5 text-[10.5px] text-slate-500 dark:text-slate-400">
                Learned countermeasure for MITRE technique <span className="font-mono">{mitre}</span>. Reused automatically on the next matching attack.
              </p>
            </div>
          ))}
        </div>
      )}

      {/* chat history */}
      {tab === 'chat' && (
        <div className="rounded-xl border border-slate-200/60 dark:border-slate-800/60 p-4 max-h-[460px] overflow-auto">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-[11px] font-bold text-slate-700 dark:text-slate-200">Commander conversation log</h3>
            {chat.length > 0 && <button onClick={clearChat} className="text-[10px] font-mono text-red-500 hover:underline">Clear</button>}
          </div>
          {chat.length === 0 && <p className="text-[11px] text-slate-400 font-mono">No conversation yet.</p>}
          <div className="space-y-2">
            {chat.map((t, i) => (
              <div key={i} className={`text-[11px] ${t.role === 'user' ? 'text-right' : ''}`}>
                <span className={`inline-block max-w-[80%] px-2.5 py-1.5 rounded-lg text-left ${
                  t.role === 'user' ? 'bg-cyan-500/10 text-slate-700 dark:text-slate-200' : 'bg-slate-100 dark:bg-slate-800/60 text-slate-600 dark:text-slate-300'
                }`}>
                  {t.content}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default MemoryView
