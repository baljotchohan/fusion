// components/SettingsView.tsx — preferences panel.
import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Sun, Moon, Sliders, UserCheck, Trash2 } from 'lucide-react'
import { AGENTS, API_BASE } from '@/lib/agents'

interface SettingsViewProps {
  theme: 'dark' | 'light'
  onToggleTheme: () => void
}

export default function SettingsView({ theme, onToggleTheme }: SettingsViewProps) {
  const [mockPace, setMockPace] = useState(0.6)
  const [, setLoading] = useState(true)

  const [confirmReset, setConfirmReset] = useState(false)
  const [resetting, setResetting] = useState(false)

  const [activeAgents, setActiveAgents] = useState<Record<string, boolean>>(
    () => Object.fromEntries(AGENTS.map(a => [a.name, true]))
  )

  const fetchSettings = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/system/settings`)
      if (!response.ok) throw new Error('Failed to load settings')
      const data = await response.json()
      if (data.simulation) {
        setMockPace(data.simulation.mock_pace ?? 0.6)
      }
    } catch (error) {
      console.error('Error fetching settings:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchSettings() }, [])

  const updateSetting = async (patch: { mock_pace?: number }) => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/system/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch),
      })
      if (!response.ok) throw new Error('Failed to update setting')
      const data = await response.json()
      if (data.applied && data.applied.mock_pace !== undefined) {
        setMockPace(data.applied.mock_pace)
      }
    } catch (error) {
      console.error('Error updating setting:', error)
    }
  }

  const resetAllHistory = async () => {
    setResetting(true)
    try {
      await fetch(`${API_BASE}/api/v1/system/reset-all`, { method: 'POST' })
    } catch (e) {
      console.error('Reset failed:', e)
    } finally {
      // Full reload guarantees in-memory chat + live state start clean
      window.location.reload()
    }
  }

  const toggleAgent = (name: string) => setActiveAgents(prev => ({ ...prev, [name]: !prev[name] }))
  const isDark = theme === 'dark'

  const sectionCls = 'rounded-2xl bg-bg-card border border-border shadow-sm p-6'
  const labelCls = 'text-[10px] font-semibold uppercase tracking-wider text-text-muted'

  return (
    <div className="h-full overflow-y-auto px-6 py-8 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-[22px] font-bold text-text-primary tracking-tight">Settings</h1>
        <p className="text-[13px] text-text-secondary mt-1">Customize your FUSION VC Command Center experience</p>
      </div>

      {/* Appearance */}
      <section className={sectionCls}>
        <p className={`${labelCls} mb-4`}>Appearance</p>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[13px] font-medium text-text-primary">Theme</p>
            <p className="text-[11.5px] text-text-secondary mt-0.5">Switch between light and dark mode</p>
          </div>
          <button onClick={onToggleTheme} aria-label="Toggle theme"
            className={`relative w-[58px] h-[30px] rounded-full transition-colors duration-300 focus:outline-none cursor-pointer ${isDark ? 'bg-accent' : 'bg-bg-muted'}`}>
            <Sun className="absolute left-[7px] top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-amber-400 opacity-60" />
            <Moon className="absolute right-[7px] top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-secondary opacity-60" />
            <motion.span layout className="absolute top-[3px] w-[24px] h-[24px] rounded-full bg-white shadow-md"
              animate={{ left: isDark ? 30 : 3 }} transition={{ type: 'spring', stiffness: 500, damping: 30 }} />
          </button>
        </div>
      </section>

      {/* Deliberation Pacing */}
      <section className={sectionCls}>
        <div className="flex items-center gap-2 mb-4">
          <Sliders className="w-4 h-4 text-text-muted" />
          <p className={labelCls}>Deliberation Pacing</p>
        </div>
        <p className="text-[13px] font-medium text-text-primary mb-1">Agent Response Speed ({mockPace}s)</p>
        <p className="text-[11.5px] text-text-secondary mb-5">Adjust the simulation tick delay between agent boardroom updates</p>
        <div className="space-y-2">
          <input type="range" min={0.1} max={3.0} step={0.1} value={mockPace}
            onChange={e => setMockPace(Number(e.target.value))}
            onMouseUp={e => updateSetting({ mock_pace: Number((e.target as HTMLInputElement).value) })}
            onTouchEnd={e => updateSetting({ mock_pace: Number((e.target as HTMLInputElement).value) })}
            className="w-full h-1.5 rounded-full appearance-none bg-bg-muted cursor-pointer accent-accent
                       [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4
                       [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent
                       [&::-webkit-slider-thumb]:shadow-md [&::-webkit-slider-thumb]:cursor-pointer
                       [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white" />
          <div className="flex justify-between text-[10.5px] text-text-muted font-medium">
            <span>Rapid (0.1s)</span><span>Careful (3.0s)</span>
          </div>
        </div>
      </section>

      {/* Active Partners */}
      <section className={sectionCls}>
        <div className="flex items-center gap-2 mb-4">
          <UserCheck className="w-4 h-4 text-text-muted" />
          <p className={labelCls}>Active Partners</p>
        </div>
        <p className="text-[11.5px] text-text-secondary mb-5">Enable or disable individual partners in the committee</p>
        <ul className="space-y-1">
          {AGENTS.map(agent => {
            const on = activeAgents[agent.name]
            return (
              <li key={agent.name}>
                <button onClick={() => toggleAgent(agent.name)}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors hover:bg-bg-subtle group cursor-pointer">
                  <span className="text-[18px] leading-none select-none">{agent.icon}</span>
                  <div className="flex-1 text-left">
                    <p className="text-[13px] font-medium text-text-primary">{agent.displayName}</p>
                    <p className="text-[11px] text-text-muted">{agent.role}</p>
                  </div>
                  <span className={`relative inline-flex w-[40px] h-[22px] rounded-full transition-colors duration-300 ${on ? 'bg-accent' : 'bg-bg-muted'}`}>
                    <motion.span layout className="absolute top-[2px] w-[18px] h-[18px] rounded-full bg-white shadow-sm"
                      animate={{ left: on ? 19 : 2 }} transition={{ type: 'spring', stiffness: 500, damping: 30 }} />
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      </section>

      {/* Danger Zone — Reset & Clear All History */}
      <section className="rounded-2xl bg-bg-card border border-danger/30 shadow-sm p-6">
        <div className="flex items-center gap-2 mb-4">
          <Trash2 className="w-4 h-4 text-danger" />
          <p className="text-[10px] font-semibold uppercase tracking-wider text-danger">Danger Zone</p>
        </div>
        <p className="text-[13px] font-medium text-text-primary mb-1">Reset &amp; Clear All History</p>
        <p className="text-[11.5px] text-text-secondary mb-4">
          Permanently delete every deal record, learned risk pattern, and chat message, and reset the live committee state. This cannot be undone.
        </p>

        {!confirmReset ? (
          <button onClick={() => setConfirmReset(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-danger/40 text-danger text-[12px] font-semibold hover:bg-danger-soft transition cursor-pointer">
            <Trash2 className="w-4 h-4" />
            Reset &amp; Clear All History
          </button>
        ) : (
          <div className="rounded-xl bg-danger-soft border border-danger/25 p-4">
            <p className="text-[12px] font-semibold text-danger mb-3">This will wipe all deals, patterns, and chat. Are you sure?</p>
            <div className="flex items-center gap-2">
              <button onClick={resetAllHistory} disabled={resetting}
                className="px-3.5 py-2 rounded-lg bg-danger text-white text-[12px] font-semibold hover:opacity-90 transition cursor-pointer disabled:opacity-60">
                {resetting ? 'Wiping…' : 'Yes, wipe everything'}
              </button>
              <button onClick={() => setConfirmReset(false)} disabled={resetting}
                className="px-3.5 py-2 rounded-lg border border-border text-text-secondary text-[12px] font-semibold hover:bg-bg-muted transition cursor-pointer">
                Cancel
              </button>
            </div>
          </div>
        )}
      </section>

      {/* About */}
      <section className={`${sectionCls} text-center`}>
        <p className={`${labelCls} mb-3`}>About</p>
        <p className="text-[13px] font-medium text-text-primary">FUSION v2.0</p>
        <p className="text-[11.5px] text-text-secondary mt-1">AI-Powered VC Investment Committee Command Center</p>
        <p className="text-[10.5px] text-text-muted mt-3">Built with <span className="text-accent font-medium">Band of Agents</span></p>
      </section>

      <div className="h-4" />
    </div>
  )
}
