// pages/index.tsx — FUSION VC Command Center
import React, { useState, useEffect, useRef, useCallback } from 'react'
// @ts-ignore — suppress missing type defs for lucide-react icons
import Head from 'next/head'
import { useAgentWebSocket } from '@/hooks/useAgentWebSocket'
import { AGENTS, API_BASE } from '@/lib/agents'
import { renderMarkdown } from '@/lib/markdown'
import Logo from '@/components/Logo'
import AgentGraph from '@/components/AgentGraph'
import LiveLog from '@/components/LiveLog'
import AgentDetailPanel from '@/components/AgentDetailPanel'
import MemoryView from '@/components/MemoryView'
import SettingsView from '@/components/SettingsView'
import { IntegrationsView } from '@/components/IntegrationsView'
import { PartnersView } from '@/components/PartnersView'
import DocsView from '@/components/DocsView'
import DemoDeals from '@/components/DemoDeals'
import {
  LayoutDashboard,
  History,
  Lightbulb,
  Plug,
  Users,
  Settings,
  ChevronLeft,
  Send,
  Plus,
  Sun,
  Moon,
  BookOpen,
  MessageSquare,
  Maximize2,
  Minimize2,
  X,
  AlertCircle,
  Download,
  ShieldCheck,
  ShieldX,
  Scale,
  Users2,
  FileText,
  Menu,
} from 'lucide-react'

type Tab = 'overview' | 'history' | 'insights' | 'integrations' | 'partners' | 'settings' | 'docs'
type OverviewTab = 'roundtable' | 'minutes' | 'binders'

interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
  incidentId?: string
  intent?: string
}

const NAV_GROUPS = [
  {
    title: 'MAIN',
    items: [{ id: 'overview' as Tab, label: 'Overview', Icon: LayoutDashboard }],
  },
  {
    title: 'REPORTS',
    items: [
      { id: 'history' as Tab, label: 'History', Icon: History },
      { id: 'insights' as Tab, label: 'Insights', Icon: Lightbulb },
    ],
  },
  {
    title: 'WORKSPACE',
    items: [
      { id: 'integrations' as Tab, label: 'Integrations', Icon: Plug },
      { id: 'partners' as Tab, label: 'Partners', Icon: Users },
    ],
  },
  {
    title: 'HELP',
    items: [{ id: 'docs' as Tab, label: 'Documentation', Icon: BookOpen }],
  },
]

const CHAT_MIN = 300
const CHAT_MAX = 600
const CHAT_DEFAULT = 380

function verdictTone(raw?: string): { label: string; cls: string; ring: string; Icon: typeof ShieldCheck } {
  const v = String(raw || '').toUpperCase()
  if (v === 'INVEST' || v === 'APPROVE' || v === 'YES')
    return { label: 'INVEST', cls: 'text-success', ring: 'border-success/30 bg-success-soft', Icon: ShieldCheck }
  if (v === 'CONDITIONAL')
    return { label: 'CONDITIONAL', cls: 'text-warning', ring: 'border-warning/30 bg-warning-soft', Icon: Scale }
  return { label: v || 'PASS', cls: 'text-danger', ring: 'border-danger/30 bg-danger-soft', Icon: ShieldX }
}

function riskTone(score: number): { cls: string; bar: string } {
  if (score >= 7.5) return { cls: 'text-danger', bar: 'bg-danger' }
  if (score >= 5) return { cls: 'text-warning', bar: 'bg-warning' }
  return { cls: 'text-success', bar: 'bg-success' }
}

