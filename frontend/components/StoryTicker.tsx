// components/StoryTicker.tsx — plain-English narrative of the live incident.
import React from 'react'
import { StoryBeat } from '../hooks/useAgentWebSocket'

interface StoryTickerProps {
  beats: StoryBeat[]
  isSimulating: boolean
  hasDecision: boolean
}

const toneStyle: Record<StoryBeat['tone'], string> = {
  info: 'border-l-cyan-500 text-slate-600 dark:text-slate-300',
  alert: 'border-l-red-500 text-slate-700 dark:text-slate-200',
  success: 'border-l-emerald-500 text-slate-700 dark:text-slate-200',
}

export function StoryTicker({ beats, isSimulating, hasDecision }: StoryTickerProps) {
  const idle = beats.length === 0 && !isSimulating

  return (
    <div className="glassmorphic border border-slate-200/60 dark:border-slate-800/60 rounded-2xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-base">📖</span>
          <h2 className="text-[12px] font-bold text-slate-800 dark:text-slate-100">What’s happening</h2>
        </div>
        {isSimulating && !hasDecision && (
          <span className="flex items-center gap-1.5 text-[9px] font-mono uppercase tracking-wider text-amber-600 dark:text-amber-400">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" /> Live
          </span>
        )}
        {hasDecision && (
          <span className="text-[9px] font-mono uppercase tracking-wider text-emerald-600 dark:text-emerald-400">✓ Resolved</span>
        )}
      </div>

      {idle && (
        <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-800 p-4">
          <p className="text-[12px] text-slate-600 dark:text-slate-300 leading-relaxed">
            <strong className="text-slate-800 dark:text-white">The scenario:</strong> a hacker emails the CEO a fake
            invoice with malware attached. Click <strong className="text-slate-800 dark:text-white">Simulate Attack</strong> and
            watch nine AI specialists detect it, predict the attacker’s next move, build a defense, and make the
            business call — in under a minute.
          </p>
        </div>
      )}

      {!idle && (
        <ol className="space-y-2">
          {isSimulating && beats.length === 0 && (
            <li className="text-[12px] text-slate-500 dark:text-slate-400 italic pl-3">
              📧 A malicious invoice email just hit the CEO’s inbox — the team is engaging…
            </li>
          )}
          {beats.map((b, i) => (
            <li key={i} className={`pl-3 border-l-2 ${toneStyle[b.tone]} text-[12px] leading-relaxed`}>
              <span className="font-mono text-[9px] text-slate-400 dark:text-slate-600 mr-2">{String(i + 1).padStart(2, '0')}</span>
              {b.line}
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}

export default StoryTicker
