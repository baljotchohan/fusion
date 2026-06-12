// components/ThreatGauge.tsx — Committee Risk Score display card.
'use client'

import React from 'react'
import { ShieldAlert, ShieldCheck, Shield } from 'lucide-react'

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */

interface ThreatGaugeProps {
  score: number // 0–10 combined risk score
}

/* ------------------------------------------------------------------ */
/*  Risk tiers                                                         */
/* ------------------------------------------------------------------ */

function getRiskTier(score: number) {
  if (score <= 0) {
    return {
      label: 'No Assessment',
      bar: 'bg-bg-muted',
      text: 'text-text-muted',
      scoreFg: 'text-text-muted',
      icon: Shield,
      iconColor: 'text-text-muted',
      bgGlow: '',
    }
  }
  if (score <= 3) {
    return {
      label: 'Low Risk',
      bar: 'bg-success',
      text: 'text-success',
      scoreFg: 'text-success',
      icon: ShieldCheck,
      iconColor: 'text-success',
      bgGlow: '',
    }
  }
  if (score <= 6) {
    return {
      label: 'Moderate Risk',
      bar: 'bg-warning',
      text: 'text-warning',
      scoreFg: 'text-warning',
      icon: ShieldAlert,
      iconColor: 'text-warning',
      bgGlow: '',
    }
  }
  if (score <= 8) {
    return {
      label: 'High Risk',
      bar: 'bg-danger',
      text: 'text-danger',
      scoreFg: 'text-danger',
      icon: ShieldAlert,
      iconColor: 'text-danger',
      bgGlow: 'shadow-[0_0_20px_rgba(239,68,68,0.08)]',
    }
  }
  return {
    label: 'Critical Risk',
    bar: 'bg-danger',
    text: 'text-danger',
    scoreFg: 'text-danger',
    icon: ShieldAlert,
    iconColor: 'text-danger',
    bgGlow: 'shadow-[0_0_24px_rgba(239,68,68,0.12)]',
  }
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function ThreatGauge({ score }: ThreatGaugeProps) {
  const clamped = Math.max(0, Math.min(10, score))
  const tier = getRiskTier(clamped)
  const percentage = (clamped / 10) * 100
  const Icon = tier.icon

  return (
    <div className={`rounded-xl bg-bg-card border border-border shadow-sm p-5 space-y-4 ${tier.bgGlow}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className={`w-4 h-4 ${tier.iconColor}`} strokeWidth={2} />
          <h3 className="text-[10px] font-bold font-mono tracking-widest text-text-muted uppercase">
            Committee Risk Score
          </h3>
        </div>
      </div>

      {/* Large score display */}
      <div className="flex items-baseline gap-1.5">
        {clamped > 0 ? (
          <>
            <span className={`text-4xl font-bold font-mono tabular-nums tracking-tighter ${tier.scoreFg}`}>
              {clamped % 1 === 0 ? clamped.toFixed(0) : clamped.toFixed(1)}
            </span>
            <span className="text-sm font-mono text-text-muted">/10</span>
          </>
        ) : (
          <span className="text-lg font-medium text-text-muted">—</span>
        )}
      </div>

      {/* Progress bar */}
      <div className="space-y-2">
        <div className="w-full bg-bg-muted rounded-full h-2.5 overflow-hidden">
          <div
            className={`h-2.5 rounded-full transition-all duration-1000 ease-out ${tier.bar}`}
            style={{ width: clamped > 0 ? `${Math.max(percentage, 3)}%` : '0%' }}
          />
        </div>

        {/* Scale markers */}
        <div className="flex justify-between text-[8px] font-mono text-text-muted uppercase tracking-wider">
          <span>0</span>
          <span>3</span>
          <span>6</span>
          <span>10</span>
        </div>
      </div>

      {/* Risk level label */}
      <div className="flex items-center gap-2 pt-1 border-t border-border">
        {clamped > 0 ? (
          <>
            <span className={`w-2 h-2 rounded-full ${tier.bar}`} />
            <span className={`text-[11px] font-semibold tracking-wide ${tier.text}`}>
              {tier.label}
            </span>
          </>
        ) : (
          <span className="text-[11px] text-text-muted italic">
            No assessment available yet
          </span>
        )}
      </div>
    </div>
  )
}

export default ThreatGauge
