// components/SettingsView.tsx — LLM providers, MCP surface, runtime controls.
import React, { useEffect, useState, useCallback } from 'react'
import { API_BASE } from '../lib/agents'

interface Provider {
  id: string; env: string; label: string; note: string
  configured: boolean; in_chain: boolean; masked_key: string | null
}
interface McpTool { name: string; category: string; description: string; inputs: string[] }
interface Settings {
  mode: string
  band_mock: boolean
  llm: { primary: string; degraded: boolean; providers: Provider[]; active_provider: string }
  simulation: { running: boolean; active_incident_id: string | null; mock_pace: number }
  rooms: string[]
  agents: string[]
  mcp: { server: string; transport: string; tool_count: number; tools: McpTool[]; connect_hint: string }
}

function Card({ title, icon, children }: { title: string; icon: string; children: React.ReactNode }) {
  return (
    <div className="glassmorphic border border-slate-200/60 dark:border-slate-800/60 rounded-2xl p-5 shadow-sm">
      <h3 className="flex items-center gap-2 text-[12px] font-bold text-slate-800 dark:text-slate-100 mb-4">
        <span>{icon}</span>{title}
      </h3>
      {children}
    </div>
  )
}

export function SettingsView({ theme, onToggleTheme }: { theme: 'dark' | 'light'; onToggleTheme: () => void }) {
  const [s, setS] = useState<Settings | null>(null)
  const [saving, setSaving] = useState(false)
  const [pace, setPace] = useState(0.6)

  const load = useCallback(() => {
    fetch(`${API_BASE}/api/v1/system/settings`).then(r => r.json()).then((d: Settings) => {
      setS(d); setPace(d.simulation.mock_pace)
    }).catch(() => {})
  }, [])
  useEffect(() => { load() }, [load])

  const patch = async (body: Record<string, any>) => {
    setSaving(true)
    try {
      await fetch(`${API_BASE}/api/v1/system/settings`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      })
      load()
    } finally { setSaving(false) }
  }

  if (!s) return <p className="text-[11px] font-mono text-slate-400 p-6">Loading settings…</p>

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      {/* LLM providers */}
      <Card title="AI Providers" icon="🧠">
        <div className="mb-3 flex items-center gap-2 text-[10px] font-mono">
          <span className="text-slate-400">Active engine:</span>
          <span className={`px-2 py-0.5 rounded-full ${
            s.llm.degraded ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400' : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
          }`}>
            {s.llm.degraded ? 'Local simulation engine (providers cooling down)' : s.llm.active_provider}
          </span>
        </div>
        <div className="space-y-2">
          {s.llm.providers.map(p => (
            <div key={p.id} className="flex items-center justify-between rounded-xl border border-slate-200/60 dark:border-slate-800/60 p-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-200">{p.label}</span>
                  {s.llm.primary === p.id && <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">PRIMARY</span>}
                </div>
                <p className="text-[9.5px] font-mono text-slate-400 dark:text-slate-500">{p.note} · {p.env}{p.masked_key ? ` · ${p.masked_key}` : ''}</p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${
                  p.configured ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : 'bg-slate-500/10 text-slate-400'
                }`}>{p.configured ? 'configured' : 'no key'}</span>
                {p.configured && s.llm.primary !== p.id && (
                  <button onClick={() => patch({ primary_provider: p.id })} disabled={saving}
                    className="text-[9px] font-mono text-cyan-600 dark:text-cyan-400 hover:underline">make primary</button>
                )}
              </div>
            </div>
          ))}
        </div>
        <p className="mt-3 text-[10px] text-slate-400 dark:text-slate-500 leading-relaxed">
          Add a key to <span className="font-mono">.env</span> and restart to enable a provider. Fusion auto-falls back down the
          chain, and drops to the built-in local engine if every provider is rate-limited — so a demo never stalls.
        </p>
        {s.llm.degraded && (
          <button onClick={() => patch({ reset_llm_degradation: true })} disabled={saving}
            className="mt-3 text-[10px] font-mono px-3 py-1.5 rounded-lg border border-amber-500/40 text-amber-600 dark:text-amber-400 hover:bg-amber-500/10">
            ↻ Retry live providers now
          </button>
        )}
      </Card>

      {/* MCP */}
      <Card title="MCP Server" icon="🔌">
        <div className="flex items-center gap-2 mb-3 text-[10px] font-mono">
          <span className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500">{s.mcp.server}</span>
          <span className="text-slate-400">transport: {s.mcp.transport}</span>
          <span className="px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">{s.mcp.tool_count} tools</span>
        </div>
        <div className="space-y-2 max-h-72 overflow-auto pr-1">
          {s.mcp.tools.map(t => (
            <div key={t.name} className="rounded-xl border border-slate-200/60 dark:border-slate-800/60 p-2.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono font-semibold text-slate-700 dark:text-slate-200">{t.name}</span>
                <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-400">{t.category}</span>
              </div>
              <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">{t.description}</p>
              <div className="mt-1 flex flex-wrap gap-1">
                {t.inputs.map(inp => <span key={inp} className="text-[8.5px] font-mono px-1 rounded bg-cyan-500/5 text-cyan-600/80 dark:text-cyan-400/80">{inp}</span>)}
              </div>
            </div>
          ))}
        </div>
        <p className="mt-3 text-[10px] text-slate-400 dark:text-slate-500 leading-relaxed">{s.mcp.connect_hint}</p>
      </Card>

      {/* Runtime */}
      <Card title="Simulation & Runtime" icon="⚙️">
        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-[11px] font-semibold text-slate-700 dark:text-slate-200">Demo pacing</label>
              <span className="text-[10px] font-mono text-slate-400">{pace === 0 ? 'instant' : `${pace.toFixed(1)}×`}</span>
            </div>
            <input
              type="range" min={0} max={1.5} step={0.1} value={pace}
              onChange={e => setPace(Number(e.target.value))}
              onMouseUp={() => patch({ mock_pace: pace })}
              onTouchEnd={() => patch({ mock_pace: pace })}
              className="w-full accent-cyan-500"
            />
            <p className="text-[9.5px] text-slate-400 dark:text-slate-500 mt-1">Lower = faster cinematic delays in the offline engine. 0 runs the whole chain instantly.</p>
          </div>
          <Row label="Coordination mode" value={s.band_mock ? 'Offline mock bus' : 'Live Band SDK'} />
          <Row label="Simulation running" value={s.simulation.running ? 'yes' : 'no'} />
          <Row label="Active incident" value={s.simulation.active_incident_id || '—'} />
          <Row label="Registered rooms" value={`${s.rooms.length} active`} />
        </div>
      </Card>

      {/* Appearance */}
      <Card title="Appearance" icon="🎨">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[11px] font-semibold text-slate-700 dark:text-slate-200">Theme</p>
            <p className="text-[9.5px] text-slate-400 dark:text-slate-500">Switch between dark command-center and light mode.</p>
          </div>
          <button onClick={onToggleTheme}
            className="px-3 py-1.5 rounded-lg border border-slate-200/60 dark:border-slate-800 text-[11px] font-mono text-slate-600 dark:text-slate-300 hover:border-cyan-500/40">
            {theme === 'dark' ? '🌙 Dark' : '☀️ Light'}
          </button>
        </div>
        <div className="mt-4 pt-4 border-t border-slate-200/50 dark:border-slate-800/60">
          <Row label="Agents online" value={`${s.agents.length} / 9`} />
          <Row label="Backend" value={`${API_BASE.replace('http://', '')}`} />
        </div>
      </Card>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-[11px]">
      <span className="text-slate-400 dark:text-slate-500">{label}</span>
      <span className="font-mono text-slate-600 dark:text-slate-300">{value}</span>
    </div>
  )
}

export default SettingsView
