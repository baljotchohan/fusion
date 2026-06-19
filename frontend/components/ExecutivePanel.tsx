// components/ExecutivePanel.tsx — The Verdict Memo card.
'use client'

import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Gavel, ShieldCheck, ShieldX, Scale, Download } from 'lucide-react'

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ExecutivePanelProps {
  decision: Record<string, any> | null
  threatScore: number
  isSimulating: boolean
  onDownloadReport?: () => void
  partialConfidence?: number
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Normalise verdict string to a canonical form. */
function normaliseVerdict(raw: string): 'INVEST' | 'PASS' {
  const upper = String(raw).toUpperCase().trim()
  if (upper === 'INVEST' || upper === 'APPROVE' || upper === 'YES') return 'INVEST'
  return 'PASS'
}

/** Format threat / risk score to a 0-10 string. */
function fmtRisk(score: number): string {
  const clamped = Math.max(0, Math.min(10, score))
  return clamped % 1 === 0 ? String(clamped) : clamped.toFixed(1)
}

/** Risk color classes by severity. */
function riskColor(score: number): { text: string; bar: string } {
  if (score >= 7.5) return { text: 'text-red-600 dark:text-red-400', bar: 'bg-red-500' }
  if (score >= 5) return { text: 'text-amber-600 dark:text-amber-400', bar: 'bg-amber-500' }
  return { text: 'text-emerald-600 dark:text-emerald-400', bar: 'bg-emerald-500' }
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-[9px] font-bold uppercase tracking-[0.08em] text-slate-400 dark:text-slate-500">
      {children}
    </span>
  )
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */


export function ExecutivePanel({
  decision,
  threatScore,
  isSimulating,
  onDownloadReport,
  partialConfidence = 0,
}: ExecutivePanelProps) {
  const hasDecision = decision !== null && typeof decision?.verdict === 'string'

  return (
    <div className="glassmorphic border border-slate-200/60 dark:border-slate-800/60 rounded-2xl shadow-sm p-5 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Gavel className="w-4 h-4 text-slate-400 dark:text-slate-500" />
          <h2 className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Verdict Memo
          </h2>
        </div>
        {hasDecision && (
          <span className="text-[9px] font-mono uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
            ✓ Delivered
          </span>
        )}
      </div>

      <AnimatePresence mode="wait">
        {/* ---- State 1: Deliberating ---- */}
        {!hasDecision && isSimulating && (
          <motion.div
            key="deliberating"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
            className="flex flex-col items-center justify-center py-10"
          >
            {/* Animated pulse ring */}
            <div className="relative mb-5">
              <span className="absolute inset-0 rounded-full bg-amber-400/20 animate-ping" />
              <div className="relative w-14 h-14 rounded-full bg-amber-50 dark:bg-amber-500/10 border border-amber-200/60 dark:border-amber-500/20 flex items-center justify-center">
                <Scale className="w-6 h-6 text-amber-500" />
              </div>
            </div>
            <p className="text-[13px] font-semibold text-slate-700 dark:text-slate-200 mb-1">
              Committee deliberating…
            </p>
            <p className="text-[11px] text-slate-400 dark:text-slate-500 text-center max-w-[220px] leading-relaxed">
              Partners are reviewing findings and building the investment recommendation.
            </p>
            {partialConfidence > 0 && (
              <div className="w-full mt-4 px-2">
                <div className="flex justify-between mb-1">
                  <span className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Diligence coverage</span>
                  <span className="text-[10px] font-semibold tabular-nums text-amber-600 dark:text-amber-400">{partialConfidence}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800/60 overflow-hidden">
                  <motion.div
                    animate={{ width: `${partialConfidence}%` }}
                    transition={{ duration: 0.6, ease: 'easeOut' }}
                    className="h-full rounded-full bg-amber-400"
                  />
                </div>
              </div>
            )}
          </motion.div>
        )}

        {/* ---- State 2: Empty / idle ---- */}
        {!hasDecision && !isSimulating && (
          <motion.div
            key="empty"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
            className="flex flex-col items-center justify-center py-10"
          >
            <div className="w-12 h-12 rounded-2xl bg-slate-100 dark:bg-slate-800/50 flex items-center justify-center mb-4">
              <Gavel className="w-5 h-5 text-slate-300 dark:text-slate-600" />
            </div>
            <p className="text-[12px] text-slate-500 dark:text-slate-400 font-medium mb-1">
              No active evaluation
            </p>
            <p className="text-[11px] text-slate-400 dark:text-slate-500 text-center max-w-[200px] leading-relaxed">
              Submit a deal to receive the committee&apos;s verdict memo.
            </p>
          </motion.div>
        )}

        {/* ---- State 3: Decision rendered ---- */}
        {hasDecision && (
          <motion.div
            key="decision"
            initial={{ opacity: 0, scale: 0.95, y: 14 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.45, ease: 'easeOut' }}
            className="space-y-5"
          >
            {(() => {
              const verdict = normaliseVerdict(decision!.verdict)
              const isInvest = verdict === 'INVEST'
              const confidence = typeof decision!.confidence === 'number'
                ? Math.max(0, Math.min(100, decision!.confidence))
                : 0
              const justification = typeof decision!.justification === 'string'
                ? decision!.justification
                : null
              const risk = riskColor(threatScore)

              return (
                <>
                  {/* Verdict badge */}
                  <motion.div
                    initial={{ scale: 0.8 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.15, type: 'spring', stiffness: 260, damping: 18 }}
                    className="flex justify-center"
                  >
                    <div
                      className={`
                        inline-flex items-center gap-2.5 px-6 py-3 rounded-xl border
                        ${isInvest
                          ? 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-300/60 dark:border-emerald-500/25'
                          : 'bg-red-50 dark:bg-red-500/10 border-red-300/60 dark:border-red-500/25'
                        }
                      `}
                    >
                      {isInvest ? (
                        <ShieldCheck className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                      ) : (
                        <ShieldX className="w-5 h-5 text-red-600 dark:text-red-400" />
                      )}
                      <span
                        className={`text-lg font-bold tracking-wide ${
                          isInvest
                            ? 'text-emerald-700 dark:text-emerald-300'
                            : 'text-red-700 dark:text-red-300'
                        }`}
                      >
                        {verdict}
                      </span>
                    </div>
                  </motion.div>

                  {/* Confidence bar */}
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <SectionLabel>Confidence</SectionLabel>
                      <span className="text-[12px] font-semibold tabular-nums text-slate-700 dark:text-slate-200">
                        {confidence}%
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800/60 overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${confidence}%` }}
                        transition={{ delay: 0.25, duration: 0.7, ease: 'easeOut' }}
                        className={`h-full rounded-full ${
                          isInvest ? 'bg-emerald-500' : 'bg-red-500'
                        }`}
                      />
                    </div>
                  </div>

                  {/* Risk score */}
                  <div className="flex items-center justify-between rounded-xl bg-slate-50/60 dark:bg-slate-800/30 border border-slate-200/40 dark:border-slate-700/40 px-4 py-3">
                    <SectionLabel>Risk Score</SectionLabel>
                    <div className="flex items-baseline gap-1">
                      <span className={`text-xl font-bold tabular-nums ${risk.text}`}>
                        {fmtRisk(threatScore)}
                      </span>
                      <span className="text-[10px] text-slate-400 dark:text-slate-500 font-medium">
                        / 10
                      </span>
                    </div>
                  </div>

                  {/* Justification */}
                  {justification && (
                    <div>
                      <SectionLabel>Justification</SectionLabel>
                      <div className="mt-2 rounded-xl bg-slate-50/60 dark:bg-slate-800/30 border border-slate-200/40 dark:border-slate-700/40 p-4">
                        <p className="text-[12px] text-slate-600 dark:text-slate-300 leading-relaxed whitespace-pre-line">
                          {justification}
                        </p>
                      </div>
                    </div>
                  )}

                  {onDownloadReport && (
                    <button
                      onClick={onDownloadReport}
                      className="mt-3 w-full flex items-center justify-center gap-2 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-[12px] font-semibold transition cursor-pointer"
                    >
                      <Download className="w-4 h-4 text-slate-500" />
                      Download Research Report
                    </button>
                  )}
                </>
              )
            })()}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default ExecutivePanel
