// components/SettingsView.tsx — preferences panel.
import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Sun, Moon, Trash2, Plug, Copy, Check, ExternalLink, Lock, BarChart2, Key, ChevronDown } from 'lucide-react'
import { API_BASE } from '@/lib/agents'
import { apiFetch, logActivity } from '@/lib/apiFetch'

interface SettingsViewProps {
  theme: 'dark' | 'light'
  onToggleTheme: () => void
  isLoggedIn?: boolean
}

type ClientId = 'claude_ai' | 'vscode' | 'cursor' | 'claude_code' | 'claude_desktop'

// ─── Brand logos ───────────────────────────────────────────────────────────────

const AnthropicLogo = () => (
  <svg viewBox="0 0 41 40" width="18" height="18" fill="#C2410C">
    <path d="M23.55 0H17.45L0 40h6.55l4.16-10.48h19.58L34.45 40H41L23.55 0ZM12.82 23.61L20.5 4.27l7.68 19.34H12.82Z" />
  </svg>
)

const VSCodeLogo = () => (
  <svg viewBox="0 0 100 100" width="18" height="18">
    <path fill="#007ACC" d="M74.5 3.2L30.1 43.7 13.4 30.7 3.2 37.1V62.9l10.2 6.4 16.7-13L74.5 96.8 96.8 88V12L74.5 3.2zM74.5 74.8L42.7 50 74.5 25.2V74.8z" />
  </svg>
)

const CursorLogo = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
    <rect width="24" height="24" rx="5" fill="#000" />
    <path d="M7 8l5 4-5 4M13 16h4" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)

const TerminalLogo = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
    <rect x="1" y="3" width="22" height="18" rx="3" fill="#4F46E5" />
    <path d="M5 9.5l4 2.5-4 2.5" stroke="#fff" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M11 14.5h7" stroke="#fff" strokeWidth="1.7" strokeLinecap="round" />
  </svg>
)

// ─── Shared sub-components ─────────────────────────────────────────────────────

const StepRow = ({ n, text, children }: { n: number; text: string; children?: React.ReactNode }) => (
  <div className="flex items-start gap-3">
    <span className="w-[22px] h-[22px] rounded-full bg-bg-muted border border-border flex items-center justify-center text-[10px] font-bold text-text-muted shrink-0 mt-0.5 tabular-nums">{n}</span>
    <div className="flex-1 min-w-0">
      <p className="text-[12px] text-text-secondary leading-relaxed">{text}</p>
      {children}
    </div>
  </div>
)

const StepCopy = ({ label, onClick }: { label: string; onClick: () => void }) => (
  <button onClick={onClick} className="mt-1.5 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-bg-muted border border-border text-[11px] font-medium text-text-primary hover:bg-bg-card transition cursor-pointer">
    <Copy className="w-3 h-3" />{label}
  </button>
)

const StepOpen = ({ label, href }: { label: string; href: string }) => (
  <a href={href} target="_blank" rel="noreferrer" className="mt-1.5 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-bg-muted border border-border text-[11px] font-medium text-text-primary hover:bg-bg-card transition cursor-pointer">
    <ExternalLink className="w-3 h-3" />{label}
  </a>
)

