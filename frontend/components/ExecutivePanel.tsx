// components/ExecutivePanel.tsx
import React from 'react'

interface ExecutivePanelProps {
  decision: Record<string, any> | null
  threatScore: number
}

export function ExecutivePanel({ decision, threatScore }: ExecutivePanelProps) {
  // If no threat score and no decision, or threat score is below threshold and no decision, display standby.
  if (!decision && threatScore < 70) {
    return (
      <div className="glassmorphic border border-slate-200/60 dark:border-slate-850/50 rounded-2xl p-6 text-center shadow-sm flex flex-col items-center justify-center h-[200px] transition-all duration-300">
        <div className="w-8 h-8 rounded-full bg-slate-100/50 dark:bg-slate-900/50 border border-slate-200/40 dark:border-slate-800/80 flex items-center justify-center mb-3">
          <span className="text-slate-400 dark:text-slate-600 font-mono text-xs">○</span>
        </div>
        <h3 className="font-semibold text-xs tracking-wider text-slate-400 dark:text-slate-500 uppercase font-mono">Executive Boardroom Standby</h3>
        <p className="text-[10.5px] text-slate-500 dark:text-slate-400 max-w-sm mt-1 leading-relaxed">
          The Executive Boardroom escalates automatically when threat metrics reach critical thresholds (Risk Score ≥ 70/100).
        </p>
      </div>
    )
  }

  // Board has been convened, but agents are still deliberating (calculating responses)
  if (!decision && threatScore >= 70) {
    return (
      <div className="border border-amber-300/80 bg-amber-500/5 dark:border-amber-500/20 dark:bg-amber-500/5 rounded-2xl p-5 shadow-sm space-y-4 transition-all duration-300">
        <div className="flex items-center justify-between pb-3 border-b border-slate-200/50 dark:border-slate-800/80">
          <div>
            <h3 className="font-bold text-xs font-mono text-amber-600 dark:text-amber-400 tracking-wider">👔 EXECUTIVE BOARDROOM CONVENED</h3>
            <p className="text-[9.5px] text-slate-400 dark:text-slate-500 font-mono">Incident ID: ARGUS-INC-2026-001 • ESCALATED RISK: {threatScore}/100</p>
          </div>
          <div className="flex items-center gap-2 bg-amber-100/50 dark:bg-amber-950/40 border border-amber-200/40 dark:border-amber-900/50 px-2.5 py-0.5 rounded-full">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-amber-500"></span>
            </span>
            <span className="text-[8.5px] font-mono font-bold tracking-widest text-amber-600 dark:text-amber-400 uppercase">DELIBERATING...</span>
          </div>
        </div>
        
        {/* Dynamic Deliberation Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[
            { seat: 'CFO (Financial)', role: 'Evaluating cost/ROI trade-offs...' },
            { seat: 'Legal (Regulations)', role: 'Assessing compliance liabilities...' },
            { seat: 'Operations (Continuity)', role: 'Modeling system downtime impact...' },
            { seat: 'CEO (Verdict)', role: 'Awaiting board members report...' }
          ].map((seat, i) => (
            <div key={i} className="glassmorphic border border-slate-200/50 dark:border-slate-850/50 rounded-xl p-4 flex flex-col justify-between h-[135px]">
              <div className="flex items-center justify-between">
                <span className="text-[9.5px] font-bold text-slate-400 dark:text-slate-500 font-mono uppercase tracking-wider">{seat.seat}</span>
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
              </div>
              <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-normal italic font-sans py-2">
                "{seat.role}"
              </p>
              <div className="flex items-center gap-1.5 text-[8.5px] font-mono text-amber-500 uppercase tracking-widest font-bold bg-amber-50 dark:bg-amber-950/20 px-2 py-0.5 rounded-md border border-amber-100/30 dark:border-amber-900/20 w-fit">
                <span className="w-1 h-1 rounded-full bg-amber-500 animate-ping"></span>
                Processing
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  // Decision has been made! Render high-fidelity dashboard verdict.
  const cfoData = decision?.executive_decision?.cfo || decision?.cfo || {
    breach_cost_estimate: "$2,400,000 (liability + churn)",
    containment_cost: "$180,000 (remediation + patching)",
    recommendation: "Immediate containment is 13.3x cheaper than a breach."
  }

  const legalData = decision?.executive_decision?.legal || decision?.legal || {
    regulations_triggered: ["GDPR Article 33", "India DPDP Act"],
    liability_exposure: "Up to €20M or 4% of annual global turnover",
    notification_deadline: "DPA notification required within 72 hours"
  }

  const opsData = decision?.executive_decision?.operations || decision?.operations || {
    systems_offline: ["Corporate Webmail Portal (4h)", "Internal RDP (2h)"],
    recovery_estimate: "6-8 hours to full baseline operations"
  }

  const ceoData = decision?.executive_decision?.ceo || decision?.ceo || {
    decision: decision?.verdict || "CONTAIN",
    justification: decision?.justification || "Containment cost is substantially lower than projected breach exposure. Regulatory clock is running.",
    board_communication: "Security incident contained. System hardening in progress. No data exfiltration detected."
  }

  const verdict = ceoData.decision || "CONTAIN"
  const isShutdown = verdict.toUpperCase() === 'SHUTDOWN'

  return (
    <div className={`border rounded-2xl p-5 shadow-sm space-y-5 transition-all duration-500 ${
      isShutdown 
        ? 'border-red-500/30 bg-red-500/5 dark:border-red-500/20' 
        : 'border-emerald-500/30 bg-emerald-500/5 dark:border-emerald-500/20'
    }`}>
      {/* Title & Verdict Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3.5 border-b border-slate-200/50 dark:border-slate-800/80">
        <div>
          <h3 className="font-bold text-xs font-mono text-slate-800 dark:text-slate-200 tracking-wider">👔 EXECUTIVE BOARDROOM REPORT</h3>
          <p className="text-[9.5px] text-slate-400 dark:text-slate-500 font-mono">Incident ID: ARGUS-INC-2026-001 • TOTAL RISK SCORE: {threatScore}/100</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">VERDICT:</span>
          <span className={`font-black text-xs px-3.5 py-1.5 rounded-lg border tracking-widest ${
            isShutdown 
              ? 'bg-red-500 text-white border-red-600 dark:bg-red-950/80 dark:text-red-400 dark:border-red-500/50 shadow-[0_0_15px_rgba(239,68,68,0.25)]' 
              : 'bg-emerald-500 text-white border-emerald-600 dark:bg-emerald-950/80 dark:text-emerald-400 dark:border-emerald-500/50 shadow-[0_0_15px_rgba(16,185,129,0.25)]'
          }`}>
            🚨 {verdict.toUpperCase()} DECISION
          </span>
        </div>
      </div>

      {/* 3 Advisor Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* CFO CARD */}
        <div className="glassmorphic border border-slate-200/60 dark:border-slate-850/50 rounded-xl p-4 flex flex-col justify-between h-[155px]">
          <div>
            <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 font-mono uppercase tracking-wider">CFO Financial Audit</span>
            <div className="mt-2 space-y-1 text-[10.5px] text-slate-500 dark:text-slate-400 font-sans leading-relaxed">
              <p><span className="text-slate-400 dark:text-slate-500 font-mono">Breach Cost:</span> {cfoData.breach_cost_estimate}</p>
              <p><span className="text-slate-400 dark:text-slate-500 font-mono">Contain Cost:</span> {cfoData.containment_cost}</p>
            </div>
          </div>
          <p className="text-[9.5px] text-emerald-600 dark:text-emerald-400 font-mono font-bold border-t border-slate-250/20 dark:border-slate-800/40 pt-2 leading-relaxed">
            💡 {cfoData.recommendation}
          </p>
        </div>

        {/* LEGAL CARD */}
        <div className="glassmorphic border border-slate-200/60 dark:border-slate-850/50 rounded-xl p-4 flex flex-col justify-between h-[155px]">
          <div>
            <span className="text-[10px] font-bold text-blue-600 dark:text-blue-400 font-mono uppercase tracking-wider">Legal Compliance</span>
            <div className="mt-2 space-y-1 text-[10.5px] text-slate-500 dark:text-slate-400 font-sans leading-relaxed">
              <p><span className="text-slate-400 dark:text-slate-500 font-mono">Triggered:</span> {Array.isArray(legalData.regulations_triggered) ? legalData.regulations_triggered.join(', ') : legalData.regulations_triggered}</p>
              <p><span className="text-slate-400 dark:text-slate-500 font-mono">Exposure:</span> {legalData.liability_exposure}</p>
            </div>
          </div>
          <p className="text-[9.5px] text-blue-600 dark:text-blue-400 font-mono font-bold border-t border-slate-250/20 dark:border-slate-800/40 pt-2 leading-relaxed">
            ⏰ {legalData.notification_deadline}
          </p>
        </div>

        {/* OPS CARD */}
        <div className="glassmorphic border border-slate-200/60 dark:border-slate-850/50 rounded-xl p-4 flex flex-col justify-between h-[155px]">
          <div>
            <span className="text-[10px] font-bold text-amber-600 dark:text-amber-400 font-mono uppercase tracking-wider">Ops & Continuity</span>
            <div className="mt-2 space-y-1 text-[10.5px] text-slate-500 dark:text-slate-400 font-sans leading-relaxed">
              <p><span className="text-slate-400 dark:text-slate-500 font-mono">Offlined:</span> {Array.isArray(opsData.systems_offline) ? opsData.systems_offline.join(', ') : opsData.systems_offline}</p>
            </div>
          </div>
          <p className="text-[9.5px] text-amber-600 dark:text-amber-400 font-mono font-bold border-t border-slate-250/20 dark:border-slate-800/40 pt-2 leading-relaxed">
            📅 {opsData.recovery_estimate}
          </p>
        </div>
      </div>

      {/* CEO Verdict Details Card */}
      <div className="glassmorphic border border-slate-200/60 dark:border-slate-850/50 rounded-xl p-4 space-y-2">
        <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 font-mono uppercase tracking-wider">CEO JUSTIFICATION & DIRECTION</span>
        <p className="text-xs text-slate-700 dark:text-slate-350 leading-relaxed font-sans italic font-medium">
          "{ceoData.justification}"
        </p>
        <div className="pt-2 border-t border-slate-250/20 dark:border-slate-800/40 text-[10px] text-slate-500 dark:text-slate-400 font-mono">
          <span className="text-slate-400 dark:text-slate-500">BOARD COMMUNICATION:</span> <span className="font-sans text-slate-700 dark:text-slate-300">{ceoData.board_communication}</span>
        </div>
      </div>
    </div>
  )
}

export default ExecutivePanel;
