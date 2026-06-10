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
  const [agentOutputs, setAgentOutputs] = useState<Record<string, Record<string, any>>>({})
  const [logEvents, setLogEvents] = useState<AgentUpdate[]>([])
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
        logger_info('WebSocket connected to FastAPI server')
        setIsConnected(true)
      }

      ws.onmessage = (event) => {
        try {
          const update: AgentUpdate = JSON.parse(event.data)

          setAgentStates(prev => ({
            ...prev,
            [update.agent]: update.status
          }))

          if (update.output && Object.keys(update.output).length > 0) {
            setAgentOutputs(prev => ({
              ...prev,
              [update.agent]: update.output
            }))
          }

          setLogEvents(prev => [update, ...prev].slice(0, 50))

          if (update.agent === 'attack_path_agent' && update.output) {
            if (update.output.score) {
              setThreatScore(Number(update.output.score))
            } else if (update.output.report) {
              const match = update.output.report.match(/Combined Risk Score:\s*(\d+)/i)
              if (match) setThreatScore(Number(match[1]))
            }
          }

          if (update.agent === 'executive_decision' && update.output) {
            if (update.output.report) {
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
        logger_info('WebSocket disconnected — reconnecting in 3s...')
        setIsConnected(false)
        reconnectTimer = setTimeout(connect, 3000)
      }

      ws.onerror = () => {
        ws?.close()
      }
    }

    connect()

    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer)
      ws?.close()
    }
  }, [])

  return { agentStates, agentOutputs, logEvents, threatScore, ceoDecision, isConnected, setAgentStates, setAgentOutputs, setThreatScore, setCeoDecision, setLogEvents }
}

function logger_info(msg: string) {
  console.log(`[ARGUS WS] ${msg}`)
}