const CodeBlock = ({ code, onCopy, isCopied }: { code: string; onCopy: () => void; isCopied: boolean }) => (
  <div className="relative">
    <pre className="bg-bg-muted rounded-xl px-3.5 py-3 font-mono text-[10px] text-text-primary overflow-x-auto whitespace-pre leading-relaxed">{code}</pre>
    <button onClick={onCopy} className="absolute top-2 right-2 p-1 rounded-md text-text-muted hover:text-text-primary transition cursor-pointer">
      {isCopied ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  </div>
)

// ─── Component ─────────────────────────────────────────────────────────────────

export default function SettingsView({ theme, onToggleTheme, isLoggedIn = false }: SettingsViewProps) {
  const [, setLoading] = useState(true)
  const [confirmReset, setConfirmReset] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [expandedClient, setExpandedClient] = useState<ClientId | null>('claude_ai')
  const [copiedId, setCopiedId] = useState<ClientId | null>(null)
  const [copiedKey, setCopiedKey] = useState(false)
  const [desktopOs, setDesktopOs] = useState<'mac' | 'win'>('mac')
  const [sessionUsage, setSessionUsage] = useState<{ used: number; limit: number; remaining: number } | null>(null)
  const [mcpKey, setMcpKey] = useState<string | null>(null)

  const mcpUrl = 'https://baljot07-fusion.hf.space/mcp/'
  const smitheryUrl = 'https://smithery.ai/server/@baljotchohan/fusion-vc'
  const proxyDownloadUrl = 'https://raw.githubusercontent.com/baljotchohan/fusion/main/scripts/mcp_proxy.py'
  const keyDisplay = mcpKey ?? 'fus_YOUR_KEY'

  const vsCodeJson = JSON.stringify({
    servers: { 'fusion-vc': { type: 'http', url: mcpUrl, headers: { Authorization: `Bearer ${keyDisplay}` } } },
  }, null, 2)

  const cursorJson = JSON.stringify({
    mcpServers: { 'fusion-vc': { url: mcpUrl, headers: { Authorization: `Bearer ${keyDisplay}` } } },
  }, null, 2)

  const claudeCodeCmd = `claude mcp add fusion-vc --transport http ${mcpUrl} --header "Authorization: Bearer ${keyDisplay}"`

  // Mac/Linux: mcp-remote via npx (npx path is clean on these platforms)
  const claudeDesktopMacJson = JSON.stringify({
    mcpServers: {
      'fusion-vc': {
        command: 'npx',
        args: ['-y', 'mcp-remote', mcpUrl, '--header', `Authorization: Bearer ${keyDisplay}`],
      },
    },
  }, null, 2)

  // Windows: Python proxy — npx resolves to "C:\Program Files\..." (space in path → cmd.exe error)
  const claudeDesktopWinJson = JSON.stringify({
    mcpServers: {
      'fusion-vc': {
        command: 'python',
        args: ['C:\\Users\\you\\mcp_proxy.py', keyDisplay],
      },
    },
  }, null, 2)

  const copyItem = async (id: ClientId, text: string) => {
    try { if (navigator.clipboard) await navigator.clipboard.writeText(text) } catch { /* denied */ }
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
    logActivity('mcp_config_copied', { type: id })
  }

  const copyKey = async () => {
    if (!mcpKey) return
    try { if (navigator.clipboard) await navigator.clipboard.writeText(mcpKey) } catch { /* denied */ }
    setCopiedKey(true)
    setTimeout(() => setCopiedKey(false), 2000)
  }

  useEffect(() => {
    apiFetch(`${API_BASE}/api/v1/system/settings`)
      .then(r => r.json())
      .then(() => {})
      .catch(() => {})
      .finally(() => setLoading(false))
    apiFetch(`${API_BASE}/api/v1/session-usage`).then(r => r.json()).then(d => setSessionUsage(d)).catch(() => {})
    if (isLoggedIn) {
      apiFetch(`${API_BASE}/api/v1/mcp-key`).then(r => r.json()).then(d => { if (d.key) setMcpKey(d.key) }).catch(() => {})
    }
  }, [isLoggedIn])

  const resetAllHistory = async () => {
    setResetting(true)
    try {
      logActivity('danger_zone_reset_all')
      const res = await apiFetch(`${API_BASE}/api/v1/system/reset-all`, { method: 'POST' })
      if (!res.ok) throw new Error(`${res.status}`)
      window.location.reload()
    } catch {
      setResetting(false)
      setConfirmReset(false)
    }
  }

  const isDark = theme === 'dark'
  const sectionCls = 'rounded-2xl bg-bg-card border border-border shadow-sm p-6'
  const labelCls = 'text-[10px] font-semibold uppercase tracking-wider text-text-muted'

  // ─── MCP client definitions ────────────────────────────────────────────────
  type Step = { text: string; cta?: { label: string; fn: () => void } }
  const clients: {
    id: ClientId
    name: string
    sub: string
    badge?: string
    logo: React.ReactNode
    copyText: string
    copyLabel: string
    steps: Step[]
    code?: string
    paths?: string[]
  }[] = [
    {
      id: 'claude_ai',
      name: 'Claude.ai',
      sub: 'Web · Desktop · Mobile — one setup, all devices',
      badge: '★ Best',
      logo: <AnthropicLogo />,
      copyText: mcpUrl,
      copyLabel: 'Copy URL',
      steps: [
        { text: 'Copy your FUSION server URL', cta: { label: 'Copy URL', fn: () => copyItem('claude_ai', mcpUrl) } },
        { text: 'Open Claude.ai → Settings → Integrations', cta: { label: 'Open Claude.ai', fn: () => { window.open('https://claude.ai/settings/integrations', '_blank', 'noopener'); logActivity('mcp_claude_ai_connect_click') } } },
        { text: 'Click "Add custom connector", paste the URL, connect and sign in. Automatically syncs to Claude Desktop and mobile.' },
      ],
    },
    {
      id: 'vscode',
      name: 'VS Code',
      sub: 'Requires VS Code 1.99+ with GitHub Copilot',
      logo: <VSCodeLogo />,
      copyText: vsCodeJson,
      copyLabel: 'Copy Config',
      steps: [
        { text: 'Copy the config below', cta: { label: 'Copy Config', fn: () => copyItem('vscode', vsCodeJson) } },
        { text: 'Create .vscode/mcp.json in your project root and paste' },
        { text: 'Restart VS Code — the server appears automatically' },
      ],
      code: vsCodeJson,
    },
    {
      id: 'cursor',
      name: 'Cursor',
      sub: 'Global or per-project config',
      logo: <CursorLogo />,
      copyText: cursorJson,
      copyLabel: 'Copy Config',
      steps: [
        { text: 'Copy the config below', cta: { label: 'Copy Config', fn: () => copyItem('cursor', cursorJson) } },
        { text: 'Open ~/.cursor/mcp.json (global) or .cursor/mcp.json (project) and paste' },
        { text: 'Reload Cursor — check Settings → MCP to confirm it appears' },
      ],
      code: cursorJson,
    },
    {
      id: 'claude_code',
      name: 'Claude Code',
      sub: 'Terminal — one command, any OS',
      logo: <TerminalLogo />,
      copyText: claudeCodeCmd,
      copyLabel: 'Copy Command',
      steps: [
        { text: 'Open a terminal' },
        { text: 'Copy and run the command below', cta: { label: 'Copy Command', fn: () => copyItem('claude_code', claudeCodeCmd) } },
      ],
      code: claudeCodeCmd,
    },
    {
      id: 'claude_desktop',
      name: 'Claude Desktop',
      sub: 'Windows · Mac · Linux',
      logo: <AnthropicLogo />,
      copyText: desktopOs === 'win' ? claudeDesktopWinJson : claudeDesktopMacJson,
      copyLabel: 'Copy Config',
      steps: [], // rendered via custom expand below
    },
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
        <div className="space-y-2">
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
              <div className="h-full rounded-full bg-slate-400 dark:bg-slate-500 transition-all duration-500" style={{ width: `${Math.min(100, (sessionUsage.used / 14) * 100)}%` }} />
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
              <p className="text-[11px] text-text-secondary mt-0.5">{isLoggedIn ? 'Unlimited' : '100 messages / hour'}</p>
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
        <p className="text-[11.5px] text-text-secondary mb-5">
          Use FUSION&apos;s 5-agent VC committee from any AI tool — with your own isolated deal history.
        </p>

        {!isLoggedIn ? (
          <div className="flex flex-col items-center justify-center gap-3 py-6 px-4 rounded-xl border border-border bg-bg-muted text-center">
            <div className="w-10 h-10 rounded-full bg-bg-subtle border border-border flex items-center justify-center">
              <Lock className="w-4 h-4 text-text-muted" />
            </div>
            <div>
              <p className="text-[13px] font-semibold text-text-primary">Sign in to access MCP</p>
              <p className="text-[11.5px] text-text-secondary mt-1 max-w-xs">MCP requires a personal API key tied to your account. Sign in to generate yours.</p>
            </div>
          </div>
        ) : (
          <>
            {/* Personal API key */}
            <div className="mb-4 flex items-center gap-3 px-3 py-2.5 rounded-xl border border-border bg-bg-muted">
              <Key className="w-3.5 h-3.5 text-text-muted shrink-0" />
              <code className="flex-1 text-[11px] font-mono text-text-primary truncate">{mcpKey ?? 'Loading…'}</code>
              {mcpKey && (
                <button onClick={copyKey} className="shrink-0 text-text-muted hover:text-text-primary transition cursor-pointer">
                  {copiedKey ? <Check className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              )}
            </div>

            {/* Accordion clients */}
            <div className="space-y-2">
              {clients.map(client => {
                const isOpen = expandedClient === client.id
                const isCopied = copiedId === client.id

                return (
                  <div key={client.id} className="rounded-xl border border-border overflow-hidden">

                    {/* Header row */}
                    <div className="flex items-center gap-3 px-3.5 py-2.5 bg-bg-card">
                      <div className="w-9 h-9 rounded-lg bg-bg-subtle border border-border/60 flex items-center justify-center shrink-0">
                        {client.logo}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="text-[13px] font-semibold text-text-primary">{client.name}</span>
                          {client.badge && (
                            <span className="text-[9px] font-bold text-amber-600 dark:text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded-full">{client.badge}</span>
                          )}
                        </div>
                        <p className="text-[10.5px] text-text-muted truncate">{client.sub}</p>
                      </div>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <button
                          onClick={() => { setExpandedClient(isOpen ? null : client.id); logActivity('mcp_setup_toggled', { client: client.id }) }}
                          className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg border text-[11px] font-medium transition cursor-pointer select-none ${isOpen ? 'border-border bg-bg-muted text-text-primary' : 'border-border text-text-secondary hover:text-text-primary hover:bg-bg-muted'}`}
                        >
                          Setup <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
                        </button>
                        <button
                          onClick={() => copyItem(client.id, client.copyText)}
                          className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-border text-[11px] font-medium text-text-secondary hover:text-text-primary hover:bg-bg-muted transition cursor-pointer select-none"
                        >
                          {isCopied ? <Check className="w-3 h-3 text-success" /> : <Copy className="w-3 h-3" />}
                          <span>{isCopied ? 'Copied' : client.copyLabel}</span>
                        </button>
                      </div>
                    </div>

                    {/* Expanded content */}
                    {isOpen && (
                      <div className="border-t border-border bg-bg-subtle px-4 py-4 space-y-4">

                        {client.id === 'claude_desktop' ? (
                          <>
                            {/* OS selector */}
                            <div className="flex gap-1 bg-bg-muted rounded-lg p-1">
                              {(['mac', 'win'] as const).map(os => (
                                <button key={os} onClick={() => setDesktopOs(os)}
                                  className={`flex-1 py-1.5 rounded-md text-[11px] font-medium transition cursor-pointer ${desktopOs === os ? 'bg-bg-card text-text-primary shadow-sm' : 'text-text-muted hover:text-text-primary'}`}>
                                  {os === 'mac' ? 'Mac / Linux' : 'Windows'}
                                </button>
                              ))}
                            </div>

                            {desktopOs === 'win' ? (
                              <div className="space-y-4">
                                <div className="space-y-3">
                                  <StepRow n={1} text="Download the Python proxy script (one file, no install needed)">
                                    <StepOpen label="Download mcp_proxy.py" href={proxyDownloadUrl} />
                                  </StepRow>
                                  <StepRow n={2} text={'Save it somewhere accessible, e.g. C:\\Users\\you\\mcp_proxy.py — note the full path'} />
                                  <StepRow n={3} text="Copy the config below, then update the path on line 4 to match where you saved it">
                                    <StepCopy label="Copy Config" onClick={() => copyItem('claude_desktop', claudeDesktopWinJson)} />
                                  </StepRow>
                                  <StepRow n={4} text="Open File → Settings → Developer → Edit Config, paste, save, fully quit and reopen Claude Desktop" />
                                </div>
                                <CodeBlock code={claudeDesktopWinJson} onCopy={() => copyItem('claude_desktop', claudeDesktopWinJson)} isCopied={isCopied} />
                                <p className="text-[10px] text-text-muted font-mono">Config: %APPDATA%\Claude\claude_desktop_config.json</p>
                              </div>
                            ) : (
                              <div className="space-y-4">
                                <div className="space-y-3">
                                  <StepRow n={1} text="Copy the config below (requires Node.js / npx)">
                                    <StepCopy label="Copy Config" onClick={() => copyItem('claude_desktop', claudeDesktopMacJson)} />
                                  </StepRow>
                                  <StepRow n={2} text="Open claude_desktop_config.json via File → Settings → Developer → Edit Config" />
                                  <StepRow n={3} text="Paste, save, then fully quit and reopen Claude Desktop" />
                                </div>
                                <CodeBlock code={claudeDesktopMacJson} onCopy={() => copyItem('claude_desktop', claudeDesktopMacJson)} isCopied={isCopied} />
                                <div className="space-y-0.5">
                                  <p className="text-[10px] text-text-muted font-mono">Mac   ~/Library/Application Support/Claude/claude_desktop_config.json</p>
                                  <p className="text-[10px] text-text-muted font-mono">Linux ~/.config/Claude/claude_desktop_config.json</p>
                                </div>
                              </div>
                            )}
                          </>
                        ) : (
                          <>
                            {/* Generic steps */}
                            <div className="space-y-3">
                              {client.steps.map((step, i) => (
                                <StepRow key={i} n={i + 1} text={step.text}>
                                  {step.cta && (
                                    step.cta.label.startsWith('Open')
                                      ? <StepOpen label={step.cta.label} href="#" />
                                      : <StepCopy label={step.cta.label} onClick={step.cta.fn} />
                                  )}
                                </StepRow>
                              ))}
                            </div>
                            {client.code && (
                              <CodeBlock code={client.code} onCopy={() => copyItem(client.id, client.copyText)} isCopied={isCopied} />
                            )}
                            {client.paths && (
                              <div className="space-y-0.5">
                                {client.paths.map((p, i) => <p key={i} className="text-[10px] text-text-muted font-mono">{p}</p>)}
                              </div>
                            )}
                          </>
                        )}

                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            <div className="mt-4 pt-3 border-t border-border">
              <a href={smitheryUrl} target="_blank" rel="noreferrer" onClick={() => logActivity('mcp_smithery_click')}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-text-secondary text-[11px] font-medium hover:text-text-primary transition">
                <ExternalLink className="w-3 h-3" />Also on Smithery
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
        <p className="text-[11.5px] text-text-secondary mb-4">Permanently delete every deal record, learned risk pattern, and chat message, and reset the live committee state. This cannot be undone.</p>
        {!confirmReset ? (
          <button onClick={() => setConfirmReset(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-danger/40 text-danger text-[12px] font-semibold hover:bg-danger-soft transition cursor-pointer">
            <Trash2 className="w-4 h-4" />Reset &amp; Clear All History
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
