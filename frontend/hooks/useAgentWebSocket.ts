// hooks/useAgentWebSocket.ts
import { useState, useEffect } from 'react'

export type AgentStatus = 'idle' | 'working' | 'done' | 'alert'

export interface AgentUpdate {
  agent: string
  status: AgentStatus
  output: Record<string, any>
  timestamp: string
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
  const [logEvents, setLogEvents] = useState<AgentUpdate[]>([])
  const [threatScore, setThreatScore] = useState<number>(0)
  const [ceoDecision, setCeoDecision] = useState<Record<string, any> | null>(null)
  const [isConnected, setIsConnected] = useState<boolean>(false)

  useEffect(() => {
    // Connect to FastAPI websocket server
    const ws = new WebSocket('ws://localhost:8000/ws')

    ws.onopen = () => {
      logger_info('WebSocket connected to FastAPI server')
      setIsConnected(true)
    }

    ws.onmessage = (event) => {
      try {
        const update: AgentUpdate = JSON.parse(event.data)
        
        // Update individual agent status
        setAgentStates(prev => ({
          ...prev,
          [update.agent]: update.status
        }))
        
        // Add message payload to logs
        setLogEvents(prev => [update, ...prev].slice(0, 50)) // Keep last 50 events

        // Special handlers for outputs
        if (update.agent === 'attack_path_agent' && update.output) {
          // Extract score (e.g. from report text or structured output)
          // For demo, if score is calculated we extract it
          if (update.output.score) {
            setThreatScore(Number(update.output.score))
          } else if (update.output.report) {
            // regex search for risk score in report text
            const match = update.output.report.match(/Combined Risk Score:\s*(\d+)/i)
            if (match) {
              setThreatScore(Number(match[1]))
            }
          }
        }

        if (update.agent === 'executive_decision' && update.output) {
          if (update.output.report) {
            // Parse CEO decision out of final text or structure
            const ceoMatch = update.output.report.match(/FINAL CEO DECISION:\s*(\w+)/i)
            const justificationMatch = update.output.report.match(/Justification:\s*([^\n]+)/i)
            if (ceoMatch) {
              setCeoDecision({
                verdict: ceoMatch[1],
                justification: justificationMatch ? justificationMatch[1] : 'Threat containment ROI validated.'
              })
            }
          }
        }
      } catch (e) {
        console.error('Error parsing WebSocket message:', e)
      }
    }

    ws.onclose = () => {
      logger_info('WebSocket connection closed')
      setIsConnected(false)
    }

    return () => {
      ws.close()
    }
  }, [])

  return { agentStates, logEvents, threatScore, ceoDecision, isConnected, setAgentStates, setThreatScore, setCeoDecision, setLogEvents }
}

function logger_info(msg: string) {
  console.log(`[ARGUS WS] ${msg}`)
}
