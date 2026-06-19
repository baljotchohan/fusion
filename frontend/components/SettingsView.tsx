// components/SettingsView.tsx — preferences panel.
import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Sun, Moon, Trash2, Plug, Copy, Check, ExternalLink, Lock, BarChart2, Key } from 'lucide-react'
import { API_BASE } from '@/lib/agents'
import { apiFetch, logActivity } from '@/lib/apiFetch'

interface SettingsViewProps {
  theme: 'dark' | 'light'
  onToggleTheme: () => void
  isLoggedIn?: boolean
}

type McpTab = 'claude_ai' | 'vscode' | 'cursor' | 'claude_code' | 'claude_desktop'

export default function SettingsView({ theme, onToggleTheme, isLoggedIn = false }: SettingsViewProps) {
  const [mockPace, setMockPace] = useState(0.6)
  const [, setLoading] = useState(true)
  const [confirmReset, setConfirmReset] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [mcpTab, setMcpTab] = useState<McpTab>('claude_ai')
  const [copied, setCopied] = useState(false)
  const [sessionUsage, setSessionUsage] = useState<{ used: number; limit: number; remaining: number } | null>(null)
  const [mcpKey, setMcpKey] = useState<string | null>(null)

  const mcpUrl = 'https://baljot07-fusion.hf.space/mcp/'
  const smitheryUrl = 'https://smithery.ai/server/@baljotchohan/fusion-vc'
  const keyDisplay = mcpKey ?? 'fus_YOUR_KEY'

  const vsCodeJson = JSON.stringify({
    servers: {
      'fusion-vc': {
        type: 'http',
        url: mcpUrl,
        headers: { Authorization: `Bearer ${keyDisplay}` },
      },
    },
  }, null, 2)

  const cursorJson = JSON.stringify({
    mcpServers: {
      'fusion-vc': {
        url: mcpUrl,
        headers: { Authorization: `Bearer ${keyDisplay}` },
      },
    },
  }, null, 2)

  const claudeCodeCmd = `claude mcp add fusion-vc --transport http ${mcpUrl} --header "Authorization: Bearer ${keyDisplay}"`

  // Native url field — works on Windows, Mac, Linux identically. No npx, no mcp-remote.
  const claudeDesktopJson = JSON.stringify({
    mcpServers: {
      'fusion-vc': {
        url: mcpUrl,
        headers: { Authorization: `Bearer ${keyDisplay}` },
      },
    },
  }, null, 2)

  const claudeAiUrl = 'https://claude.ai/settings/integrations'

  const openClaudeAi = async () => {
    try { if (navigator.clipboard) await navigator.clipboard.writeText(mcpUrl) } catch { /* ok */ }
    window.open(claudeAiUrl, '_blank', 'noopener')
    logActivity('mcp_claude_ai_connect_click')
  }

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
      if (data.simulation) setMockPace(data.simulation.mock_pace ?? 0.6)
    } catch (error) {
      console.error('Error fetching settings:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSettings()
    apiFetch(`${API_BASE}/api/v1/session-usage`).then(r => r.json()).then(d => setSessionUsage(d)).catch(() => {})
    if (isLoggedIn) {
      apiFetch(`${API_BASE}/api/v1/mcp-key`).then(r => r.json()).then(d => {
        if (d.key) setMcpKey(d.key)
      }).catch(() => {})
    }
  }, [isLoggedIn])

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

  const MCP_TABS: { id: McpTab; label: string; badge?: string }[] = [
    { id: 'claude_ai', label: 'Claude.ai', badge: '★ Best' },
    { id: 'vscode', label: 'VS Code' },
    { id: 'cursor', label: 'Cursor' },
    { id: 'claude_code', label: 'Claude Code' },
    { id: 'claude_desktop', label: 'Desktop App' },
  ]

  return (
    <div className="h-full overflow-y-auto px-6 py-8 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-[22px] font-bold text-text-primary tracking-tight">Settings</h1>
        <p className="text-[13px] text-text-secondary mt-1">Customize your FUSION VC Command Center experience</p>
      </div>

      {/* Usage & Limits */}
      <section className={sectionCls}>
        <div className="flex items-center gap-2 mb-4">
          <BarChart2 className="w-4 h-4 text-accent" />
          <p className={labelCls}>Usage &amp; Limits</p>
        </div>
        <div className="space-y-3">
          <div className="flex items-center justify-between py-2.5 px-3 rounded-xl bg-bg-muted">
            <div>
              <p className="text-[12.5px] font-medium text-text-primary">Committee sessions</p>
              <p className="text-[11px] text-text-secondary mt-0.5">
                {isLoggedIn ? 'Unlimited — no cap' : '14 sessions / week — sign in for unlimited'}
              </p>
            </div>
            <div className="text-right shrink-0 ml-4">
              {isLoggedIn ? (
                <span className="text-[22px] font-bold text-text-primary">∞</span>
              ) : (
                <>
                  <span className="text-[18px] font-bold tabular-nums text-text-primary">
                    {sessionUsage ? `${sessionUsage.used}/14` : '—'}
                  </span>
                  <p className="text-[9px] text-text-muted uppercase tracking-wider">used</p>
                </>
              )}
            </div>
          </div>
          {!isLoggedIn && sessionUsage && (
            <div className="h-1.5 rounded-full bg-bg-subtle overflow-hidden">
              <div
                className="h-full rounded-full bg-slate-400 dark:bg-slate-500 transition-all duration-500"
                style={{ width: `${Math.min(100, (sessionUsage.used / 14) * 100)}%` }}
              />
            </div>
          )}
          <div className="flex items-center justify-between py-2.5 px-3 rounded-xl bg-bg-muted">
            <div>
              <p className="text-[12.5px] font-medium text-text-primary">MCP access</p>
              <p className="text-[11px] text-text-secondary mt-0.5">Connect AI tools to the committee</p>
            </div>
            <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border border-border ${isLoggedIn ? 'bg-bg-subtle text-text-primary' : 'bg-bg-subtle text-text-muted'}`}>
              {isLoggedIn ? 'Unlimited' : 'Sign in required'}
            </span>
          </div>
          <div className="flex items-center justify-between py-2.5 px-3 rounded-xl bg-bg-muted">
            <div>
              <p className="text-[12.5px] font-medium text-text-primary">Chat messages</p>
              <p className="text-[11px] text-text-secondary mt-0.5">
                {isLoggedIn ? 'Unlimited' : '100 messages / hour'}
              </p>
            </div>
            <span className="text-[11px] font-semibold text-text-primary">{isLoggedIn ? '∞' : '100/hr'}</span>
          </div>
        </div>
      </section>

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
          Use FUSION&apos;s 5-agent VC committee from VS Code, Cursor, Claude Code, or Claude Desktop — with your own isolated deal history.
        </p>

        {!isLoggedIn ? (
          <div className="flex flex-col items-center justify-center gap-3 py-6 px-4 rounded-xl border border-border bg-bg-muted text-center">
            <div className="w-10 h-10 rounded-full bg-bg-subtle border border-border flex items-center justify-center">
              <Lock className="w-4 h-4 text-text-muted" />
            </div>
            <div>
              <p className="text-[13px] font-semibold text-text-primary">Sign in to access MCP</p>
              <p className="text-[11.5px] text-text-secondary mt-1 max-w-xs">MCP integration requires a personal API key tied to your account. Sign in to generate yours.</p>
            </div>
          </div>
        ) : (
          <>
            {/* Personal API key */}
            <div className="mb-4 p-3 rounded-xl border border-border bg-bg-muted">
              <div className="flex items-center gap-2 mb-1.5">
                <Key className="w-3.5 h-3.5 text-accent" />
                <span className="text-[10px] font-bold uppercase tracking-wider text-text-muted">Your Personal MCP Key</span>
              </div>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-[11.5px] font-mono text-text-primary truncate">{mcpKey ?? 'Loading…'}</code>
                {mcpKey && (
                  <button onClick={() => copyToClipboard(mcpKey)} className="shrink-0 text-text-muted hover:text-accent transition cursor-pointer">
                    {copied ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                )}
              </div>
              <p className="text-[10.5px] text-text-muted mt-1.5">This key isolates your committee history — do not share it.</p>
            </div>

            {/* Client tabs */}
            <div className="flex gap-1 mb-4 bg-bg-muted rounded-lg p-1 flex-wrap">
              {MCP_TABS.map(({ id, label, badge }) => (
                <button key={id} onClick={() => { setMcpTab(id); logActivity('mcp_tab_changed', { tab: id }) }}
                  className={`flex items-center gap-1 px-3 py-1.5 rounded-md text-[11px] font-medium transition-colors cursor-pointer ${mcpTab === id ? 'bg-bg-card text-text-primary shadow-sm' : 'text-text-muted hover:text-text-primary'}`}>
                  {label}
                  {badge && <span className="text-[9px] font-bold text-amber-500">{badge}</span>}
                </button>
              ))}
            </div>

            {mcpTab === 'claude_ai' && (
              <div className="space-y-4">
                <div className="rounded-xl bg-bg-subtle border border-border p-3.5">
                  <p className="text-[12px] font-semibold text-text-primary mb-1">Works on every device — one connection</p>
                  <p className="text-[11px] text-text-secondary">Connect via claude.ai and it automatically syncs to Claude Desktop (Mac/Win/Linux) and the Claude mobile app. No config files, no keys to paste.</p>
                </div>
                <div className="space-y-2">
                  <div className="flex items-start gap-3 py-2.5 px-3 rounded-xl bg-bg-muted">
                    <span className="text-[11px] font-bold text-text-muted w-4 shrink-0 mt-0.5">1</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-[11.5px] font-medium text-text-primary">Copy your server URL</p>
                      <div className="flex items-center gap-2 mt-1.5 bg-bg-subtle rounded-lg px-2.5 py-1.5">
                        <code className="text-[10.5px] font-mono text-text-secondary flex-1 truncate">{mcpUrl}</code>
                        <button onClick={() => copyToClipboard(mcpUrl)} className="shrink-0 text-text-muted hover:text-text-primary transition cursor-pointer">
                          {copied ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 py-2.5 px-3 rounded-xl bg-bg-muted">
                    <span className="text-[11px] font-bold text-text-muted w-4 shrink-0 mt-0.5">2</span>
                    <div className="flex-1">
                      <p className="text-[11.5px] font-medium text-text-primary mb-1.5">Open Claude.ai Connectors</p>
                      <button onClick={openClaudeAi}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-text-primary text-bg-card text-[11px] font-semibold hover:opacity-90 transition cursor-pointer">
                        <ExternalLink className="w-3 h-3" />
                        Open Claude.ai Connectors →
                      </button>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 py-2.5 px-3 rounded-xl bg-bg-muted">
                    <span className="text-[11px] font-bold text-text-muted w-4 shrink-0 mt-0.5">3</span>
                    <p className="text-[11.5px] text-text-secondary">Click <strong className="text-text-primary">Add custom connector</strong>, paste the URL, click Connect, and sign in to your FUSION account.</p>
                  </div>
                </div>
                <p className="text-[10.5px] text-text-muted">Also works in ChatGPT: Settings → Apps → paste the same URL.</p>
              </div>
            )}

            {mcpTab === 'vscode' && (
              <div className="space-y-3">
                <p className="text-[12px] text-text-secondary">
                  Add to <code className="text-[11px] bg-bg-muted px-1 py-0.5 rounded">.vscode/mcp.json</code> in your project root (VS Code 1.99+ with Copilot or MCP extension):
                </p>
                <div className="relative">
                  <pre className="bg-bg-muted rounded-lg px-3 py-3 text-[10.5px] font-mono text-text-primary overflow-x-auto whitespace-pre">{vsCodeJson}</pre>
                  <button onClick={() => copyToClipboard(vsCodeJson)}
                    className="absolute top-2 right-2 text-text-muted hover:text-accent transition cursor-pointer">
                    {copied ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
                <p className="text-[10.5px] text-text-muted">Restart VS Code after saving the file. The key above is already filled in.</p>
              </div>
            )}

            {mcpTab === 'cursor' && (
              <div className="space-y-3">
                <p className="text-[12px] text-text-secondary">
                  Add to <code className="text-[11px] bg-bg-muted px-1 py-0.5 rounded">~/.cursor/mcp.json</code> (global) or <code className="text-[11px] bg-bg-muted px-1 py-0.5 rounded">.cursor/mcp.json</code> (project):
                </p>
                <div className="relative">
                  <pre className="bg-bg-muted rounded-lg px-3 py-3 text-[10.5px] font-mono text-text-primary overflow-x-auto whitespace-pre">{cursorJson}</pre>
                  <button onClick={() => copyToClipboard(cursorJson)}
                    className="absolute top-2 right-2 text-text-muted hover:text-accent transition cursor-pointer">
                    {copied ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
                <p className="text-[10.5px] text-text-muted">Reload Cursor after saving. Open Settings → MCP to verify the server appears.</p>
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
                <p className="text-[12px] text-text-secondary">
                  Works on <strong className="text-text-primary">Windows, Mac, and Linux</strong> — same config, no mcp-remote needed.
                  Add to <code className="text-[11px] bg-bg-muted px-1 py-0.5 rounded">claude_desktop_config.json</code> (File → Settings → Developer):
                </p>
                <div className="relative">
                  <pre className="bg-bg-muted rounded-lg px-3 py-3 text-[10.5px] font-mono text-text-primary overflow-x-auto whitespace-pre">{claudeDesktopJson}</pre>
                  <button onClick={() => copyToClipboard(claudeDesktopJson)}
                    className="absolute top-2 right-2 text-text-muted hover:text-text-primary transition cursor-pointer">
                    {copied ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
                <div className="text-[10.5px] text-text-muted space-y-0.5">
                  <p>Mac: <code className="bg-bg-subtle px-1 rounded">~/Library/Application Support/Claude/claude_desktop_config.json</code></p>
                  <p>Windows: <code className="bg-bg-subtle px-1 rounded">%APPDATA%\Claude\claude_desktop_config.json</code></p>
                  <p>Linux: <code className="bg-bg-subtle px-1 rounded">~/.config/Claude/claude_desktop_config.json</code></p>
                </div>
                <p className="text-[10.5px] text-text-muted">Fully quit and reopen Claude Desktop after saving.</p>
              </div>
            )}

            <div className="mt-4 pt-3 border-t border-border flex items-center gap-2">
              <a href={smitheryUrl} target="_blank" rel="noreferrer" onClick={() => logActivity('mcp_smithery_click')}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-text-secondary text-[11px] font-medium hover:text-accent hover:border-accent transition">
                <ExternalLink className="w-3 h-3" />
                Also on Smithery (easiest setup)
              </a>
            </div>
          </>
        )}
      </section>

      {/* Danger Zone */}
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
