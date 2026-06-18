// components/AgentGraph.tsx — Partner Status Board: clean card-based layout
// replacing the old roundtable ellipse with a structured, responsive grid.
'use client'

import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AGENTS, type AgentMeta } from '../lib/agents'
import type { AgentStatus } from '../hooks/useAgentWebSocket'

/* ── Props ─────────────────────────────────────────────────── */
interface AgentGraphProps {
  agentStates: Record<string, AgentStatus>
  theme: 'dark' | 'light'
  heightClass?: string
}

/* ── Status → visual config ────────────────────────────────── */
function statusConfig(status: AgentStatus) {
  switch (status) {
    case 'working':
      return {
        ring: 'border-accent-amber/60',
        glow: 'shadow-[0_0_20px_rgba(217,119,6,0.15)]',
        badge: 'Auditing',
        badgeCls: 'text-accent-amber bg-accent-amber-soft border-accent-amber/30',
        dotCls: 'bg-accent-amber animate-pulse',
        dimmed: false,
      }
    case 'done':
      return {
        ring: 'border-accent-green/60',
        glow: 'shadow-[0_0_20px_rgba(46,158,58,0.12)]',
        badge: 'Complete',
        badgeCls: 'text-accent-green bg-accent-green-soft border-accent-green/30',
        dotCls: 'bg-accent-green',
        dimmed: false,
      }
    case 'alert':
      return {
        ring: 'border-danger/60',
        glow: 'shadow-[0_0_20px_rgba(220,38,38,0.12)]',
        badge: 'Alert',
        badgeCls: 'text-danger bg-danger-soft border-danger/30',
        dotCls: 'bg-danger',
        dimmed: false,
      }
    default:
      return {
        ring: 'border-border',
        glow: '',
        badge: 'Standby',
        badgeCls: 'text-text-muted bg-bg-muted border-border',
        dotCls: 'bg-text-muted/40',
        dimmed: true,
      }
  }
}

/* ── Card animation variants ───────────────────────────────── */
const cardVariants = {
  hidden: { opacity: 0, y: 16, scale: 0.96 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { delay: 0.08 * i, type: 'spring' as const, stiffness: 300, damping: 26 },
  }),
}

const headerVariants = {
  hidden: { opacity: 0, y: -8 },
  visible: { opacity: 1, y: 0, transition: { delay: 0.05, duration: 0.35 } },
}

