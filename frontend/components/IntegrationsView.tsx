// components/IntegrationsView.tsx
import React, { useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plug, Copy, Check, ExternalLink, KeyRound, Mail, Lock, Unlock, Loader } from 'lucide-react'
import { API_BASE } from '@/lib/agents'

const SMITHERY_URL = 'https://smithery.ai/server/@baljotchohan/fusion-vc'
const LS_KEY = 'fusion_mcp_key'

/* ── copy button ── */
function CopyButton({ text, disabled }: { text: string; disabled?: boolean }) {
  const [ok, setOk] = useState(false)
  return (
    <button
      disabled={disabled}
      onClick={() => { navigator.clipboard?.writeText(text); setOk(true); setTimeout(() => setOk(false), 1400) }}
      className={`shrink-0 inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12px] font-semibold transition-all cursor-pointer
        ${disabled ? 'opacity-30 cursor-not-allowed' : ok ? 'bg-accent text-white' : 'bg-accent/10 text-accent hover:bg-accent/20'}`}
    >
      {ok ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
      {ok ? 'Copied!' : 'Copy'}
    </button>
  )
}

/* ── command row: label + code + copy ── */
function CmdRow({ label, code, locked }: { label: string; code: string; locked: boolean }) {
  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-[11px] font-semibold uppercase tracking-widest text-text-muted">{label}</p>
      <div className={`flex items-center gap-2 rounded-xl border bg-bg-subtle p-3 transition-opacity ${locked ? 'opacity-40 select-none' : ''}`}>
        <code className="flex-1 min-w-0 font-mono text-[11.5px] text-text-primary break-all leading-relaxed">{code}</code>
        <CopyButton text={code} disabled={locked} />
      </div>
    </div>
  )
}

/* ── client card ── */
function ClientCard({
  icon, name, desc, locked, children,
}: { icon: string; name: string; desc: string; locked: boolean; children: React.ReactNode }) {
  return (
    <div className={`rounded-2xl border bg-bg-card p-5 flex flex-col gap-4 transition-opacity ${locked ? 'opacity-60' : ''}`}>
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-bg-muted border border-border flex items-center justify-center shrink-0 text-xl">{icon}</div>
        <div>
          <p className="text-[13px] font-semibold text-text-primary">{name}</p>
          <p className="text-[11.5px] text-text-secondary">{desc}</p>
        </div>
        {locked && <Lock className="w-3.5 h-3.5 text-text-muted ml-auto" />}
      </div>
      {children}
    </div>
  )
}

/* ── VS Code icon ── */
function VSCodeIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" className="text-[#007ACC]">
      <path d="M23.15 2.587L18.21.21a1.494 1.494 0 0 0-1.705.29l-9.46 8.63-4.12-3.128a.999.999 0 0 0-1.276.057L.327 7.261A1 1 0 0 0 .326 8.74L3.899 12 .326 15.26a1 1 0 0 0 .001 1.479L1.65 17.94a.999.999 0 0 0 1.276.057l4.12-3.128 9.46 8.63a1.492 1.492 0 0 0 1.704.29l4.942-2.377A1.5 1.5 0 0 0 24 20.06V3.94a1.5 1.5 0 0 0-.85-1.353zm-5.146 14.861L10.826 12l7.178-5.448v10.896z" />
    </svg>
  )
}

