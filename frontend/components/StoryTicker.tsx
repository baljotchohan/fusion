// components/StoryTicker.tsx — horizontal narrative ticker that streams
// plain-English story beats as the committee deliberates.
'use client'

import React, { useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AGENT_BY_NAME } from '../lib/agents'
import type { StoryBeat } from '../hooks/useAgentWebSocket'

/* ── Props ─────────────────────────────────────────────────── */
interface StoryTickerProps {
  beats: StoryBeat[]
  isSimulating: boolean
  hasDecision: boolean
}

/* ── Tone → accent mapping ─────────────────────────────────── */
const toneAccent: Record<StoryBeat['tone'], { dot: string; text: string }> = {
  info:    { dot: 'bg-accent-cyan',  text: 'text-text-secondary' },
  alert:   { dot: 'bg-danger',       text: 'text-danger' },
  success: { dot: 'bg-accent-green', text: 'text-accent-green' },
}

/* ── Component ─────────────────────────────────────────────── */
export function StoryTicker({ beats, isSimulating, hasDecision }: StoryTickerProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to newest beat
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({ left: scrollRef.current.scrollWidth, behavior: 'smooth' })
    }
  }, [beats.length])

  const idle = beats.length === 0 && !isSimulating && !hasDecision

  return (
    <div className="w-full rounded-xl bg-bg-card border border-border shadow-sm overflow-hidden">
      {/* Header strip */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border">
        <div className="flex items-center gap-2">
          <span className="text-sm">📖</span>
          <span className="text-[11px] font-mono font-bold tracking-wider uppercase text-text-secondary">
            Live Narrative
          </span>
        </div>

        {/* Status indicator */}
        {isSimulating && !hasDecision && (
          <span className="flex items-center gap-1.5 text-[9px] font-mono uppercase tracking-wider text-accent-amber">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full rounded-full bg-accent-amber opacity-75 animate-ping" />
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-accent-amber" />
            </span>
            Live
          </span>
        )}

        {hasDecision && (
          <span className="flex items-center gap-1.5 text-[9px] font-mono uppercase tracking-wider text-accent-green">
            <span className="text-xs">✓</span>
            Deliberation complete
          </span>
        )}
      </div>

      {/* Ticker body */}
      <div
        ref={scrollRef}
        className="flex items-center gap-3 px-4 py-3 overflow-x-auto noscrollbar"
      >
        {/* Empty / idle state */}
        {idle && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-2 whitespace-nowrap"
          >
            <span className="text-sm">🪑</span>
            <span className="text-[11px] text-text-muted italic font-medium">
              Committee standing by…
            </span>
          </motion.div>
        )}

        {/* Simulating but no beats yet — animated dots */}
        {isSimulating && beats.length === 0 && !hasDecision && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-2 whitespace-nowrap"
          >
            <span className="text-sm">📧</span>
            <span className="text-[11px] text-text-secondary font-medium">
              Partners engaging
            </span>
            <span className="flex items-center gap-1 ml-1">
              {[0, 1, 2].map(i => (
                <motion.span
                  key={i}
                  className="w-1 h-1 rounded-full bg-accent-amber"
                  animate={{ opacity: [0.25, 1, 0.25] }}
                  transition={{ duration: 1, repeat: Infinity, delay: i * 0.25 }}
                />
              ))}
            </span>
          </motion.div>
        )}

        {/* Story beats */}
        <AnimatePresence mode="popLayout">
          {beats.map((beat, i) => {
            const agent = AGENT_BY_NAME[beat.agent]
            const tone = toneAccent[beat.tone] || toneAccent.info

            return (
              <motion.div
                key={`${beat.agent}-${i}`}
                layout
                initial={{ opacity: 0, x: 24, scale: 0.92 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: -12 }}
                transition={{ type: 'spring', stiffness: 300, damping: 28 }}
                className="flex-shrink-0 flex items-center gap-2.5 pl-3 pr-4 py-2 rounded-lg bg-bg-subtle border border-border hover:border-border-strong transition-colors duration-200 group"
              >
                {/* Tone dot */}
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${tone.dot}`} />

                {/* Agent icon */}
                <span className="text-base flex-shrink-0" title={agent?.displayName}>
                  {agent?.icon ?? '🤖'}
                </span>

                {/* Narrative text */}
                <span className={`text-[11px] font-medium leading-snug whitespace-nowrap ${tone.text}`}>
                  {beat.line}
                </span>
              </motion.div>
            )
          })}
        </AnimatePresence>

        {/* Decision complete badge */}
        <AnimatePresence>
          {hasDecision && beats.length > 0 && (
            <motion.div
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ delay: 0.2, type: 'spring', stiffness: 300, damping: 24 }}
              className="flex-shrink-0 flex items-center gap-2 px-4 py-2 rounded-lg bg-accent-green-soft border border-accent-green/30"
            >
              <span className="text-accent-green text-xs font-bold">✓</span>
              <span className="text-[11px] font-mono font-bold text-accent-green tracking-wider uppercase whitespace-nowrap">
                Verdict Rendered
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

export default StoryTicker
