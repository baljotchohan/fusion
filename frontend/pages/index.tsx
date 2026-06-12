// pages/index.tsx — Fusion command center shell.
import React, { useState, useEffect } from 'react'
import Head from 'next/head'
import { useAgentWebSocket } from '../hooks/useAgentWebSocket'
import { AgentGraph } from '../components/AgentGraph'
import { LiveLog } from '../components/LiveLog'
import { ExecutivePanel } from '../components/ExecutivePanel'
import { ChatPanel } from '../components/ChatPanel'
import { ThreatGauge } from '../components/ThreatGauge'
import { StoryTicker } from '../components/StoryTicker'
import { AgentDetailPanel } from '../components/AgentDetailPanel'
import { MemoryView } from '../components/MemoryView'
import { SettingsView } from '../components/SettingsView'
import { DocsView } from '../components/DocsView'
import { API_BASE } from '../lib/agents'

type Tab = 'war' | 'memory' | 'settings' | 'docs'

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'war', label: 'War Room', icon: '⚡' },
  { id: 'memory', label: 'Memory', icon: '🧠' },
  { id: 'settings', label: 'Settings', icon: '⚙️' },
  { id: 'docs', label: 'Docs', icon: '📖' },
]

export default function Fusion() {
  const {
    agentStates, agentOutputs, logEvents, storyFeed, threatScore, ceoDecision, isConnected, resetAll,
  } = useAgentWebSocket()

  const [tab, setTab] = useState<Tab>('war')
  const [isSimulating, setIsSimulating] = useState(false)
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')
  const [devMode, setDevMode] = useState(false)

  useEffect(() => {
    const saved = localStorage.getItem('theme') as 'dark' | 'light' | null
    if (saved) setTheme(saved)
    else if (window.matchMedia?.('(prefers-color-scheme: light)').matches) setTheme('light')
  }, [])

  useEffect(() => {
    const root = window.document.documentElement
    theme === 'dark' ? root.classList.add('dark') : root.classList.remove('dark')
  }, [theme])

  useEffect(() => {
    if (ceoDecision) {
      const timer = setTimeout(() => setIsSimulating(false), 5000)
      return () => clearTimeout(timer)
    }
  }, [ceoDecision])

  const triggerAttack = async () => {
    setIsSimulating(true)
    setTab('war')
    try {
      await fetch(`${API_BASE}/api/trigger-attack`, { method: 'POST' })
    } catch {
      setIsSimulating(false)
    }
  }

  const resetSimulation = async () => {
    setIsSimulating(false)
    resetAll()
    try { await fetch(`${API_BASE}/api/reset`, { method: 'POST' }) } catch {}
  }

  const toggleTheme = () => setTheme(prev => {
    const next = prev === 'dark' ? 'light' : 'dark'
    localStorage.setItem('theme', next)
    return next
  })

  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-300 font-sans antialiased">
      <Head>
        <title>Fusion — Autonomous Cyber Defense Command Center</title>
        <meta name="description" content="Nine autonomous AI agents that detect, analyze, and respond to cyber threats — and make the business call." />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      {/* Header */}
      <header className="sticky top-0 z-50 glassmorphic border-b border-slate-200/50 dark:border-slate-800/60 backdrop-blur-xl">
        <div className="max-w-[1400px] mx-auto px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-sm shadow-md">🛡️</div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-[15px] tracking-tight text-slate-900 dark:text-white">Fusion</span>
                <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[8px] font-bold font-mono tracking-wider ${isConnected ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : 'bg-red-500/10 text-red-600 dark:text-red-400'}`}>
                  <span className={`h-1.5 w-1.5 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
                  {isConnected ? 'ONLINE' : 'OFFLINE'}
                </span>
              </div>
              <p className="text-[9px] text-slate-400 dark:text-slate-500 font-mono tracking-wide hidden sm:block">Autonomous Cyber Defense Command Center</p>
            </div>
          </div>

          {/* Tabs */}
          <nav className="hidden md:flex items-center gap-1 bg-slate-100/60 dark:bg-slate-900/50 rounded-xl p-1">
            {TABS.map(t => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`px-3.5 py-1.5 rounded-lg text-[12px] font-semibold transition flex items-center gap-1.5 ${
                  tab === t.id ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
                }`}
              >
                <span className="text-[11px]">{t.icon}</span>{t.label}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setDevMode(p => !p)}
              className={`hidden sm:block h-8 px-2.5 rounded-lg text-[10px] font-bold font-mono tracking-wider border transition ${
                devMode ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-600 dark:text-cyan-400' : 'bg-transparent border-slate-200/60 dark:border-slate-800 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
              }`}
            >{'{ }'} DEV</button>
            <button
              onClick={triggerAttack}
              disabled={isSimulating}
              className={`h-8 px-4 rounded-lg text-[12px] font-bold transition shadow-sm ${
                isSimulating ? 'bg-slate-100 dark:bg-slate-900 text-slate-400 dark:text-slate-600 cursor-not-allowed' : 'bg-gradient-to-br from-cyan-600 to-blue-600 text-white hover:opacity-90 active:scale-95'
              }`}
            >{isSimulating ? 'Simulating…' : '⚡ Simulate Attack'}</button>
            {isSimulating && (
              <button onClick={resetSimulation} className="h-8 px-3 rounded-lg text-[11px] font-semibold border border-slate-200/60 dark:border-slate-800 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200">Reset</button>
            )}
          </div>
        </div>

        {/* Mobile tabs */}
        <nav className="md:hidden flex items-center gap-1 px-4 pb-2 overflow-x-auto">
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`px-3 py-1.5 rounded-lg text-[11px] font-semibold whitespace-nowrap ${tab === t.id ? 'bg-slate-200/70 dark:bg-slate-800 text-slate-900 dark:text-white' : 'text-slate-500'}`}>
              {t.icon} {t.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="max-w-[1400px] mx-auto p-4 sm:p-6">
        {tab === 'war' && (
          <div className="space-y-5">
            {/* Top: narrative + threat gauge */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
              <div className="lg:col-span-8"><StoryTicker beats={storyFeed} isSimulating={isSimulating} hasDecision={!!ceoDecision} /></div>
              <div className="lg:col-span-4 flex flex-col justify-center"><ThreatGauge score={threatScore} /></div>
            </div>

            {/* Middle: chat (left) + graph & logs (right) — equal height columns */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 lg:items-stretch">
              <div className="lg:col-span-5"><ChatPanel devMode={devMode} onIncident={() => setIsSimulating(true)} /></div>
              <div className="lg:col-span-7 flex flex-col gap-4 lg:h-[640px]">
                <div className="flex flex-col min-h-0 flex-1">
                  <div className="flex items-center justify-between mb-2">
                    <h2 className="text-[11px] font-bold font-mono tracking-widest text-slate-400 dark:text-slate-500 uppercase">Agent Coordination Graph</h2>
                    {threatScore > 0 && (
                      <span className="text-[9.5px] font-mono font-bold px-2 py-0.5 rounded bg-red-500/10 text-red-600 dark:text-red-400">RISK {threatScore}/100</span>
                    )}
                  </div>
                  <AgentGraph agentStates={agentStates} theme={theme} heightClass="flex-1 min-h-[300px]" />
                </div>
                <div className="flex flex-col h-[220px]">
                  <h2 className="text-[11px] font-bold font-mono tracking-widest text-slate-400 dark:text-slate-500 uppercase mb-2">Live Operations Log</h2>
                  <div className="flex-1 min-h-0"><LiveLog events={logEvents} /></div>
                </div>
              </div>
            </div>

            {/* Executive verdict */}
            <ExecutivePanel decision={ceoDecision} threatScore={threatScore} />

            {/* Specialist details */}
            <div>
              <h2 className="text-[11px] font-bold font-mono tracking-widest text-slate-400 dark:text-slate-500 uppercase mb-3">Specialist Swarm — Details</h2>
              <AgentDetailPanel agentStates={agentStates} agentOutputs={agentOutputs} devMode={devMode} />
            </div>
          </div>
        )}

        {tab === 'memory' && <MemoryView />}
        {tab === 'settings' && <SettingsView theme={theme} onToggleTheme={toggleTheme} />}
        {tab === 'docs' && <DocsView />}
      </main>
    </div>
  )
}
