// hooks/useAgentWebSocket.ts
import { useState, useEffect, useCallback } from 'react'
import { getCurrentIdToken } from '@/lib/firebase'

export type AgentStatus = 'idle' | 'working' | 'done' | 'alert'
export type EventStatus = AgentStatus | 'debate' | 'memory_match' | 'confidence_update'

export interface AgentUpdate {
  agent: string
  status: EventStatus
  output: Record<string, any>
  timestamp: string
}

export interface StoryBeat {
  agent: string
  line: string
  tone: 'info' | 'alert' | 'success'
  timestamp: string
}

// Display names for the story feed — the actual finding text comes from the backend output.
const AGENT_LABELS: Record<string, string> = {
  managing_partner: 'Managing Partner',
  financial_partner: 'Financial Partner',
  legal_partner: 'Legal Partner',
  technical_partner: 'Technical Partner',
  market_partner: 'Market Partner',
}

function buildStoryLine(agent: string, output: Record<string, any>): { line: string; tone: StoryBeat['tone'] } {
  const label = AGENT_LABELS[agent] || agent
  // Prefer structured backend summary, then first 120 chars of the report
  const summary: string = output?.summary || output?.current_action || ''
  const report: string = output?.report || ''
  const firstLine = (summary || report).replace(/[-—#*`]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 120)
  const redFlagCount: number = output?.red_flag_count ?? 0
  const tone: StoryBeat['tone'] = redFlagCount > 0 ? 'alert' : agent === 'managing_partner' ? 'info' : 'alert'
  const line = firstLine
    ? `${label}: ${firstLine}${firstLine.length >= 120 ? '…' : ''}`
    : `${label} completed analysis.`
  return { line, tone }
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
  const [partialConfidence, setPartialConfidence] = useState<number>(0)
  const [memoryMatch, setMemoryMatch] = useState<{ company: string; deal: string } | null>(null)

  const [showRecoveryPrompt, setShowRecoveryPrompt] = useState(false)

  // Stable reference — all deps are React-guaranteed stable state setters.
  // Must be useCallback so restoreDealState (which depends on it) doesn't
  // get a new reference every render and trigger an infinite effect loop.
  const resetAll = useCallback(() => {
    setThreatScore(0)
    setCeoDecision(null)
    setLogEvents([])
    setStoryFeed([])
    setAgentOutputs({})
    setShowRecoveryPrompt(false)
    setPartialConfidence(0)
    setMemoryMatch(null)
    setAgentStates({
      managing_partner: 'idle',
      financial_partner: 'idle',
      legal_partner: 'idle',
      technical_partner: 'idle',
      market_partner: 'idle',
    })
  }, [])

  useEffect(() => {
    resetAll()

    let ws: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let reconnectDelay = 1000
    const maxDelay = 10000
    let cancelled = false  // guards all setState calls after unmount/uid-change

    async function connect() {
      if (cancelled) return
      const baseUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws'
      const token = await getCurrentIdToken().catch(() => null)
      if (cancelled) return  // uid may have changed while we awaited the token
      const wsUrl = token ? `${baseUrl}?token=${encodeURIComponent(token)}` : baseUrl
      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        if (cancelled) { ws?.close(); return }
        console.log('[FUSION WS] connected')
        setIsConnected(true)
        reconnectDelay = 1000
      }

      ws.onmessage = (event) => {
        if (cancelled) return
        try {
          const update: AgentUpdate = JSON.parse(event.data)

          // Handle memory match — surface it but don't change agent status
          if (update.status === 'memory_match') {
            setMemoryMatch({ company: update.output?.matched_company || '', deal: update.output?.matched_deal || '' })
            setLogEvents(prev => [...prev, update].slice(-80))
            return
          }

          // Handle partial confidence updates embedded in specialist "done" events
          if (typeof update.output?.partial_confidence === 'number') {
            setPartialConfidence(update.output.partial_confidence)
          }

          // Debate events go into the log but don't change the agent card status
          if (update.status === 'debate' || update.status === 'confidence_update') {
            setLogEvents(prev => [...prev, update].slice(-80))
            return
          }

          setAgentStates(prev => ({ ...prev, [update.agent]: update.status as AgentStatus }))

          if (update.output && Object.keys(update.output).length > 0) {
            setAgentOutputs(prev => ({ ...prev, [update.agent]: update.output }))
          }

          // Collapse consecutive heartbeats from the same agent in the same phase
          setLogEvents(prev => {
            const last = prev[prev.length - 1]
            if (last && last.agent === update.agent && last.status === update.status) {
              return [...prev.slice(0, -1), update].slice(-80)
            }
            return [...prev, update].slice(-80)
          })

          // Build the plain-English story feed from actual backend output
          if (update.status === 'done') {
            setStoryFeed(prev => {
              if (prev.some(b => b.agent === update.agent)) return prev
              const { line, tone } = buildStoryLine(update.agent, update.output)
              return [...prev, { agent: update.agent, line, tone, timestamp: update.timestamp }]
            })
          }

          if (update.agent === 'managing_partner' && update.output) {
            const out = update.output
            const report: string = out.report || ''
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
        if (cancelled) return
        setIsConnected(false)
        console.log(`[FUSION WS] closed. Reconnecting in ${reconnectDelay}ms...`)
        reconnectTimer = setTimeout(connect, reconnectDelay)
        reconnectDelay = Math.min(reconnectDelay * 2, maxDelay)
      }
      ws.onerror = () => { if (!cancelled) ws?.close() }
    }

    connect()
    return () => {
      cancelled = true
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
    showRecoveryPrompt, setShowRecoveryPrompt,
    partialConfidence, setPartialConfidence,
    memoryMatch, setMemoryMatch,
  }
}
