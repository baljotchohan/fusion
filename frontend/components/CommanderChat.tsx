// components/CommanderChat.tsx
import React, { useState, useRef, useEffect } from 'react'

interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
  incidentId?: string
}

interface CommanderChatProps {
  devMode: boolean
}

export function CommanderChat({ devMode }: CommanderChatProps) {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatTurn[]>([])
  const [thinking, setThinking] = useState(false)
  const [lastRaw, setLastRaw] = useState<Record<string, any> | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, thinking])

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || thinking) return

    setMessages(prev => [...prev, { role: 'user', content: text }])
    setInput('')
    setThinking(true)

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiBase}/api/v1/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_message: text }),
      })
      const data = await response.json()
      setLastRaw(data)
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: data.commander_response, incidentId: data.incident_id },
      ])
    } catch (e) {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: '⚠ Cannot reach the Incident Commander — is the ARGUS backend running?' },
      ])
    } finally {
      setThinking(false)
    }
  }

  return (
    <div className="glassmorphic border border-slate-200/60 dark:border-slate-850/50 rounded-xl p-4 flex flex-col shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-[10px] font-bold font-mono tracking-widest text-slate-400 dark:text-slate-500 uppercase">
          Chat with Incident Commander
        </h2>
        <span className="text-[8px] font-mono text-slate-400 dark:text-slate-600 uppercase tracking-wider">
          plain english in · 9 agents out
        </span>
      </div>

      <div
        ref={scrollRef}
        className="bg-slate-50/50 dark:bg-slate-950/40 border border-slate-200/40 dark:border-slate-800/60 rounded-lg p-3 h-56 overflow-y-auto mb-3 space-y-3"
      >
        {messages.length === 0 && (
          <p className="text-[11px] text-slate-400 dark:text-slate-600 font-mono">
            Try: “We got a phishing email” · “Are we under attack?” · “What did the team learn?”
          </p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={msg.role === 'user' ? 'text-right' : 'text-left'}>
            <div
              className={`inline-block px-3 py-2 rounded-lg max-w-[85%] text-[11.5px] leading-relaxed whitespace-pre-wrap text-left ${
                msg.role === 'user'
                  ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-950'
                  : 'bg-white dark:bg-slate-900 border border-slate-200/60 dark:border-slate-800 text-slate-700 dark:text-slate-200'
              }`}
            >
              {msg.content}
              {msg.incidentId && (
                <div className="mt-1.5 text-[8.5px] font-mono opacity-60 uppercase tracking-wider">
                  {msg.incidentId}
                </div>
              )}
            </div>
          </div>
        ))}
        {thinking && (
          <div className="text-left">
            <div className="inline-block px-3 py-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200/60 dark:border-slate-800 text-[11px] font-mono text-slate-400 animate-pulse">
              Commander coordinating agents…
            </div>
          </div>
        )}
      </div>

      {devMode && lastRaw && (
        <pre className="text-[9px] font-mono bg-slate-950 text-emerald-400/90 p-2.5 rounded-lg overflow-auto max-h-32 mb-3 border border-slate-800">
          {JSON.stringify(lastRaw, null, 2)}
        </pre>
      )}

      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Ask about threat level, report an incident, query team memory…"
          className="flex-1 bg-white/60 dark:bg-slate-900/60 border border-slate-200/60 dark:border-slate-800 text-slate-800 dark:text-slate-100 px-3 py-2 rounded-lg text-[12px] focus:outline-none focus:ring-1 focus:ring-slate-400 dark:focus:ring-slate-600 placeholder:text-slate-400 dark:placeholder:text-slate-600"
        />
        <button
          onClick={sendMessage}
          disabled={thinking || !input.trim()}
          className={`px-5 py-2 rounded-lg text-xs font-bold font-mono tracking-wider transition-all duration-300 ${
            thinking || !input.trim()
              ? 'bg-slate-100 text-slate-400 dark:bg-slate-900/50 dark:text-slate-600 cursor-not-allowed'
              : 'bg-slate-900 hover:bg-black text-white dark:bg-white dark:hover:bg-slate-100 dark:text-slate-950'
          }`}
        >
          SEND
        </button>
      </div>
    </div>
  )
}

export default CommanderChat
