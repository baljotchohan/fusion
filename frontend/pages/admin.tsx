import { useEffect, useState, useRef, useCallback } from 'react'
import { useRouter } from 'next/router'
import { motion, AnimatePresence } from 'framer-motion'
import { getDatabase, ref as dbRef, get } from 'firebase/database'
import { auth, signInAsGuest } from '@/lib/firebase'
import {
  Shield, LayoutDashboard, Users, Activity, Database, GitBranch,
  BarChart2, Zap, AlertTriangle, AlertCircle, CheckCircle,
  X, Copy, RefreshCw, Trash2, ChevronDown, ChevronRight, Brain,
  MessageSquare, Terminal, Eye, Cpu,
  FileText, Loader2,
} from 'lucide-react'

// ── Types ─────────────────────────────────────────────────────────────────────

type Severity = 'critical' | 'warning' | 'info'
type Alert = { id: string; rule: string; message: string; severity: Severity; timestamp: string; resolved: boolean }
type Section = 'overview' | 'users' | 'feed' | 'vault' | 'build' | 'agents' | 'patterns' | 'controls' | 'sentinel'

interface AgentProfile { findings_logged: number; incidents: string[]; last_active: string | null }
interface McpEntry { tool: string; timestamp: string; success: boolean; latency_ms: number }
interface Session { session_id: string; title: string; message_count: number; timestamp: string | null; messages: { role: string; content: string; timestamp?: string }[] }
interface DealRecord { incident_id: string; company: string; verdict: string; findings: number; created_at: string | null; final_decision: string | null; timeline: { agent: string; finding: string; severity?: number; timestamp: string }[] }
interface UserData { uid: string; email?: string | null; display_name?: string | null; photo_url?: string | null; ip?: string | null; device?: string | null; source?: string; deal_count: number; session_count: number; finding_count: number; pattern_count: number; last_active: string | null; agent_profiles: Record<string, AgentProfile>; incidents: DealRecord[]; sessions: Session[]; patterns: Record<string, { detection: string; defense: string; success_rate: number; learned_at: string }[]>; mcp_log: McpEntry[]; mcp_key: string | null; mcp_key_created: string | null }
interface SystemStatus { status: string; mock_mode: boolean; simulation_running: boolean; active_incident_id: string | null; memory_incidents: number; agent_statuses: Record<string, string> }
interface MemStats { total_incidents: number; total_findings: number; learned_patterns: Record<string, number>; agent_profiles: Record<string, AgentProfile> }
interface GitCommit { hash: string; full_hash: string; subject: string; author: string; relative: string; date: string | null }
interface VercelDep { uid: string; state: 'READY' | 'ERROR' | 'BUILDING' | 'QUEUED'; createdAt: number; readyAt?: number; url?: string; meta?: { githubCommitRef?: string; githubCommitSha?: string; githubCommitMessage?: string } }
interface WsEvent { agent?: string; status?: string; current_action?: string; output?: Record<string, unknown>; timestamp?: string; debate_type?: string; uid?: string }
interface SystemSnapshot { status: SystemStatus | null; wsEvents: WsEvent[]; lastWsEventAt: number; wsConnected: boolean; vercelDeps: VercelDep[]; memStats: MemStats | null; statusFailCount: number; users: UserData[] }

// ── Constants ─────────────────────────────────────────────────────────────────

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws'

const AGENT_LABEL: Record<string, string> = {
  managing_partner: 'Managing Partner',
  financial_partner: 'Financial Partner',
  legal_partner: 'Legal Partner',
  technical_partner: 'Technical Partner',
  market_partner: 'Market Partner',
}
const AGENT_COLOR: Record<string, string> = {
  managing_partner: 'text-accent',
  financial_partner: 'text-emerald-400',
  legal_partner: 'text-purple-400',
  technical_partner: 'text-blue-400',
  market_partner: 'text-amber-400',
}
const AGENT_BG: Record<string, string> = {
  managing_partner: 'bg-accent/10',
  financial_partner: 'bg-emerald-400/10',
  legal_partner: 'bg-purple-400/10',
  technical_partner: 'bg-blue-400/10',
  market_partner: 'bg-amber-400/10',
}

const NAV_ITEMS: { id: Section; label: string; Icon: React.ElementType }[] = [
  { id: 'overview', label: 'Overview', Icon: LayoutDashboard },
  { id: 'users', label: 'Users', Icon: Users },
  { id: 'feed', label: 'Live Feed', Icon: Activity },
  { id: 'vault', label: 'Deal Vault', Icon: Database },
  { id: 'build', label: 'Build Log', Icon: GitBranch },
  { id: 'agents', label: 'Agent Performance', Icon: BarChart2 },
  { id: 'patterns', label: 'Memory & Patterns', Icon: Brain },
  { id: 'controls', label: 'System Controls', Icon: Terminal },
  { id: 'sentinel', label: 'SENTINEL', Icon: Eye },
]

// ── Helpers ───────────────────────────────────────────────────────────────────

