// components/IntegrationsView.tsx — Connect FUSION to any AI tool
// True one-click deep links for Cursor + VS Code; Smithery handles everything else.
import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Plug, Copy, Check, ExternalLink, Zap, KeyRound, Mail } from 'lucide-react'
import { API_BASE } from '@/lib/agents'

const SMITHERY_URL = 'https://smithery.ai/server/@baljotchohan/fusion-vc'

/* ── tiny helpers ───────────────────────────────────────────────────────────── */

function CopyButton({ text, className = '' }: { text: string; className?: string }) {
  const [ok, setOk] = useState(false)
  return (
    <button
      onClick={() => { navigator.clipboard?.writeText(text); setOk(true); setTimeout(() => setOk(false), 1400) }}
      className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12px] font-semibold cursor-pointer transition-colors ${ok ? 'bg-accent text-white' : 'bg-accent/10 text-accent hover:bg-accent/20'} ${className}`}
    >
      {ok ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
      {ok ? 'Copied!' : 'Copy'}
    </button>
  )
}

function CodeBox({ code }: { code: string }) {
  return (
    <div className="relative rounded-xl border border-border bg-bg-subtle">
      <pre className="overflow-x-auto p-3.5 pr-[72px] font-mono text-[11.5px] text-text-primary whitespace-pre-wrap break-all leading-relaxed">{code}</pre>
      <div className="absolute top-2.5 right-2.5"><CopyButton text={code} /></div>
    </div>
  )
}

/* ── section label ── */
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <div className="h-px flex-1 bg-border/60" />
      <span className="text-[10px] font-bold uppercase tracking-widest text-text-muted px-1 shrink-0">{children}</span>
      <div className="h-px flex-1 bg-border/60" />
    </div>
  )
}

/* ── deep-link install card ─────────────────────────────────────────────────── */
function DeepLinkCard({
  logo, name, tagline, deepLink, note,
}: {
  logo: React.ReactNode
  name: string
  tagline: string
  deepLink: string
  note?: string
}) {
  return (
    <div className="rounded-xl border border-border bg-bg-card p-4 flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-bg-muted border border-border flex items-center justify-center shrink-0">
          {logo}
        </div>
        <div className="min-w-0">
          <p className="text-[13px] font-semibold text-text-primary">{name}</p>
          <p className="text-[11.5px] text-text-secondary">{tagline}</p>
        </div>
      </div>
      <a
        href={deepLink}
        className="inline-flex items-center justify-center gap-2 w-full rounded-lg bg-accent text-white text-[12.5px] font-semibold py-2.5 hover:opacity-90 transition-opacity cursor-pointer no-underline"
      >
        <Zap className="w-3.5 h-3.5" />
        Install in {name}
      </a>
      {note && <p className="text-[10.5px] text-text-muted text-center">{note}</p>}
    </div>
  )
}

/* ── external-link card (Smithery) ──────────────────────────────────────────── */
function SmitheryCard() {
  return (
    <div className="rounded-xl border border-border bg-bg-card p-4 flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-bg-muted border border-border flex items-center justify-center shrink-0 text-[18px]">
          🔮
        </div>
        <div className="min-w-0">
          <p className="text-[13px] font-semibold text-text-primary">Smithery</p>
          <p className="text-[11.5px] text-text-secondary">Claude Desktop · Windsurf · Zed · Cline · 10+ more</p>
        </div>
      </div>
      <a
        href={SMITHERY_URL}
        target="_blank"
        rel="noreferrer"
        className="inline-flex items-center justify-center gap-2 w-full rounded-lg bg-bg-muted border border-border text-text-primary text-[12.5px] font-semibold py-2.5 hover:border-accent/40 hover:text-accent transition-colors cursor-pointer no-underline"
      >
        <ExternalLink className="w-3.5 h-3.5" />
        Open on Smithery
      </a>
      <p className="text-[10.5px] text-text-muted text-center">Opens smithery.ai → pick your app → one click → done</p>
    </div>
  )
}

/* ── script card (Claude Desktop auto-install) ──────────────────────────────── */
function ScriptCard({ url }: { url: string }) {
  // Patches claude_desktop_config.json automatically on Mac + Windows
  const script = `python3 -c "import json,os; p=(os.path.expanduser('~/Library/Application Support/Claude/claude_desktop_config.json') if os.name!='nt' else os.path.join(os.environ.get('APPDATA',''),'Claude','claude_desktop_config.json')); os.makedirs(os.path.dirname(p),exist_ok=True); d=json.load(open(p)) if os.path.exists(p) else {}; d.setdefault('mcpServers',{})['fusion-vc']={'command':'npx','args':['-y','mcp-remote','${url}','--header','Authorization: Bearer YOUR_KEY']}; json.dump(d,open(p,'w'),indent=2); print('FUSION added to Claude Desktop! Restart the app.')"`

  return (
    <div className="rounded-xl border border-border bg-bg-card p-4 flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-bg-muted border border-border flex items-center justify-center shrink-0 text-[18px]">
          🖥
        </div>
        <div className="min-w-0">
          <p className="text-[13px] font-semibold text-text-primary">Claude Desktop</p>
          <p className="text-[11.5px] text-text-secondary">Mac &amp; Windows — auto-patches your config</p>
        </div>
      </div>
      <ol className="space-y-1.5 list-none pl-0">
        {['Open Terminal (Mac: Cmd+Space → "Terminal")', 'Copy the command below, paste it, press Enter', 'Restart Claude Desktop — FUSION appears in tools'].map((s, i) => (
          <li key={i} className="flex gap-2.5">
            <span className="shrink-0 w-4 h-4 rounded-full bg-accent/10 text-accent text-[10px] font-bold flex items-center justify-center mt-px">{i + 1}</span>
            <span className="text-[12px] text-text-secondary">{s}</span>
          </li>
        ))}
      </ol>
      <CodeBox code={script} />
    </div>
  )
}

/* ── command card (Claude Code, Windsurf, etc.) ─────────────────────────────── */
function CommandCard({
  emoji, name, subtitle, command,
}: { emoji: string; name: string; subtitle: string; command: string }) {
  return (
    <div className="rounded-xl border border-border bg-bg-card p-4 flex flex-col gap-2.5">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-bg-muted border border-border flex items-center justify-center shrink-0 text-[16px]">{emoji}</div>
        <div className="min-w-0">
          <p className="text-[13px] font-semibold text-text-primary">{name}</p>
          <p className="text-[11.5px] text-text-secondary">{subtitle}</p>
        </div>
      </div>
      <CodeBox code={command} />
    </div>
  )
}

/* ── manual JSON card ────────────────────────────────────────────────────────── */
function ManualCard({ url }: { url: string }) {
  const json = JSON.stringify({ mcpServers: { 'fusion-vc': { type: 'http', url } } }, null, 2)
  return (
    <div className="rounded-xl border border-border bg-bg-card p-4 flex flex-col gap-2.5">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-bg-muted border border-border flex items-center justify-center shrink-0 text-[16px]">📋</div>
        <div className="min-w-0">
          <p className="text-[13px] font-semibold text-text-primary">Any MCP Client</p>
          <p className="text-[11.5px] text-text-secondary">Paste into your config file under "mcpServers"</p>
        </div>
      </div>
      <CodeBox code={json} />
    </div>
  )
}

/* ── tool chip ──────────────────────────────────────────────────────────────── */
function ToolChip({ name, description }: { name: string; description: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-border/60 bg-bg-subtle px-3 py-2">
      <Check className="w-3.5 h-3.5 text-accent shrink-0 mt-0.5" />
      <div className="min-w-0">
        <code className="text-[11px] font-mono text-text-primary">{name}</code>
        <p className="text-[10.5px] text-text-muted leading-snug mt-0.5 line-clamp-2">{description}</p>
      </div>
    </div>
  )
}

/* ── Cursor SVG logo ─────────────────────────────────────────────────────────── */
function CursorIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="text-text-primary">
      <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

/* ── VS Code SVG logo ────────────────────────────────────────────────────────── */
function VSCodeIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" className="text-[#007ACC]">
      <path d="M23.15 2.587L18.21.21a1.494 1.494 0 0 0-1.705.29l-9.46 8.63-4.12-3.128a.999.999 0 0 0-1.276.057L.327 7.261A1 1 0 0 0 .326 8.74L3.899 12 .326 15.26a1 1 0 0 0 .001 1.479L1.65 17.94a.999.999 0 0 0 1.276.057l4.12-3.128 9.46 8.63a1.492 1.492 0 0 0 1.704.29l4.942-2.377A1.5 1.5 0 0 0 24 20.06V3.94a1.5 1.5 0 0 0-.85-1.353zm-5.146 14.861L10.826 12l7.178-5.448v10.896z" />
    </svg>
  )
}

/* ── main component ─────────────────────────────────────────────────────────── */
export function IntegrationsView() {
  const [url, setUrl] = useState(`${API_BASE}/mcp`)
  const [online, setOnline] = useState<boolean | null>(null)
  const [toolCount, setToolCount] = useState(5)
  const [tools, setTools] = useState<{ name: string; description: string }[]>([])

  useEffect(() => {
    let alive = true
    fetch(`${API_BASE}/api/v1/system/mcp`)
      .then(r => r.json())
      .then(d => {
        if (!alive) return
        const http = (d.transports ?? []).find((t: { type: string }) => t.type === 'streamable-http')
        // Only use backend URL if it's a real public URL (not localhost fallback)
        if (http?.url && !http.url.includes('localhost') && !http.url.includes('127.0.0.1')) {
          setUrl(http.url)
        }
        if (typeof d.tool_count === 'number') setToolCount(d.tool_count)
        if (Array.isArray(d.tools)) setTools(d.tools)
        setOnline(true)
      })
      .catch(() => { if (alive) setOnline(false) })
    return () => { alive = false }
  }, [])

  // Cursor: base64-encoded JSON config using mcp-remote as HTTP bridge
  const cursorDeepLink = (() => {
    try {
      const cfg = JSON.stringify({ command: 'npx', args: ['-y', 'mcp-remote', url, '--header', 'Authorization: Bearer YOUR_KEY'] })
      return `cursor://anysphere.cursor-deeplink/mcp/install?name=fusion-vc&config=${btoa(cfg)}`
    } catch { return SMITHERY_URL }
  })()

  // VS Code: URL-encoded JSON config with auth header (native HTTP MCP, VS Code 1.99+)
  const vsCodeDeepLink = (() => {
    try {
      const cfg = JSON.stringify({ name: 'fusion-vc', type: 'http', url, headers: { Authorization: 'Bearer YOUR_KEY' } })
      return `vscode:mcp/install?config=${encodeURIComponent(cfg)}`
    } catch { return SMITHERY_URL }
  })()

  const claudeCodeCmd = `claude mcp add fusion-vc --transport http ${url} --header "Authorization: Bearer YOUR_KEY"`

  const windsurfConfig = JSON.stringify(
    { mcpServers: { 'fusion-vc': { command: 'npx', args: ['-y', 'mcp-remote', url, '--header', 'Authorization: Bearer YOUR_KEY'] } } },
    null, 2
  )

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-6 max-w-3xl mx-auto py-4"
    >
      {/* ── header ── */}
      <div>
        <div className="flex items-center gap-2 mb-1.5">
          <Plug className="w-5 h-5 text-accent" />
          <h1 className="text-2xl font-bold text-text-primary tracking-tight">Connect your AI</h1>
        </div>
        <p className="text-text-secondary text-[13px]">
          Use FUSION's full investment committee inside any AI tool — no browser, no login.
        </p>
      </div>

      {/* ── status + link ── */}
      <div className="rounded-2xl border border-border bg-bg-card p-5 flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full shrink-0 ${online === false ? 'bg-text-muted' : 'bg-success animate-pulse'}`} />
          <span className={`text-[12px] font-semibold ${online === false ? 'text-text-muted' : 'text-success'}`}>
            {online === false ? 'Offline — start the server' : `Live · ${toolCount} tools`}
          </span>
        </div>
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <code className="flex-1 min-w-0 rounded-lg border border-border bg-bg-subtle px-3 py-2 text-[12px] font-mono text-text-primary truncate">{url}</code>
          <CopyButton text={url} />
        </div>
      </div>

      {/* ── API key notice ── */}
      <div className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-4 flex gap-3">
        <KeyRound className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
        <div className="min-w-0">
          <p className="text-[13px] font-semibold text-text-primary mb-0.5">API key required</p>
          <p className="text-[12px] text-text-secondary leading-relaxed">
            FUSION MCP is key-protected — only authorised partners can connect.
            Each key allows <span className="font-semibold text-text-primary">30 tool calls / hour</span>.
            Replace <code className="font-mono text-amber-500 bg-amber-500/10 px-1 rounded">YOUR_KEY</code> in every
            snippet below with the key we issue you.
          </p>
        </div>
      </div>

      {/* ── one-click section ── */}
      <div>
        <SectionLabel>One click — app opens and installs automatically</SectionLabel>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <DeepLinkCard
            logo={<CursorIcon />}
            name="Cursor"
            tagline="Opens Cursor — confirm install"
            deepLink={cursorDeepLink}
            note="Requires Cursor to be installed"
          />
          <DeepLinkCard
            logo={<VSCodeIcon />}
            name="VS Code"
            tagline="Opens VS Code — confirm install"
            deepLink={vsCodeDeepLink}
            note="Requires VS Code 1.99+"
          />
          <SmitheryCard />
        </div>
      </div>

      {/* ── quick setup section ── */}
      <div>
        <SectionLabel>Quick setup — copy one thing, paste, done</SectionLabel>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <ScriptCard url={url} />
          <div className="flex flex-col gap-3">
            <CommandCard
              emoji="⚡"
              name="Claude Code"
              subtitle="Terminal — run once, works immediately"
              command={claudeCodeCmd}
            />
            <CommandCard
              emoji="🌊"
              name="Windsurf"
              subtitle="Paste into ~/.codeium/windsurf/mcp_config.json"
              command={windsurfConfig}
            />
          </div>
        </div>
      </div>

      {/* ── manual / any client ── */}
      <div>
        <SectionLabel>Any other MCP client</SectionLabel>
        <ManualCard url={url} />
      </div>

      {/* ── what FUSION can do ── */}
      {tools.length > 0 && (
        <div>
          <SectionLabel>What your AI can now do</SectionLabel>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {tools.map(t => <ToolChip key={t.name} name={t.name} description={t.description} />)}
          </div>
        </div>
      )}

      {/* ── request access ── */}
      <div className="rounded-2xl border border-border bg-bg-card p-5 flex flex-col sm:flex-row gap-5 sm:items-center">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <KeyRound className="w-4 h-4 text-accent" />
            <h2 className="text-[13px] font-bold text-text-primary">Get your API key</h2>
          </div>
          <p className="text-[12px] text-text-secondary leading-relaxed">
            Keys are issued by the FUSION team. Free keys available for hackathon evaluators,
            judges, and approved partners. Commercial access available on request.
          </p>
          <div className="mt-3 flex flex-col gap-1.5">
            <div className="flex items-center gap-2 text-[12px] text-text-secondary">
              <span className="text-success font-bold">✓</span> Free tier — 30 calls/hour
            </div>
            <div className="flex items-center gap-2 text-[12px] text-text-secondary">
              <span className="text-success font-bold">✓</span> Full access to all 5 partner agents
            </div>
            <div className="flex items-center gap-2 text-[12px] text-text-secondary">
              <span className="text-success font-bold">✓</span> Works with Claude Desktop, Cursor, VS Code, Windsurf &amp; more
            </div>
          </div>
        </div>
        <a
          href="mailto:jattbad328@gmail.com?subject=FUSION%20MCP%20Access%20Request&body=Hi%2C%20I%27d%20like%20to%20request%20an%20API%20key%20for%20FUSION%20MCP."
          className="shrink-0 inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent text-white text-[13px] font-semibold hover:opacity-90 transition cursor-pointer no-underline"
        >
          <Mail className="w-4 h-4" />
          Request access
        </a>
      </div>

      {/* ── other tools note ── */}
      <div className="rounded-2xl border border-border/70 bg-bg-subtle p-5">
        <h2 className="text-[13px] font-bold text-text-primary mb-1.5">Slack, Notion, Google Drive &amp; more</h2>
        <p className="text-[12.5px] text-text-secondary leading-relaxed">
          Those tools publish their own MCP servers. Add them to the{' '}
          <span className="font-semibold text-text-primary">same AI assistant</span> you connected FUSION to — your
          AI can then use FUSION and your workspace tools together in one conversation.
        </p>
      </div>
    </motion.div>
  )
}
