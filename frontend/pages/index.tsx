// pages/index.tsx
import React, { useState, useEffect } from 'react'
import Head from 'next/head'
import { useAgentWebSocket, AgentStatus } from '../hooks/useAgentWebSocket'
import { AgentCard } from '../components/AgentCard'
import { AgentGraph } from '../components/AgentGraph'
import { LiveLog } from '../components/LiveLog'
import { ExecutivePanel } from '../components/ExecutivePanel'

const AGENTS = [
  { 
    name: 'threat_intel_agent', 
    displayName: 'Threat Intel', 
    description: 'Parses raw alerts; maps MITRE TTPs and CVE vulnerability links.',
    llm: 'Gemini 2.0 Flash',
    room: '#threat-intel-room'
  },
  { 
    name: 'recon_agent', 
    displayName: 'Recon', 
    description: 'Maps target systems topology and local vulnerabilities using digital twin.',
    llm: 'Gemini 2.0 Flash',
    room: '#recon-room'
  },
  { 
    name: 'detection_agent', 
    displayName: 'Detection', 
    description: 'Scans fake logs and email archives for matching domains and file hashes.',
    llm: 'Gemini 2.0 Flash',
    room: '#detection-room'
  },
  { 
    name: 'red_team_agent', 
    displayName: 'Red Team', 
    description: 'Simulates lateral movement progression paths from entry to final target.',
    llm: 'Gemini 2.0 Flash',
    room: '#redteam-room'
  },
  { 
    name: 'attack_path_agent', 
    displayName: 'Attack Path', 
    description: 'Predicts hacker next moves and computes combined critical risk score.',
    llm: 'Gemini 2.0 Flash',
    room: '#attack-path-room'
  },
  { 
    name: 'malware_agent', 
    displayName: 'Malware Inv.', 
    description: 'Analyzes files static structure, PE headers, entropy, and dropped IOCs.',
    llm: 'Mistral 7B',
    room: '#malware-room'
  },
  { 
    name: 'blue_team_agent', 
    displayName: 'Blue Team', 
    description: 'Formulates prioritized defensive playbooks and calculates downtime.',
    llm: 'Gemini 2.0 Flash',
    room: '#blueteam-room'
  },
  { 
    name: 'incident_commander', 
    displayName: 'Incident Cmdr', 
    description: 'Central conductor room that orchestrates hands-offs and dynamic recruitment.',
    llm: 'Gemini 1.5 Pro',
    room: '#incident-command-room'
  },
  { 
    name: 'executive_decision', 
    displayName: 'Executive Board', 
    description: 'Boardroom debate (CFO -> Legal -> Ops -> CEO) to yield containment choice.',
    llm: 'Gemini 1.5 Pro',
    room: '#executive-room'
  },
]

