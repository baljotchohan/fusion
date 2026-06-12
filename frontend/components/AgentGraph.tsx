// components/AgentGraph.tsx — Deliberation Roundtable: 5 partners seated
// around a glowing oval table with a live Verdict Ledger at center.
'use client'

import React, { useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AGENTS, type AgentMeta } from '../lib/agents'
import type { AgentStatus } from '../hooks/useAgentWebSocket'

/* ── Props ─────────────────────────────────────────────────── */
interface AgentGraphProps {
  agentStates: Record<string, AgentStatus>
  theme: 'dark' | 'light'
  heightClass?: string
}

/* ── Seat layout: angles around an ellipse (degrees, 0 = top) ───── */
const SEAT_ANGLES: number[] = [270, 330, 30, 150, 210] // top, top-right, bottom-right, bottom-left, top-left

/* ── Per-agent accent gradient ─────────────────────────────── */
const SEAT_GRADIENTS: Record<string, string> = {
  managing_partner:  'from-amber-500 to-orange-600',
  financial_partner: 'from-cyan-500 to-blue-600',
  legal_partner:     'from-indigo-500 to-violet-600',
  technical_partner: 'from-emerald-500 to-teal-600',
  market_partner:    'from-pink-500 to-rose-600',
}

/* ── Status → visual config ────────────────────────────────── */
function statusConfig(status: AgentStatus) {
  switch (status) {
    case 'working':
      return {
        ring: 'border-accent-amber shadow-[0_0_22px_var(--accent-amber)]',
        badge: '🔄',
        label: 'Auditing',
        badgeCls: 'text-accent-amber bg-accent-amber-soft border-accent-amber/30 animate-pulse',
        dimmed: false,
      }
    case 'done':
      return {
        ring: 'border-accent-green shadow-[0_0_18px_var(--accent-green)]',
        badge: '✓',
        label: 'Done',
        badgeCls: 'text-accent-green bg-accent-green-soft border-accent-green/30 font-bold',
        dimmed: false,
      }
    case 'alert':
      return {
        ring: 'border-danger shadow-[0_0_22px_var(--danger)]',
        badge: '🚨',
        label: 'Alert',
        badgeCls: 'text-danger bg-danger-soft border-danger/30',
        dimmed: false,
      }
    default:
      return {
        ring: 'border-border',
        badge: '💤',
        label: 'Standby',
        badgeCls: 'text-text-muted bg-bg-muted border-border',
        dimmed: true,
      }
  }
}

/* ── Seat animation variants ───────────────────────────────── */
const seatVariants = {
  hidden: { opacity: 0, scale: 0.6, y: 18 },
  visible: (i: number) => ({
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { delay: 0.12 * i, type: 'spring' as const, stiffness: 260, damping: 22 },
  }),
}

const ledgerVariants = {
  hidden: { opacity: 0, scale: 0.85 },
  visible: { opacity: 1, scale: 1, transition: { delay: 0.55, duration: 0.5, ease: 'easeOut' as const } },
}

