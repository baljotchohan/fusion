// components/AgentGraph.tsx
import React, { useMemo } from 'react'
import ReactFlow, { Node, Edge, Background, Controls } from 'reactflow'
import 'reactflow/dist/style.css'
import { AgentStatus } from '../hooks/useAgentWebSocket'

function getNodeStyle(status: AgentStatus) {
  const base = {
    borderRadius: '12px',
    fontSize: '11px',
    padding: '10px 14px',
    fontFamily: 'monospace',
    letterSpacing: '0.05em',
    fontWeight: 'bold',
    minWidth: '150px',
    textAlign: 'center' as const,
    transition: 'all 0.5s ease-in-out',
    boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06)'
  }
  
  const styles = {
    idle: {
      ...base,
      background: '#0f172a',
      color: '#64748b',
      border: '1px solid #1e293b'
    },
    working: {
      ...base,
      background: '#78350f',
      color: '#f59e0b',
      border: '2px solid #f59e0b',
      boxShadow: '0 0 20px rgba(245,158,11,0.25)'
    },
    done: {
      ...base,
      background: '#064e3b',
      color: '#34d399',
      border: '2px solid #10b981',
      boxShadow: '0 0 15px rgba(16,185,129,0.15)'
    },
    alert: {
      ...base,
      background: '#7f1d1d',
      color: '#fca5a5',
      border: '2px solid #ef4444',
      boxShadow: '0 0 20px rgba(239,68,68,0.3)'
    }
  }
  return styles[status] || styles.idle
}

interface AgentGraphProps {
  agentStates: Record<string, AgentStatus>
}

export function AgentGraph({ agentStates }: AgentGraphProps) {
  
  const nodes = useMemo<Node[]>(() => [
    // Top Row: Analysis & Input
    {
      id: 'threat_intel_agent',
      position: { x: 50, y: 50 },
      data: { label: '🔍 THREAT INTEL' },
      style: getNodeStyle(agentStates['threat_intel_agent'])
    },
    {
      id: 'recon_agent',
      position: { x: 260, y: 50 },
      data: { label: '🗺 RECON' },
      style: getNodeStyle(agentStates['recon_agent'])
    },
    {
      id: 'detection_agent',
      position: { x: 470, y: 50 },
      data: { label: '📡 DETECTION' },
      style: getNodeStyle(agentStates['detection_agent'])
    },

    // Middle Row: Simulation & Evaluation
    {
      id: 'red_team_agent',
      position: { x: 50, y: 200 },
      data: { label: '⚔ RED TEAM' },
      style: getNodeStyle(agentStates['red_team_agent'])
    },
    {
      id: 'attack_path_agent',
      position: { x: 260, y: 200 },
      data: { label: '📊 ATTACK PATH' },
      style: getNodeStyle(agentStates['attack_path_agent'])
    },
    {
      id: 'malware_agent',
      position: { x: 470, y: 200 },
      data: { label: '🦠 MALWARE INV' },
      style: getNodeStyle(agentStates['malware_agent'])
    },

    // Bottom Row: Mitigation & Brain
    {
      id: 'blue_team_agent',
      position: { x: 140, y: 350 },
      data: { label: '🛡 BLUE TEAM' },
      style: getNodeStyle(agentStates['blue_team_agent'])
    },
    {
      id: 'incident_commander',
      position: { x: 380, y: 350 },
      data: { label: '🎯 INCIDENT COMMANDER' },
      style: {
        ...getNodeStyle(agentStates['incident_commander']),
        width: 200,
        height: 48,
        fontSize: '12px'
      }
    },

    // Executive Layer
    {
      id: 'executive_decision',
      position: { x: 240, y: 480 },
      data: { label: '👔 EXECUTIVE BOARD' },
      style: getNodeStyle(agentStates['executive_decision'])
    }
  ], [agentStates])

  // Connection Edges showing data flow via the Commander
  const edges = useMemo<Edge[]>(() => [
    { id: 'e1', source: 'threat_intel_agent', target: 'incident_commander', animated: true, style: { stroke: '#475569' } },
    { id: 'e2', source: 'incident_commander', target: 'recon_agent', animated: true, style: { stroke: '#475569' } },
    { id: 'e3', source: 'incident_commander', target: 'detection_agent', animated: true, style: { stroke: '#475569' } },
    { id: 'e4', source: 'incident_commander', target: 'red_team_agent', animated: true, style: { stroke: '#475569' } },
    { id: 'e5', source: 'red_team_agent', target: 'attack_path_agent', animated: true, style: { stroke: '#475569' } },
    { id: 'e6', source: 'incident_commander', target: 'malware_agent', animated: true, style: { stroke: '#475569' } },
    { id: 'e7', source: 'incident_commander', target: 'blue_team_agent', animated: true, style: { stroke: '#475569' } },
    { id: 'e8', source: 'incident_commander', target: 'executive_decision', animated: true, style: { stroke: '#475569' } }
  ], [])

  return (
    <div className="w-full h-[580px] bg-slate-950/80 rounded-2xl overflow-hidden border border-slate-900 shadow-inner">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
      >
        <Background color="#334155" gap={20} size={1} />
        <Controls showInteractive={false} className="bg-slate-900 border border-slate-800 text-slate-300" />
      </ReactFlow>
    </div>
  )
}
export default AgentGraph;