function rel(ts: string | null | undefined): string {
  if (!ts) return 'Never'
  const diff = Date.now() - new Date(ts).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

function fmtDate(ts: string | null | undefined): string {
  if (!ts) return '—'
  try { return new Date(ts).toLocaleString() } catch { return ts }
}

async function apiFetch<T>(path: string): Promise<T | null> {
  try {
    const r = await fetch(`${API}${path}`)
    if (!r.ok) return null
    return r.json()
  } catch { return null }
}

async function apiPost(path: string, body?: unknown): Promise<unknown> {
  try {
    const r = await fetch(`${API}${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined })
    return r.json()
  } catch (e) { return { error: String(e) } }
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const v = verdict?.toUpperCase()
  const cls = v === 'INVEST' ? 'bg-success/10 text-success border-success/20'
    : v === 'CONDITIONAL' ? 'bg-warning/10 text-warning border-warning/20'
    : v === 'PENDING' ? 'bg-bg-muted text-text-muted border-border'
    : 'bg-danger/10 text-danger border-danger/20'
  return <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold border ${cls}`}>{v || 'PENDING'}</span>
}

function AgentDot({ status }: { status: string }) {
  const cls = status === 'working' ? 'bg-warning animate-pulse' : status === 'done' ? 'bg-success' : status === 'alert' ? 'bg-danger' : 'bg-text-muted/30'
  return <span className={`inline-block w-2 h-2 rounded-full ${cls}`} />
}

function CopyBtn({ text }: { text: string }) {
  const [done, setDone] = useState(false)
  return (
    <button onClick={() => { navigator.clipboard.writeText(text); setDone(true); setTimeout(() => setDone(false), 1500) }}
      className="p-1 rounded hover:bg-bg-muted text-text-muted hover:text-text-primary transition">
      {done ? <CheckCircle className="w-3.5 h-3.5 text-success" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  )
}

function SectionHead({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-5">
      <h2 className="text-base font-semibold text-text-primary">{title}</h2>
      {subtitle && <p className="text-xs text-text-muted mt-0.5">{subtitle}</p>}
    </div>
  )
}

// ── SENTINEL rules ────────────────────────────────────────────────────────────

function runSentinel(snap: SystemSnapshot, prev: Alert[]): Alert[] {
  const make = (id: string, rule: string, message: string, severity: Severity): Alert =>
    ({ id, rule, message, severity, timestamp: new Date().toISOString(), resolved: false })

  const fired: Alert[] = []

  // 1 Deal Stall
  if (snap.status?.simulation_running && snap.lastWsEventAt > 0) {
    const idle = (Date.now() - snap.lastWsEventAt) / 1000
    if (idle > 90) fired.push(make('deal-stall', 'Deal Stall', `Active deal idle for ${Math.round(idle)}s (>90s).`, 'critical'))
  }
  // 2 Agent Death
  const dead = snap.wsEvents.slice(0, 100).find(e => e.status === 'alert')
  if (dead) fired.push(make('agent-death', 'Agent Death', `Agent "${dead.agent}" reported a fatal error.`, 'critical'))
  // 3 Backend unreachable
  if (snap.statusFailCount >= 3) fired.push(make('backend-down', 'Backend Unreachable', `API health check failed ${snap.statusFailCount}× consecutively.`, 'critical'))
  // 4 All agents silent
  if (snap.status?.simulation_running && snap.lastWsEventAt > 0) {
    const idle = (Date.now() - snap.lastWsEventAt) / 1000
    if (idle > 60 && idle <= 90) fired.push(make('agents-silent', 'All Agents Silent', `No agent events for ${Math.round(idle)}s while deal is running.`, 'warning'))
  }
  // 5 Vercel build failed
  const failedDep = snap.vercelDeps.find(d => d.state === 'ERROR')
  if (failedDep) fired.push(make('vercel-fail', 'Vercel Build Failed', `Deployment ${failedDep.uid?.slice(0, 8)} failed on ${failedDep.meta?.githubCommitRef || 'unknown branch'}.`, 'warning'))
  // 6 MCP error rate
  const oneHrAgo = Date.now() - 3600000
  const recentMcp = snap.users.flatMap(u => u.mcp_log || []).filter(e => new Date(e.timestamp).getTime() > oneHrAgo)
  if (recentMcp.length >= 5 && recentMcp.filter(e => !e.success).length / recentMcp.length > 0.5)
    fired.push(make('mcp-errors', 'MCP Error Rate High', `>50% of ${recentMcp.length} MCP calls in the last hour failed.`, 'warning'))
  // 7 LLM degraded
  if (snap.wsEvents.slice(0, 50).some(e => JSON.stringify(e).toLowerCase().includes('mock-llm') || JSON.stringify(e).toLowerCase().includes('fallback')))
    fired.push(make('llm-degraded', 'LLM Degraded', 'System is using mock-LLM fallback — real LLM provider may be down.', 'warning'))
  // 8 Long-running deal (>5min)
  if (snap.status?.simulation_running && snap.lastWsEventAt > 0 && (Date.now() - snap.lastWsEventAt) / 1000 > 300)
    fired.push(make('long-deal', 'Long-Running Deal', 'Active deal has been running for more than 5 minutes.', 'info'))
  // 9 WS disconnected
  if (!snap.wsConnected) fired.push(make('ws-down', 'Feed Disconnected', 'Admin WebSocket is disconnected — live events paused.', 'info'))
  // 10 Memory bloat
  if (snap.memStats && (snap.memStats.total_incidents > 100 || snap.memStats.total_findings > 1000))
    fired.push(make('mem-bloat', 'Memory Bloat', `Memory graph: ${snap.memStats.total_incidents} incidents, ${snap.memStats.total_findings} findings.`, 'info'))
  // 11 Pattern rising (≥5 hits across users)
  const allPatternCounts: Record<string, number> = {}
  for (const u of snap.users) for (const [kw, entries] of Object.entries(u.patterns || {})) allPatternCounts[kw] = (allPatternCounts[kw] || 0) + entries.length
  const rising = Object.entries(allPatternCounts).find(([, c]) => c >= 5)
  if (rising) fired.push(make('pattern-rising', 'Pattern Rising', `Risk pattern "${rising[0]}" triggered ${rising[1]}× across users.`, 'info'))
  // 12 No WS connection yet
  if (!snap.wsConnected && snap.statusFailCount === 0 && !snap.status?.simulation_running) {
    // don't fire ws-down if we're just starting up — already covered above
  }

  // merge: keep existing resolved state if rule already present, add new ones
  const existing = new Map(prev.map(a => [a.id, a]))
  const firedIds = new Set(fired.map(a => a.id))
  const result: Alert[] = []
  for (const a of fired) {
    const old = existing.get(a.id)
    result.push(old ? { ...a, resolved: old.resolved } : a)
  }
  // carry over manually-resolved alerts for rules no longer firing
  for (const a of prev) {
    if (!firedIds.has(a.id) && a.resolved) result.push(a)
  }
  return result
}

// ── Key Gate ──────────────────────────────────────────────────────────────────

function KeyGate({ onUnlock }: { onUnlock: () => void }) {
  const [val, setVal] = useState('')
  const [err, setErr] = useState(false)
  const inp = useRef<HTMLInputElement>(null)

  useEffect(() => { inp.current?.focus() }, [])

  const attempt = () => {
    if (val === 'IMTHECEOBITCH') {
      sessionStorage.setItem('admin_unlocked', '1')
      onUnlock()
    } else {
      setErr(true)
      setVal('')
      setTimeout(() => setErr(false), 1500)
    }
  }

  return (
    <div className="fixed inset-0 bg-bg-base flex items-center justify-center z-50">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
        className="bg-bg-card border border-border rounded-2xl p-8 w-[380px] shadow-2xl">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center">
            <Shield className="w-5 h-5 text-accent" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-text-primary">FUSION Admin</h1>
            <p className="text-[11px] text-text-muted">God-mode control panel</p>
          </div>
        </div>
        <p className="text-xs text-text-secondary mb-3">Enter admin access key</p>
        <input ref={inp} type="password" value={val} onChange={e => setVal(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && attempt()} placeholder="Access key"
          className={`w-full px-3 py-2.5 rounded-lg bg-bg-subtle border text-text-primary text-sm mb-3 outline-none focus:border-accent transition font-mono tracking-widest ${err ? 'border-danger' : 'border-border'}`} />
        {err && <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-xs text-danger mb-3">Incorrect key.</motion.p>}
        <button onClick={attempt} className="w-full py-2.5 rounded-lg bg-accent text-white text-sm font-semibold hover:bg-accent/90 active:scale-95 transition">
          Unlock
        </button>
      </motion.div>
    </div>
  )
}

// ── SENTINEL Strip ────────────────────────────────────────────────────────────

function SentinelStrip({ alerts, onJump }: { alerts: Alert[]; onJump: () => void }) {
  const active = alerts.filter(a => !a.resolved)
  const crit = active.filter(a => a.severity === 'critical').length
  const warn = active.filter(a => a.severity === 'warning').length
  const info = active.filter(a => a.severity === 'info').length
  if (active.length === 0) return null
  return (
    <button onClick={onJump}
      className="w-full flex items-center gap-3 px-4 py-2 bg-bg-subtle border-b border-border text-xs hover:bg-bg-muted transition text-left">
      <Eye className="w-3.5 h-3.5 text-text-muted shrink-0" />
      <span className="text-text-muted">SENTINEL</span>
      {crit > 0 && <span className="px-2 py-0.5 rounded-full bg-danger/15 text-danger font-bold">{crit} critical</span>}
      {warn > 0 && <span className="px-2 py-0.5 rounded-full bg-warning/15 text-warning font-bold">{warn} warning</span>}
      {info > 0 && <span className="px-2 py-0.5 rounded-full bg-accent/15 text-accent font-bold">{info} info</span>}
      <span className="ml-auto text-text-muted">View all →</span>
    </button>
  )
}

// ── Overview Section ──────────────────────────────────────────────────────────

function OverviewSection({ status, users, wsConnected }: { status: SystemStatus | null; users: UserData[]; memStats: MemStats | null; wsConnected: boolean }) {
  const totalDeals = users.reduce((s, u) => s + u.deal_count, 0)
  const totalFindings = users.reduce((s, u) => s + u.finding_count, 0)
  const totalPatterns = users.reduce((s, u) => s + u.pattern_count, 0)
  const totalSessions = users.reduce((s, u) => s + u.session_count, 0)
  const stats = [
    { label: 'Users', value: users.length, Icon: Users },
    { label: 'Total Deals', value: totalDeals, Icon: Database },
    { label: 'Findings', value: totalFindings, Icon: FileText },
    { label: 'Patterns', value: totalPatterns, Icon: Brain },
    { label: 'Sessions', value: totalSessions, Icon: MessageSquare },
  ]

  const agentStatuses = status?.agent_statuses || {}
  const AGENTS = ['managing_partner', 'financial_partner', 'legal_partner', 'technical_partner', 'market_partner']

  return (
    <div>
      <SectionHead title="Overview" subtitle="System-wide snapshot, refreshed every 5s" />

      {/* Stat cards */}
      <div className="grid grid-cols-5 gap-3 mb-6">
        {stats.map(s => (
          <div key={s.label} className="bg-bg-card border border-border rounded-xl p-4">
            <s.Icon className="w-4 h-4 text-text-muted mb-2" />
            <p className="text-2xl font-bold text-text-primary">{s.value}</p>
            <p className="text-[11px] text-text-muted mt-0.5">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* System status */}
        <div className="bg-bg-card border border-border rounded-xl p-4">
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs font-bold text-text-muted uppercase tracking-wider">System Status</p>
            <div className={`flex items-center gap-1.5 text-[11px] ${wsConnected ? 'text-success' : 'text-danger'}`}>
              <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-success animate-pulse' : 'bg-danger'}`} />
              {wsConnected ? 'Live' : 'Disconnected'}
            </div>
          </div>
          <div className="space-y-2">
            <Row label="Backend" value={status ? '✓ Healthy' : '— Unreachable'} cls={status ? 'text-success' : 'text-danger'} />
            <Row label="Mode" value={status?.mock_mode ? 'Mock (deterministic)' : 'Real Band'} />
            <Row label="Simulation" value={status?.simulation_running ? '● RUNNING' : '○ Idle'} cls={status?.simulation_running ? 'text-warning' : 'text-text-secondary'} />
            {status?.active_incident_id && <Row label="Active Deal" value={status.active_incident_id} mono />}
            <Row label="Incidents in memory" value={String(status?.memory_incidents ?? '—')} />
          </div>
        </div>

        {/* Agent status grid */}
        <div className="bg-bg-card border border-border rounded-xl p-4">
          <p className="text-xs font-bold text-text-muted uppercase tracking-wider mb-4">Partner Agents</p>
          <div className="space-y-2">
            {AGENTS.map(a => (
              <div key={a} className="flex items-center gap-2">
                <AgentDot status={agentStatuses[a] || 'idle'} />
                <span className={`text-[13px] font-medium ${AGENT_COLOR[a]}`}>{AGENT_LABEL[a]}</span>
                <span className="ml-auto text-[11px] text-text-muted capitalize">{agentStatuses[a] || 'idle'}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function Row({ label, value, cls, mono }: { label: string; value: string; cls?: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between text-[12px]">
      <span className="text-text-muted">{label}</span>
      <span className={`${cls || 'text-text-primary'} ${mono ? 'font-mono text-[11px]' : ''} max-w-[180px] truncate`}>{value}</span>
    </div>
  )
}

// ── Users Section ─────────────────────────────────────────────────────────────

function UsersSection({ users, activeUid }: { users: UserData[]; activeUid: string | null }) {
  const [selected, setSelected] = useState<UserData | null>(null)

  return (
    <div>
      <SectionHead title="Users" subtitle={`${users.length} user${users.length !== 1 ? 's' : ''} · RTDB + local`} />
      {users.length === 0 && <p className="text-sm text-text-muted">No users found. Run a deal first.</p>}
      <div className="grid grid-cols-3 gap-3">
        {users.map(u => {
          const label = u.display_name || u.email || u.uid
          const initial = label[0].toUpperCase()
          return (
          <button key={u.uid} onClick={() => setSelected(u)}
            className="bg-bg-card border border-border rounded-xl p-4 text-left hover:border-accent/40 transition group">
            <div className="flex items-start gap-3 mb-3">
              <div className="w-9 h-9 rounded-full bg-accent flex items-center justify-center text-white font-bold text-sm shrink-0">
                {initial}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  {activeUid === u.uid && <span className="w-2 h-2 rounded-full bg-success animate-pulse shrink-0" />}
                  {u.source === 'rtdb' && <span className="text-[9px] font-bold px-1 py-0.5 rounded bg-accent/15 text-accent shrink-0">RTDB</span>}
                  {u.source === 'both' && <span className="text-[9px] font-bold px-1 py-0.5 rounded bg-success/15 text-success shrink-0">SYNC</span>}
                  <p className="text-[12px] font-semibold text-text-primary truncate">{u.display_name || u.email || u.uid}</p>
                </div>
                {u.email && u.display_name && <p className="text-[10px] text-text-muted truncate">{u.email}</p>}
                <p className="text-[10px] text-text-muted font-mono truncate opacity-60">{u.uid}</p>
                <p className="text-[10px] text-text-muted mt-0.5">{rel(u.last_active)}</p>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-1 text-center">
              {[['Deals', u.deal_count], ['Sessions', u.session_count], ['Findings', u.finding_count]].map(([l, v]) => (
                <div key={String(l)} className="bg-bg-subtle rounded-lg py-1.5">
                  <p className="text-sm font-bold text-text-primary">{v}</p>
                  <p className="text-[10px] text-text-muted">{l}</p>
                </div>
              ))}
            </div>
          </button>
          )
        })}
      </div>

      <AnimatePresence>
        {selected && <UserDetailDrawer user={selected} onClose={() => setSelected(null)} />}
      </AnimatePresence>
    </div>
  )
}

function UserDetailDrawer({ user, onClose }: { user: UserData; onClose: () => void }) {
  const [openDeal, setOpenDeal] = useState<string | null>(null)
  const [openSession, setOpenSession] = useState<string | null>(null)
  const AGENTS = ['managing_partner', 'financial_partner', 'legal_partner', 'technical_partner', 'market_partner']

  return (
    <>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        onClick={onClose} className="fixed inset-0 bg-black/40 z-40" />
      <motion.div initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
        transition={{ type: 'spring', damping: 28, stiffness: 220 }}
        className="fixed top-0 right-0 bottom-0 w-[620px] bg-bg-card border-l border-border overflow-y-auto z-50 flex flex-col">

        {/* Header */}
        <div className="sticky top-0 bg-bg-card border-b border-border px-6 py-4 flex items-center gap-3 shrink-0">
          <div className="w-10 h-10 rounded-full bg-accent flex items-center justify-center text-white font-bold">
            {(user.display_name || user.email || user.uid)[0].toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-bold text-text-primary truncate">{user.display_name || user.email || user.uid}</p>
            {user.email && user.display_name && <p className="text-[11px] text-text-muted truncate">{user.email}</p>}
            <p className="text-[10px] font-mono text-text-muted opacity-60 truncate">{user.uid}</p>
            <p className="text-[11px] text-text-muted">{user.deal_count} deals · {user.session_count} sessions · {user.finding_count} findings · last active {rel(user.last_active)}</p>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-bg-muted text-text-muted">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6 space-y-6 flex-1">

          {/* Stat mini-row */}
          <div className="grid grid-cols-4 gap-2">
            {[['Deals', user.deal_count], ['Sessions', user.session_count], ['Patterns', user.pattern_count], ['MCP Calls', user.mcp_log.length]].map(([l, v]) => (
              <div key={String(l)} className="bg-bg-subtle border border-border rounded-lg p-3 text-center">
                <p className="text-lg font-bold text-text-primary">{v as number}</p>
                <p className="text-[10px] text-text-muted mt-0.5">{String(l)}</p>
              </div>
            ))}
          </div>

          {/* Deals */}
          <TreeBlock title={`Deals (${user.incidents.length})`} Icon={Database}>
            {user.incidents.length === 0 && <p className="text-xs text-text-muted px-2 py-1">No deals yet.</p>}
            {user.incidents.map(inc => (
              <div key={inc.incident_id} className="border border-border rounded-lg mb-2">
                <button onClick={() => setOpenDeal(openDeal === inc.incident_id ? null : inc.incident_id)}
                  className="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:bg-bg-muted rounded-lg transition">
                  {openDeal === inc.incident_id ? <ChevronDown className="w-3.5 h-3.5 text-text-muted shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-text-muted shrink-0" />}
                  <span className="text-[13px] font-medium text-text-primary flex-1">{inc.company}</span>
                  <VerdictBadge verdict={inc.verdict} />
                  <span className="text-[11px] text-text-muted ml-2">{inc.findings} findings</span>
                  <span className="text-[11px] text-text-muted ml-2">{rel(inc.created_at)}</span>
                </button>
                <AnimatePresence>
                  {openDeal === inc.incident_id && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden border-t border-border">
                      <div className="p-3 space-y-3">
                        {inc.timeline.length > 0 && (
                          <div>
                            <p className="text-[10px] font-bold text-text-muted uppercase mb-2">Timeline</p>
                            <div className="space-y-1.5">
                              {inc.timeline.map((ev, i) => (
                                <div key={i} className="flex items-start gap-2">
                                  <span className={`text-[11px] font-semibold shrink-0 ${AGENT_COLOR[ev.agent] || 'text-text-muted'}`}>{AGENT_LABEL[ev.agent] || ev.agent}</span>
                                  <span className="text-[11px] text-text-secondary line-clamp-2">{ev.finding?.slice(0, 120)}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        {inc.final_decision && (
                          <div>
                            <p className="text-[10px] font-bold text-text-muted uppercase mb-2">Verdict Card</p>
                            <pre className="text-[10px] font-mono text-text-secondary bg-bg-subtle rounded p-2 whitespace-pre-wrap max-h-40 overflow-y-auto">{inc.final_decision}</pre>
                          </div>
                        )}
                        <p className="text-[10px] text-text-muted">ID: {inc.incident_id} · {fmtDate(inc.created_at)}</p>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </TreeBlock>

          {/* Chat Sessions */}
          <TreeBlock title={`Chat Sessions (${user.sessions.length})`} Icon={MessageSquare}>
            {user.sessions.length === 0 && <p className="text-xs text-text-muted px-2 py-1">No sessions.</p>}
            {user.sessions.map(sess => (
              <div key={sess.session_id} className="border border-border rounded-lg mb-2">
                <button onClick={() => setOpenSession(openSession === sess.session_id ? null : sess.session_id)}
                  className="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:bg-bg-muted rounded-lg transition">
                  {openSession === sess.session_id ? <ChevronDown className="w-3.5 h-3.5 text-text-muted shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-text-muted shrink-0" />}
                  <span className="text-[13px] text-text-primary flex-1 truncate">{sess.title}</span>
                  <span className="text-[11px] text-text-muted">{sess.message_count} msgs</span>
                  <span className="text-[11px] text-text-muted ml-2">{rel(sess.timestamp)}</span>
                </button>
                <AnimatePresence>
                  {openSession === sess.session_id && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden border-t border-border">
                      <div className="p-3 space-y-1.5 max-h-60 overflow-y-auto">
                        {sess.messages.map((m, i) => (
                          <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'justify-end' : ''}`}>
                            {m.role !== 'user' && <span className="text-[10px] font-bold text-accent shrink-0 mt-0.5">MP</span>}
                            <p className={`text-[11px] rounded-lg px-2.5 py-1.5 max-w-[90%] ${m.role === 'user' ? 'bg-accent/10 text-accent' : 'bg-bg-subtle text-text-secondary'}`}>{m.content.slice(0, 200)}</p>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </TreeBlock>

          {/* Agent Memory */}
          <TreeBlock title="Agent Memory" Icon={Brain}>
            <div className="space-y-2">
              {AGENTS.map(a => {
                const p = user.agent_profiles[a]
                if (!p) return <div key={a} className="flex items-center gap-2 py-1"><span className={`text-[13px] ${AGENT_COLOR[a]}`}>{AGENT_LABEL[a]}</span><span className="text-[11px] text-text-muted ml-auto">No data</span></div>
                const pct = Math.min(100, (p.findings_logged / Math.max(1, user.finding_count)) * 100)
                return (
                  <div key={a} className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className={`text-[13px] font-medium ${AGENT_COLOR[a]}`}>{AGENT_LABEL[a]}</span>
                      <span className="text-[11px] text-text-muted ml-auto">{p.findings_logged} findings · {rel(p.last_active)}</span>
                    </div>
                    <div className="h-1.5 bg-bg-muted rounded-full"><div className={`h-1.5 rounded-full ${AGENT_BG[a].replace('/10', '')} bg-current ${AGENT_COLOR[a]}`} style={{ width: `${pct}%` }} /></div>
                  </div>
                )
              })}
            </div>
          </TreeBlock>

          {/* Risk Patterns */}
          {Object.keys(user.patterns).length > 0 && (
            <TreeBlock title={`Risk Patterns (${user.pattern_count})`} Icon={AlertTriangle}>
              <div className="space-y-1.5">
                {Object.entries(user.patterns).map(([kw, entries]) => (
                  <div key={kw} className="flex items-center gap-2 py-1 border-b border-border last:border-0">
                    <span className="text-[13px] text-text-primary font-mono">{kw}</span>
                    <span className="text-[11px] text-text-muted ml-auto">hit {entries.length}×</span>
                    <span className="text-[11px] text-text-muted">{rel(entries[0]?.learned_at)}</span>
                  </div>
                ))}
              </div>
            </TreeBlock>
          )}

          {/* MCP Usage */}
          <TreeBlock title="MCP Usage" Icon={Zap}>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-[12px] text-text-muted">Key:</span>
                {user.mcp_key ? (
                  <div className="flex items-center gap-1">
                    <span className="font-mono text-[11px] text-text-primary">{user.mcp_key.slice(0, 10)}…</span>
                    <CopyBtn text={user.mcp_key} />
                  </div>
                ) : <span className="text-[12px] text-text-muted">Not generated</span>}
                {user.mcp_key_created && <span className="text-[11px] text-text-muted ml-auto">{rel(user.mcp_key_created)}</span>}
              </div>
              {user.mcp_log.length === 0 && <p className="text-xs text-text-muted">No MCP calls logged.</p>}
              <div className="max-h-48 overflow-y-auto space-y-1">
                {[...user.mcp_log].reverse().map((e, i) => (
                  <div key={i} className="flex items-center gap-2 py-1 border-b border-border/50 last:border-0 text-[11px]">
                    <span className={e.success ? 'text-success' : 'text-danger'}>{e.success ? '✓' : '✗'}</span>
                    <span className="font-mono text-text-primary">{e.tool}</span>
                    <span className="text-text-muted ml-auto">{e.latency_ms}ms</span>
                    <span className="text-text-muted">{rel(e.timestamp)}</span>
                  </div>
                ))}
              </div>
            </div>
          </TreeBlock>
        </div>
      </motion.div>
    </>
  )
}

function TreeBlock({ title, Icon, children }: { title: string; Icon: React.ElementType; children: React.ReactNode }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <Icon className="w-3.5 h-3.5 text-text-muted" />
        <p className="text-[11px] font-bold text-text-muted uppercase tracking-wider">{title}</p>
      </div>
      {children}
    </div>
  )
}

// ── Live Feed ─────────────────────────────────────────────────────────────────

function LiveFeedSection({ events, paused, onPause, onClear }: { events: WsEvent[]; paused: boolean; onPause: () => void; onClear: () => void }) {
  const [filter, setFilter] = useState<string>('all')
  const bottomRef = useRef<HTMLDivElement>(null)

  const filtered = filter === 'all' ? events : events.filter(e => e.agent === filter || e.status === filter)

  useEffect(() => {
    if (!paused) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events.length, paused])

  const AGENTS_LIST = ['managing_partner', 'financial_partner', 'legal_partner', 'technical_partner', 'market_partner']

  return (
    <div>
      <SectionHead title="Live Activity Feed" subtitle="Real-time WebSocket event stream" />
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        {['all', ...AGENTS_LIST, 'working', 'done', 'alert', 'debate'].map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition ${filter === f ? 'bg-accent text-white' : 'bg-bg-card border border-border text-text-secondary hover:text-text-primary'}`}>
            {f === 'all' ? 'All' : AGENT_LABEL[f] || f}
          </button>
        ))}
        <div className="ml-auto flex gap-2">
          <button onClick={onPause} className={`px-3 py-1.5 rounded-lg text-[12px] border transition ${paused ? 'border-accent text-accent' : 'border-border text-text-secondary hover:border-accent hover:text-accent'}`}>
            {paused ? '▶ Resume' : '⏸ Pause'}
          </button>
          <button onClick={onClear} className="px-3 py-1.5 rounded-lg text-[12px] border border-border text-text-secondary hover:border-danger hover:text-danger transition">Clear</button>
        </div>
      </div>
      <div className="bg-bg-card border border-border rounded-xl h-[500px] overflow-y-auto font-mono text-[11px]">
        {filtered.length === 0 && <p className="text-text-muted p-4">No events. Trigger a deal from the main dashboard.</p>}
        {filtered.map((ev, i) => {
          const cls = ev.status === 'alert' ? 'text-danger' : ev.status === 'done' ? 'text-success' : ev.status === 'debate' ? 'text-purple-400' : ev.agent ? (AGENT_COLOR[ev.agent] || 'text-text-secondary') : 'text-text-muted'
          return (
            <div key={i} className="flex gap-3 px-3 py-1.5 border-b border-border/30 hover:bg-bg-subtle transition">
              <span className="text-text-muted shrink-0 w-16">{ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : '—'}</span>
              {ev.agent && <span className={`shrink-0 w-28 truncate ${AGENT_COLOR[ev.agent] || 'text-text-muted'}`}>{AGENT_LABEL[ev.agent] || ev.agent}</span>}
              <span className={`shrink-0 w-14 ${cls}`}>{ev.status || '—'}</span>
              <span className="text-text-secondary flex-1 truncate">{ev.current_action || (ev.output as Record<string,string>)?.report?.slice(0, 80) || JSON.stringify(ev.output || {}).slice(0, 80)}</span>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

// ── Deal Vault ────────────────────────────────────────────────────────────────

function DealVaultSection({ users, onDelete }: { users: UserData[]; onDelete: (id: string) => void }) {
  const [selected, setSelected] = useState<DealRecord | null>(null)
  const [confirm, setConfirm] = useState<string | null>(null)
  const [sortCol, setSortCol] = useState<'date' | 'score' | 'verdict'>('date')

  const allDeals = users.flatMap(u => u.incidents.map(inc => ({ ...inc, uid: u.uid })))
  const sorted = [...allDeals].sort((a, b) => {
    if (sortCol === 'date') return (b.created_at || '').localeCompare(a.created_at || '')
    if (sortCol === 'verdict') return a.verdict.localeCompare(b.verdict)
    return 0
  })

  const doDelete = (id: string) => { onDelete(id); setConfirm(null) }

  return (
    <div>
      <SectionHead title="Deal Vault" subtitle={`${allDeals.length} deals across ${users.length} users`} />
      <div className="bg-bg-card border border-border rounded-xl overflow-hidden">
        <div className="grid grid-cols-[1fr_1fr_120px_80px_100px_100px] text-[11px] font-bold text-text-muted uppercase tracking-wider px-4 py-2.5 border-b border-border bg-bg-subtle">
          {['Company', 'User', 'Verdict', 'Findings', 'Date', ''].map((h, i) => (
            <span key={i} className={h ? 'cursor-pointer hover:text-text-primary' : ''} onClick={() => h === 'Date' ? setSortCol('date') : h === 'Verdict' ? setSortCol('verdict') : undefined}>{h}</span>
          ))}
        </div>
        {sorted.length === 0 && <p className="text-sm text-text-muted p-4">No deals found.</p>}
        {sorted.map((deal) => (
          <div key={deal.incident_id}
            className="grid grid-cols-[1fr_1fr_120px_80px_100px_100px] items-center px-4 py-2.5 border-b border-border/50 last:border-0 hover:bg-bg-subtle transition text-[12px]">
            <button onClick={() => setSelected(deal)} className="text-left text-text-primary font-medium hover:text-accent truncate">{deal.company}</button>
            <span className="font-mono text-text-muted truncate">{(deal as DealRecord & { uid?: string }).uid}</span>
            <span><VerdictBadge verdict={deal.verdict} /></span>
            <span className="text-text-secondary">{deal.findings}</span>
            <span className="text-text-muted">{rel(deal.created_at)}</span>
            <div className="flex justify-end">
              {confirm === deal.incident_id ? (
                <div className="flex gap-1">
                  <button onClick={() => doDelete(deal.incident_id)} className="px-2 py-0.5 rounded text-[10px] bg-danger text-white">Delete</button>
                  <button onClick={() => setConfirm(null)} className="px-2 py-0.5 rounded text-[10px] bg-bg-muted text-text-muted">Cancel</button>
                </div>
              ) : (
                <button onClick={() => setConfirm(deal.incident_id)} className="p-1.5 rounded hover:bg-danger/10 text-text-muted hover:text-danger transition">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      <AnimatePresence>
        {selected && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setSelected(null)} className="fixed inset-0 bg-black/40 z-40" />
            <motion.div initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 28, stiffness: 220 }}
              className="fixed top-0 right-0 bottom-0 w-[560px] bg-bg-card border-l border-border overflow-y-auto z-50">
              <div className="sticky top-0 bg-bg-card border-b border-border px-5 py-4 flex items-center gap-3">
                <div className="flex-1">
                  <p className="font-bold text-text-primary">{selected.company}</p>
                  <div className="flex items-center gap-2 mt-1"><VerdictBadge verdict={selected.verdict} /><span className="text-[11px] text-text-muted">{fmtDate(selected.created_at)}</span></div>
                </div>
                <button onClick={() => setSelected(null)} className="p-2 rounded-lg hover:bg-bg-muted text-text-muted"><X className="w-4 h-4" /></button>
              </div>
              <div className="p-5 space-y-4">
                {selected.timeline.map((ev, i) => (
                  <div key={i} className="border border-border rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`text-[12px] font-bold ${AGENT_COLOR[ev.agent] || 'text-text-muted'}`}>{AGENT_LABEL[ev.agent] || ev.agent}</span>
                      <span className="text-[11px] text-text-muted ml-auto">{rel(ev.timestamp)}</span>
                    </div>
                    <p className="text-[12px] text-text-secondary whitespace-pre-wrap">{ev.finding?.slice(0, 600)}{(ev.finding?.length || 0) > 600 ? '…' : ''}</p>
                  </div>
                ))}
                {selected.final_decision && (
                  <div>
                    <p className="text-[11px] font-bold text-text-muted uppercase mb-2">Verdict Card</p>
                    <pre className="text-[11px] font-mono bg-bg-subtle border border-border rounded-lg p-3 whitespace-pre-wrap">{selected.final_decision}</pre>
                  </div>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}

// ── Build Log ─────────────────────────────────────────────────────────────────

function BuildLogSection({ gitLog, vercelDeps, onRefresh }: { gitLog: GitCommit[]; vercelDeps: VercelDep[]; onRefresh: () => void }) {
  const [tab, setTab] = useState<'git' | 'vercel'>('git')

  const stateClr = (s: string) => s === 'READY' ? 'text-success bg-success/10' : s === 'ERROR' ? 'text-danger bg-danger/10' : s === 'BUILDING' ? 'text-warning bg-warning/10 animate-pulse' : 'text-text-muted bg-bg-muted'

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-base font-semibold text-text-primary">Build &amp; Changes Log</h2>
          <p className="text-xs text-text-muted mt-0.5">Git history and deployment status</p>
        </div>
        <button onClick={onRefresh} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-[12px] text-text-secondary hover:text-text-primary hover:border-accent transition">
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>
      <div className="flex gap-1 mb-4">
        {([['git', 'Git Log'], ['vercel', 'Vercel Deployments']] as [string, string][]).map(([id, label]) => (
          <button key={id} onClick={() => setTab(id as 'git' | 'vercel')}
            className={`px-3 py-1.5 rounded-lg text-[12px] font-medium transition ${tab === id ? 'bg-accent text-white' : 'border border-border text-text-secondary hover:text-text-primary'}`}>
            {label}
          </button>
        ))}
      </div>

      {tab === 'git' && (
        <div className="bg-bg-card border border-border rounded-xl overflow-hidden">
          {gitLog.length === 0 && <p className="text-sm text-text-muted p-4">No commits found.</p>}
          {gitLog.map(c => (
            <div key={c.full_hash} className="flex items-start gap-3 px-4 py-3 border-b border-border/50 last:border-0 hover:bg-bg-subtle transition">
              <span className="font-mono text-[11px] text-text-muted shrink-0 mt-0.5 w-16">{c.hash}</span>
              <div className="flex-1 min-w-0">
                <p className="text-[13px] text-text-primary truncate">{c.subject}</p>
                <p className="text-[11px] text-text-muted mt-0.5">{c.author}</p>
              </div>
              <span className="text-[11px] text-text-muted shrink-0">{c.relative}</span>
            </div>
          ))}
        </div>
      )}

      {tab === 'vercel' && (
        <div className="bg-bg-card border border-border rounded-xl overflow-hidden">
          {vercelDeps.length === 0 && <p className="text-sm text-text-muted p-4">No deployments found. Set VERCEL_TOKEN and VERCEL_PROJECT_ID in your .env to enable this.</p>}
          {vercelDeps.map(d => (
            <div key={d.uid} className="flex items-center gap-3 px-4 py-3 border-b border-border/50 last:border-0 hover:bg-bg-subtle transition">
              <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${stateClr(d.state)}`}>{d.state}</span>
              <div className="flex-1 min-w-0">
                <p className="text-[13px] text-text-primary truncate">{d.meta?.githubCommitMessage || '—'}</p>
                <p className="text-[11px] text-text-muted mt-0.5">{d.meta?.githubCommitRef || 'main'} · {d.meta?.githubCommitSha?.slice(0, 8) || '—'}</p>
              </div>
              <span className="text-[11px] text-text-muted shrink-0">{d.createdAt ? rel(new Date(d.createdAt).toISOString()) : '—'}</span>
              {d.url && <a href={`https://${d.url}`} target="_blank" rel="noopener noreferrer" className="text-[11px] text-accent hover:underline shrink-0">Open ↗</a>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Agent Performance ─────────────────────────────────────────────────────────

function AgentPerfSection({ users, memStats }: { users: UserData[]; memStats: MemStats | null }) {
  const AGENTS = ['managing_partner', 'financial_partner', 'legal_partner', 'technical_partner', 'market_partner']
  const totals = AGENTS.map(a => {
    // Prefer backend memStats (global across all deals), fall back to aggregating user profiles
    const mp = memStats?.agent_profiles?.[a]
    const findings = mp?.findings_logged ?? users.reduce((s, u) => s + (u.agent_profiles[a]?.findings_logged || 0), 0)
    const incidents = mp?.incidents?.length ?? users.reduce((s, u) => s + (u.agent_profiles[a]?.incidents?.length || 0), 0)
    const lastActive = mp?.last_active ?? users.map(u => u.agent_profiles[a]?.last_active || '').filter(Boolean).sort().pop()
    return { agent: a, findings, incidents, lastActive }
  })
  const maxFindings = Math.max(...totals.map(t => t.findings), 1)

  return (
    <div>
      <SectionHead title="Agent Performance" subtitle="Global findings and activity across all users" />
      <div className="grid grid-cols-5 gap-3 mb-6">
        {totals.map(t => (
          <div key={t.agent} className="bg-bg-card border border-border rounded-xl p-4">
            <div className={`w-8 h-8 rounded-lg ${AGENT_BG[t.agent]} flex items-center justify-center mb-3`}>
              <Cpu className={`w-4 h-4 ${AGENT_COLOR[t.agent]}`} />
            </div>
            <p className={`text-[11px] font-bold mb-1 ${AGENT_COLOR[t.agent]}`}>{AGENT_LABEL[t.agent]}</p>
            <p className="text-2xl font-bold text-text-primary">{t.findings}</p>
            <p className="text-[10px] text-text-muted">findings</p>
            <p className="text-[11px] text-text-secondary mt-2">{t.incidents} deals</p>
            <p className="text-[10px] text-text-muted">{rel(t.lastActive || null)}</p>
          </div>
        ))}
      </div>
      <div className="bg-bg-card border border-border rounded-xl p-5">
        <p className="text-[11px] font-bold text-text-muted uppercase tracking-wider mb-4">Findings Distribution</p>
        <div className="space-y-3">
          {totals.map(t => (
            <div key={t.agent} className="flex items-center gap-3">
              <span className={`text-[12px] font-medium w-36 shrink-0 ${AGENT_COLOR[t.agent]}`}>{AGENT_LABEL[t.agent]}</span>
              <div className="flex-1 bg-bg-muted rounded-full h-2">
                <div className={`h-2 rounded-full bg-current ${AGENT_COLOR[t.agent]} transition-all duration-500`} style={{ width: `${(t.findings / maxFindings) * 100}%` }} />
              </div>
              <span className="text-[12px] text-text-primary w-8 text-right">{t.findings}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Memory & Patterns ─────────────────────────────────────────────────────────

function PatternsSection({ users }: { users: UserData[] }) {
  const [newKw, setNewKw] = useState('')
  const [newCl, setNewCl] = useState('')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  const all: Record<string, { entries: unknown[]; users: string[] }> = {}
  for (const u of users) for (const [kw, entries] of Object.entries(u.patterns || {})) {
    if (!all[kw]) all[kw] = { entries: [], users: [] }
    all[kw].entries.push(...entries)
    all[kw].users.push(u.uid)
  }

  const save = async () => {
    if (!newKw.trim() || !newCl.trim()) return
    setSaving(true)
    await apiPost('/api/v1/memory/pattern', { keyword: newKw.trim(), checklist: newCl.trim(), success_rate: 0.8 })
    setMsg(`Pattern "${newKw}" taught.`)
    setNewKw(''); setNewCl('')
    setSaving(false)
    setTimeout(() => setMsg(''), 3000)
  }

  return (
    <div>
      <SectionHead title="Memory & Risk Patterns" subtitle="Learned patterns across all users" />
      <div className="bg-bg-card border border-border rounded-xl overflow-hidden mb-5">
        <div className="grid grid-cols-[1fr_80px_1fr] text-[11px] font-bold text-text-muted uppercase tracking-wider px-4 py-2.5 border-b border-border bg-bg-subtle">
          <span>Keyword</span><span>Hits</span><span>Users</span>
        </div>
        {Object.keys(all).length === 0 && <p className="text-sm text-text-muted p-4">No patterns learned yet.</p>}
        {Object.entries(all).map(([kw, data]) => (
          <div key={kw} className="grid grid-cols-[1fr_80px_1fr] items-center px-4 py-3 border-b border-border/50 last:border-0 hover:bg-bg-subtle transition text-[12px]">
            <span className="font-mono text-text-primary">{kw}</span>
            <span className="text-text-secondary">{data.entries.length}</span>
            <span className="text-text-muted truncate">{[...new Set(data.users)].join(', ')}</span>
          </div>
        ))}
      </div>

      <div className="bg-bg-card border border-border rounded-xl p-5">
        <p className="text-[11px] font-bold text-text-muted uppercase tracking-wider mb-4">Teach New Pattern</p>
        <div className="space-y-3">
          <input value={newKw} onChange={e => setNewKw(e.target.value)} placeholder="Keyword (e.g. revenue-concentration)"
            className="w-full px-3 py-2 rounded-lg bg-bg-subtle border border-border text-text-primary text-sm outline-none focus:border-accent transition" />
          <textarea value={newCl} onChange={e => setNewCl(e.target.value)} rows={3} placeholder="Checklist / risk description"
            className="w-full px-3 py-2 rounded-lg bg-bg-subtle border border-border text-text-primary text-sm outline-none focus:border-accent transition resize-none" />
          <div className="flex items-center gap-3">
            <button onClick={save} disabled={saving || !newKw || !newCl}
              className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium disabled:opacity-50 hover:bg-accent/90 transition">
              {saving ? 'Saving…' : 'Teach Pattern'}
            </button>
            {msg && <span className="text-[12px] text-success">{msg}</span>}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── System Controls ───────────────────────────────────────────────────────────

function SystemControlsSection({ status, onRefresh }: { status: SystemStatus | null; onRefresh: () => void }) {
  const [confirm, setConfirm] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [msg, setMsg] = useState('')
  const [settings, setSettings] = useState<Record<string, unknown> | null>(null)

  useEffect(() => {
    apiFetch<Record<string, unknown>>('/api/v1/system/settings').then(s => s && setSettings(s))
  }, [])

  const action = async (name: string, path: string, method = 'POST') => {
    setBusy(name); setConfirm(null)
    const r = method === 'POST' ? await apiPost(path) : await apiFetch(path)
    setMsg(`${name}: ${(r as Record<string,string>)?.status || (r as Record<string,string>)?.message || 'done'}`)
    setBusy(null); onRefresh()
    setTimeout(() => setMsg(''), 4000)
  }

  const ACTIONS = [
    { id: 'reset', label: 'Reset Simulation', desc: 'Clear current session lock', path: '/api/reset', danger: false },
    { id: 'force', label: 'Force Verdict', desc: 'Emit partial verdict for stalled deal', path: '/api/force-verdict', danger: false, disabled: !status?.simulation_running },
    { id: 'reset-all', label: 'Reset ALL History', desc: 'Delete all deals, sessions, and memory', path: '/api/v1/system/reset-all', danger: true },
  ]

  return (
    <div>
      <SectionHead title="System Controls" subtitle="Actions, settings, and configuration" />
      <div className="grid grid-cols-2 gap-4 mb-6">
        {/* Action buttons */}
        <div className="bg-bg-card border border-border rounded-xl p-5">
          <p className="text-[11px] font-bold text-text-muted uppercase tracking-wider mb-4">Actions</p>
          <div className="space-y-2">
            {ACTIONS.map(a => (
              <div key={a.id}>
                {confirm === a.id ? (
                  <div className="flex items-center gap-2 p-3 rounded-lg bg-danger/5 border border-danger/20">
                    <span className="text-[12px] text-danger flex-1">Confirm: {a.label}?</span>
                    <button onClick={() => action(a.label, a.path)} className="px-2.5 py-1 rounded bg-danger text-white text-[11px]">Yes</button>
                    <button onClick={() => setConfirm(null)} className="px-2.5 py-1 rounded bg-bg-muted text-text-muted text-[11px]">No</button>
                  </div>
                ) : (
                  <button onClick={() => a.danger ? setConfirm(a.id) : action(a.label, a.path)}
                    disabled={!!(busy || (a as typeof a & { disabled?: boolean }).disabled)}
                    className={`w-full flex items-center gap-3 p-3 rounded-lg border text-left transition disabled:opacity-40 ${a.danger ? 'border-danger/20 hover:bg-danger/5 text-danger' : 'border-border hover:bg-bg-subtle text-text-primary'}`}>
                    <div className="flex-1">
                      <p className="text-[13px] font-medium">{a.label}</p>
                      <p className={`text-[11px] ${a.danger ? 'text-danger/70' : 'text-text-muted'}`}>{a.desc}</p>
                    </div>
                    {busy === a.label ? <Loader2 className="w-4 h-4 animate-spin" /> : <ChevronRight className="w-4 h-4" />}
                  </button>
                )}
              </div>
            ))}
          </div>
          {msg && <p className="text-[12px] text-success mt-3">{msg}</p>}
        </div>

        {/* Status summary */}
        <div className="bg-bg-card border border-border rounded-xl p-5">
          <p className="text-[11px] font-bold text-text-muted uppercase tracking-wider mb-4">System State</p>
          <div className="space-y-2">
            <Row label="Backend" value={status ? 'Healthy' : 'Unreachable'} cls={status ? 'text-success' : 'text-danger'} />
            <Row label="Mode" value={status?.mock_mode ? 'Mock' : 'Real Band'} />
            <Row label="Running" value={status?.simulation_running ? 'Yes' : 'No'} cls={status?.simulation_running ? 'text-warning' : 'text-success'} />
            <Row label="Incidents" value={String(status?.memory_incidents ?? '—')} />
          </div>
          <div className="mt-4">
            <p className="text-[11px] font-bold text-text-muted uppercase tracking-wider mb-3">Agent Statuses</p>
            {Object.entries(status?.agent_statuses || {}).map(([a, s]) => (
              <div key={a} className="flex items-center gap-2 py-1"><AgentDot status={s} /><span className="text-[12px] text-text-secondary">{AGENT_LABEL[a] || a}</span><span className="ml-auto text-[11px] text-text-muted">{s}</span></div>
            ))}
          </div>
        </div>
      </div>

      {/* Settings */}
      {settings && (
        <div className="bg-bg-card border border-border rounded-xl p-5">
          <p className="text-[11px] font-bold text-text-muted uppercase tracking-wider mb-4">System Settings (read-only)</p>
          <pre className="text-[11px] font-mono text-text-secondary bg-bg-subtle rounded-lg p-3 overflow-x-auto max-h-60">{JSON.stringify(settings, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}

// ── SENTINEL Section ──────────────────────────────────────────────────────────

function SentinelSection({ alerts, setAlerts }: { alerts: Alert[]; setAlerts: (a: Alert[]) => void }) {
  const sev = (s: Severity) => s === 'critical' ? 'text-danger bg-danger/10 border-danger/20' : s === 'warning' ? 'text-warning bg-warning/10 border-warning/20' : 'text-accent bg-accent/10 border-accent/20'
  const active = alerts.filter(a => !a.resolved)
  const resolved = alerts.filter(a => a.resolved)

  const resolve = (id: string) => setAlerts(alerts.map(a => a.id === id ? { ...a, resolved: !a.resolved } : a))

  return (
    <div>
      <SectionHead title="SENTINEL" subtitle="Autonomous health monitoring — 12 detection rules running every 5s" />
      {active.length === 0 && resolved.length === 0 && (
        <div className="bg-bg-card border border-border rounded-xl p-8 text-center">
          <CheckCircle className="w-8 h-8 text-success mx-auto mb-2" />
          <p className="text-sm text-text-primary font-medium">All systems nominal</p>
          <p className="text-xs text-text-muted mt-1">No active alerts detected</p>
        </div>
      )}
      {active.length > 0 && (
        <div className="mb-5 space-y-2">
          <p className="text-[11px] font-bold text-text-muted uppercase tracking-wider mb-3">Active Alerts ({active.length})</p>
          {active.map(a => (
            <div key={a.id} className={`flex items-start gap-3 p-4 rounded-xl border ${sev(a.severity)}`}>
              {a.severity === 'critical' ? <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" /> : a.severity === 'warning' ? <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" /> : <Eye className="w-4 h-4 shrink-0 mt-0.5" />}
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-[12px] font-bold">{a.rule}</span>
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${sev(a.severity)}`}>{a.severity.toUpperCase()}</span>
                </div>
                <p className="text-[12px] mt-0.5 opacity-80">{a.message}</p>
                <p className="text-[10px] mt-1 opacity-60">{fmtDate(a.timestamp)}</p>
              </div>
              <button onClick={() => resolve(a.id)} className="text-[11px] opacity-60 hover:opacity-100 transition">Resolve</button>
            </div>
          ))}
        </div>
      )}
      {resolved.length > 0 && (
        <div>
          <p className="text-[11px] font-bold text-text-muted uppercase tracking-wider mb-3">Resolved ({resolved.length})</p>
          <div className="space-y-1.5">
            {resolved.map(a => (
              <div key={a.id} className="flex items-center gap-3 px-4 py-2.5 bg-bg-card border border-border rounded-lg opacity-50">
                <CheckCircle className="w-3.5 h-3.5 text-success shrink-0" />
                <span className="text-[12px] text-text-secondary">{a.rule}: {a.message}</span>
                <button onClick={() => resolve(a.id)} className="ml-auto text-[11px] text-text-muted hover:text-text-primary transition">Unresolve</button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Rules reference */}
      <div className="mt-8 bg-bg-card border border-border rounded-xl p-5">
        <p className="text-[11px] font-bold text-text-muted uppercase tracking-wider mb-4">Active Rules (12)</p>
        <div className="grid grid-cols-2 gap-2">
          {[
            ['deal-stall', 'Deal Stall', 'Idle >90s while running', 'critical'],
            ['agent-death', 'Agent Death', 'Agent emitted alert status', 'critical'],
            ['backend-down', 'Backend Unreachable', 'API failed 3× in a row', 'critical'],
            ['agents-silent', 'All Agents Silent', 'No events for 60s while running', 'warning'],
            ['vercel-fail', 'Vercel Build Failed', 'Recent deployment in ERROR state', 'warning'],
            ['mcp-errors', 'MCP Error Rate High', '>50% MCP calls failed in 1h', 'warning'],
            ['llm-degraded', 'LLM Degraded', 'Mock-LLM fallback detected', 'warning'],
            ['long-deal', 'Long-Running Deal', 'Deal running >5 minutes', 'info'],
            ['ws-down', 'Feed Disconnected', 'Admin WebSocket disconnected', 'info'],
            ['mem-bloat', 'Memory Bloat', '>100 incidents or >1000 findings', 'info'],
            ['pattern-rising', 'Pattern Rising', 'Same pattern hit ≥5× across users', 'info'],
            ['—', 'More rules', 'Auto-detecting anomalies continuously', 'info'],
          ].map(([id, rule, desc, sev_]) => (
            <div key={id} className="flex items-start gap-2 p-2 rounded-lg bg-bg-subtle">
              <span className={`w-2 h-2 rounded-full mt-1 shrink-0 ${sev_ === 'critical' ? 'bg-danger' : sev_ === 'warning' ? 'bg-warning' : 'bg-accent'}`} />
              <div>
                <p className="text-[11px] font-semibold text-text-primary">{rule}</p>
                <p className="text-[10px] text-text-muted">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Main Dashboard ────────────────────────────────────────────────────────────

export default function AdminDashboard() {
  const router = useRouter()

  const [unlocked, setUnlocked] = useState(false)
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (sessionStorage.getItem('admin_unlocked') === '1') setUnlocked(true)
  }, [])
  const [section, setSection] = useState<Section>('overview')

  // Data state
  const [users, setUsers] = useState<UserData[]>([])
  const [activeUid, setActiveUid] = useState<string | null>(null)
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const [memStats, setMemStats] = useState<MemStats | null>(null)
  const [gitLog, setGitLog] = useState<GitCommit[]>([])
  const [vercelDeps, setVercelDeps] = useState<VercelDep[]>([])
  const [wsEvents, setWsEvents] = useState<WsEvent[]>([])
  const [lastWsEventAt, setLastWsEventAt] = useState(0)
  const [wsConnected, setWsConnected] = useState(false)
  const [feedPaused, setFeedPaused] = useState(false)
  const [statusFailCount, setStatusFailCount] = useState(0)
  const [sentinelAlerts, setSentinelAlerts] = useState<Alert[]>([])
  const [usersLoading, setUsersLoading] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const feedPausedRef = useRef(false)
  useEffect(() => { feedPausedRef.current = feedPaused }, [feedPaused])

  // Initial data fetch
  const fetchAll = useCallback(async () => {
    const [stat, mem] = await Promise.all([
      apiFetch<SystemStatus>('/api/status'),
      apiFetch<MemStats>('/api/v1/memory/stats'),
    ])
    if (stat) { setSystemStatus(stat); setStatusFailCount(0) }
    else setStatusFailCount(c => c + 1)
    if (mem) setMemStats(mem)
  }, [])

  const fetchUsers = useCallback(async () => {
    setUsersLoading(true)

    // ── Local fusion_memory users (from backend) ─────────────────────────
    const r = await apiFetch<{ users: UserData[]; active_uid: string | null }>('/api/admin/users')
    const localUsers: UserData[] = r?.users ?? []
    if (r?.active_uid !== undefined) setActiveUid(r.active_uid)

    // ── RTDB users (direct Firebase client read) ─────────────────────────
    const rtdbUsers: UserData[] = []
    try {
      // Ensure we have a Firebase auth session so RTDB rules pass
      if (!auth.currentUser) await signInAsGuest()
      const db = getDatabase()
      const [usersSnap, mcpSnap] = await Promise.all([
        get(dbRef(db, '/users')),
        get(dbRef(db, '/mcp_usage')),
      ])
      const usersData: Record<string, Record<string, unknown>> = usersSnap.val() || {}
      const mcpData: Record<string, Record<string, unknown>> = mcpSnap.val() || {}

      for (const [username, node] of Object.entries(usersData)) {
        if (!node || typeof node !== 'object') continue
        const profile = (node.profile as Record<string, string>) || {}
        const deals = (node.deals as Record<string, Record<string, unknown>>) || {}
        const chats = (node.chats as Record<string, Record<string, unknown>>) || {}
        const sessions = (node.sessions as Record<string, Record<string, unknown>>) || {}

        // Build incidents from RTDB deals
        const incidents: DealRecord[] = Object.entries(deals).map(([id, d]) => {
          const fd = String(d?.final_decision || d?.verdict || '')
          const verdict = fd.match(/INVEST|CONDITIONAL|PASS/i)?.[0]?.toUpperCase() ?? (d?.verdict as string ?? 'PENDING')
          return {
            incident_id: id,
            company: String(d?.company || (d?.metadata as Record<string,string>)?.company || 'Unknown'),
            verdict,
            findings: Number(d?.findings_count || 0),
            created_at: String(d?.createdAt || d?.updatedAt || ''),
            final_decision: fd.slice(0, 5000) || null,
            timeline: (d?.timeline as DealRecord['timeline']) || [],
          }
        }).sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))

        // Build sessions from RTDB chats + sessions
        const chatMsgs = Object.values(chats).sort((a, b) =>
          String(a?.timestamp || '').localeCompare(String(b?.timestamp || '')))
        const chatSessions: Session[] = chatMsgs.length ? [{
          session_id: 'rtdb_chat',
          title: String(chatMsgs[0]?.message || 'Chat').slice(0, 60),
          message_count: chatMsgs.length,
          timestamp: String(chatMsgs[chatMsgs.length - 1]?.timestamp || null),
          messages: chatMsgs.slice(-30).map(m => ({
            role: 'user', content: String(m?.message || ''), timestamp: String(m?.timestamp || ''),
          })),
        }] : []
        const sessionList: Session[] = Object.entries(sessions).map(([sid, s]) => ({
          session_id: sid,
          title: String(s?.title || sid).slice(0, 60),
          message_count: Number(s?.messageCount || 0),
          timestamp: String(s?.updatedAt || s?.createdAt || null),
          messages: [],
        }))

        // MCP log from /mcp_usage/{username}
        const mcpEntries = Object.values(mcpData[username] || {}).map(e => ({
          tool: String((e as Record<string,unknown>)?.tool || ''),
          timestamp: String((e as Record<string,unknown>)?.timestamp || ''),
          success: true,
          latency_ms: 0,
        })).sort((a, b) => a.timestamp.localeCompare(b.timestamp))

        rtdbUsers.push({
          uid: username,
          email: profile.email || null,
          display_name: profile.displayName || null,
          photo_url: profile.photoURL || null,
          ip: profile.ip || null,
          device: profile.device || null,
          source: 'rtdb',
          deal_count: incidents.length,
          session_count: chatSessions.length + sessionList.length,
          finding_count: incidents.reduce((s, i) => s + i.findings, 0),
          pattern_count: 0,
          last_active: profile.lastSeen || incidents[0]?.created_at || null,
          agent_profiles: {},
          incidents,
          sessions: [...chatSessions, ...sessionList],
          patterns: {},
          mcp_log: mcpEntries.slice(-200),
          mcp_key: null,
          mcp_key_created: null,
        })
      }
    } catch (e) {
      console.warn('RTDB direct read failed (rules may require auth):', e)
    }

    // ── Merge: RTDB wins on identity fields, local wins on agent data ────
    const byUid = new Map<string, UserData>()
    for (const u of localUsers) byUid.set(u.uid, u)
    for (const u of rtdbUsers) {
      const existing = byUid.get(u.uid)
      if (existing) {
        byUid.set(u.uid, {
          ...existing, ...u,
          agent_profiles: existing.agent_profiles,
          patterns: existing.patterns,
          incidents: u.incidents.length ? u.incidents : existing.incidents,
          sessions: u.sessions.length ? u.sessions : existing.sessions,
          source: 'both',
        })
      } else {
        byUid.set(u.uid, u)
      }
    }

    const merged = Array.from(byUid.values())
      .sort((a, b) => (b.last_active || '').localeCompare(a.last_active || ''))
    setUsers(merged)
    setUsersLoading(false)
  }, [])

  const fetchBuildData = useCallback(async () => {
    const [git, vercel] = await Promise.all([
      apiFetch<{ commits: GitCommit[] }>('/api/admin/git-log'),
      apiFetch<{ deployments: VercelDep[] }>('/api/admin/vercel-deployments'),
    ])
    if (git) setGitLog(git.commits)
    if (vercel) setVercelDeps(vercel.deployments)
  }, [])

  useEffect(() => {
    if (!unlocked) return
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchAll()
    fetchUsers()
    fetchBuildData()
    const id1 = setInterval(fetchAll, 5000)
    const id2 = setInterval(fetchUsers, 10000)
    const id3 = setInterval(fetchBuildData, 30000)
    return () => { clearInterval(id1); clearInterval(id2); clearInterval(id3) }
  }, [unlocked, fetchAll, fetchUsers, fetchBuildData])

  // WebSocket
  const connectWs = useCallback(() => {
    if (!unlocked) return
    const ws = new WebSocket(WS_BASE)
    wsRef.current = ws
    ws.onopen = () => setWsConnected(true)
    ws.onclose = () => {
      setWsConnected(false)
      // eslint-disable-next-line react-hooks/immutability
      reconnectTimer.current = setTimeout(connectWs, Math.min(5000, 1000 + Math.random() * 2000))
    }
    ws.onmessage = (e) => {
      if (feedPausedRef.current) return
      try {
        const ev: WsEvent = JSON.parse(e.data)
        if (ev.agent || ev.status) {
          setWsEvents(prev => [{ ...ev, timestamp: ev.timestamp || new Date().toISOString() }, ...prev].slice(0, 1000))
          setLastWsEventAt(Date.now())
        }
      } catch { /* ignore malformed */ }
    }
  }, [unlocked])

  useEffect(() => {
    connectWs()
    return () => { wsRef.current?.close(); if (reconnectTimer.current) clearTimeout(reconnectTimer.current) }
  }, [connectWs])

  // SENTINEL: run on every data tick
  useEffect(() => {
    const snap: SystemSnapshot = { status: systemStatus, wsEvents, lastWsEventAt, wsConnected, vercelDeps, memStats, statusFailCount, users }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSentinelAlerts(prev => runSentinel(snap, prev))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [systemStatus, wsEvents.length, vercelDeps.length, wsConnected, statusFailCount, users.length, lastWsEventAt, memStats])

  const deleteIncident = async (id: string) => {
    await apiPost(`/api/incident/${id}`, undefined)
    await fetchUsers()
  }

  if (!unlocked) return <KeyGate onUnlock={() => setUnlocked(true)} />

  const activeAlerts = sentinelAlerts.filter(a => !a.resolved)
  const critCount = activeAlerts.filter(a => a.severity === 'critical').length

  return (
    <div className="h-screen overflow-hidden flex bg-bg-base">

      {/* Sidebar */}
      <aside className="w-[220px] shrink-0 bg-bg-subtle border-r border-border flex flex-col h-full">
        <div className="px-4 py-4 border-b border-border">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center shrink-0">
              <Shield className="w-4 h-4 text-white" />
            </div>
            <div>
              <p className="text-[13px] font-bold text-text-primary">FUSION</p>
              <p className="text-[10px] text-text-muted">Admin Panel</p>
            </div>
            {critCount > 0 && <span className="ml-auto w-5 h-5 rounded-full bg-danger text-white text-[10px] font-bold flex items-center justify-center shrink-0">{critCount}</span>}
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto py-2">
          {NAV_ITEMS.map(item => (
            <button key={item.id} onClick={() => setSection(item.id)}
              className={`w-full flex items-center gap-2.5 px-3 py-2 mx-1.5 rounded-lg text-[13px] transition mb-0.5 ${section === item.id ? 'bg-accent/10 text-accent font-semibold' : 'text-text-secondary hover:bg-bg-muted hover:text-text-primary'}`}
              style={{ width: 'calc(100% - 12px)' }}>
              <item.Icon className={`w-4 h-4 shrink-0 ${section === item.id ? 'text-accent' : 'text-text-muted'}`} />
              {item.label}
              {item.id === 'sentinel' && activeAlerts.length > 0 && (
                <span className={`ml-auto text-[10px] font-bold px-1.5 py-0.5 rounded-full ${critCount > 0 ? 'bg-danger/15 text-danger' : 'bg-warning/15 text-warning'}`}>{activeAlerts.length}</span>
              )}
              {item.id === 'users' && usersLoading && <Loader2 className="ml-auto w-3 h-3 animate-spin text-text-muted" />}
            </button>
          ))}
        </nav>

        <div className="p-3 border-t border-border">
          <div className="flex items-center gap-2 px-1">
            <div className="w-6 h-6 rounded-full bg-accent flex items-center justify-center text-[10px] font-bold text-white shrink-0">A</div>
            <span className="text-[11px] text-text-muted truncate">Admin</span>
          </div>
          <button onClick={() => router.push('/')} className="mt-2 w-full text-[11px] text-text-muted hover:text-text-primary py-1 transition text-left px-1">← Back to War Room</button>
        </div>
      </aside>

      {/* Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* SENTINEL strip */}
        <SentinelStrip alerts={sentinelAlerts} onJump={() => setSection('sentinel')} />

        <main className="flex-1 overflow-y-auto p-6">
          <AnimatePresence mode="wait">
            <motion.div key={section} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
              {section === 'overview' && <OverviewSection status={systemStatus} users={users} memStats={memStats} wsConnected={wsConnected} />}
              {section === 'users' && <UsersSection users={users} activeUid={activeUid} />}
              {section === 'feed' && <LiveFeedSection events={wsEvents} paused={feedPaused} onPause={() => setFeedPaused(p => !p)} onClear={() => setWsEvents([])} />}
              {section === 'vault' && <DealVaultSection users={users} onDelete={deleteIncident} />}
              {section === 'build' && <BuildLogSection gitLog={gitLog} vercelDeps={vercelDeps} onRefresh={fetchBuildData} />}
              {section === 'agents' && <AgentPerfSection users={users} memStats={memStats} />}
              {section === 'patterns' && <PatternsSection users={users} />}
              {section === 'controls' && <SystemControlsSection status={systemStatus} onRefresh={fetchAll} />}
              {section === 'sentinel' && <SentinelSection alerts={sentinelAlerts} setAlerts={setSentinelAlerts} />}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
