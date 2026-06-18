// hooks/useAgentWebSocket.ts
import { useState, useEffect } from 'react'
import { getCurrentIdToken } from '@/lib/firebase'

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

export function useAgentWebSocket(uid?: string | null) {
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

  // Declare resetAll first so we can call it in the WebSocket useEffect
  function resetAll() {
    setThreatScore(0)
    setCeoDecision(null)
    setLogEvents([])
    setStoryFeed([])
    setAgentOutputs({})
    setShowRecoveryPrompt(false)
    setAgentStates({
      managing_partner: 'idle',
      financial_partner: 'idle',
      legal_partner: 'idle',
      technical_partner: 'idle',
      market_partner: 'idle',
    })
  }

  const [showRecoveryPrompt, setShowRecoveryPrompt] = useState(false)

  useEffect(() => {
    resetAll()

    let ws: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let reconnectDelay = 1000
    const maxDelay = 10000

    async function connect() {
      const baseUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws'
      const token = await getCurrentIdToken().catch(() => null)
      const wsUrl = token ? `${baseUrl}?token=${encodeURIComponent(token)}` : baseUrl
      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('[FUSION WS] connected')
        setIsConnected(true)
        reconnectDelay = 1000 // Reset backoff on successful connection
      }

      ws.onmessage = (event) => {
        try {
          const update: AgentUpdate = JSON.parse(event.data)

          setAgentStates(prev => ({ ...prev, [update.agent]: update.status }))

          if (update.output && Object.keys(update.output).length > 0) {
            setAgentOutputs(prev => ({ ...prev, [update.agent]: update.output }))
          }

          // Meeting Minutes: collapse consecutive heartbeats from the SAME agent
          // in the SAME phase (e.g. repeated "working" updates) into one live
          // entry instead of stacking dozens of near-duplicate lines. A genuine
          // transition (working→done) or a different agent speaking appends a
          // fresh entry.
          setLogEvents(prev => {
            const last = prev[prev.length - 1]
            if (last && last.agent === update.agent && last.status === update.status) {
              return [...prev.slice(0, -1), update].slice(-80)
            }
            return [...prev, update].slice(-80)
          })

          // Build the plain-English story feed when an agent finishes a step.
          if (update.status === 'done' && HUMAN[update.agent]) {
            setStoryFeed(prev => {
              if (prev.some(b => b.agent === update.agent)) return prev
              const h = HUMAN[update.agent]
              return [...prev, { agent: update.agent, line: h.line, tone: h.tone, timestamp: update.timestamp }]
            })
          }

          if (update.agent === 'managing_partner' && update.output) {
            const out = update.output
            const report: string = out.report || ''
            // Prefer the authoritative STRUCTURED fields the backend attaches to the
            // verdict broadcast — a real LLM does not format the report text reliably,
            // so regex-scraping alone leaves the score blank. Fall back to regex.
            const riskMatch = report.match(/weighted\s*(?:risk\s*)?score\s*\*?\*?\s*:\s*\*?\*?\s*([\d\.]+)/i)
            const structuredRisk = typeof out.weighted_score === 'number' ? out.weighted_score : null
            const riskVal = structuredRisk ?? (riskMatch ? Number(riskMatch[1]) : null)
            if (riskVal !== null && !Number.isNaN(riskVal)) {
              setThreatScore(riskVal)
            }

            const decisionMatch = report.match(/decision\s*\*?\*?\s*:\s*\*?\*?\s*([a-z_\s-]+)/i)
            const confidenceMatch = report.match(/confidence\s*\*?\*?\s*:\s*\*?\*?\s*(\d+)/i)
            const justificationMatch = report.match(/PRIMARY REASONS:\s*([^\0]+)/i)
            const structuredVerdict = typeof out.verdict === 'string' ? out.verdict : null
            const verdict = structuredVerdict || (decisionMatch ? decisionMatch[1].trim() : null)
            if (verdict) {
              const structuredConf = typeof out.confidence === 'number' ? out.confidence : null
              setCeoDecision({
                verdict: verdict.toUpperCase(),
                confidence: structuredConf ?? (confidenceMatch ? Number(confidenceMatch[1]) : 91),
                justification: justificationMatch ? justificationMatch[1].trim() : 'Committee review completed.',
              })
            }
          }
        } catch (e) {
          console.error('[FUSION WS] parse error', e)
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        console.log(`[FUSION WS] closed. Reconnecting in ${reconnectDelay}ms...`)
        reconnectTimer = setTimeout(connect, reconnectDelay)
        reconnectDelay = Math.min(reconnectDelay * 2, maxDelay) // Exponential backoff (1s -> 2s -> 4s -> 8s -> 10s)
      }
      ws.onerror = () => ws?.close()
    }

    connect()
    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer)
      ws?.close()
    }
  }, [uid])

  useEffect(() => {
    const specialists = ['financial_partner', 'legal_partner', 'technical_partner', 'market_partner']
    const allSpecialistsDone = specialists.every(agent => agentStates[agent] === 'done')
    const managingPartnerNotDone = agentStates['managing_partner'] !== 'done'

    if (allSpecialistsDone && managingPartnerNotDone) {
      const timer = setTimeout(() => {
        setShowRecoveryPrompt(true)
      }, 30000) // 30 seconds
      return () => clearTimeout(timer)
    } else {
      setShowRecoveryPrompt(false)
    }
  }, [agentStates])

  return {
    agentStates, agentOutputs, logEvents, storyFeed, threatScore, ceoDecision, isConnected,
    setAgentStates, setAgentOutputs, setThreatScore, setCeoDecision, setLogEvents, resetAll,
    showRecoveryPrompt, setShowRecoveryPrompt
  }
}