export default function FUSION() {
  const {
    agentStates, agentOutputs, logEvents, threatScore, ceoDecision, isConnected, resetAll,
  } = useAgentWebSocket()

  const [tab, setTab] = useState<Tab>('overview')
  const [overviewTab, setOverviewTab] = useState<OverviewTab>('roundtable')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [chatCollapsed, setChatCollapsed] = useState(false)
  const [chatFullscreen, setChatFullscreen] = useState(false)
  const [isSimulating, setIsSimulating] = useState(false)
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')

  const [activeIncidentId, setActiveIncidentId] = useState<string | null>(null)
  const maxFileSizeMb = 2

  // Resizable chat width (persisted)
  const [chatWidth, setChatWidth] = useState<number>(CHAT_DEFAULT)
  const chatWidthRef = useRef(chatWidth)
  const resizingRef = useRef(false)
  useEffect(() => { chatWidthRef.current = chatWidth }, [chatWidth])

  // Load persisted chat width on mount
  useEffect(() => {
    const w = localStorage.getItem('fusion.chatWidth')
    if (w) setChatWidth(Math.min(CHAT_MAX, Math.max(CHAT_MIN, Number(w))))
  }, [])

  // Chat resize drag
  useEffect(() => {
    const move = (e: MouseEvent) => {
      if (!resizingRef.current) return
      const w = Math.min(CHAT_MAX, Math.max(CHAT_MIN, window.innerWidth - e.clientX))
      setChatWidth(w)
    }
    const up = () => {
      if (!resizingRef.current) return
      resizingRef.current = false
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      localStorage.setItem('fusion.chatWidth', String(Math.round(chatWidthRef.current)))
    }
    window.addEventListener('mousemove', move)
    window.addEventListener('mouseup', up)
    return () => {
      window.removeEventListener('mousemove', move)
      window.removeEventListener('mouseup', up)
    }
  }, [])

  const startResize = (e: React.MouseEvent) => {
    e.preventDefault()
    resizingRef.current = true
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }

  // File Upload State
  const [isDragging, setIsDragging] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'processing' | 'complete'>('idle')
  const [uploadedFile, setUploadedFile] = useState<{ name: string; size: number } | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Chat State
  const [chatInput, setChatInput] = useState('')
  const [chatHistory, setChatHistory] = useState<ChatTurn[]>([])
  const [chatThinking, setChatThinking] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  // Mentions Autocomplete
  const [showMentionPopup, setShowMentionPopup] = useState(false)
  const [mentionSearch, setMentionSearch] = useState('')
  const [mentionIndex, setMentionIndex] = useState(0)
  const [cursorPosition, setCursorPosition] = useState(0)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const agentsList = AGENTS.map(a => ({
    handle: `@${a.name.replace(/_/g, '-')}`,
    name: a.displayName,
    icon: a.icon,
  }))
  const filteredAgents = agentsList.filter(a =>
    a.handle.toLowerCase().includes(mentionSearch.toLowerCase()) ||
    a.name.toLowerCase().includes(mentionSearch.toLowerCase())
  )

  // Theme
  useEffect(() => {
    const saved = localStorage.getItem('theme') as 'dark' | 'light' | null
    if (saved) setTheme(saved)
    else if (window.matchMedia?.('(prefers-color-scheme: light)').matches) setTheme('light')
  }, [])

  useEffect(() => {
    const root = window.document.documentElement
    theme === 'dark' ? root.classList.add('dark') : root.classList.remove('dark')
  }, [theme])

  useEffect(() => {
    if (ceoDecision) { setIsSimulating(false); setUploadStatus('idle') }
  }, [ceoDecision])

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [chatHistory, chatThinking])

  // Load chat history
  useEffect(() => {
    fetch(`${API_BASE}/api/v1/chat/history?limit=40`).then(r => r.json()).then(d => {
      if (Array.isArray(d.history) && d.history.length) {
        setChatHistory(d.history.map((t: any) => ({ role: t.role, content: t.content, incidentId: t.meta?.incident_id, intent: t.meta?.intent })))
      }
    }).catch(() => {})
  }, [])

  // File Upload
  const handleFileDrop = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(false); const f = e.dataTransfer.files[0]; if (f) handleFileUpload(f) }
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => { const f = e.target.files?.[0]; if (f) handleFileUpload(f) }

  const handleFileUpload = async (file: File) => {
    setUploadError(null)
    const fileSizeMb = file.size / (1024 * 1024)
    if (fileSizeMb > maxFileSizeMb) {
      setUploadError(`That file is ${fileSizeMb.toFixed(1)} MB — the limit is 2 MB. Please upload a smaller document.`)
      return
    }

    setUploadedFile({ name: file.name, size: file.size })
    setUploadStatus('uploading')

    try {
      const formData = new FormData()
      formData.append('file', file)
      const response = await fetch(`${API_BASE}/api/v1/upload-pitch`, { method: 'POST', body: formData })
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Upload failed')
      }
      const data = await response.json()
      setActiveIncidentId(data.incident_id)
      setUploadStatus('complete')
      triggerDealSimulation(data.company_name)
    } catch (err: any) {
      setUploadStatus('idle')
      setUploadedFile(null)
      setUploadError(err.message || 'We could not read that document. Try a JSON, PDF, TXT, or MD file.')
    }
  }

  const triggerDealSimulation = async (companyName: string = 'NovaPay Inc') => {
    setIsSimulating(true); setTab('overview'); setOverviewTab('roundtable')
    try {
      const res = await fetch(`${API_BASE}/api/trigger-deal?company=${encodeURIComponent(companyName)}`, { method: 'POST' })
      const data = await res.json()
      if (data.deal_id) setActiveIncidentId(data.deal_id)
    } catch {
      setIsSimulating(false)
      setUploadStatus('idle')
      setUploadError('Cannot reach the FUSION backend — is it running on port 8000?')
    }
  }

  const resetSimulation = async () => {
    setIsSimulating(false); setUploadStatus('idle'); setUploadedFile(null); setActiveIncidentId(null); setUploadError(null); resetAll()
    try { await fetch(`${API_BASE}/api/reset`, { method: 'POST' }) } catch {}
  }

  const toggleTheme = () => setTheme(prev => { const next = prev === 'dark' ? 'light' : 'dark'; localStorage.setItem('theme', next); return next })

  const triggerMockUpload = () => {
    setUploadError(null)
    setUploadedFile({ name: 'novapay_pitch.json', size: 9481 }); setUploadStatus('uploading')
    setTimeout(() => { setUploadStatus('complete'); triggerDealSimulation('NovaPay Inc') }, 800)
  }

  // Chat
  const sendChatMessage = useCallback(async (textToSend?: string) => {
    const text = (textToSend ?? chatInput).trim()
    if (!text || chatThinking) return
    setChatHistory(prev => [...prev, { role: 'user', content: text }]); setChatInput(''); setChatThinking(true); setShowMentionPopup(false)
    try {
      const response = await fetch(`${API_BASE}/api/v1/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_message: text, incident_id: activeIncidentId || undefined }),
      })
      const data = await response.json()
      if (data.incident_id) setActiveIncidentId(data.incident_id)
      if (data.dispatched) { setIsSimulating(true); setUploadStatus('processing'); setTab('overview') }
      setChatHistory(prev => [...prev, { role: 'assistant', content: data.commander_response, incidentId: data.incident_id, intent: data.intent }])
    } catch {
      setChatHistory(prev => [...prev, { role: 'assistant', content: 'Cannot reach the Managing Partner — is the FUSION backend running?' }])
    } finally { setChatThinking(false) }
  }, [chatInput, chatThinking, activeIncidentId])

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value; setChatInput(val)
    const pos = e.target.selectionStart || 0; setCursorPosition(pos)
    const textBeforeCursor = val.slice(0, pos); const words = textBeforeCursor.split(/\s/); const lastWord = words[words.length - 1]
    if (lastWord.startsWith('@')) { setShowMentionPopup(true); setMentionSearch(lastWord); setMentionIndex(0) } else { setShowMentionPopup(false) }
  }

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (showMentionPopup) {
      if (e.key === 'ArrowDown') { e.preventDefault(); setMentionIndex(prev => (prev + 1) % filteredAgents.length) }
      else if (e.key === 'ArrowUp') { e.preventDefault(); setMentionIndex(prev => (prev - 1 + filteredAgents.length) % filteredAgents.length) }
      else if (e.key === 'Enter') { e.preventDefault(); if (filteredAgents[mentionIndex]) insertMention(filteredAgents[mentionIndex].handle) }
      else if (e.key === 'Escape') { setShowMentionPopup(false) }
    } else if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage() }
  }

  const insertMention = (handle: string) => {
    const val = chatInput; const pos = cursorPosition; const textBeforeCursor = val.slice(0, pos); const textAfterCursor = val.slice(pos)
    const words = textBeforeCursor.split(/\s/); words[words.length - 1] = handle; const newTextBeforeCursor = words.join(' ') + ' '
    setChatInput(newTextBeforeCursor + textAfterCursor); setShowMentionPopup(false)
    setTimeout(() => { if (inputRef.current) { inputRef.current.focus(); const newPos = newTextBeforeCursor.length; inputRef.current.setSelectionRange(newPos, newPos) } }, 10)
  }

  // Auto-grow the textarea
  useEffect(() => {
    const el = inputRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }, [chatInput, chatFullscreen])

  const isActive = (tid: Tab) => tab === tid
  const partnersDone = Object.values(agentStates).filter(s => s === 'done').length
  const partnersTotal = AGENTS.length

  /* ── Shared chat fragments (rendered in either side panel or full-screen) ── */
  const chatMessages = (big: boolean) => (
    <div className={`flex-1 overflow-y-auto flex flex-col gap-3 bg-bg-base ${big ? 'px-4 sm:px-6 py-4 sm:py-6' : 'p-3 sm:p-4'}`}>
      {chatHistory.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center px-4">
          <div className="w-12 h-12 rounded-2xl bg-accent-soft flex items-center justify-center mb-3">
            <Logo className="w-6 h-6 text-accent" />
          </div>
          <h4 className="text-[12px] sm:text-[13px] font-semibold text-text-primary mb-1">Managing Partner</h4>
          <p className="text-[11px] sm:text-[11.5px] text-text-secondary mb-5 max-w-[260px]">Ask about deal financials, lawsuits, tech vulnerabilities, or market validation — or just say hello.</p>
          <div className="flex flex-col gap-1.5 w-full max-w-[280px]">
            {['Evaluate NovaPay Inc', 'What should I look for in this deal?', 'How does FUSION work?'].map(s => (
              <button key={s} onClick={() => sendChatMessage(s)} className="text-[11.5px] text-left px-3 py-2 bg-bg-subtle border border-border rounded-lg hover:border-accent/50 hover:text-accent transition-colors text-text-secondary">
                {s}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className={big ? 'w-full max-w-3xl mx-auto flex flex-col gap-4' : 'flex flex-col gap-3'}>
          {chatHistory.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {m.role === 'assistant' && (
                <div className="w-7 h-7 rounded-lg bg-accent-soft flex items-center justify-center mr-2 shrink-0 self-start mt-0.5">
                  <Logo className="w-4 h-4 text-accent" />
                </div>
              )}
              <div className={`${big ? 'max-w-[85%] text-[13.5px]' : 'max-w-[88%] text-[12.5px]'} rounded-2xl px-4 py-2.5 leading-relaxed ${
                m.role === 'user'
                  ? 'bg-accent text-white rounded-br-md'
                  : 'bg-bg-subtle border border-border text-text-primary rounded-bl-md'
              }`}>
                {m.role === 'user'
                  ? <p className="whitespace-pre-wrap">{m.content}</p>
                  : <div className="space-y-0.5">{renderMarkdown(m.content)}</div>}
              </div>
            </div>
          ))}
          {chatThinking && (
            <div className="flex justify-start">
              <div className="w-7 h-7 rounded-lg bg-accent-soft flex items-center justify-center mr-2 shrink-0">
                <Logo className="w-4 h-4 text-accent" />
              </div>
              <div className="bg-bg-subtle border border-border rounded-2xl rounded-bl-md px-3.5 py-3 flex gap-1.5 items-center">
                <span className="w-1.5 h-1.5 bg-accent rounded-full animate-pulse" />
                <span className="w-1.5 h-1.5 bg-accent rounded-full animate-pulse" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-accent rounded-full animate-pulse" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          )}
        </div>
      )}
      <div ref={chatEndRef} />
    </div>
  )

  const chatInputBar = (big: boolean) => (
    <div className={`bg-bg-card border-t border-border ${big ? 'px-4 sm:px-6 py-3 sm:py-4' : 'p-2.5 sm:p-3'}`}>
      <div className={big ? 'w-full max-w-3xl mx-auto' : ''}>
        {showMentionPopup && filteredAgents.length > 0 && (
          <div className="mb-2 bg-bg-card border border-border rounded-xl shadow-md overflow-hidden">
            <div className="px-3 py-1.5 border-b border-border text-[10px] font-semibold text-text-muted uppercase tracking-wider">Mention Partner</div>
            {filteredAgents.map((a, i) => (
              <button key={a.handle} onClick={() => insertMention(a.handle)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 text-left text-[11px] transition ${i === mentionIndex ? 'bg-accent-soft text-accent font-semibold' : 'text-text-secondary hover:bg-bg-subtle'}`}>
                <span className="text-[13px]">{a.icon}</span>
                <div>
                  <div className="font-semibold text-[11px]">{a.handle}</div>
                  <div className="text-[9px] text-text-muted">{a.name}</div>
                </div>
              </button>
            ))}
          </div>
        )}
        <div className="flex items-end gap-2">
          <button onClick={() => fileInputRef.current?.click()}
            className="w-9 h-9 rounded-lg bg-bg-subtle border border-border hover:border-accent/50 hover:text-accent text-text-muted flex items-center justify-center transition shrink-0" title="Upload document">
            <Plus className="w-4 h-4" />
          </button>
          <textarea
            ref={inputRef}
            value={chatInput}
            onChange={handleInputChange}
            onKeyDown={handleInputKeyDown}
            placeholder="Ask your partner…  (@ to mention, Shift+Enter for newline)"
            rows={1}
            className="flex-1 resize-none bg-bg-subtle border border-border rounded-xl px-3.5 py-2.5 text-[13px] leading-relaxed focus:outline-none focus:border-accent transition-colors text-text-primary placeholder:text-text-muted max-h-40"
            disabled={chatThinking}
          />
          <button onClick={() => sendChatMessage()} disabled={!chatInput.trim() || chatThinking}
            className={`w-9 h-9 flex items-center justify-center rounded-lg transition shrink-0 ${chatInput.trim() && !chatThinking ? 'bg-accent text-white hover:bg-accent-hover' : 'bg-bg-muted text-text-muted cursor-not-allowed'}`}>
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )

  const chatHeader = (big: boolean) => (
    <div className="flex items-center gap-3 p-4 border-b border-border">
      <div className="w-8 h-8 rounded-lg bg-accent-soft flex items-center justify-center shrink-0">
        <Logo className="w-5 h-5 text-accent" />
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="font-semibold text-text-primary text-[13px]">Managing Partner</h3>
        <div className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-success' : 'bg-text-muted'}`} />
          <span className="text-[10px] font-medium text-text-secondary">{isConnected ? 'Ready' : 'Offline'}</span>
        </div>
      </div>
      <button onClick={() => setChatFullscreen(f => !f)} title={big ? 'Exit full screen' : 'Full screen'}
        className="w-8 h-8 rounded-lg border border-border flex items-center justify-center text-text-muted hover:text-text-primary hover:bg-bg-muted transition">
        {big ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
      </button>
      {big && (
        <button onClick={() => setChatFullscreen(false)} title="Close"
          className="w-8 h-8 rounded-lg border border-border flex items-center justify-center text-text-muted hover:text-text-primary hover:bg-bg-muted transition">
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  )

  const hasActivity = (Array.isArray(logEvents) && logEvents.length > 0) || isSimulating || uploadStatus !== 'idle'

  return (
    <div className="flex h-[100dvh] w-screen bg-bg-base text-text-primary font-sans antialiased overflow-hidden">
      <Head>
        <title>FUSION — AI-Powered Investment Committee</title>
        <meta name="description" content="Five specialized AI partner agents that orchestrate startup due diligence and deliver unified investment verdicts." />
        <link rel="icon" href="/favicon.ico" />
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
      </Head>

      {/* ═══════════ MOBILE OVERLAY ═══════════ */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 md:hidden" onClick={() => setMobileMenuOpen(false)}>
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
          <aside className="absolute left-0 top-0 h-full w-[260px] bg-bg-subtle border-r border-border flex flex-col animate-slide-in-left" onClick={e => e.stopPropagation()}>
            <div className="h-[52px] flex items-center border-b border-border px-4 gap-2.5">
              <Logo className="w-7 h-7 text-accent shrink-0" />
              <span className="font-bold text-[15px] tracking-tight text-text-primary">FUSION</span>
              <button onClick={() => setMobileMenuOpen(false)} className="ml-auto w-8 h-8 flex items-center justify-center rounded-lg hover:bg-bg-muted text-text-muted">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto py-4 noscrollbar">
              {NAV_GROUPS.map((group, idx) => (
                <div key={idx} className="mb-5">
                  <div className="px-4 mb-2 text-[11px] font-bold text-text-muted tracking-wider">{group.title}</div>
                  <ul className="space-y-0.5">
                    {group.items.map((item) => {
                      const active = isActive(item.id)
                      return (
                        <li key={item.id} className="px-2">
                          <button onClick={() => { setTab(item.id); setMobileMenuOpen(false) }}
                            className={`w-full flex items-center gap-3 px-2.5 py-2.5 rounded-lg transition-colors group relative text-[13px] ${active ? 'bg-accent-soft text-accent font-semibold' : 'text-text-secondary hover:bg-bg-muted hover:text-text-primary'}`}>
                            {active && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-accent rounded-r-full" />}
                            <item.Icon className={`w-[18px] h-[18px] shrink-0 ${active ? 'text-accent' : 'text-text-muted group-hover:text-text-primary'}`} />
                            <span className="truncate">{item.label}</span>
                          </button>
                        </li>
                      )
                    })}
                  </ul>
                </div>
              ))}
            </div>
            <div className="p-2 border-t border-border">
              <button onClick={() => { setTab('settings'); setMobileMenuOpen(false) }}
                className={`w-full flex items-center gap-3 px-2.5 py-2.5 rounded-lg transition-colors text-[13px] ${isActive('settings') ? 'bg-accent-soft text-accent font-semibold' : 'text-text-secondary hover:bg-bg-muted hover:text-text-primary'}`}>
                <Settings className={`w-[18px] h-[18px] shrink-0 ${isActive('settings') ? 'text-accent' : 'text-text-muted'}`} />
                <span>Settings</span>
              </button>
            </div>
          </aside>
        </div>
      )}

      {/* ═══════════ LEFT SIDEBAR (desktop) ═══════════ */}
      <aside className={`relative h-full bg-bg-subtle border-r border-border transition-all duration-300 flex-col z-40 hidden md:flex ${sidebarCollapsed ? 'w-16' : 'w-[220px]'}`}>
        <div className="h-[52px] flex items-center border-b border-border pl-5 gap-2.5">
          <Logo className="w-7 h-7 text-accent shrink-0" />
          {!sidebarCollapsed && <span className="font-bold text-[15px] tracking-tight text-text-primary whitespace-nowrap">FUSION</span>}
        </div>

        <div className="flex-1 overflow-y-auto py-4 noscrollbar">
          {NAV_GROUPS.map((group, idx) => (
            <div key={idx} className="mb-5">
              {!sidebarCollapsed && <div className="px-4 mb-2 text-[11px] font-bold text-text-muted tracking-wider">{group.title}</div>}
              <ul className="space-y-0.5">
                {group.items.map((item) => {
                  const active = isActive(item.id)
                  return (
                    <li key={item.id} className="px-2">
                      <button onClick={() => setTab(item.id)} title={sidebarCollapsed ? item.label : undefined}
                        className={`w-full flex items-center gap-3 px-2.5 py-2 rounded-lg transition-colors group relative text-[13px] ${active ? 'bg-accent-soft text-accent font-semibold' : 'text-text-secondary hover:bg-bg-muted hover:text-text-primary'}`}>
                        {active && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-accent rounded-r-full" />}
                        <item.Icon className={`w-[18px] h-[18px] shrink-0 ${active ? 'text-accent' : 'text-text-muted group-hover:text-text-primary'}`} />
                        {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
                      </button>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
        </div>

        <div className="p-2 border-t border-border space-y-1">
          <button onClick={() => setTab('settings')}
            className={`w-full flex items-center gap-3 px-2.5 py-2 rounded-lg transition-colors text-[13px] ${isActive('settings') ? 'bg-accent-soft text-accent font-semibold' : 'text-text-secondary hover:bg-bg-muted hover:text-text-primary'}`}>
            <Settings className={`w-[18px] h-[18px] shrink-0 ${isActive('settings') ? 'text-accent' : 'text-text-muted'}`} />
            {!sidebarCollapsed && <span>Settings</span>}
          </button>
          <button onClick={() => setSidebarCollapsed(!sidebarCollapsed)} title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className="w-full p-2 flex items-center justify-center text-text-muted hover:text-text-primary hover:bg-bg-muted rounded-lg transition-colors">
            <ChevronLeft className={`w-[18px] h-[18px] transition-transform duration-300 ${sidebarCollapsed ? 'rotate-180' : ''}`} />
          </button>
        </div>
      </aside>

      {/* ═══════════ MAIN COLUMN ═══════════ */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <header className="h-[52px] border-b border-border flex items-center justify-between px-3 sm:px-6 shrink-0 bg-bg-card/80 backdrop-blur-xl">
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Mobile hamburger */}
            <button onClick={() => setMobileMenuOpen(true)} className="w-8 h-8 rounded-lg border border-border flex items-center justify-center text-text-muted hover:text-text-primary hover:bg-bg-muted transition md:hidden">
              <Menu className="w-4 h-4" />
            </button>
            {/* Mobile logo */}
            <Logo className="w-6 h-6 text-accent md:hidden shrink-0" />
            <h1 className="font-bold text-[14px] sm:text-[15px] capitalize text-text-primary">{tab}</h1>
            <span className={`hidden sm:inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wider ${isConnected ? 'bg-success-soft text-success' : 'bg-danger-soft text-danger'}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${isConnected ? 'bg-success animate-pulse' : 'bg-danger'}`} />
              {isConnected ? 'Online' : 'Offline'}
            </span>
          </div>
          <div className="flex items-center gap-1.5 sm:gap-2">
            {tab === 'overview' && (isSimulating || uploadedFile || hasActivity) && (
              <button onClick={resetSimulation} className="h-8 px-2 sm:px-3 rounded-lg text-[10px] sm:text-[11px] font-semibold border border-border text-text-secondary hover:text-text-primary hover:bg-bg-muted transition">
                Reset
              </button>
            )}
            <button onClick={() => { if (window.innerWidth < 1024) { setChatFullscreen(f => !f); setChatCollapsed(false) } else { setChatCollapsed(prev => !prev); setChatFullscreen(false) } }}
              className={`w-8 h-8 rounded-lg border flex items-center justify-center transition cursor-pointer ${!chatCollapsed ? 'border-accent/30 bg-accent-soft text-accent' : 'border-border text-text-muted hover:bg-bg-muted hover:text-text-primary'}`}
              title={chatCollapsed ? 'Show Chat' : 'Hide Chat'}>
              <MessageSquare className="w-4 h-4" />
            </button>
            <button onClick={toggleTheme} className="w-8 h-8 rounded-lg border border-border flex items-center justify-center hover:bg-bg-muted text-text-muted hover:text-text-primary transition cursor-pointer">
              {theme === 'dark' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
            </button>
          </div>
        </header>

        {/* Content + Chat */}
        <div className="flex-1 flex overflow-hidden">
          <main className="flex-1 overflow-y-auto overflow-x-hidden relative">
            <div className="p-4 sm:p-6 lg:p-8 max-w-[1100px] w-full mx-auto">

              {/* ═══ OVERVIEW ═══ */}
              {tab === 'overview' && (
                <div className="space-y-6">
                  {!hasActivity ? (
                    /* Idle: uploader + demo deals */
                    <div className="flex flex-col items-center max-w-[860px] mx-auto py-4 sm:py-6 space-y-6">
                      <div className="flex flex-col items-center text-center space-y-4 sm:space-y-5 w-full max-w-[560px]">
                        <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-xl bg-accent-soft flex items-center justify-center">
                          <Logo className="w-5 h-5 sm:w-6 sm:h-6 text-accent" />
                        </div>
                        <div>
                          <h2 className="text-[18px] sm:text-[22px] font-bold tracking-tight text-text-primary">Evaluate a startup</h2>
                          <p className="text-[12px] sm:text-[13px] text-text-secondary mt-1.5 leading-relaxed max-w-sm mx-auto">
                            Drop your own pitch deck, financials brief, or memo — or explore one of the demo deals below. FUSION mobilizes five partner agents and returns a committee verdict.
                          </p>
                        </div>
                        <div
                          onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
                          onDragLeave={() => setIsDragging(false)}
                          onDrop={handleFileDrop}
                          onClick={() => fileInputRef.current?.click()}
                          className={`w-full border border-dashed rounded-2xl p-6 sm:p-9 cursor-pointer transition flex flex-col items-center gap-2 sm:gap-3 ${isDragging ? 'border-accent bg-accent-soft' : 'border-border-strong hover:border-accent/50 hover:bg-bg-subtle'}`}>
                          <FileText className="w-6 h-6 text-text-muted" />
                          <p className="text-[12px] sm:text-[13px] font-medium text-text-primary">Drag &amp; drop or click to upload</p>
                          <div className="flex items-center gap-1.5">
                            {['JSON', 'TXT', 'PDF', 'MD'].map(ext => (
                              <span key={ext} className="text-[10px] font-semibold px-2 py-0.5 rounded bg-bg-muted text-text-muted">{ext}</span>
                            ))}
                          </div>
                        </div>
                        {uploadError && (
                          <div className="w-full rounded-xl bg-danger-soft border border-danger/25 px-4 py-3 flex items-start gap-2.5 text-left">
                            <AlertCircle className="w-4 h-4 text-danger mt-0.5 shrink-0" />
                            <p className="text-[12px] text-danger">{uploadError}</p>
                          </div>
                        )}
                      </div>

                      <DemoDeals onRun={(co) => triggerDealSimulation(co)} />
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {/* Analyzing banner */}
                      {(uploadStatus === 'uploading' || uploadStatus === 'processing' || (isSimulating && !ceoDecision)) && (
                        <div className="rounded-xl bg-accent-soft border border-accent/20 p-4 flex items-center gap-3">
                          <span className="relative flex h-2.5 w-2.5">
                            <span className="absolute inline-flex h-full w-full rounded-full bg-accent opacity-60 animate-ping" />
                            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-accent" />
                          </span>
                          <div>
                            <h4 className="text-[12px] font-semibold text-accent">
                              {uploadStatus === 'uploading' ? 'Reading the document…' : 'Committee in session — partners are auditing the deal…'}
                            </h4>
                            {uploadedFile && <p className="text-[10px] text-text-muted mt-0.5">{uploadedFile.name}</p>}
                          </div>
                        </div>
                      )}

                      {/* Verdict hero */}
                      <VerdictHero
                        decision={ceoDecision}
                        risk={threatScore}
                        partnersDone={partnersDone}
                        partnersTotal={partnersTotal}
                        isSimulating={isSimulating}
                        onDownloadPdf={activeIncidentId ? () => window.open(`${API_BASE}/api/v1/generate-report?incident_id=${activeIncidentId}&format=pdf`, '_blank') : undefined}
                        onDownloadMd={activeIncidentId ? () => window.open(`${API_BASE}/api/v1/generate-report?incident_id=${activeIncidentId}&format=md`, '_blank') : undefined}
                      />

                      {/* Tabs */}
                      <div>
                        <div className="flex items-center gap-1 border-b border-border mb-4">
                          {([
                            { id: 'roundtable' as OverviewTab, label: 'Roundtable', Icon: Users2 },
                            { id: 'minutes' as OverviewTab, label: 'Minutes', Icon: FileText },
                            { id: 'binders' as OverviewTab, label: 'Diligence Binders', Icon: BookOpen },
                          ]).map(t => (
                            <button key={t.id} onClick={() => setOverviewTab(t.id)}
                              className={`flex items-center gap-1.5 px-3.5 py-2.5 text-[12.5px] font-medium border-b-2 -mb-px transition ${overviewTab === t.id ? 'border-accent text-accent' : 'border-transparent text-text-secondary hover:text-text-primary'}`}>
                              <t.Icon className="w-4 h-4" />
                              {t.label}
                            </button>
                          ))}
                        </div>
                        {overviewTab === 'roundtable' && <AgentGraph agentStates={agentStates} theme={theme} />}
                        {overviewTab === 'minutes' && <div className="h-[420px]"><LiveLog events={logEvents} /></div>}
                        {overviewTab === 'binders' && <AgentDetailPanel agentStates={agentStates} agentOutputs={agentOutputs} devMode={false} />}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ═══ OTHER TABS ═══ */}
              {tab === 'history' && <MemoryView defaultTab="incidents" />}
              {tab === 'insights' && <MemoryView defaultTab="patterns" />}
              {tab === 'integrations' && <IntegrationsView />}
              {tab === 'partners' && <PartnersView />}
              {tab === 'settings' && <SettingsView theme={theme} onToggleTheme={toggleTheme} />}
              {tab === 'docs' && <DocsView />}
            </div>
          </main>

          {/* ═══ RESIZABLE SIDE CHAT ═══ */}
          {!chatCollapsed && !chatFullscreen && (
            <div className="relative h-full hidden lg:flex shrink-0" style={{ width: chatWidth }}>
              {/* drag handle */}
              <div onMouseDown={startResize} className="absolute left-0 top-0 h-full w-1.5 -ml-0.5 cursor-col-resize z-20 group">
                <div className="h-full w-px mx-auto bg-border group-hover:bg-accent transition-colors" />
              </div>
              <div className="flex-1 h-full flex flex-col border-l border-border bg-bg-card min-w-0">
                {chatHeader(false)}
                {chatMessages(false)}
                {chatInputBar(false)}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ═══ FULL-SCREEN CHAT OVERLAY ═══ */}
      {chatFullscreen && (
        <div className="fixed inset-0 z-50 bg-bg-base flex flex-col animate-fade-in-up">
          {chatHeader(true)}
          {chatMessages(true)}
          {chatInputBar(true)}
        </div>
      )}

      {/* Hidden file input */}
      <input type="file" ref={fileInputRef} onChange={handleFileSelect} className="hidden" accept=".json,.txt,.pdf,.md" />
    </div>
  )
}

/* ────────────────────────────────────────────────────────────── */
/*  Verdict hero — condenses the old ExecutivePanel + ThreatGauge   */
/* ────────────────────────────────────────────────────────────── */
function VerdictHero({
  decision, risk, partnersDone, partnersTotal, isSimulating, onDownloadPdf, onDownloadMd,
}: {
  decision: Record<string, any> | null
  risk: number
  partnersDone: number
  partnersTotal: number
  isSimulating: boolean
  onDownloadPdf?: () => void
  onDownloadMd?: () => void
}) {
  const has = decision && typeof decision.verdict === 'string'
  const tone = verdictTone(decision?.verdict)
  const rTone = riskTone(risk)
  const confidence = typeof decision?.confidence === 'number' ? Math.max(0, Math.min(100, decision.confidence)) : 0
  const riskPct = Math.max(0, Math.min(100, (risk / 10) * 100))

  return (
    <div className="rounded-2xl border border-border bg-bg-card shadow-sm overflow-hidden">
      <div className="grid grid-cols-1 md:grid-cols-12">
        {/* Verdict */}
        <div className="md:col-span-7 p-4 sm:p-6 md:border-r border-b md:border-b-0 border-border">
          <div className="flex items-center gap-2 mb-3 sm:mb-4">
            <Scale className="w-4 h-4 text-text-muted" />
            <span className="text-[10px] font-bold uppercase tracking-wider text-text-muted">Committee Verdict</span>
          </div>

          {has ? (
            <>
              <div className="flex items-center gap-3">
                <span className={`inline-flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-1.5 sm:py-2 rounded-xl border ${tone.ring}`}>
                  <tone.Icon className={`w-4 h-4 sm:w-5 sm:h-5 ${tone.cls}`} />
                  <span className={`font-serif-display text-xl sm:text-2xl font-semibold ${tone.cls}`}>{tone.label}</span>
                </span>
                <div className="text-text-secondary text-[12px] sm:text-[13px]">
                  <span className="font-semibold text-text-primary tabular-nums">{confidence}%</span> confidence
                </div>
              </div>
              <div className="mt-4 h-1.5 rounded-full bg-bg-muted overflow-hidden max-w-sm">
                <div className={`h-full rounded-full ${tone.cls.replace('text-', 'bg-')}`} style={{ width: `${confidence}%` }} />
              </div>
              <div className="mt-4 sm:mt-5 flex flex-wrap gap-2.5">
                {onDownloadPdf && (
                  <button
                    onClick={onDownloadPdf}
                    className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-accent text-white hover:bg-accent/90 active:scale-95 text-[11px] sm:text-[12px] font-semibold shadow-sm transition-all duration-150"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download PDF Report
                  </button>
                )}
                {onDownloadMd && (
                  <button
                    onClick={onDownloadMd}
                    className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg border border-border bg-bg-card hover:bg-bg-muted active:scale-95 text-text-primary text-[11px] sm:text-[12px] font-semibold transition-all duration-150"
                  >
                    <FileText className="w-3.5 h-3.5 text-text-muted" />
                    Download Markdown
                  </button>
                )}
              </div>
            </>
          ) : (
            <div className="py-2 sm:py-3">
              <div className="font-serif-display text-xl sm:text-2xl font-semibold text-text-primary">
                {isSimulating ? 'Deliberating…' : 'Awaiting verdict'}
              </div>
              <p className="text-[12.5px] text-text-secondary mt-1.5 max-w-sm leading-relaxed">
                {isSimulating
                  ? 'Partners are auditing the deal and building the recommendation.'
                  : 'Submit a deal to receive the committee’s verdict memo.'}
              </p>
            </div>
          )}
        </div>

        {/* Risk + progress */}
        <div className="md:col-span-5 p-4 sm:p-6 bg-bg-subtle/40">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[10px] font-bold uppercase tracking-wider text-text-muted">Weighted Risk</span>
            <span className="text-[10px] text-text-muted tabular-nums">{partnersDone}/{partnersTotal} partners</span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className={`text-3xl sm:text-4xl font-bold tabular-nums tracking-tight font-mono ${risk > 0 ? rTone.cls : 'text-text-muted'}`}>
              {risk > 0 ? (risk % 1 === 0 ? risk.toFixed(0) : risk.toFixed(1)) : '—'}
            </span>
            {risk > 0 && <span className="text-sm text-text-muted font-mono">/10</span>}
          </div>
          <div className="mt-3 h-2 rounded-full bg-bg-muted overflow-hidden">
            <div className={`h-full rounded-full transition-all duration-700 ${rTone.bar}`} style={{ width: risk > 0 ? `${Math.max(riskPct, 3)}%` : '0%' }} />
          </div>
          <p className="mt-3 sm:mt-4 text-[10px] sm:text-[11px] text-text-muted leading-relaxed">
            Financial 30% · Legal 25% · Technical 25% · Market 20%
          </p>
        </div>
      </div>
    </div>
  )
}
