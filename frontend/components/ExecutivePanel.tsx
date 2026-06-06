// components/ExecutivePanel.tsx
import React from 'react'

interface ExecutivePanelProps {
  decision: Record<string, any> | null
  threatScore: number
}

export function ExecutivePanel({ decision, threatScore }: ExecutivePanelProps) {
  if (!decision && threatScore < 70) {
    return (
      <div className="flex flex-col h-[200px] items-center justify-center text-slate-500 text-xs font-mono border border-slate-900 bg-slate-950/40 rounded-xl">
        <span>BOARDROOM DEBATE STANDBY</span>
        <span className="text-[10px] mt-1 text-slate-600">(Escalates automatically if risk reaches 70+)</span>
      </div>
    )
  }

  // Mock boardroom details if decision is triggered but text parsing is standard
  const cfo = {
    loss: "$2,400,000 (PII fine liability + customer churn)",
    cost: "$180,000 (mail server patching + IT ops)",
    roi: "Containment is 13x cheaper than full breach."
  }

  const legal = {
    rules: ["GDPR Article 33 (72h limit)", "India DPDP Act Section 8"],
    fine: "Up to €20M or 4% annual global turnover",
    deadline: "DPA notification required within 24 hours"
  }

  const ops = {
    offline: ["Corporate Webmail Portal (4 hours)", "Admin RDP Access (2 hours)"],
    window: "Schedule maintenance for 02:00 - 06:00 AM local time"
  }

  const verdict = decision?.verdict || "CONTAIN"
  const justification = decision?.justification || "Containment cost is substantially lower than projected breach exposure. Regulatory clock is running."

  return (
    <div className="border border-red-500/25 bg-red-950/5 rounded-2xl p-5 backdrop-blur-md shadow-[0_0_25px_rgba(239,68,68,0.02)] space-y-4">
      {/* Title & Verdict Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-4 border-b border-slate-900">
        <div>
          <h3 className="font-bold text-sm text-red-400 tracking-wider">👔 EXECUTIVE BOARDROOM REPORT</h3>
          <p className="text-[11px] text-slate-500 font-mono">Incident ID: ARGUS-INC-2026-001</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-bold text-slate-400">VERDICT:</span>
          <span className="bg-red-950 text-red-400 border border-red-500/50 font-black text-sm px-4 py-1.5 rounded-lg animate-pulse">
            🚨 {verdict} DECISION
          </span>
        </div>
      </div>

      {/* Grid of assessments */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* CFO */}
        <div className="bg-slate-950/80 border border-slate-900 rounded-xl p-3.5 space-y-2">
          <div className="flex items-center gap-2 border-b border-slate-900 pb-1.5">
            <span className="text-xs font-bold text-emerald-400 tracking-wide">CFO Financial ROI</span>
          </div>
          <div className="space-y-1 text-xs text-slate-400 leading-relaxed font-sans">
            <p><span className="text-slate-500 font-mono">Breach Cost:</span> {cfo.loss}</p>
            <p><span className="text-slate-500 font-mono">Contain Cost:</span> {cfo.cost}</p>
            <p className="text-[10px] text-emerald-400 font-mono font-semibold pt-1 border-t border-slate-900/40">
              💡 {cfo.roi}
            </p>
          </div>
        </div>

        {/* Legal */}
        <div className="bg-slate-950/80 border border-slate-900 rounded-xl p-3.5 space-y-2">
          <div className="flex items-center gap-2 border-b border-slate-900 pb-1.5">
            <span className="text-xs font-bold text-blue-400 tracking-wide">Legal & Regulatory</span>
          </div>
          <div className="space-y-1 text-xs text-slate-400 leading-relaxed font-sans">
            <p><span className="text-slate-500 font-mono">Triggered:</span> {legal.rules.join(", ")}</p>
            <p><span className="text-slate-500 font-mono">Max Exposure:</span> {legal.fine}</p>
            <p className="text-[10px] text-blue-400 font-mono font-semibold pt-1 border-t border-slate-900/40">
              ⏰ {legal.deadline}
            </p>
          </div>
        </div>

        {/* Ops */}
        <div className="bg-slate-950/80 border border-slate-900 rounded-xl p-3.5 space-y-2">
          <div className="flex items-center gap-2 border-b border-slate-900 pb-1.5">
            <span className="text-xs font-bold text-amber-400 tracking-wide">Ops & Continuity</span>
          </div>
          <div className="space-y-1 text-xs text-slate-400 leading-relaxed font-sans">
            <p><span className="text-slate-500 font-mono">Downtime:</span> {ops.offline.join(", ")}</p>
            <p className="text-[10px] text-amber-400 font-mono font-semibold pt-1 border-t border-slate-900/40">
              📅 {ops.window}
            </p>
          </div>
        </div>
      </div>

      {/* CEO Justification Box */}
      <div className="bg-slate-950/80 border border-slate-900 rounded-xl p-4 space-y-1.5">
        <h4 className="text-xs font-bold text-slate-300 font-mono">CEO JUSTIFICATION</h4>
        <p className="text-xs text-slate-400 leading-relaxed font-sans italic">
          "{justification}"
        </p>
      </div>
    </div>
  )
}
export default ExecutivePanel;