export default function WarRoom() {
  const {
    agentStates,
    logEvents,
    threatScore,
    ceoDecision,
    isConnected,
    setAgentStates,
    setThreatScore,
    setCeoDecision,
    setLogEvents
  } = useAgentWebSocket()

  const [isSimulating, setIsSimulating] = useState(false)
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')

  // Theme Sync on Mount
  useEffect(() => {
    const saved = localStorage.getItem('theme') as 'dark' | 'light' | null
    if (saved) {
      setTheme(saved)
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      setTheme('light')
    }
  }, [])

  // Apply Theme class to document root
  useEffect(() => {
    const root = window.document.documentElement
    if (theme === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
  }, [theme])

  const triggerAttack = async () => {
    setIsSimulating(true)
    try {
      const response = await fetch('http://localhost:8000/api/trigger-attack', { method: 'POST' })
      const data = await response.json()
      console.log('Triggered Attack:', data)
    } catch (e) {
      console.error('Failed to trigger attack:', e)
      setIsSimulating(false)
    }
  }

  const resetSimulation = () => {
    setIsSimulating(false)
    setThreatScore(0)
    setCeoDecision(null)
    setLogEvents([])
    
    // Reset agent states to idle
    const resetStates: Record<string, AgentStatus> = {}
    AGENTS.forEach(a => {
      resetStates[a.name] = 'idle'
    })
    setAgentStates(resetStates)
  }

  const toggleTheme = () => {
    setTheme(prev => {
      const next = prev === 'dark' ? 'light' : 'dark'
      localStorage.setItem('theme', next)
      return next
    })
  }

  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-300 font-sans antialiased">
      <Head>
        <title>ARGUS — Autonomous Cyber Defense Command Center</title>
        <meta name="description" content="9 autonomous AI agents coordinating through Band to triage and mitigate cybersecurity threats." />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      {/* Premium Apple/ChatGPT Style Minimalist Header */}
      <header className="sticky top-0 z-50 glassmorphic border-b border-slate-200/50 dark:border-slate-850/50 px-6 py-3.5 backdrop-blur-md">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-0.5">
            <div className="flex items-center gap-3">
              <span className="font-extrabold text-base tracking-wider text-slate-900 dark:text-white flex items-center gap-1.5 font-mono">
                ⚡ ARGUS SYSTEM
                <span className="text-[9px] px-1.5 py-0.5 rounded-full font-mono bg-slate-100 dark:bg-slate-900 text-slate-400 dark:text-slate-500 font-normal border border-slate-200/40 dark:border-slate-800/80">
                  v1.0.0
                </span>
              </span>
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold font-mono tracking-wider ${isConnected ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20'}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`}></span>
                {isConnected ? 'ONLINE' : 'OFFLINE'}
              </span>
            </div>
            <p className="text-[10px] text-slate-400 dark:text-slate-500 font-mono tracking-wider uppercase">9 agents. All seeing. Never sleeps.</p>
          </div>

          <div className="flex items-center gap-3">
            {/* Theme Toggle Button */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg border border-slate-200/60 dark:border-slate-800/80 bg-white/40 dark:bg-slate-900/10 hover:bg-slate-100 dark:hover:bg-slate-900 text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-white transition duration-300 shadow-sm"
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m12.728 12.728l.707.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                </svg>
              )}
            </button>

            {isSimulating && (
              <button
                onClick={resetSimulation}
                className="h-8.5 px-4 rounded-lg text-xs font-semibold border border-slate-200/60 dark:border-slate-800/80 bg-white/40 dark:bg-slate-900/10 hover:bg-slate-50 dark:hover:bg-slate-900 text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-white transition duration-300 font-mono shadow-sm"
              >
                RESET DEMO
              </button>
            )}
            <button
              onClick={triggerAttack}
              disabled={isSimulating}
              className={`h-8.5 px-5 rounded-lg text-xs font-bold font-mono tracking-wider transition-all duration-300 shadow-sm ${
                isSimulating 
                  ? 'bg-slate-100 border border-slate-250 text-slate-400 dark:bg-slate-900/50 dark:border-slate-850 dark:text-slate-600 cursor-not-allowed shadow-none' 
                  : 'bg-slate-900 hover:bg-black text-white dark:bg-white dark:hover:bg-slate-100 dark:text-slate-950 hover:scale-[1.01] active:scale-[0.99]'
              }`}
            >
              {isSimulating ? 'SIMULATING THREAT...' : 'SIMULATE ATTACK'}
            </button>
          </div>
        </div>
      </header>

      {/* Main layout */}
      <main className="max-w-7xl mx-auto p-6 space-y-6">
        {/* Top Segment: React Flow Graph + Logs Panel */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Active Flow Graph Visualizer */}
          <div className="lg:col-span-8 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-[10px] font-bold font-mono tracking-widest text-slate-400 dark:text-slate-500 uppercase">Interactive Node Handoff Graph</h2>
              {threatScore > 0 && (
                <span className="text-[9.5px] font-mono font-bold tracking-wider px-2 py-0.5 rounded bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20 shadow-sm">
                  COMBINED RISK: {threatScore}/100
                </span>
              )}
            </div>
            <AgentGraph agentStates={agentStates} theme={theme} />
          </div>

          {/* Console / Event Log Feed */}
          <div className="lg:col-span-4 space-y-4 flex flex-col justify-between">
            <div className="space-y-3 flex-1 flex flex-col">
              <h2 className="text-[10px] font-bold font-mono tracking-widest text-slate-400 dark:text-slate-500 uppercase">Live Operations Log</h2>
              <LiveLog events={logEvents} />
            </div>
            
            {/* Simple Legend Card */}
            <div className="glassmorphic border border-slate-200/60 dark:border-slate-850/50 rounded-xl p-4 space-y-2.5 shadow-sm">
              <h3 className="text-[9px] font-mono font-bold text-slate-400 dark:text-slate-500 tracking-wider">COORDINATION METRICS</h3>
              <div className="grid grid-cols-2 gap-2.5 text-[10px] font-mono text-slate-500 dark:text-slate-400">
                <div>• Total Swarms: <span className="text-slate-700 dark:text-slate-200 font-semibold">9 Agents</span></div>
                <div>• Rooms: <span className="text-slate-700 dark:text-slate-200 font-semibold">9 Active</span></div>
                <div>• Platform: <span className="text-slate-700 dark:text-slate-200 font-semibold">Band AI SDK</span></div>
                <div>• Interface: <span className="text-slate-700 dark:text-slate-200 font-semibold">FastAPI WS</span></div>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Segment: Boardroom Verdict or Status Cards */}
        <div className="space-y-6">
          {/* Boardroom Escalation Panel */}
          <ExecutivePanel decision={ceoDecision} threatScore={threatScore} />

          {/* Individual Agent status list */}
          <div className="space-y-3">
            <h2 className="text-[10px] font-bold font-mono tracking-widest text-slate-400 dark:text-slate-500 uppercase">Autonomous Specialist Swarm</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
              {AGENTS.map((agent) => (
                <AgentCard
                  key={agent.name}
                  name={agent.name}
                  displayName={agent.displayName}
                  status={agentStates[agent.name]}
                  description={agent.description}
                  llm={agent.llm}
                  room={agent.room}
                />
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
