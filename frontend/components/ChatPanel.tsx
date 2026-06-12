// components/ChatPanel.tsx — Commander chat with visible reasoning steps.
import React, { useState, useRef, useEffect, useCallback } from 'react'
import { API_BASE } from '../lib/agents'

interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
  incidentId?: string
  intent?: string
  thinkingSteps?: string[]
  suggestions?: string[]
}

// Minimal **bold** + line-break renderer so replies read cleanly without a markdown dep.
function RichText({ text }: { text: string }) {
  const lines = text.split('\n')
  return (
    <>
      {lines.map((line, li) => {
        const parts = line.split(/(\*\*[^*]+\*\*)/g)
        return (
          <span key={li} className="block">
            {parts.map((p, pi) =>
              p.startsWith('**') && p.endsWith('**')
                ? <strong key={pi} className="font-semibold text-slate-900 dark:text-white">{p.slice(2, -2)}</strong>
                : <span key={pi}>{p}</span>
            )}
          </span>
        )
      })}
    </>
  )
}

function ThinkingTrace({ steps, live }: { steps: string[]; live?: boolean }) {
  const [open, setOpen] = useState(true)
  return (
    <div className="mb-2 rounded-lg border border-slate-200/60 dark:border-slate-800/70 bg-slate-50/70 dark:bg-slate-950/50 overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider text-slate-500 dark:text-slate-400 hover:bg-slate-100/60 dark:hover:bg-slate-900/60 transition"
      >
        <span className={`transition-transform ${open ? 'rotate-90' : ''}`}>▸</span>
        <span className="flex items-center gap-1.5">
          {live && <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-pulse" />}
          Commander reasoning · {steps.length} step{steps.length === 1 ? '' : 's'}
        </span>
      </button>
      {open && (
        <ol className="px-3 pb-2.5 pt-1 space-y-1.5">
          {steps.map((s, i) => (
            <li key={i} className="flex gap-2 text-[11px] leading-relaxed text-slate-600 dark:text-slate-300">
              <span className="mt-1 w-1.5 h-1.5 rounded-full bg-cyan-500/70 shrink-0" />
              <span><RichText text={s} /></span>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}

interface ChatPanelProps {
  devMode: boolean
  onIncident?: () => void
}

export function ChatPanel({ devMode, onIncident }: ChatPanelProps) {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatTurn[]>([])
  const [thinking, setThinking] = useState(false)
  const [liveSteps, setLiveSteps] = useState<string[]>([])
  const [lastRaw, setLastRaw] = useState<Record<string, any> | null>(null)
  const [suggestions, setSuggestions] = useState<string[]>([
    'We got a phishing email', 'Are we under attack?', 'What has the team learned?',
  ])
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, thinking, liveSteps])

  // Load persisted history once on mount.
  useEffect(() => {
    fetch(`${API_BASE}/api/v1/chat/history?limit=40`)
      .then(r => r.json())
      .then(d => {
        if (Array.isArray(d.history) && d.history.length) {
          setMessages(d.history.map((t: any) => ({
            role: t.role,
            content: t.content,
            incidentId: t.meta?.incident_id,
            intent: t.meta?.intent,
          })))
        }
      })
      .catch(() => {})
  }, [])

  const send = useCallback(async (raw?: string) => {
    const text = (raw ?? input).trim()
    if (!text || thinking) return

    setMessages(prev => [...prev, { role: 'user', content: text }])
    setInput('')
    setThinking(true)
    setLiveSteps(['Parsing your message…'])

    // Gentle staged "thinking" animation so the user sees work happening.
    const stagedTimers = [
      setTimeout(() => setLiveSteps(s => [...s, 'Classifying intent…']), 350),
      setTimeout(() => setLiveSteps(s => [...s, 'Consulting team memory graph…']), 750),
    ]

    try {
      const response = await fetch(`${API_BASE}/api/v1/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_message: text }),
      })
      const data = await response.json()
      setLastRaw(data)
      if (data.dispatched) onIncident?.()
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.commander_response,
        incidentId: data.incident_id,
        intent: data.intent,
        thinkingSteps: data.thinking_steps || [],
        suggestions: data.suggestions || [],
      }])
      if (data.suggestions?.length) setSuggestions(data.suggestions)
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '⚠ Cannot reach the Incident Commander — is the Fusion backend running on port 8000?',
      }])
    } finally {
      stagedTimers.forEach(clearTimeout)
      setThinking(false)
      setLiveSteps([])
    }
  }, [input, thinking, onIncident])

  return (
    <div className="glassmorphic border border-slate-200/60 dark:border-slate-800/60 rounded-2xl flex flex-col shadow-sm h-[640px]">
      {/* header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200/50 dark:border-slate-800/60">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-xs shadow-sm">🎯</div>
          <div>
            <h2 className="text-[12px] font-bold text-slate-800 dark:text-slate-100">Incident Commander</h2>
            <p className="text-[9px] font-mono text-slate-400 dark:text-slate-500 uppercase tracking-wider">Plain English in · 9 agents out</p>
          </div>
        </div>
        <span className="text-[8.5px] font-mono text-slate-400 dark:text-slate-600 uppercase tracking-wider px-2 py-0.5 rounded-full border border-slate-200/60 dark:border-slate-800">live</span>
      </div>

      {/* message stream */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && !thinking && (
          <div className="h-full flex flex-col items-center justify-center text-center px-6">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-cyan-500/15 to-blue-600/15 flex items-center justify-center text-xl mb-3">🛡️</div>
            <p className="text-[13px] font-semibold text-slate-700 dark:text-slate-200">How can I help you defend?</p>
            <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-1 max-w-xs leading-relaxed">
              Report something suspicious and I’ll mobilize the right specialists, or ask about our status and what we’ve learned.
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
            <div className={`max-w-[88%] ${msg.role === 'user' ? '' : 'w-full'}`}>
              {msg.role === 'assistant' && msg.thinkingSteps && msg.thinkingSteps.length > 0 && (
                <ThinkingTrace steps={msg.thinkingSteps} />
              )}
              <div className={`px-3.5 py-2.5 rounded-2xl text-[12px] leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-gradient-to-br from-cyan-600 to-blue-600 text-white rounded-br-md'
                  : 'bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800 text-slate-700 dark:text-slate-200 rounded-bl-md'
              }`}>
                <RichText text={msg.content} />
                {msg.incidentId && msg.intent === 'attack_report' && (
                  <div className="mt-2 inline-flex items-center gap-1.5 text-[8.5px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 border border-cyan-500/20">
                    ● {msg.incidentId}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}

        {thinking && (
          <div className="flex justify-start">
            <div className="w-full">
              <ThinkingTrace steps={liveSteps} live />
              <div className="inline-flex items-center gap-2 px-3.5 py-2.5 rounded-2xl rounded-bl-md bg-white dark:bg-slate-900 border border-slate-200/70 dark:border-slate-800">
                <span className="flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                </span>
                <span className="text-[10px] font-mono text-slate-400">Coordinating…</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {devMode && lastRaw && (
        <pre className="mx-4 mb-2 text-[9px] font-mono bg-slate-950 text-emerald-400/90 p-2.5 rounded-lg overflow-auto max-h-28 border border-slate-800">
          {JSON.stringify(lastRaw, null, 2)}
        </pre>
      )}

      {/* suggestion chips */}
      <div className="px-4 pb-2 flex flex-wrap gap-1.5">
        {suggestions.slice(0, 3).map((s, i) => (
          <button
            key={i}
            onClick={() => send(s)}
            disabled={thinking}
            className="text-[10.5px] px-2.5 py-1 rounded-full border border-slate-200/70 dark:border-slate-800 text-slate-500 dark:text-slate-400 hover:border-cyan-500/40 hover:text-cyan-600 dark:hover:text-cyan-300 transition disabled:opacity-40"
          >
            {s}
          </button>
        ))}
      </div>

      {/* composer */}
      <div className="p-3 border-t border-slate-200/50 dark:border-slate-800/60 flex gap-2">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          placeholder="Report an incident or ask the Commander…"
          className="flex-1 bg-white/70 dark:bg-slate-950/60 border border-slate-200/70 dark:border-slate-800 text-slate-800 dark:text-slate-100 px-3.5 py-2.5 rounded-xl text-[12px] focus:outline-none focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-500/40 placeholder:text-slate-400 dark:placeholder:text-slate-600"
        />
        <button
          onClick={() => send()}
          disabled={thinking || !input.trim()}
          className={`px-4 rounded-xl text-xs font-bold transition ${
            thinking || !input.trim()
              ? 'bg-slate-100 text-slate-400 dark:bg-slate-900/50 dark:text-slate-600 cursor-not-allowed'
              : 'bg-gradient-to-br from-cyan-600 to-blue-600 text-white hover:opacity-90 active:scale-95'
          }`}
        >
          Send
        </button>
      </div>
    </div>
  )
}

export default ChatPanel
