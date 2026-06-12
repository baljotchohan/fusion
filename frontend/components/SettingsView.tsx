// components/SettingsView.tsx — preferences panel.
import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Sun, Moon, Cpu, ShieldAlert, CheckCircle, Sliders, HardDrive, UserCheck } from 'lucide-react'
import { AGENTS, API_BASE } from '@/lib/agents'

interface SettingsViewProps {
  theme: 'dark' | 'light'
  onToggleTheme: () => void
}

const fade = {
  hidden: { opacity: 0, y: 12 },
  show: (i: number) => ({ opacity: 1, y: 0, transition: { delay: i * 0.06, duration: 0.35 } }),
}

export default function SettingsView({ theme, onToggleTheme }: SettingsViewProps) {
  const [mockPace, setMockPace] = useState(0.6)
  const [maxFileSizeMb, setMaxFileSizeMb] = useState(10)
  const [primaryProvider, setPrimaryProvider] = useState('gemini')
  const [providers, setProviders] = useState<any[]>([])
  const [activeProvider, setActiveProvider] = useState('local-engine')
  const [llmDegraded, setLlmDegraded] = useState(false)
  const [loading, setLoading] = useState(true)

  const [activeAgents, setActiveAgents] = useState<Record<string, boolean>>(
    () => Object.fromEntries(AGENTS.map(a => [a.name, true]))
  )

  // Fetch settings from backend on mount
  const fetchSettings = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/system/settings`)
      if (!response.ok) throw new Error('Failed to load settings')
      const data = await response.json()
      
      if (data.simulation) {
        setMockPace(data.simulation.mock_pace ?? 0.6)
        setMaxFileSizeMb(data.simulation.max_file_size_mb ?? 10)
      }
      if (data.llm) {
        setPrimaryProvider(data.llm.primary ?? 'gemini')
        setProviders(data.llm.providers ?? [])
        setActiveProvider(data.llm.active_provider ?? 'local-engine')
        setLlmDegraded(data.llm.degraded ?? false)
      }
    } catch (error) {
      console.error('Error fetching settings:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSettings()
  }, [])

  const updateSetting = async (patch: { mock_pace?: number; primary_provider?: string; max_file_size_mb?: number; reset_llm_degradation?: boolean }) => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/system/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch),
      })
      if (!response.ok) throw new Error('Failed to update setting')
      const data = await response.json()
      
      // Update local state based on what was applied
      if (data.applied) {
        if (data.applied.mock_pace !== undefined) setMockPace(data.applied.mock_pace)
        if (data.applied.max_file_size_mb !== undefined) setMaxFileSizeMb(data.applied.max_file_size_mb)
        if (data.applied.primary_provider !== undefined) {
          setPrimaryProvider(data.applied.primary_provider)
          // Refetch to get the updated active provider status
          fetchSettings()
        }
      }
    } catch (error) {
      console.error('Error updating setting:', error)
    }
  }

  const toggleAgent = (name: string) =>
    setActiveAgents(prev => ({ ...prev, [name]: !prev[name] }))

  const isDark = theme === 'dark'

  return (
    <div className="h-full overflow-y-auto px-6 py-8 max-w-2xl mx-auto space-y-8">
      {/* ── Header ── */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
        <h1 className="text-[22px] font-bold text-text-primary tracking-tight">Settings</h1>
        <p className="text-[13px] text-text-secondary mt-1">Customize your FUSION VC Command Center experience</p>
      </motion.div>

      {/* ── 1. Appearance ── */}
      <motion.section
        className="rounded-xl bg-bg-card border border-border shadow-sm p-6"
        variants={fade} custom={0} initial="hidden" animate="show"
      >
        <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-4">
          Appearance
        </p>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-[13px] font-medium text-text-primary">Theme</p>
            <p className="text-[11.5px] text-text-secondary mt-0.5">
              Switch between light and dark mode
            </p>
          </div>

          <button
            onClick={onToggleTheme}
            className={`
              relative w-[58px] h-[30px] rounded-full transition-colors duration-300 focus:outline-none cursor-pointer
              ${isDark ? 'bg-accent' : 'bg-bg-muted'}
            `}
            aria-label="Toggle theme"
          >
            {/* track icons */}
            <Sun className="absolute left-[7px] top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-amber-400 opacity-60" />
            <Moon className="absolute right-[7px] top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-indigo-300 opacity-60" />

            {/* thumb */}
            <motion.span
              layout
              className="absolute top-[3px] w-[24px] h-[24px] rounded-full bg-white shadow-md"
              animate={{ left: isDark ? 30 : 3 }}
              transition={{ type: 'spring', stiffness: 500, damping: 30 }}
            />
          </button>
        </div>
      </motion.section>

      {/* ── 2. Deliberation Pacing ── */}
      <motion.section
        className="rounded-xl bg-bg-card border border-border shadow-sm p-6"
        variants={fade} custom={1} initial="hidden" animate="show"
      >
        <div className="flex items-center gap-2 mb-4">
          <Sliders className="w-4 h-4 text-text-muted" />
          <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
            Deliberation Pacing
          </p>
        </div>

        <p className="text-[13px] font-medium text-text-primary mb-1">Agent Response Speed ({mockPace}s)</p>
        <p className="text-[11.5px] text-text-secondary mb-5">
          Adjust the simulation tick delay between agent boardroom updates
        </p>

        <div className="space-y-2">
          <input
            type="range"
            min={0.1}
            max={3.0}
            step={0.1}
            value={mockPace}
            onChange={e => updateSetting({ mock_pace: Number(e.target.value) })}
            className="w-full h-1.5 rounded-full appearance-none bg-bg-muted cursor-pointer
                       accent-accent
                       [&::-webkit-slider-thumb]:appearance-none
                       [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4
                       [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent
                       [&::-webkit-slider-thumb]:shadow-md [&::-webkit-slider-thumb]:cursor-pointer
                       [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-white"
          />
          <div className="flex justify-between text-[10.5px] text-text-muted font-medium">
            <span>Rapid (0.1s)</span>
            <span>Careful (3.0s)</span>
          </div>
        </div>
      </motion.section>

      {/* ── 3. File Upload Limit ── */}
      <motion.section
        className="rounded-xl bg-bg-card border border-border shadow-sm p-6"
        variants={fade} custom={2} initial="hidden" animate="show"
      >
        <div className="flex items-center gap-2 mb-4">
          <HardDrive className="w-4 h-4 text-text-muted" />
          <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
            File Ingestion settings
          </p>
        </div>

        <p className="text-[13px] font-medium text-text-primary mb-1">Maximum Pitch File Size</p>
        <p className="text-[11.5px] text-text-secondary mb-4">
          Limit the file upload size allowed for startup Pitch Decks (2MB - 10MB)
        </p>

        <div className="flex items-center gap-2">
          {[2, 5, 10, 20].map(size => (
            <button
              key={size}
              onClick={() => updateSetting({ max_file_size_mb: size })}
              className={`px-4 py-2 rounded-lg text-[12px] font-semibold border transition cursor-pointer ${
                maxFileSizeMb === size
                  ? 'bg-accent border-accent text-white'
                  : 'bg-bg-subtle border-border text-text-secondary hover:bg-bg-muted'
              }`}
            >
              {size} MB
            </button>
          ))}
        </div>
      </motion.section>

      {/* ── 4. AI Intelligence Engine ── */}
      <motion.section
        className="rounded-xl bg-bg-card border border-border shadow-sm p-6"
        variants={fade} custom={3} initial="hidden" animate="show"
      >
        <div className="flex items-center gap-2 mb-4">
          <Cpu className="w-4 h-4 text-text-muted" />
          <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
            AI Intelligence Engine
          </p>
        </div>

        <p className="text-[13px] font-medium text-text-primary mb-1">Primary Reasoning Engine</p>
        <p className="text-[11.5px] text-text-secondary mb-4">
          Choose which LLM API provider powers the Swarm's intelligence
        </p>

        {llmDegraded && (
          <div className="rounded-xl bg-red-50 dark:bg-red-500/10 border border-red-200/50 dark:border-red-500/25 p-3.5 mb-4 flex items-start gap-3">
            <ShieldAlert className="w-4 h-4 text-red-600 dark:text-red-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-[12px] font-bold text-red-700 dark:text-red-400">API Degradation Active</p>
              <p className="text-[11px] text-red-600 dark:text-red-500 mt-0.5">
                The router is currently bypassing degraded remote providers. Let's clear this to try re-connecting.
              </p>
              <button
                onClick={() => updateSetting({ reset_llm_degradation: true }).then(() => fetchSettings())}
                className="mt-2 text-[10.5px] font-semibold px-2.5 py-1 rounded bg-red-600 hover:bg-red-700 text-white transition cursor-pointer"
              >
                Reset Cooldown
              </button>
            </div>
          </div>
        )}

        <div className="space-y-3">
          <select
            value={primaryProvider}
            onChange={e => updateSetting({ primary_provider: e.target.value })}
            className="w-full bg-bg-subtle border border-border rounded-lg px-3 py-2 text-[13px] text-text-primary focus:outline-none focus:border-accent transition cursor-pointer"
          >
            {providers.map((p: any) => (
              <option key={p.id} value={p.id} disabled={!p.configured}>
                {p.label} {p.configured ? '(Ready)' : '(Not Configured — keys missing)'}
              </option>
            ))}
            {providers.length === 0 && (
              <option value="gemini">Google Gemini 2.0 Flash (Default)</option>
            )}
          </select>

          <div className="flex items-center gap-1.5 text-[11px] text-text-muted mt-1">
            <span className="font-semibold text-text-secondary">Active engine:</span>
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-bg-muted font-mono text-[10px]">
              <span className={`w-1 h-1 rounded-full ${activeProvider === 'local-engine' ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400'}`} />
              {activeProvider}
            </span>
          </div>
        </div>
      </motion.section>

      {/* ── 5. Active Partners ── */}
      <motion.section
        className="rounded-xl bg-bg-card border border-border shadow-sm p-6"
        variants={fade} custom={4} initial="hidden" animate="show"
      >
        <div className="flex items-center gap-2 mb-4">
          <UserCheck className="w-4 h-4 text-text-muted" />
          <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
            Active Partners
          </p>
        </div>
        <p className="text-[11.5px] text-text-secondary mb-5">
          Enable or disable individual partners in the committee
        </p>

        <ul className="space-y-1">
          {AGENTS.map(agent => {
            const on = activeAgents[agent.name]
            return (
              <li key={agent.name}>
                <button
                  onClick={() => toggleAgent(agent.name)}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors
                             hover:bg-bg-subtle group cursor-pointer"
                >
                  {/* icon */}
                  <span className="text-[18px] leading-none select-none">{agent.icon}</span>

                  {/* name + role */}
                  <div className="flex-1 text-left">
                    <p className="text-[13px] font-medium text-text-primary">{agent.displayName}</p>
                    <p className="text-[11px] text-text-muted">{agent.role}</p>
                  </div>

                  {/* toggle */}
                  <span
                    className={`
                      relative inline-flex w-[40px] h-[22px] rounded-full transition-colors duration-300
                      ${on ? 'bg-accent' : 'bg-bg-muted'}
                    `}
                  >
                    <motion.span
                      layout
                      className="absolute top-[2px] w-[18px] h-[18px] rounded-full bg-white shadow-sm"
                      animate={{ left: on ? 19 : 2 }}
                      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                    />
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      </motion.section>

      {/* ── 6. About ── */}
      <motion.section
        className="rounded-xl bg-bg-card border border-border shadow-sm p-6 text-center"
        variants={fade} custom={5} initial="hidden" animate="show"
      >
        <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-3">
          About
        </p>
        <p className="text-[13px] font-medium text-text-primary">
          FUSION v2.0
        </p>
        <p className="text-[11.5px] text-text-secondary mt-1">
          AI-Powered VC Investment Committee Command Center
        </p>
        <p className="text-[10.5px] text-text-muted mt-3">
          Built with <span className="text-accent font-medium">Band of Agents</span>
        </p>
      </motion.section>

      {/* bottom breathing room */}
      <div className="h-4" />
    </div>
  )
}
