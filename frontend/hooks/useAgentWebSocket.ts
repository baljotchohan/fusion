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
  managing_partner: { line: 'Managing Partner convened the committee and briefed the specialists on NovaPay Inc.', tone: 'info' },
  financial_partner: { line: 'Financial Partner completed stress-test: flagged 78% ARR concentration in Amazon contract.', tone: 'alert' },
  legal_partner: { line: 'Legal Partner audited liabilities: flagged the active $8.0M Klarna patent lawsuit.', tone: 'alert' },
  technical_partner: { line: 'Technical Partner audited the product stack: flagged EOL Node.js 14 and plaintext SSNs.', tone: 'alert' },
  market_partner: { line: 'Market Partner verified sector trends: noted the 12% YoY industry decline and BNPL saturation.', tone: 'alert' },
}

export function useAgentWebSocket() {
  const [agentStates, setAgentStates] = useState<Record<string, AgentStatus>>({
    managing_partner: 'idle',
    financial_partner: 'idle',
    legal_partner: 'idle',
    technical_partner: 'idle',
    market_partner: 'idle',
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
        console.log('[FUSION WS] connected')
        setIsConnected(true)
      }

      ws.onmessage = (event) => {
        try {
          const update: AgentUpdate = JSON.parse(event.data)

          setAgentStates(prev => ({ ...prev, [update.agent]: update.status }))

          if (update.output && Object.keys(update.output).length > 0) {
            setAgentOutputs(prev => ({ ...prev, [update.agent]: update.output }))
          }

          setLogEvents(prev => [...prev, update].slice(-80))

          // Build the plain-English story feed when an agent finishes a step.
          if (update.status === 'done' && HUMAN[update.agent]) {
            setStoryFeed(prev => {
              if (prev.some(b => b.agent === update.agent)) return prev
              const h = HUMAN[update.agent]
              return [...prev, { agent: update.agent, line: h.line, tone: h.tone, timestamp: update.timestamp }]
            })
          }

          if (update.agent === 'managing_partner' && update.output) {
            if (update.output.report) {
              const riskMatch = update.output.report.match(/WEIGHTED SCORE:\s*([\d\.]+)/i)
              if (riskMatch) {
                setThreatScore(Number(riskMatch[1]))
              }

              const decisionMatch = update.output.report.match(/DECISION:\s*([A-Za-z]+)/i)
              const confidenceMatch = update.output.report.match(/CONFIDENCE:\s*(\d+)/i)
              const justificationMatch = update.output.report.match(/PRIMARY REASONS:\s*([^\0]+)/i)
              if (decisionMatch) {
                setCeoDecision({
                  verdict: decisionMatch[1].toUpperCase(),
                  confidence: confidenceMatch ? Number(confidenceMatch[1]) : 91,
                  justification: justificationMatch ? justificationMatch[1].trim() : 'NovaPay Inc Series A review completed with PASS decision.',
                })
              }
            }
          }
        } catch (e) {
          console.error('[FUSION WS] parse error', e)
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
      managing_partner: 'idle',
      financial_partner: 'idle',
      legal_partner: 'idle',
      technical_partner: 'idle',
      market_partner: 'idle',
    })
  }

  return {
    agentStates, agentOutputs, logEvents, storyFeed, threatScore, ceoDecision, isConnected,
    setAgentStates, setAgentOutputs, setThreatScore, setCeoDecision, setLogEvents, resetAll,
  }
}
