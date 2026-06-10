// components/AgentGraph.tsx
import React, { useMemo } from 'react'
import ReactFlow, { Node, Edge, Background, Controls } from 'reactflow'
import 'reactflow/dist/style.css'
import { AgentStatus } from '../hooks/useAgentWebSocket'

function getNodeStyle(status: AgentStatus, theme: 'dark' | 'light') {
  const base = {
    borderRadius: '12px',
    fontSize: '10px',
    padding: '12px 16px',
    fontFamily: 'var(--font-mono)',
    letterSpacing: '0.05em',
    fontWeight: 'bold',
    minWidth: '160px',
    textAlign: 'center' as const,
    transition: 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
    boxShadow: theme === 'dark' 
      ? '0 4px 12px rgba(0, 0, 0, 0.3)' 
      : '0 4px 8px rgba(0, 0, 0, 0.03)'
  }
  
  const lightStyles = {
    idle: {
      ...base,
      background: '#ffffff',
      color: '#64748b',
      border: '1px solid rgba(0,0,0,0.08)'
    },
    working: {
      ...base,
      background: '#fffbeb',
      color: '#d97706',
      border: '1.5px solid #f59e0b',
      boxShadow: '0 0 16px rgba(245,158,11,0.2)'
    },
    done: {
      ...base,
      background: '#f0fdf4',
      color: '#16a34a',
      border: '1.5px solid #10b981',
      boxShadow: '0 0 16px rgba(16,185,129,0.15)'
    },
    alert: {
      ...base,
      background: '#fef2f2',
      color: '#dc2626',
      border: '1.5px solid #ef4444',
      boxShadow: '0 0 20px rgba(239,68,68,0.2)'
    }
  }

  const darkStyles = {
    idle: {
      ...base,
      background: '#121214',
      color: '#94a3b8',
      border: '1px solid rgba(255,255,255,0.06)'
    },
    working: {
      ...base,
      background: '#1e150a',
      color: '#fbbf24',
      border: '1.5px solid #fbbf24',
      boxShadow: '0 0 20px rgba(251,191,36,0.25)'
    },
    done: {
      ...base,
      background: '#091b15',
      color: '#34d399',
      border: '1.5px solid #34d399',
      boxShadow: '0 0 20px rgba(52,211,153,0.2)'
    },
    alert: {
      ...base,
      background: '#220e0e',
      color: '#f87171',
      border: '1.5px solid #f87171',
      boxShadow: '0 0 25px rgba(248,113,113,0.3)'
    }
  }
  
  const chosenStyles = theme === 'dark' ? darkStyles : lightStyles
  return chosenStyles[status] || chosenStyles.idle
}

interface AgentGraphProps {
  agentStates: Record<string, AgentStatus>
  theme: 'dark' | 'light'
  heightClass?: string
}

export function AgentGraph({ agentStates, theme, heightClass = 'h-[580px]' }: AgentGraphProps) {
  
  const nodes = useMemo<Node[]>(() => [
    // Top Row: Analysis & Input
    {
      id: 'threat_intel_agent',
      position: { x: 50, y: 50 },
      data: { label: '🔍 THREAT INTEL' },
      style: getNodeStyle(agentStates['threat_intel_agent'], theme)
    },
    {
      id: 'recon_agent',
      position: { x: 260, y: 50 },
      data: { label: '🗺 RECON' },
      style: getNodeStyle(agentStates['recon_agent'], theme)
    },
    {
      id: 'detection_agent',
      position: { x: 470, y: 50 },
      data: { label: '📡 DETECTION' },
      style: getNodeStyle(agentStates['detection_agent'], theme)
    },

    // Middle Row: Simulation & Evaluation
    {
      id: 'red_team_agent',
      position: { x: 50, y: 200 },
      data: { label: '⚔ RED TEAM' },
      style: getNodeStyle(agentStates['red_team_agent'], theme)
    },
    {
      id: 'attack_path_agent',
      position: { x: 260, y: 200 },
      data: { label: '📊 ATTACK PATH' },
      style: getNodeStyle(agentStates['attack_path_agent'], theme)
    },
    {
      id: 'malware_agent',
      position: { x: 470, y: 200 },
      data: { label: '🦠 MALWARE INV' },
      style: getNodeStyle(agentStates['malware_agent'], theme)
    },

    // Bottom Row: Mitigation & Brain
    {
      id: 'blue_team_agent',
      position: { x: 140, y: 350 },
      data: { label: '🛡 BLUE TEAM' },
      style: getNodeStyle(agentStates['blue_team_agent'], theme)
    },
    {
      id: 'incident_commander',
      position: { x: 380, y: 350 },
      data: { label: '🎯 INCIDENT CMDR' },
      style: {
        ...getNodeStyle(agentStates['incident_commander'], theme),
        width: 180,
        height: 44,
        fontSize: '11px'
      }
    },

    // Executive Layer
    {
      id: 'executive_decision',
      position: { x: 240, y: 480 },
      data: { label: '👔 EXECUTIVE BOARD' },
      style: getNodeStyle(agentStates['executive_decision'], theme)
    }
  ], [agentStates, theme])


  // Connection Edges showing data flow via the Commander
  const edgeColor = theme === 'dark' ? '#334155' : '#cbd5e1'
  const edges = useMemo<Edge[]>(() => [
    { id: 'e1', source: 'threat_intel_agent', target: 'incident_commander', animated: true, style: { stroke: edgeColor, strokeWidth: 1.5 } },
    { id: 'e2', source: 'incident_commander', target: 'recon_agent', animated: true, style: { stroke: edgeColor, strokeWidth: 1.5 } },
    { id: 'e3', source: 'incident_commander', target: 'detection_agent', animated: true, style: { stroke: edgeColor, strokeWidth: 1.5 } },
    { id: 'e4', source: 'incident_commander', target: 'red_team_agent', animated: true, style: { stroke: edgeColor, strokeWidth: 1.5 } },
    { id: 'e5', source: 'red_team_agent', target: 'attack_path_agent', animated: true, style: { stroke: edgeColor, strokeWidth: 1.5 } },
    { id: 'e6', source: 'incident_commander', target: 'malware_agent', animated: true, style: { stroke: edgeColor, strokeWidth: 1.5 } },
    { id: 'e7', source: 'incident_commander', target: 'blue_team_agent', animated: true, style: { stroke: edgeColor, strokeWidth: 1.5 } },
    { id: 'e8', source: 'incident_commander', target: 'executive_decision', animated: true, style: { stroke: edgeColor, strokeWidth: 1.5 } }
  ], [edgeColor])

  const gridColor = theme === 'dark' ? '#1f2937' : '#e2e8f0'

  return (
    <div className={`w-full ${heightClass} rounded-2xl overflow-hidden glassmorphic shadow-md transition-all duration-300`}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        style={{ background: 'transparent' }}
      >
        <Background color={gridColor} gap={20} size={1} />
        <Controls showInteractive={false} className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200" />
      </ReactFlow>
    </div>
  )
}
export default AgentGraph;
