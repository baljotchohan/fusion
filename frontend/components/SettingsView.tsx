// components/SettingsView.tsx — preferences panel.
import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Sun, Moon, Trash2, Plug, Copy, Check, ExternalLink } from 'lucide-react'
import { AGENTS, API_BASE } from '@/lib/agents'
import { apiFetch, logActivity } from '@/lib/apiFetch'

interface SettingsViewProps {
  theme: 'dark' | 'light'
  onToggleTheme: () => void
}

export default function SettingsView({ theme, onToggleTheme }: SettingsViewProps) {
  const [mockPace, setMockPace] = useState(0.6)
  const [, setLoading] = useState(true)

  const [confirmReset, setConfirmReset] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [mcpTab, setMcpTab] = useState<'smithery' | 'claude_code' | 'claude_desktop'>('smithery')
  const [copied, setCopied] = useState(false)

  const mcpUrl = `${API_BASE}/mcp`
  const smitheryUrl = 'https://smithery.ai/server/@baljotchohan/fusion-vc'
  const claudeCodeCmd = `claude mcp add fusion-vc --transport http ${mcpUrl} --header "Authorization: Bearer YOUR_KEY"`
  const claudeDesktopJson = JSON.stringify(
    { mcpServers: { 'fusion-vc': { command: 'npx', args: ['-y', 'mcp-remote', mcpUrl, '--header', 'Authorization: Bearer YOUR_KEY'] } } },
    null, 2
  )

  const copyToClipboard = async (text: string) => {
    try {
      if (navigator.clipboard) await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
      logActivity('mcp_config_copied', { type: mcpTab })
    } catch { /* clipboard denied */ }
  }

  const fetchSettings = async () => {
    try {
      const response = await apiFetch(`${API_BASE}/api/v1/system/settings`)
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
      const response = await apiFetch(`${API_BASE}/api/v1/system/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch),
      })
      if (!response.ok) throw new Error('Failed to update setting')
      const data = await response.json()
      if (data.applied && data.applied.mock_pace !== undefined) {
        setMockPace(data.applied.mock_pace)
        logActivity('mock_pace_updated', { pace: data.applied.mock_pace })
      }
    } catch (error) {
      console.error('Error updating setting:', error)
    }
  }

  const resetAllHistory = async () => {
    setResetting(true)
    try {
      logActivity('danger_zone_reset_all')
      const res = await apiFetch(`${API_BASE}/api/v1/system/reset-all`, { method: 'POST' })
      if (!res.ok) throw new Error(`Server returned ${res.status}`)
      // Full reload guarantees in-memory chat + live state start clean
      window.location.reload()
    } catch (e) {
      console.error('Reset failed:', e)
      setResetting(false)
      setConfirmReset(false)
    }
  }


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
          <button onClick={() => { onToggleTheme(); logActivity('theme_toggled', { nextTheme: isDark ? 'light' : 'dark' }) }} aria-label="Toggle theme"
            className={`relative w-[58px] h-[30px] rounded-full transition-colors duration-300 focus:outline-none cursor-pointer ${isDark ? 'bg-accent' : 'bg-bg-muted'}`}>
            <Sun className="absolute left-[7px] top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-amber-400 opacity-60" />
            <Moon className="absolute right-[7px] top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-secondary opacity-60" />
            <motion.span layout className="absolute top-[3px] w-[24px] h-[24px] rounded-full bg-white shadow-md"
              animate={{ left: isDark ? 30 : 3 }} transition={{ type: 'spring', stiffness: 500, damping: 30 }} />
          </button>
        </div>
      </section>





      {/* MCP Connect */}
      <section className={sectionCls}>
        <div className="flex items-center gap-2 mb-1">
          <Plug className="w-4 h-4 text-accent" />
          <p className={labelCls}>Connect via MCP</p>
        </div>
        <p className="text-[11.5px] text-text-secondary mb-4">
          Use FUSION's 5-agent VC committee directly from your AI tools — no browser needed.
        </p>

        {/* Tabs */}
        <div className="flex gap-1 mb-4 bg-bg-muted rounded-lg p-1 w-fit">
          {([['smithery', 'Smithery (easiest)'], ['claude_code', 'Claude Code'], ['claude_desktop', 'Claude Desktop']] as const).map(([id, label]) => (
            <button key={id} onClick={() => { setMcpTab(id); logActivity('mcp_tab_changed', { tab: id }) }}
              className={`px-3 py-1.5 rounded-md text-[11px] font-medium transition-colors cursor-pointer ${mcpTab === id ? 'bg-bg-card text-text-primary shadow-sm' : 'text-text-muted hover:text-text-primary'}`}>
              {label}
            </button>
          ))}
        </div>

        {mcpTab === 'smithery' && (
          <div className="space-y-3">
            <p className="text-[12px] text-text-secondary">Click the button below — Smithery opens in your browser and auto-configures your AI client. No terminal, no config files.</p>
            <a href={smitheryUrl} target="_blank" rel="noreferrer" onClick={() => logActivity('mcp_smithery_click')}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-white text-[12px] font-semibold hover:opacity-90 transition">
              <ExternalLink className="w-3.5 h-3.5" />
              Connect on Smithery
            </a>
          </div>
        )}

        {mcpTab === 'claude_code' && (
          <div className="space-y-3">
            <p className="text-[12px] text-text-secondary">Run this one command in your terminal:</p>
            <div className="flex items-center gap-2 bg-bg-muted rounded-lg px-3 py-2.5 font-mono text-[11px] text-text-primary">
              <span className="flex-1 truncate">{claudeCodeCmd}</span>
              <button onClick={() => copyToClipboard(claudeCodeCmd)} className="shrink-0 text-text-muted hover:text-accent transition cursor-pointer">
                {copied ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>
        )}

        {mcpTab === 'claude_desktop' && (
          <div className="space-y-3">
            <p className="text-[12px] text-text-secondary">Add this to your <code className="text-[11px] bg-bg-muted px-1 py-0.5 rounded">claude_desktop_config.json</code>:</p>
            <div className="relative">
              <pre className="bg-bg-muted rounded-lg px-3 py-3 text-[10.5px] font-mono text-text-primary overflow-x-auto whitespace-pre">{claudeDesktopJson}</pre>
              <button onClick={() => copyToClipboard(claudeDesktopJson)}
                className="absolute top-2 right-2 text-text-muted hover:text-accent transition cursor-pointer">
                {copied ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>
        )}
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
        <p className="text-[13px] font-medium text-text-primary">FUSION v1.0</p>
        <p className="text-[11.5px] text-text-secondary mt-1">AI-Powered VC Investment Committee Command Center</p>
        <p className="text-[10.5px] text-text-muted mt-3">Built with <span className="text-accent font-medium">Band of Agents</span></p>
      </section>

      <div className="h-4" />
    </div>
  )
}
