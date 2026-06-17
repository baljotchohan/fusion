// components/IntegrationsView.tsx — "Connect FUSION to your AI" (MCP, non-technical)
// + the decorative workspace integrations grid below.
import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  HardDrive, type LucideIcon, Plug, Copy, Check, Sparkles, Link2, Terminal, FileCode2,
} from 'lucide-react'
import { API_BASE } from '@/lib/agents'

/* ──────────────────────────────────────────────────────────────
   Copy-to-clipboard button (mirrors the DocsView pattern)
   ────────────────────────────────────────────────────────────── */
function CopyButton({ text, label = 'Copy', className = '' }: { text: string; label?: string; className?: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard?.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1400)
  }
  return (
    <button
      onClick={copy}
      className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12px] font-semibold transition-colors cursor-pointer ${
        copied ? 'bg-accent text-white' : 'bg-accent/10 text-accent hover:bg-accent/20'
      } ${className}`}
      aria-label={label}
    >
      {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
      {copied ? 'Copied!' : label}
    </button>
  )
}

/* A monospace code/snippet box with its own copy button */
function Snippet({ code }: { code: string }) {
  return (
    <div className="relative rounded-xl border border-border bg-bg-subtle font-mono text-[11.5px] text-text-primary">
      <pre className="overflow-x-auto p-3.5 pr-20 whitespace-pre-wrap break-all leading-relaxed">{code}</pre>
      <div className="absolute top-2.5 right-2.5">
        <CopyButton text={code} />
      </div>
    </div>
  )
}

/* ──────────────────────────────────────────────────────────────
   Setup recipes per client. {URL} is replaced with the live endpoint.
   ────────────────────────────────────────────────────────────── */
type ClientId = 'claude-desktop' | 'cursor' | 'claude-code' | 'config'

const CLIENTS: { id: ClientId; label: string; Icon: LucideIcon }[] = [
  { id: 'claude-desktop', label: 'Claude Desktop (1-Click)', Icon: Sparkles },
  { id: 'cursor', label: 'Cursor (SSE)', Icon: Link2 },
  { id: 'claude-code', label: 'Claude Code', Icon: Terminal },
  { id: 'config', label: 'Manual JSON', Icon: FileCode2 },
]

function recipe(id: ClientId, url: string): { steps: string[]; code?: string } {
  switch (id) {
    case 'claude-desktop':
      return {
        steps: [
          'Open your terminal app.',
          'Copy and paste the command below, then press Enter:',
          'FUSION is now added to your Claude Desktop config. Restart Claude Desktop to use it! 🚀',
        ],
        code: `python -c "import json, os; p = os.path.expanduser('~/Library/Application Support/Claude/claude_desktop_config.json') if os.name != 'nt' else os.path.join(os.environ.get('APPDATA', ''), 'Claude', 'claude_desktop_config.json'); os.makedirs(os.path.dirname(p), exist_ok=True); d = json.load(open(p)) if os.path.exists(p) else {}; d.setdefault('mcpServers', {})['fusion'] = {'type': 'http', 'url': '${url}'}; json.dump(d, open(p, 'w'), indent=2); print('✓ FUSION MCP server added to Claude Desktop!')"`,
      }
    case 'cursor':
      return {
        steps: [
          'Open Cursor Settings -> Features -> MCP.',
          'Click "+ Add New MCP Server".',
          'Name: "fusion", Type: "SSE", URL: click "Copy link" below and paste it in.',
          'Click Save and restart Cursor to activate. ✅',
        ],
      }
    case 'claude-code':
      return {
        steps: [
          'Open your terminal.',
          'Run this command to register FUSION in Claude Code:',
          'FUSION is now registered. Run /mcp inside Claude Code to verify connection. 🚀',
        ],
        code: `claude mcp add --transport http fusion ${url}`,
      }
    case 'config':
      return {
        steps: [
          'Open your MCP config file (e.g. claude_desktop_config.json).',
          'Paste this JSON block into your "mcpServers" object:',
        ],
        code: `{
  "mcpServers": {
    "fusion": {
      "type": "http",
      "url": "${url}"
    }
  }
}`,
      }
  }
}

/* ──────────────────────────────────────────────────────────────
   The MCP connect card
   ────────────────────────────────────────────────────────────── */
function McpConnectCard() {
  const [url, setUrl] = useState(`${API_BASE}/mcp`)
  const [online, setOnline] = useState<boolean | null>(null)
  const [toolCount, setToolCount] = useState<number>(5)
  const [tools, setTools] = useState<{ name: string; description: string }[]>([])
  const [active, setActive] = useState<ClientId>('claude-desktop')

  useEffect(() => {
    let cancelled = false
    fetch(`${API_BASE}/api/v1/system/mcp`)
      .then(r => r.json())
      .then(d => {
        if (cancelled) return
        const http = (d.transports || []).find((t: { type: string }) => t.type === 'streamable-http')
        if (http?.url) setUrl(http.url)
        if (typeof d.tool_count === 'number') setToolCount(d.tool_count)
        if (Array.isArray(d.tools)) setTools(d.tools.map((t: { name: string; description: string }) => ({ name: t.name, description: t.description })))
        setOnline(true)
      })
      .catch(() => { if (!cancelled) setOnline(false) })
    return () => { cancelled = true }
  }, [])

  const r = recipe(active, url)

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="rounded-2xl bg-bg-card border border-border/80 shadow-sm overflow-hidden"
    >
      {/* Header band */}
      <div className="p-5 sm:p-6 border-b border-border/60 bg-accent/[0.04]">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-accent" />
            </div>
            <div>
              <h2 className="text-[17px] font-bold text-text-primary tracking-tight">Connect FUSION to your AI</h2>
              <p className="text-[12.5px] text-text-secondary mt-0.5">
                Use the full investment committee inside Claude, Cursor, or any AI tool — no coding.
              </p>
            </div>
          </div>
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10.5px] font-semibold ${
            online === false
              ? 'bg-bg-muted text-text-muted'
              : 'bg-success-soft text-success'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${online === false ? 'bg-text-muted' : 'bg-success animate-pulse'}`} />
            {online === false ? 'Offline — start the server' : `Live · ${toolCount} tools`}
          </span>
        </div>
      </div>

      <div className="p-5 sm:p-6 space-y-5">
        {/* The one thing they need: the link */}
        <div>
          <label className="text-[10.5px] font-bold uppercase tracking-wider text-text-muted">Your FUSION link</label>
          <div className="mt-1.5 flex items-center gap-2 flex-wrap">
            <code className="flex-1 min-w-[200px] rounded-xl border border-border bg-bg-subtle px-3.5 py-2.5 text-[13px] font-mono text-text-primary break-all">
              {url}
            </code>
            <CopyButton text={url} label="Copy link" className="px-4 py-2.5" />
          </div>
        </div>

        {/* Client picker */}
        <div className="flex flex-wrap gap-1.5">
          {CLIENTS.map(c => {
            const on = active === c.id
            return (
              <button
                key={c.id}
                onClick={() => setActive(c.id)}
                className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-[12px] font-semibold transition-colors cursor-pointer ${
                  on ? 'border-accent bg-accent/10 text-accent' : 'border-border bg-bg-card text-text-secondary hover:border-border-strong'
                }`}
              >
                <c.Icon className="w-3.5 h-3.5" />
                {c.label}
              </button>
            )
          })}
        </div>

        {/* Steps for the chosen client */}
        <ol className="space-y-2.5">
          {r.steps.map((step, i) => (
            <li key={i} className="flex gap-3">
              <span className="shrink-0 w-5 h-5 rounded-full bg-accent/10 text-accent text-[11px] font-bold flex items-center justify-center mt-px">
                {i + 1}
              </span>
              <span className="text-[12.5px] text-text-secondary leading-relaxed">{step}</span>
            </li>
          ))}
        </ol>
        {r.code && <Snippet code={r.code} />}

        {/* What it can do */}
        {tools.length > 0 && (
          <div className="pt-4 border-t border-border/60">
            <p className="text-[10.5px] font-bold uppercase tracking-wider text-text-muted mb-2.5">What your AI can now do</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {tools.map(t => (
                <div key={t.name} className="flex items-start gap-2 rounded-lg border border-border/60 bg-bg-subtle px-3 py-2">
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
      </div>
    </motion.div>
  )
}

export function IntegrationsView() {
  return (
    <div className="space-y-6 max-w-5xl mx-auto py-4">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1.5">
          <Plug className="w-5 h-5 text-accent" />
          <h1 className="text-2xl font-bold text-text-primary tracking-tight">Integrations</h1>
        </div>
        <p className="text-text-secondary text-[13px]">
          Connect the FUSION investment committee to your AI assistant in seconds.
        </p>
      </div>

      {/* The real integration: MCP */}
      <McpConnectCard />

      {/* Honest note about other tools */}
      <div className="rounded-2xl border border-border/70 bg-bg-subtle p-5">
        <h2 className="text-[13px] font-bold text-text-primary mb-1.5">Slack, Google Drive, Notion & more</h2>
        <p className="text-[12.5px] text-text-secondary leading-relaxed">
          Those tools already publish their own MCP connectors. Add them to the{' '}
          <span className="font-semibold text-text-primary">same AI assistant</span> you connected FUSION to,
          and your assistant can use FUSION and your workspace tools together — no separate setup here.
        </p>
      </div>
    </div>
  )
}