/* ── Component ─────────────────────────────────────────────── */
export function AgentGraph({ agentStates, theme, heightClass }: AgentGraphProps) {
  const statuses = Object.values(agentStates)
  const isAnyWorking = statuses.includes('working')
  const allDone = statuses.length > 0 && statuses.every(s => s === 'done')
  const hasAlert = statuses.includes('alert')
  const doneCount = statuses.filter(s => s === 'done').length
  const workingCount = statuses.filter(s => s === 'working').length

  // Status summary
  let statusText = 'Partners on standby'
  let statusAccent = 'text-text-muted'
  if (isAnyWorking) {
    statusText = `${workingCount} partner${workingCount > 1 ? 's' : ''} auditing…`
    statusAccent = 'text-accent-amber'
  } else if (allDone) {
    statusText = 'All partners reported — verdict ready'
    statusAccent = 'text-accent-green'
  } else if (hasAlert) {
    statusText = 'Critical findings detected'
    statusAccent = 'text-danger'
  } else if (doneCount > 0) {
    statusText = `${doneCount} of ${AGENTS.length} partners complete`
    statusAccent = 'text-text-secondary'
  }

  // Managing partner (chair) is always first
  const chair = AGENTS[0]
  const specialists = AGENTS.slice(1)
  const chairStatus = agentStates[chair.name] || 'idle'
  const chairCfg = statusConfig(chairStatus)

  return (
    <div className="w-full space-y-4">
      {/* ── Header Row ── */}
      <motion.div
        variants={headerVariants}
        initial="hidden"
        animate="visible"
        className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2"
      >
        <div className="flex items-center gap-2.5">
          {isAnyWorking && (
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full rounded-full bg-accent-amber opacity-60 animate-ping" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-accent-amber" />
            </span>
          )}
          <span className={`text-[12px] font-semibold ${statusAccent} transition-colors duration-300`}>
            {statusText}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          {AGENTS.map((a) => {
            const s = agentStates[a.name] || 'idle'
            const c = statusConfig(s)
            return (
              <div
                key={a.name}
                className={`w-2 h-2 rounded-full transition-colors duration-500 ${c.dotCls}`}
                title={`${a.displayName}: ${c.badge}`}
              />
            )
          })}
        </div>
      </motion.div>

      {/* ── Chair Card (Managing Partner — full width) ── */}
      <motion.div
        custom={0}
        variants={cardVariants}
        initial="hidden"
        animate="visible"
        className={`
          rounded-xl border-[1.5px] bg-bg-card p-4
          transition-all duration-500
          ${chairCfg.ring} ${chairCfg.glow}
          ${chairCfg.dimmed ? 'opacity-60' : ''}
        `}
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-xl bg-gradient-to-br from-accent to-accent-hover text-white flex items-center justify-center text-lg sm:text-xl shrink-0">
            {chair.icon}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-[13px] sm:text-[14px] font-bold text-text-primary truncate">{chair.displayName}</h4>
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[9px] sm:text-[10px] font-bold uppercase tracking-wider ${chairCfg.badgeCls}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${chairCfg.dotCls}`} />
                {chairCfg.badge}
              </span>
            </div>
            <p className="text-[11px] sm:text-[12px] text-text-secondary mt-0.5 line-clamp-1">{chair.role}</p>
          </div>
        </div>

        {/* Connecting line hint */}
        {(isAnyWorking || allDone) && (
          <div className="mt-3 pt-3 border-t border-border/60 flex items-center gap-2">
            <div className="flex -space-x-1.5">
              {specialists.map(a => (
                <div key={a.name} className="w-5 h-5 sm:w-6 sm:h-6 rounded-md bg-bg-muted border border-border flex items-center justify-center text-[10px] sm:text-[11px]">
                  {a.icon}
                </div>
              ))}
            </div>
            <span className="text-[10px] sm:text-[11px] text-text-muted">
              {allDone ? 'All reports received' : 'Dispatched to specialist partners'}
            </span>
          </div>
        )}
      </motion.div>

      {/* ── Specialist Cards (2×2 grid, responsive) ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {specialists.map((agent, index) => {
          const status: AgentStatus = agentStates[agent.name] || 'idle'
          const cfg = statusConfig(status)

          return (
            <motion.div
              key={agent.name}
              custom={index + 1}
              variants={cardVariants}
              initial="hidden"
              animate="visible"
              className={`
                group relative rounded-xl border-[1.5px] bg-bg-card p-3.5 sm:p-4
                transition-all duration-500 cursor-default
                hover:border-accent/30 hover:shadow-sm
                ${cfg.ring} ${cfg.glow}
                ${cfg.dimmed ? 'opacity-50 hover:opacity-80' : ''}
              `}
            >
              <div className="flex items-start gap-3">
                {/* Agent icon */}
                <div className={`
                  w-9 h-9 sm:w-10 sm:h-10 rounded-xl border flex items-center justify-center text-base sm:text-lg shrink-0
                  bg-bg-subtle transition-colors duration-300
                  ${cfg.dimmed ? 'border-border' : 'border-border-strong'}
                `}>
                  {agent.icon}
                </div>

                <div className="flex-1 min-w-0">
                  {/* Name + status badge */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className="text-[12px] sm:text-[13px] font-bold text-text-primary truncate">{agent.displayName}</h4>
                    <span className={`inline-flex items-center gap-1 px-1.5 py-px rounded-full border text-[8px] sm:text-[9px] font-bold uppercase tracking-wider shrink-0 ${cfg.badgeCls}`}>
                      <span className={`w-1 h-1 sm:w-1.5 sm:h-1.5 rounded-full ${cfg.dotCls}`} />
                      {cfg.badge}
                    </span>
                  </div>

                  {/* Role */}
                  <p className="text-[10px] sm:text-[11px] text-text-muted mt-0.5 line-clamp-1">{agent.role}</p>

                  {/* Working animation */}
                  <AnimatePresence>
                    {status === 'working' && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-2"
                      >
                        <div className="h-1 rounded-full bg-bg-muted overflow-hidden">
                          <motion.div
                            className="h-full rounded-full bg-accent-amber/60"
                            animate={{ x: ['-100%', '100%'] }}
                            transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
                            style={{ width: '40%' }}
                          />
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Done — show checklist peek */}
                  <AnimatePresence>
                    {status === 'done' && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-2 flex items-center gap-1.5"
                      >
                        <span className="text-accent-green text-[11px]">✓</span>
                        <span className="text-[10px] text-text-secondary">Report submitted</span>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>

              {/* Hover tooltip */}
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 bg-bg-card border border-border rounded-xl shadow-lg p-3 text-[10px] w-52 opacity-0 group-hover:opacity-100 transition-all duration-200 pointer-events-none z-50 translate-y-1 group-hover:translate-y-0 hidden sm:block">
                <div className="font-bold text-[11px] text-text-primary">{agent.displayName}</div>
                <div className="text-[9px] font-mono text-accent font-bold mt-0.5">{agent.role}</div>
                <p className="mt-1.5 text-text-secondary leading-relaxed">{agent.plain}</p>
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}

export default AgentGraph