/* ── main ── */
export function IntegrationsView() {
  const [mcpUrl, setMcpUrl] = useState(`${API_BASE}/mcp/`)
  const [serverOnline, setServerOnline] = useState<boolean | null>(null)
  const [tools, setTools] = useState<{ name: string; description: string }[]>([])

  const [key, setKey] = useState('')
  const [keyStatus, setKeyStatus] = useState<'idle' | 'checking' | 'valid' | 'invalid'>('idle')
  const unlocked = keyStatus === 'valid'

  // Load saved key from localStorage
  useEffect(() => {
    const saved = localStorage.getItem(LS_KEY)
    if (saved) { setKey(saved); setKeyStatus('valid') }
  }, [])

  // Fetch server info
  useEffect(() => {
    let alive = true
    fetch(`${API_BASE}/api/v1/system/mcp`)
      .then(r => r.json())
      .then(d => {
        if (!alive) return
        const http = (d.transports ?? []).find((t: { type: string }) => t.type === 'streamable-http')
        if (http?.url && !http.url.includes('localhost') && !http.url.includes('127.0.0.1')) setMcpUrl(http.url)
        if (Array.isArray(d.tools)) setTools(d.tools)
        setServerOnline(true)
      })
      .catch(() => { if (alive) setServerOnline(false) })
    return () => { alive = false }
  }, [])

  // Verify key against live MCP endpoint
  const verifyKey = useCallback(async (k: string) => {
    if (!k.trim()) return
    setKeyStatus('checking')
    try {
      const r = await fetch(mcpUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json, text/event-stream', Authorization: `Bearer ${k.trim()}` },
        body: JSON.stringify({ jsonrpc: '2.0', method: 'initialize', params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'fusion-ui', version: '1' } }, id: 1 }),
      })
      if (r.status === 401) {
        setKeyStatus('invalid')
        localStorage.removeItem(LS_KEY)
      } else {
        setKeyStatus('valid')
        localStorage.setItem(LS_KEY, k.trim())
      }
    } catch {
      setKeyStatus('invalid')
    }
  }, [mcpUrl])

  const handleKeySubmit = (e: React.FormEvent) => { e.preventDefault(); verifyKey(key) }
  const handleClear = () => { setKey(''); setKeyStatus('idle'); localStorage.removeItem(LS_KEY) }

  // Commands — populated with real key when unlocked
  const k = unlocked ? key.trim() : 'YOUR_KEY'
  const claudeDesktopCmd = `python3 -c "import json,os; p=(os.path.expanduser('~/Library/Application Support/Claude/claude_desktop_config.json') if os.name!='nt' else os.path.join(os.environ.get('APPDATA',''),'Claude','claude_desktop_config.json')); os.makedirs(os.path.dirname(p),exist_ok=True); d=json.load(open(p)) if os.path.exists(p) else {}; d.setdefault('mcpServers',{})['fusion-vc']={'command':'npx','args':['-y','mcp-remote','${mcpUrl}','--header','Authorization: Bearer ${k}']}; json.dump(d,open(p,'w'),indent=2); print('Done! Restart Claude Desktop.')"`
  const claudeCodeCmd = `claude mcp add fusion-vc --transport http ${mcpUrl} --header "Authorization: Bearer ${k}"`
  const windsurfConfig = JSON.stringify({ mcpServers: { 'fusion-vc': { command: 'npx', args: ['-y', 'mcp-remote', mcpUrl, '--header', `Authorization: Bearer ${k}`] } } }, null, 2)
  const cursorDeepLink = (() => { try { return `cursor://anysphere.cursor-deeplink/mcp/install?name=fusion-vc&config=${btoa(JSON.stringify({ command: 'npx', args: ['-y', 'mcp-remote', mcpUrl, '--header', `Authorization: Bearer ${k}`] }))}` } catch { return SMITHERY_URL } })()
  const vsCodeDeepLink = (() => { try { return `vscode:mcp/install?config=${encodeURIComponent(JSON.stringify({ name: 'fusion-vc', type: 'http', url: mcpUrl, headers: { Authorization: `Bearer ${k}` } }))}` } catch { return SMITHERY_URL } })()

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}
      className="space-y-5 max-w-2xl mx-auto py-4">

      {/* header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Plug className="w-5 h-5 text-accent" />
          <h1 className="text-xl font-bold text-text-primary">Connect your AI to FUSION</h1>
        </div>
        <p className="text-[12.5px] text-text-secondary">Use the full 5-agent investment committee inside Claude, Cursor, VS Code, or any AI tool.</p>
      </div>

      {/* server status */}
      <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-border bg-bg-card">
        <span className={`w-2 h-2 rounded-full shrink-0 ${serverOnline === false ? 'bg-text-muted' : 'bg-success animate-pulse'}`} />
        <span className={`text-[12px] font-medium ${serverOnline === false ? 'text-text-muted' : 'text-success'}`}>
          {serverOnline === false ? 'Server offline' : `Server live · ${tools.length || 5} tools ready`}
        </span>
        <code className="ml-auto text-[10.5px] font-mono text-text-muted truncate max-w-[240px]">{mcpUrl}</code>
      </div>

      {/* ── STEP 1: Enter key ── */}
      <div className={`rounded-2xl border p-5 transition-colors ${unlocked ? 'border-success/40 bg-success/5' : 'border-border bg-bg-card'}`}>
        <div className="flex items-center gap-2 mb-3">
          <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold ${unlocked ? 'bg-success text-white' : 'bg-accent/10 text-accent'}`}>1</div>
          <p className="text-[13px] font-semibold text-text-primary">Enter your access key</p>
          {unlocked && <span className="ml-auto flex items-center gap-1 text-[12px] font-semibold text-success"><Unlock className="w-3.5 h-3.5" /> Verified</span>}
        </div>

        <form onSubmit={handleKeySubmit} className="flex gap-2">
          <input
            type="password"
            value={key}
            onChange={e => { setKey(e.target.value); if (keyStatus !== 'idle') setKeyStatus('idle') }}
            placeholder="Paste your key here…"
            className="flex-1 min-w-0 rounded-xl border border-border bg-bg-subtle px-3 py-2.5 text-[13px] font-mono text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent transition"
          />
          {unlocked
            ? <button type="button" onClick={handleClear} className="shrink-0 px-4 py-2.5 rounded-xl border border-border text-[12px] text-text-secondary hover:border-danger/40 hover:text-danger transition cursor-pointer">Clear</button>
            : <button type="submit" disabled={!key.trim() || keyStatus === 'checking'}
                className="shrink-0 px-4 py-2.5 rounded-xl bg-accent text-white text-[12.5px] font-semibold hover:opacity-90 transition disabled:opacity-50 cursor-pointer flex items-center gap-1.5">
                {keyStatus === 'checking' ? <><Loader className="w-3.5 h-3.5 animate-spin" /> Verifying…</> : 'Verify key'}
              </button>
          }
        </form>

        <AnimatePresence>
          {keyStatus === 'invalid' && (
            <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className="mt-2 text-[12px] text-danger">
              Invalid key. <a href="mailto:jattbad328@gmail.com?subject=FUSION MCP Access Request" className="underline cursor-pointer">Request access →</a>
            </motion.p>
          )}
        </AnimatePresence>

        {!unlocked && keyStatus !== 'invalid' && (
          <p className="mt-2 text-[12px] text-text-muted">
            No key yet?{' '}
            <a href="mailto:jattbad328@gmail.com?subject=FUSION%20MCP%20Access%20Request&body=Hi%2C%20I%27d%20like%20to%20request%20an%20API%20key%20for%20FUSION%20MCP." className="text-accent underline cursor-pointer">
              Email us to get one →
            </a>
          </p>
        )}
      </div>

      {/* ── STEP 2: Pick your app ── */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold ${unlocked ? 'bg-accent/10 text-accent' : 'bg-bg-muted text-text-muted'}`}>2</div>
          <p className={`text-[13px] font-semibold ${unlocked ? 'text-text-primary' : 'text-text-muted'}`}>Pick your AI app and connect</p>
          {!unlocked && <span className="ml-2 flex items-center gap-1 text-[11px] text-text-muted"><Lock className="w-3 h-3" /> Enter key above to unlock</span>}
        </div>

        <div className="flex flex-col gap-3">

          {/* Claude Desktop */}
          <ClientCard icon="🖥" name="Claude Desktop" desc="Mac & Windows — paste one command in Terminal" locked={!unlocked}>
            <div className="flex flex-col gap-1.5">
              <p className="text-[11.5px] text-text-secondary">Open Terminal, paste this command, press Enter, then restart Claude Desktop:</p>
              <CmdRow label="" code={claudeDesktopCmd} locked={!unlocked} />
            </div>
          </ClientCard>

          {/* Claude Code */}
          <ClientCard icon="⚡" name="Claude Code" desc="Terminal — run once, works immediately" locked={!unlocked}>
            <CmdRow label="" code={claudeCodeCmd} locked={!unlocked} />
          </ClientCard>

          {/* Cursor */}
          <ClientCard icon="🖱" name="Cursor" desc="One click — opens Cursor and installs automatically" locked={!unlocked}>
            <a href={unlocked ? cursorDeepLink : undefined}
              className={`inline-flex items-center justify-center gap-2 w-full rounded-xl py-2.5 text-[12.5px] font-semibold transition
                ${unlocked ? 'bg-accent text-white hover:opacity-90 cursor-pointer no-underline' : 'bg-bg-muted text-text-muted cursor-not-allowed'}`}>
              {unlocked ? '⚡ Install in Cursor' : <><Lock className="w-3.5 h-3.5" /> Install in Cursor</>}
            </a>
          </ClientCard>

          {/* VS Code */}
          <ClientCard icon="" name="VS Code" desc="One click — opens VS Code 1.99+ and installs" locked={!unlocked}>
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 shrink-0"><VSCodeIcon /></div>
              <a href={unlocked ? vsCodeDeepLink : undefined}
                className={`flex-1 inline-flex items-center justify-center gap-2 rounded-xl py-2.5 text-[12.5px] font-semibold transition
                  ${unlocked ? 'bg-accent text-white hover:opacity-90 cursor-pointer no-underline' : 'bg-bg-muted text-text-muted cursor-not-allowed'}`}>
                {unlocked ? '⚡ Install in VS Code' : <><Lock className="w-3.5 h-3.5" /> Install in VS Code</>}
              </a>
            </div>
          </ClientCard>

          {/* Windsurf */}
          <ClientCard icon="🌊" name="Windsurf" desc="Paste into ~/.codeium/windsurf/mcp_config.json" locked={!unlocked}>
            <CmdRow label="" code={windsurfConfig} locked={!unlocked} />
          </ClientCard>

          {/* Smithery — always available, handles its own auth */}
          <div className="rounded-2xl border border-border bg-bg-card p-5 flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-bg-muted border border-border flex items-center justify-center shrink-0 text-xl">🔮</div>
            <div className="min-w-0 flex-1">
              <p className="text-[13px] font-semibold text-text-primary">Smithery</p>
              <p className="text-[11.5px] text-text-secondary">Claude Desktop · Windsurf · Zed · Cline · 10+ apps</p>
            </div>
            <a href={SMITHERY_URL} target="_blank" rel="noreferrer"
              className="shrink-0 inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-border text-[12px] font-semibold text-text-primary hover:border-accent/40 hover:text-accent transition no-underline cursor-pointer">
              <ExternalLink className="w-3.5 h-3.5" /> Open
            </a>
          </div>
        </div>
      </div>

      {/* tools */}
      {tools.length > 0 && (
        <div>
          <p className="text-[11px] font-bold uppercase tracking-widest text-text-muted mb-2">What your AI can do with FUSION</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {tools.map(t => (
              <div key={t.name} className="flex items-start gap-2 rounded-xl border border-border/60 bg-bg-subtle px-3 py-2">
                <Check className="w-3.5 h-3.5 text-accent shrink-0 mt-0.5" />
                <div className="min-w-0">
                  <code className="text-[11px] font-mono text-text-primary">{t.name}</code>
                  <p className="text-[10.5px] text-text-muted leading-snug mt-0.5 line-clamp-2">{t.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* get access card */}
      <div className="rounded-2xl border border-border bg-bg-card p-5 flex flex-col sm:flex-row gap-4 sm:items-center">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <KeyRound className="w-4 h-4 text-accent" />
            <p className="text-[13px] font-semibold text-text-primary">Need an access key?</p>
          </div>
          <p className="text-[12px] text-text-secondary">Free keys for hackathon judges and partners. Commercial plans available. We reply within a few hours.</p>
        </div>
        <a href="mailto:jattbad328@gmail.com?subject=FUSION%20MCP%20Access%20Request&body=Hi%2C%20I%27d%20like%20to%20request%20an%20API%20key%20for%20FUSION%20MCP."
          className="shrink-0 inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent text-white text-[13px] font-semibold hover:opacity-90 transition cursor-pointer no-underline">
          <Mail className="w-4 h-4" /> Request access
        </a>
      </div>

    </motion.div>
  )
}
