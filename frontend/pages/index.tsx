// pages/index.tsx
import React, { useState } from 'react'
import Head from 'next/head'
import { useAgentWebSocket, AgentStatus } from '../hooks/useAgentWebSocket'
import { AgentCard } from '../components/AgentCard'
import { AgentGraph } from '../components/AgentGraph'
import { LiveLog } from '../components/LiveLog'
import { ExecutivePanel } from '../components/ExecutivePanel'

const AGENTS = [
  { name: 'threat_intel_agent', displayName: 'Threat Intel', description: 'Parses raw alerts; maps MITRE TTPs and CVE vulnerability links.' },
  { name: 'recon_agent', displayName: 'Recon', description: 'Maps target systems topology and local vulnerabilities using digital twin.' },
  { name: 'detection_agent', displayName: 'Detection', description: 'Scans fake logs and email archives for matching domains and file hashes.' },
  { name: 'red_team_agent', displayName: 'Red Team', description: 'Simulates lateral movement progression paths from entry to final target.' },
  { name: 'attack_path_agent', displayName: 'Attack Path', description: 'Predicts hacker next moves and computes combined critical risk score.' },
  { name: 'malware_agent', displayName: 'Malware Inv.', description: 'Analyzes files static structure, PE headers, entropy, and dropped IOCs.' },
  { name: 'blue_team_agent', displayName: 'Blue Team', description: 'Formulates prioritized defensive playbooks and calculates downtime.' },
  { name: 'incident_commander', displayName: 'Incident Cmdr', description: 'Central conductor room that orchestrates hands-offs and dynamic recruitment.' },
  { name: 'executive_decision', displayName: 'Executive Board', description: ' Boardroom debate (CFO -> Legal -> Ops -> CEO) to yield containment choice.' },
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

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased">
      <Head>
        <title>ARGUS — Autonomous Cyber Defense Command Center</title>
        <meta name="description" content="9 autonomous AI agents coordinating through Band to triage and mitigate cybersecurity threats." />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      {/* Premium Glassmorphic Header */}
      <header className="sticky top-0 z-50 border-b border-slate-900 bg-slate-950/80 backdrop-blur-md px-6 py-4">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-black tracking-wider bg-clip-text text-transparent bg-gradient-to-r from-red-500 via-amber-500 to-red-400">
                ⚡ ARGUS SYSTEM
              </h1>
              <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold font-mono tracking-widest ${isConnected ? 'bg-emerald-950 text-emerald-400' : 'bg-red-950 text-red-400'}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`}></span>
                {isConnected ? 'ONLINE' : 'OFFLINE'}
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono">Autonomous Cyber Defense Command Center — 9 agents. All seeing. Never sleeps.</p>
          </div>

          <div className="flex items-center gap-3">
            {isSimulating && (
              <button
                onClick={resetSimulation}
                className="bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 font-bold py-2 px-5 rounded-xl transition text-xs font-mono"
              >
                RESET DEMO
              </button>
            )}
            <button
              onClick={triggerAttack}
              disabled={isSimulating}
              className={`font-black py-2 px-6 rounded-xl transition text-xs font-mono tracking-widest ${isSimulating ? 'bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed' : 'bg-gradient-to-r from-red-600 to-amber-600 hover:from-red-500 hover:to-amber-500 text-white shadow-lg shadow-red-900/30'}`}
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
              <h2 className="text-xs font-bold font-mono tracking-widest text-slate-500 uppercase">Interactive Node Handoff Graph</h2>
              {threatScore > 0 && (
                <span className={`text-[10px] font-mono font-bold tracking-wider px-2 py-0.5 rounded bg-red-950 text-red-400 border border-red-500/25`}>
                  COMBINED RISK: {threatScore}/100
                </span>
              )}
            </div>
            <AgentGraph agentStates={agentStates} />
          </div>

          {/* Console / Event Log Feed */}
          <div className="lg:col-span-4 space-y-3 flex flex-col justify-between">
            <div>
              <h2 className="text-xs font-bold font-mono tracking-widest text-slate-500 uppercase mb-3">Live Operations Log</h2>
              <LiveLog events={logEvents} />
            </div>
            
            {/* Simple Legend Card */}
            <div className="bg-slate-900/40 border border-slate-900 rounded-xl p-4 space-y-2">
              <h3 className="text-[10px] font-mono font-bold text-slate-500 tracking-wider">COORDINATION METRICS</h3>
              <div className="grid grid-cols-2 gap-2 text-[10px] font-mono text-slate-400">
                <div>• Total Swarms: <span className="text-slate-200">9 Agents</span></div>
                <div>• Rooms: <span className="text-slate-200">9 Active</span></div>
                <div>• Platform: <span className="text-slate-200">Band AI SDK</span></div>
                <div>• Interface: <span className="text-slate-200">FastAPI WS</span></div>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Segment: Boardroom Verdict or Status Cards */}
        <div className="space-y-6">
          {/* Boardroom Escalation Panel */}
          <ExecutivePanel decision={ceoDecision} threatScore={threatScore} />

          {/* Individual Agent status list */}
          <div>
            <h2 className="text-xs font-bold font-mono tracking-widest text-slate-500 uppercase mb-4">Autonomous Specialist Swarm</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-9 gap-4">
              {AGENTS.map((agent) => (
                <div key={agent.name} className="lg:col-span-1 md:col-span-1">
                  <AgentCard
                    name={agent.name}
                    displayName={agent.displayName}
                    status={agentStates[agent.name]}
                    description={agent.description}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
export default WarRoom;
