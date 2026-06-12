// hooks/useAgentWebSocket.ts
import { useState, useEffect } from 'react'

export type AgentStatus = 'idle' | 'working' | 'done' | 'alert'

export interface AgentUpdate {
  agent: string
  status: AgentStatus
  output: Record<string, any>
  timestamp: string
}

export interface StoryBeat {
  agent: string
  line: string
  tone: 'info' | 'alert' | 'success'
  timestamp: string
}

// Plain-English narration for each agent's completed work. Keeps the dashboard
// readable for non-experts — the raw report still lives on the agent card.
const HUMAN: Record<string, { line: string; tone: StoryBeat['tone'] }> = {
  threat_intel_agent: { line: 'Threat Intel identified a spear-phishing attack aimed at the CEO and mapped it to known hacker techniques (MITRE ATT&CK).', tone: 'alert' },
  recon_agent: { line: 'Recon mapped the network — the mail server and customer database are the exposed, high-value targets.', tone: 'info' },
  detection_agent: { line: 'Detection confirmed it got in: the CEO’s workstation actually executed the malicious attachment.', tone: 'alert' },
  red_team_agent: { line: 'Red Team predicted the attacker’s path: pivot from the CEO’s laptop to the customer database within hours.', tone: 'info' },
  malware_agent: { line: 'Malware Investigation identified the file as an Emotet-style trojan calling home to 2 attacker-controlled domains.', tone: 'alert' },
  attack_path_agent: { line: 'Attack Path scored the overall risk CRITICAL and flagged the customer database as the crown jewel at risk.', tone: 'alert' },
  blue_team_agent: { line: 'Blue Team built the containment playbook: isolate the CEO’s machine, block the C2 domains, reset C-Suite passwords.', tone: 'success' },
  incident_commander: { line: 'Incident Commander correlated every specialist report into one incident timeline.', tone: 'info' },
  executive_decision: { line: 'Executive Board (CFO → Legal → Ops → CEO) weighed cost vs. risk and reached a business decision.', tone: 'success' },
}

export function useAgentWebSocket() {
  const [agentStates, setAgentStates] = useState<Record<string, AgentStatus>>({
    threat_intel_agent: 'idle',
    recon_agent: 'idle',
    red_team_agent: 'idle',
    attack_path_agent: 'idle',
    detection_agent: 'idle',
    malware_agent: 'idle',
    blue_team_agent: 'idle',
    incident_commander: 'idle',
    executive_decision: 'idle',
  })
  const [agentOutputs, setAgentOutputs] = useState<Record<string, Record<string, any>>>({})
  const [logEvents, setLogEvents] = useState<AgentUpdate[]>([])
  const [storyFeed, setStoryFeed] = useState<StoryBeat[]>([])
  const [threatScore, setThreatScore] = useState<number>(0)
  const [ceoDecision, setCeoDecision] = useState<Record<string, any> | null>(null)
  const [isConnected, setIsConnected] = useState<boolean>(false)

  useEffect(() => {
    let ws: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null

    function connect() {
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws'
      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('[Fusion WS] connected')
        setIsConnected(true)
      }

      ws.onmessage = (event) => {
        try {
          const update: AgentUpdate = JSON.parse(event.data)

          setAgentStates(prev => ({ ...prev, [update.agent]: update.status }))

          if (update.output && Object.keys(update.output).length > 0) {
            setAgentOutputs(prev => ({ ...prev, [update.agent]: update.output }))
          }

          setLogEvents(prev => [update, ...prev].slice(0, 80))

          // Build the plain-English story feed when an agent finishes a step.
          if (update.status === 'done' && HUMAN[update.agent]) {
            setStoryFeed(prev => {
              if (prev.some(b => b.agent === update.agent)) return prev
              const h = HUMAN[update.agent]
              return [...prev, { agent: update.agent, line: h.line, tone: h.tone, timestamp: update.timestamp }]
            })
          }

          if (update.agent === 'attack_path_agent' && update.output) {
            if (update.output.score) {
              setThreatScore(Number(update.output.score))
            } else if (update.output.report) {
              const match = update.output.report.match(/Combined Risk Score:\s*(\d+)/i)
              if (match) setThreatScore(Number(match[1]))
            }
          }

          if (update.agent === 'executive_decision' && update.output?.report) {
            const ceoMatch = update.output.report.match(/FINAL CEO DECISION:\s*(\w+)/i)
            const justificationMatch = update.output.report.match(/Justification:\s*([^\n]+)/i)
            if (ceoMatch) {
              setCeoDecision({
                verdict: ceoMatch[1],
                justification: justificationMatch ? justificationMatch[1] : 'Threat containment ROI validated.',
              })
            }
          }
        } catch (e) {
          console.error('[Fusion WS] parse error', e)
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        reconnectTimer = setTimeout(connect, 3000)
      }
      ws.onerror = () => ws?.close()
    }

    connect()
    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer)
      ws?.close()
    }
  }, [])

  function resetAll() {
    setThreatScore(0)
    setCeoDecision(null)
    setLogEvents([])
    setStoryFeed([])
    setAgentOutputs({})
    setAgentStates({
      threat_intel_agent: 'idle', recon_agent: 'idle', red_team_agent: 'idle',
      attack_path_agent: 'idle', detection_agent: 'idle', malware_agent: 'idle',
      blue_team_agent: 'idle', incident_commander: 'idle', executive_decision: 'idle',
    })
  }

  return {
    agentStates, agentOutputs, logEvents, storyFeed, threatScore, ceoDecision, isConnected,
    setAgentStates, setAgentOutputs, setThreatScore, setCeoDecision, setLogEvents, resetAll,
  }
}