/* ── Component ─────────────────────────────────────────────── */
export function AgentGraph({ agentStates, theme, heightClass = 'h-[420px]' }: AgentGraphProps) {
  // Build deterministic seat array from AGENTS
  const seats = useMemo(
    () =>
      AGENTS.map((a, i) => ({
        agent: a,
        angle: SEAT_ANGLES[i] ?? 0,
        gradient: SEAT_GRADIENTS[a.name] ?? 'from-slate-500 to-slate-600',
      })),
    [],
  )

  // Global state aggregation
  const statuses = Object.values(agentStates)
  const isAnyWorking = statuses.includes('working')
  const allDone = statuses.length > 0 && statuses.every(s => s === 'done')
  const hasAlert = statuses.includes('alert')

  // Table glow + ledger text
  let tableGlow = 'border-border shadow-sm'
  let ledgerTitle = 'Awaiting Documents…'
  let ledgerSub = 'Ready for deal pitch'
  let ledgerAccent = 'text-text-muted'

  if (isAnyWorking) {
    tableGlow = 'border-accent-amber/60 shadow-[0_0_40px_var(--accent-amber),0_0_80px_rgba(217,119,6,0.12)]'
    ledgerTitle = 'Diligence In Progress'
    ledgerSub = 'Partners are auditing the brief'
    ledgerAccent = 'text-accent-amber'
  } else if (allDone) {
    tableGlow = 'border-accent-green/60 shadow-[0_0_40px_var(--accent-green),0_0_80px_rgba(22,163,74,0.12)]'
    ledgerTitle = 'VERDICT REACHED'
    ledgerSub = 'Committee deliberation complete'
    ledgerAccent = 'text-accent-green'
  } else if (hasAlert) {
    tableGlow = 'border-danger/60 shadow-[0_0_35px_var(--danger)]'
    ledgerTitle = 'RISK ESCALATED'
    ledgerSub = 'Critical findings require attention'
    ledgerAccent = 'text-danger'
  }

  /* Ellipse radii — seats orbit on this path */
  const RX = 44 // % of container width
  const RY = 40 // % of container height

  return (
    <div className={`relative w-full ${heightClass} flex items-center justify-center select-none`}>
      {/* Subtle radial backdrop */}
      <div className="absolute inset-0 pointer-events-none -z-20 rounded-full opacity-30 bg-[radial-gradient(ellipse_at_center,var(--bg-muted)_0%,transparent_70%)]" />

      {/* aspect-ratio locked roundtable wrapper */}
      <div className="relative w-[54%] aspect-[1.65/1] flex items-center justify-center">
        {/* ── The Roundtable ── */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className={`
            absolute inset-0 rounded-full
            border-[3px] bg-bg-card/50 backdrop-blur-xl
            flex flex-col items-center justify-center
            transition-all duration-700 z-10
            ${tableGlow}
          `}
        >
          {/* Inner table surface */}
          <div className="absolute inset-3 rounded-full bg-gradient-to-b from-bg-subtle/40 to-transparent pointer-events-none -z-10" />

          {/* ── Verdict Ledger (center) ── */}
          <motion.div
            variants={ledgerVariants}
            initial="hidden"
            animate="visible"
            className="text-center px-6"
          >
            <span className="text-[9px] font-mono tracking-[0.2em] font-extrabold text-text-muted uppercase">
              Verdict Ledger
            </span>

            <h4 className={`text-[14px] font-black tracking-wider mt-1.5 font-mono transition-colors duration-500 ${ledgerAccent}`}>
              {ledgerTitle}
            </h4>

            <p className="text-[10px] text-text-secondary mt-1 italic font-medium leading-none">
              {ledgerSub}
            </p>

            {/* Animated dots when working */}
            {isAnyWorking && (
              <div className="flex items-center justify-center gap-1.5 mt-2.5">
                {[0, 1, 2].map(i => (
                  <motion.span
                    key={i}
                    className="w-1.5 h-1.5 rounded-full bg-accent-amber"
                    animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1.2, 0.8] }}
                    transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
                  />
                ))}
              </div>
            )}

            {/* Verdict badge when all done */}
            <AnimatePresence>
              {allDone && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="mt-2.5 inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-accent-green-soft border border-accent-green/30"
                >
                  <span className="text-accent-green text-xs">✓</span>
                  <span className="text-[10px] font-mono font-bold text-accent-green tracking-wider uppercase">Complete</span>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </motion.div>

        {/* ── Partner Seats ── */}
        {seats.map(({ agent, angle, gradient }, index) => {
          const status: AgentStatus = agentStates[agent.name] || 'idle'
          const cfg = statusConfig(status)

          // Convert angle → x/y % offsets from center
          const rad = (angle * Math.PI) / 180
          const cx = 50 + 50 * Math.cos(rad)
          const cy = 50 + 50 * Math.sin(rad)

          return (
            <motion.div
              key={agent.name}
              custom={index}
              variants={seatVariants}
              initial="hidden"
              animate="visible"
              className="absolute z-30 flex flex-col items-center group"
              style={{ left: `${cx}%`, top: `${cy}%`, transform: 'translate(-50%, -50%)' }}
            >
              {/* Seat card */}
              <div className="relative">
                {/* Outer pulse ring when working */}
                {status === 'working' && (
                  <span className="absolute inset-0 rounded-2xl animate-ping pointer-events-none"
                    style={{ boxShadow: '0 0 0 0 var(--accent-amber)', background: 'var(--accent-amber)', opacity: 0.18 }}
                  />
                )}

                <div
                  className={`
                    w-14 h-14 rounded-2xl border-2 flex items-center justify-center
                    text-2xl bg-gradient-to-br ${gradient} text-white
                    shadow-md relative z-10 transition-all duration-500
                    ${cfg.ring}
                    ${cfg.dimmed ? 'opacity-50 grayscale-[40%]' : ''}
                  `}
                >
                  {agent.icon}
                </div>

                {/* Status badge pill */}
                <div
                  className={`
                    absolute -bottom-2.5 left-1/2 -translate-x-1/2
                    px-2 py-0.5 rounded-full border text-[8px] font-mono
                    font-bold uppercase tracking-wider flex items-center gap-1
                    shadow-sm z-20 whitespace-nowrap
                    ${cfg.badgeCls}
                  `}
                >
                  <span>{cfg.badge}</span>
                  <span>{cfg.label}</span>
                </div>
              </div>

              {/* Name label */}
              <div className="mt-4 text-center pointer-events-none">
                <div className={`text-[10px] font-mono font-bold transition-colors duration-300 ${cfg.dimmed ? 'text-text-muted' : 'text-text-primary'}`}>
                  {agent.displayName}
                </div>
                <div className="text-[8px] text-text-muted font-mono tracking-wider mt-0.5">
                  {agent.role.length > 22 ? agent.role.slice(0, 20) + '…' : agent.role}
                </div>
              </div>

              {/* Hover tooltip */}
              <div className="absolute top-[72px] bg-bg-card border border-border rounded-xl shadow-lg p-3 text-[10px] w-52 opacity-0 group-hover:opacity-100 transition-all duration-300 pointer-events-none z-50 translate-y-2 group-hover:translate-y-0">
                <div className="font-extrabold text-[11px] text-text-primary">{agent.displayName}</div>
                <div className="text-[8px] font-mono text-accent font-bold mt-0.5">{agent.role}</div>
                <p className="mt-1.5 text-text-secondary leading-relaxed">{agent.plain}</p>
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* ── CSS keyframe for amber seat glow (injected inline) ── */}
      <style>{`
        @keyframes seat-amber-pulse {
          0%, 100% { box-shadow: 0 0 12px var(--accent-amber); }
          50%      { box-shadow: 0 0 28px var(--accent-amber); }
        }
      `}</style>
    </div>
  )
}

export default AgentGraph
