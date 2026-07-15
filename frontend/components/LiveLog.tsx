// components/LiveLog.tsx — Meeting Minutes / Deliberation Transcript feed.
'use client'

import React, { useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ScrollText } from 'lucide-react'
import { AGENT_BY_NAME } from '../lib/agents'
import type { AgentUpdate, EventStatus } from '../hooks/useAgentWebSocket'

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface LiveLogProps {
  events: AgentUpdate[]
}

/* ------------------------------------------------------------------ */
/*  Status badge config                                                */
/* ------------------------------------------------------------------ */

const BADGE_CONFIG: Record<
  EventStatus,
  { label: string; dot: string; text: string; bg: string }
> = {
  working: {
    label: 'Auditing…',
    dot: 'bg-warning animate-pulse',
    text: 'text-warning',
    bg: 'bg-warning-soft border-warning/20',
  },
  done: {
    label: 'Findings Logged',
    dot: 'bg-success',
    text: 'text-success',
    bg: 'bg-success-soft border-success/20',
  },
  idle: {
    label: 'Stand-by',
    dot: 'bg-text-muted',
    text: 'text-text-secondary',
    bg: 'bg-bg-muted border-border',
  },
  alert: {
    label: 'Attention',
    dot: 'bg-danger animate-pulse',
    text: 'text-danger',
    bg: 'bg-danger-soft border-danger/20',
  },
  debate: {
    label: '⚔️ Debate',
    dot: 'bg-violet-500 animate-pulse',
    text: 'text-violet-600 dark:text-violet-400',
    bg: 'bg-violet-50 dark:bg-violet-500/10 border-violet-200/60 dark:border-violet-500/20',
  },
  memory_match: {
    label: '⚡ Memory',
    dot: 'bg-blue-500',
    text: 'text-blue-600 dark:text-blue-400',
    bg: 'bg-blue-50 dark:bg-blue-500/10 border-blue-200/60 dark:border-blue-500/20',
  },
  confidence_update: {
    label: 'Progress',
    dot: 'bg-amber-500',
    text: 'text-amber-600 dark:text-amber-400',
    bg: 'bg-amber-50 dark:bg-amber-500/10 border-amber-200/60 dark:border-amber-500/20',
  },
  thinking: {
    label: '🧠 Live Reasoning',
    dot: 'bg-success animate-pulse',
    text: 'text-success',
    bg: 'bg-success-soft border-success/20',
  },
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Pretty timestamp — e.g. "12:04 PM" */
function fmtTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
}

/** Pull a human-readable summary from the agent output, if available. */
function summarise(output: Record<string, any>): string | null {
  if (!output || Object.keys(output).length === 0) return null

  // Prefer an explicit summary field
  if (typeof output.summary === 'string' && output.summary.length > 0)
    return output.summary

  // Fallback: first ~140 chars of a report string, cleaned up
  if (typeof output.report === 'string' && output.report.length > 0)
    return output.report
      .replace(/[-—#*`]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 140) + '…'

  // Fallback: current_action from working state
  if (typeof output.current_action === 'string')
    return output.current_action

  // Fallback: real model reasoning (see AgentDetailPanel's Live Reasoning panel)
  if (typeof output.reasoning === 'string' && output.reasoning.length > 0)
    return output.reasoning

  return null
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function LiveLog({ events }: LiveLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom whenever a new event arrives
  useEffect(() => {
    const el = scrollRef.current
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
    }
  }, [events.length])

  const isEmpty = events.length === 0

  return (
    <div className="glassmorphic border border-border rounded-2xl shadow-sm flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-5 pt-5 pb-3">
        <div className="flex items-center gap-2">
          <ScrollText className="w-4 h-4 text-text-muted" />
          <h2 className="text-[11px] font-bold uppercase tracking-wider text-text-secondary">
            Meeting Minutes
          </h2>
        </div>
        {!isEmpty && (
          <span className="text-[9px] font-mono text-text-muted tabular-nums">
            {events.length} entr{events.length === 1 ? 'y' : 'ies'}
          </span>
        )}
      </div>

      {/* Scrollable feed */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-5 pb-5 scroll-smooth"
      >
        {isEmpty ? (
          /* ---- Empty state ---- */
          <div className="flex flex-col items-center justify-center h-full py-12">
            <div className="w-12 h-12 rounded-2xl bg-bg-muted flex items-center justify-center mb-4">
              <ScrollText className="w-5 h-5 text-text-muted" />
            </div>
            <p className="text-[12px] text-text-secondary font-medium mb-1">
              No minutes recorded yet
            </p>
            <p className="text-[11px] text-text-muted text-center max-w-[200px] leading-relaxed">
              Submit a deal to begin the committee deliberation.
            </p>
          </div>
        ) : (
          /* ---- Timeline ---- */
          <div className="space-y-3">
            <AnimatePresence initial={false}>
              {events.map((evt, idx) => {
                const agent = AGENT_BY_NAME[evt.agent]
                const badge = BADGE_CONFIG[evt.status] || BADGE_CONFIG.idle
                const summary = summarise(evt.output)

                return (
                  <motion.div
                    key={`${evt.agent}-${evt.timestamp}-${idx}`}
                    initial={{ opacity: 0, y: 16, scale: 0.97 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.3, ease: 'easeOut' }}
                    className="flex items-start gap-3"
                  >
                    {/* Avatar circle */}
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-bg-muted border border-border flex items-center justify-center text-sm select-none">
                      {agent?.icon ?? '🤖'}
                    </div>

                    {/* Bubble */}
                    <div className="flex-1 min-w-0 rounded-xl bg-bg-card border border-border p-3.5 shadow-sm">
                      {/* Top row: name + time + badge */}
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="text-[12px] font-semibold text-text-primary truncate">
                            {agent?.displayName ?? evt.agent}
                          </span>
                          <span className="text-[9px] font-mono text-text-muted tabular-nums flex-shrink-0">
                            {fmtTime(evt.timestamp)}
                          </span>
                        </div>

                        {/* Status badge */}
                        <div
                          className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[8px] font-bold uppercase tracking-wider flex-shrink-0 ${badge.bg} ${badge.text}`}
                        >
                          <span
                            className={`inline-block w-1.5 h-1.5 rounded-full ${badge.dot}`}
                          />
                          {badge.label}
                        </div>
                      </div>

                      {/* Summary text */}
                      {summary && (
                        <p className="text-[11px] text-text-secondary leading-relaxed line-clamp-2 overflow-hidden text-ellipsis">
                          {summary}
                        </p>
                      )}
                    </div>
                  </motion.div>
                )
              })}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  )
}

export default LiveLog
