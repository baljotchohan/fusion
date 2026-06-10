// components/ThreatGauge.tsx
import React from 'react'

interface ThreatGaugeProps {
  score: number // 0-100 combined risk score
}

export function ThreatGauge({ score }: ThreatGaugeProps) {
  const clamped = Math.max(0, Math.min(100, score))
  const level = clamped >= 70 ? 'CRITICAL' : clamped >= 40 ? 'ELEVATED' : clamped > 0 ? 'GUARDED' : 'NOMINAL'
  const barColor =
    clamped >= 70 ? 'bg-red-500' : clamped >= 40 ? 'bg-amber-500' : clamped > 0 ? 'bg-emerald-500' : 'bg-slate-400 dark:bg-slate-700'
  const textColor =
    clamped >= 70 ? 'text-red-600 dark:text-red-400' : clamped >= 40 ? 'text-amber-600 dark:text-amber-400' : 'text-slate-500 dark:text-slate-400'

  return (
    <div className="glassmorphic border border-slate-200/60 dark:border-slate-850/50 rounded-xl p-4 shadow-sm space-y-2.5">
      <div className="flex items-center justify-between">
        <h3 className="text-[10px] font-bold font-mono tracking-widest text-slate-400 dark:text-slate-500 uppercase">
          Threat Level
        </h3>
        <span className={`text-[10px] font-mono font-bold tracking-wider ${textColor}`}>
          {level} · {clamped}/100
        </span>
      </div>
      <div className="w-full bg-slate-200/60 dark:bg-slate-800/80 rounded-full h-2.5 overflow-hidden">
        <div
          className={`h-2.5 rounded-full transition-all duration-1000 ease-out ${barColor}`}
          style={{ width: `${Math.max(clamped, 2)}%` }}
        />
      </div>
      <div className="flex justify-between text-[8px] font-mono text-slate-400 dark:text-slate-600 uppercase tracking-wider">
        <span>0 · Nominal</span>
        <span>40 · Elevated</span>
        <span>70 · Critical</span>
        <span>100</span>
      </div>
    </div>
  )
}

export default ThreatGauge
