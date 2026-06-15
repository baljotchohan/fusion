// pages/index.tsx — FUSION VC Command Center
import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react'
// @ts-ignore — suppress missing type defs for lucide-react icons
import Head from 'next/head'
import { useAgentWebSocket } from '@/hooks/useAgentWebSocket'
import { AGENTS, API_BASE } from '@/lib/agents'
import { renderMarkdown } from '@/lib/markdown'
import Logo from '@/components/Logo'
import Wordmark from '@/components/Wordmark'
import FusionLogo from '@/components/FusionLogo'
import BandLogoFull from '@/components/BandLogoFull'
import AgentGraph from '@/components/AgentGraph'
import LiveLog from '@/components/LiveLog'
import AgentDetailPanel from '@/components/AgentDetailPanel'
import MemoryView from '@/components/MemoryView'
import SettingsView from '@/components/SettingsView'
import { IntegrationsView } from '@/components/IntegrationsView'
import { PartnersView } from '@/components/PartnersView'
import DocsView from '@/components/DocsView'
import DemoDeals from '@/components/DemoDeals'
import { AnimatePresence, motion } from 'framer-motion'
import { 
  Shield, Coins, Cpu, Globe, Play, CheckCircle, 
  Database, Network, Key, Mail, Lock, Sparkles, 
  RefreshCw, ChevronRight, HelpCircle, ArrowRight,
  Copy, Terminal
} from 'lucide-react'
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
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [checkingAuth, setCheckingAuth] = useState(true)

  const {
    agentStates, agentOutputs, logEvents, threatScore, ceoDecision, isConnected, resetAll,
    setCeoDecision, setThreatScore, showRecoveryPrompt, setShowRecoveryPrompt,
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
  const [activeCompany, setActiveCompany] = useState<string | null>(null)
  const maxFileSizeMb = 2

  const [lastActivityTime, setLastActivityTime] = useState<number>(Date.now())
  const [showStalledWarning, setShowStalledWarning] = useState(false)

  useEffect(() => {
    setLastActivityTime(Date.now())
  }, [logEvents, isSimulating])

  useEffect(() => {
    if (!isSimulating) {
      setShowStalledWarning(false)
      return
    }

    const interval = setInterval(() => {
      const secondsSinceLastActivity = (Date.now() - lastActivityTime) / 1000
      if (secondsSinceLastActivity > 90) {
        setShowStalledWarning(true)
      }
    }, 1000)

    return () => clearInterval(interval)
  }, [isSimulating, lastActivityTime])

  const handleRetrySimulation = () => {
    setShowStalledWarning(false)
    setShowRecoveryPrompt(false)
    if (activeCompany) {
      triggerDealSimulation(activeCompany)
    } else {
      triggerDealSimulation('NovaPay Inc')
    }
  }

  const forceVerdictSynthesis = async () => {
    try {
      setShowRecoveryPrompt(false)
      setShowStalledWarning(false)
      await fetch(`${API_BASE}/api/force-verdict?incident_id=${activeIncidentId || ''}`, { method: 'POST' })
    } catch (err) {
      console.error('Failed to force verdict synthesis:', err)
    }
  }

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

  // Restore the active deal's verdict + report buttons after a page refresh.
  // The backend can always re-derive the report from the persisted incident, so
  // we just re-seed the transient UI state from /deal-state on mount.
  useEffect(() => {
    const cached = localStorage.getItem('fusion.activeIncidentId')
    if (cached) setActiveIncidentId(cached)
    fetch(`${API_BASE}/api/v1/deal-state`).then(r => r.json()).then(d => {
      if (!d || !d.incident_id) return
      setActiveIncidentId(d.incident_id)
      if (d.company) setActiveCompany(d.company)
      if (d.report_available && d.verdict) {
        setCeoDecision({
          verdict: String(d.verdict).toUpperCase(),
          confidence: typeof d.confidence === 'number' ? d.confidence : 91,
          justification: 'Committee review completed.',
        })
        if (typeof d.weighted_score === 'number') setThreatScore(d.weighted_score)
      }
    }).catch(() => {})
  }, [setCeoDecision, setThreatScore])

  // Keep the active incident id durable across refreshes.
  useEffect(() => {
    if (activeIncidentId) localStorage.setItem('fusion.activeIncidentId', activeIncidentId)
    else localStorage.removeItem('fusion.activeIncidentId')
  }, [activeIncidentId])

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
      if (data.company_name) setActiveCompany(data.company_name)
      setUploadStatus('complete')
      triggerDealSimulation(data.company_name)
    } catch (err: any) {
      setUploadStatus('idle')
      setUploadedFile(null)
      setUploadError(err.message || 'We could not read that document. Try a JSON, PDF, TXT, or MD file.')
    }
  }

  const triggerDealSimulation = async (companyName: string = 'NovaPay Inc') => {
    resetAll()
    setIsSimulating(true); setActiveCompany(companyName); setTab('overview'); setOverviewTab('roundtable')
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
    setIsSimulating(false); setUploadStatus('idle'); setUploadedFile(null); setActiveIncidentId(null); setActiveCompany(null); setUploadError(null); resetAll()
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
      if (data.company || data.company_name) setActiveCompany(data.company || data.company_name)
      if (data.dispatched) { resetAll(); setIsSimulating(true); setUploadStatus('processing'); setTab('overview') }
      setChatHistory(prev => [...prev, { role: 'assistant', content: data.commander_response, incidentId: data.incident_id, intent: data.intent }])
    } catch {
      setChatHistory(prev => [...prev, { role: 'assistant', content: 'Cannot reach the Managing Partner — is the FUSION backend running?' }])
    } finally { setChatThinking(false) }
  }, [chatInput, chatThinking, activeIncidentId, resetAll])

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

  // Context-aware starter prompts: tailored to the active deal when one is loaded,
  // otherwise generic onboarding prompts.
  const chatSuggestions = useMemo(() => {
    const co = activeCompany?.trim()
    if (co && co.toLowerCase() !== 'unknown') {
      return [
        `What are the biggest red flags for ${co}?`,
        `Summarize the financial & legal risks for ${co}`,
        'What would change the committee verdict?',
      ]
    }
    return [
      'Evaluate the demo deal (NovaPay Inc)',
      'What does FUSION look for in a deal?',
      'How does the committee score risk?',
    ]
  }, [activeCompany])

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
            {chatSuggestions.map(s => (
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
        <div className="flex items-end gap-1.5 bg-bg-subtle border border-border rounded-2xl px-2 py-1.5 focus-within:border-accent transition-colors">
          <button onClick={() => fileInputRef.current?.click()}
            className="w-8 h-8 rounded-lg text-text-muted hover:bg-bg-muted hover:text-accent flex items-center justify-center transition shrink-0 self-end" title="Upload document">
            <Plus className="w-4 h-4" />
          </button>
          <textarea
            ref={inputRef}
            value={chatInput}
            onChange={handleInputChange}
            onKeyDown={handleInputKeyDown}
            placeholder="Ask your partner…  (@ to mention, Shift+Enter for newline)"
            rows={1}
            className="flex-1 resize-none bg-transparent border-0 px-1 py-1.5 text-[13px] leading-relaxed focus:outline-none text-text-primary placeholder:text-text-muted max-h-40"
            disabled={chatThinking}
          />
          <button onClick={() => sendChatMessage()} disabled={!chatInput.trim() || chatThinking}
            className={`w-8 h-8 flex items-center justify-center rounded-lg transition shrink-0 self-end ${chatInput.trim() && !chatThinking ? 'bg-accent text-white hover:bg-accent-hover' : 'bg-bg-muted text-text-muted cursor-not-allowed'}`}>
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

  const handleSignOut = () => {
    localStorage.removeItem('fusion_authed')
    setIsLoggedIn(false)
  }

  useEffect(() => {
    const authed = localStorage.getItem('fusion_authed')
    if (authed === 'true') {
      setIsLoggedIn(true)
    }
    setCheckingAuth(false)
  }, [])

  if (checkingAuth) {
    return (
      <div className="bg-[#020202] min-h-screen flex items-center justify-center font-mono text-accent">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          <span>Authenticating Venture Partner session...</span>
        </div>
      </div>
    )
  }

  if (!isLoggedIn) {
    return (
      <LandingPage 
        onLogin={() => {
          localStorage.setItem('fusion_authed', 'true')
          setIsLoggedIn(true)
        }} 
      />
    )
  }

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
              <Wordmark className="text-[15px]" logoClassName="w-7 h-7" />
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
          {sidebarCollapsed
            ? <Logo className="w-7 h-7 text-accent shrink-0" />
            : <Wordmark className="text-[15px] whitespace-nowrap" logoClassName="w-7 h-7" />}
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
            <button onClick={toggleTheme} className="w-8 h-8 rounded-lg border border-border flex items-center justify-center hover:bg-bg-muted text-text-muted hover:text-text-primary transition cursor-pointer" title="Toggle Theme">
              {theme === 'dark' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
            </button>
            <button onClick={handleSignOut} className="w-8 h-8 rounded-lg border border-border flex items-center justify-center hover:bg-bg-muted text-text-muted hover:text-text-primary transition cursor-pointer" title="Lock Boardroom / Sign Out">
              <Lock className="w-4 h-4" />
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

                      {/* Warning if simulation appears stalled */}
                      {showStalledWarning && (
                        <div className="rounded-xl bg-danger-soft border border-danger/20 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-slide-in-right">
                          <div className="flex items-center gap-3">
                            <AlertCircle className="w-5 h-5 text-danger shrink-0" />
                            <div>
                              <h4 className="text-[12px] font-semibold text-danger">Simulation may have stalled</h4>
                              <p className="text-[10px] text-text-muted mt-0.5">No activity detected from committee agents for over 90 seconds.</p>
                            </div>
                          </div>
                          <button
                            onClick={handleRetrySimulation}
                            className="h-8 px-3 rounded-lg text-[11px] font-semibold bg-danger text-white hover:bg-danger/90 active:scale-95 transition shrink-0"
                          >
                            Restart Diligence
                          </button>
                        </div>
                      )}

                      {/* Warning if managing partner is stuck but specialists are done */}
                      {showRecoveryPrompt && (
                        <div className="rounded-xl bg-warning-soft border border-warning/20 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-slide-in-right">
                          <div className="flex items-center gap-3">
                            <AlertCircle className="w-5 h-5 text-warning shrink-0" />
                            <div>
                              <h4 className="text-[12px] font-semibold text-warning">Diligence complete, awaiting synthesis</h4>
                              <p className="text-[10px] text-text-muted mt-0.5">All 4 specialists have submitted findings. The managing partner has not yet rendered a decision.</p>
                            </div>
                          </div>
                          <div className="flex gap-2">
                            <button
                              onClick={forceVerdictSynthesis}
                              className="h-8 px-3 rounded-lg text-[11px] font-semibold bg-warning text-bg-base hover:bg-warning/90 active:scale-95 transition shrink-0"
                            >
                              Force Synthesis
                            </button>
                            <button
                              onClick={handleRetrySimulation}
                              className="h-8 px-3 rounded-lg text-[11px] font-semibold border border-border hover:bg-bg-muted active:scale-95 transition shrink-0 text-text-primary"
                            >
                              Restart
                            </button>
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
                        onDownloadPdf={() => window.open(`${API_BASE}/api/v1/generate-report?${activeIncidentId ? `incident_id=${activeIncidentId}&` : ''}format=pdf`, '_blank')}
                        onDownloadMd={() => window.open(`${API_BASE}/api/v1/generate-report?${activeIncidentId ? `incident_id=${activeIncidentId}&` : ''}format=md`, '_blank')}
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

/* ────────────────────────────────────────────────────────────── */
/*  Landing Page Component (Gatekeeping Layer)                   */
/* ────────────────────────────────────────────────────────────── */
interface LandingPageProps {
  onLogin: () => void
}

function LandingPage({ onLogin }: LandingPageProps) {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')
  const [isLoginOpen, setIsLoginOpen] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loginStep, setLoginStep] = useState(0)
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })

  // Roundtable Simulation States
  const [simState, setSimState] = useState<'idle' | 'running' | 'completed'>('idle')
  const [simStepIdx, setSimStepIdx] = useState(-1)
  const [simLogs, setSimLogs] = useState<string[]>([])
  const [selectedSimNode, setSelectedSimNode] = useState<'managing' | 'financial' | 'legal' | 'technical' | 'market' | 'core'>('managing')

  // Docs Section State (GitHub Docs style)
  const [docCategory, setDocCategory] = useState<'welcome' | 'swarm' | 'calc' | 'band' | 'mcp' | 'api'>('welcome')

  // MCP Interactive Console State
  const [mcpConsoleTool, setMcpConsoleTool] = useState<'chat' | 'deal' | 'verdict' | 'vault' | 'learn'>('chat')
  const [mcpConsoleOutput, setMcpConsoleOutput] = useState<string>('Select an MCP tool above and click "Execute Tool" to test...')
  const [mcpConsoleArgs, setMcpConsoleArgs] = useState<string>('{\n  "message": "Evaluate NovaPay Inc raising Series A"\n}')

  const simSteps = [
    {
      phase: 'ingestion',
      activeNode: 'core',
      log: '⚙️ calculations_engine: Ingested NovaPay Inc pitch deck. Grounding ARR growth & cap table variables.',
      time: '14:20:00'
    },
    {
      phase: 'financial',
      activeNode: 'financial',
      log: '📊 financial_partner: ARR of $5.0M verified. Flagged high customer concentration (42% Penn Medicine). Gross Margin checks at 72%.',
      time: '14:20:02'
    },
    {
      phase: 'legal',
      activeNode: 'legal',
      log: '⚖️ legal_partner: Contractor risks reviewed. Checked BAA / HIPAA logs. FDA clearance warnings scanned. No active patent litigation.',
      time: '14:20:04'
    },
    {
      phase: 'technical',
      activeNode: 'technical',
      log: '🔧 technical_partner: Flagged EOL Node.js 16 package runtimes. Database passwords/SSNs are securely salted and encrypted.',
      time: '14:20:06'
    },
    {
      phase: 'market',
      activeNode: 'market',
      log: '📈 market_partner: Checked founder TAM claim ($12B). Sector density calculated. Verified competitive moats.',
      time: '14:20:08'
    },
    {
      phase: 'synthesis',
      activeNode: 'managing',
      log: '🎯 managing_partner: Synthesizing partner checks. Invoking calculations rules. Outlier score bounds resolved.',
      time: '14:20:10'
    },
    {
      phase: 'verdict',
      activeNode: 'core',
      log: '🏆 FUSION Consensus Verdict Issued: PASS (REJECT) due to critical client concentration. Recorded to Band bus.',
      time: '14:20:12'
    }
  ]

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePos({ x: e.clientX, y: e.clientY })
    }
    window.addEventListener('mousemove', handleMouseMove)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
    }
  }, [])

  useEffect(() => {
    const saved = localStorage.getItem('theme') as 'dark' | 'light' | null
    const initialTheme = saved || 'dark'
    setTheme(initialTheme)
    const root = window.document.documentElement
    initialTheme === 'dark' ? root.classList.add('dark') : root.classList.remove('dark')
  }, [])

  const toggleTheme = () => {
    setTheme(prev => {
      const next = prev === 'dark' ? 'light' : 'dark'
      localStorage.setItem('theme', next)
      const root = window.document.documentElement
      next === 'dark' ? root.classList.add('dark') : root.classList.remove('dark')
      return next
    })
  }

  // Auto-play roundtable simulator
  const runRoundtableSim = () => {
    if (simState === 'running') return
    setSimState('running')
    setSimStepIdx(0)
    setSimLogs([simSteps[0].log])
    setSelectedSimNode('core')

    let currentIdx = 0
    const interval = setInterval(() => {
      currentIdx++
      if (currentIdx < simSteps.length) {
        setSimStepIdx(currentIdx)
        setSelectedSimNode(simSteps[currentIdx].activeNode as any)
        setSimLogs(prev => [...prev, simSteps[currentIdx].log])
      } else {
        clearInterval(interval)
        setSimState('completed')
      }
    }, 2000)
  }

  const resetRoundtableSim = () => {
    setSimState('idle')
    setSimStepIdx(-1)
    setSimLogs([])
    setSelectedSimNode('managing')
  }

  const executeMcpToolSim = () => {
    setMcpConsoleOutput('Connecting to FUSION local stdio pipe...')
    setTimeout(() => {
      try {
        const parsedArgs = JSON.parse(mcpConsoleArgs)
        let response = {}
        if (mcpConsoleTool === 'chat') {
          response = {
            verdict: 'PENDING',
            managing_partner: 'Analyzing NovaPay Inc raises Series A... Let me query the specialists.',
            trace: ['intent_classification', 'history_resolve', 'room_mobilization']
          }
        } else if (mcpConsoleTool === 'deal') {
          response = {
            deal_id: parsedArgs.incident_id || 'DEAL-20260615-141022',
            company: 'NovaPay Inc',
            diligence_scores: { financial: 4.5, legal: 8.2, technical: 7.0, market: 5.5 },
            weighted_risk: 8.8,
            verdict: 'PASS (REJECT)'
          }
        } else if (mcpConsoleTool === 'verdict') {
          response = {
            deal_id: parsedArgs.incident_id || 'DEAL-20260615-141022',
            verdict: 'PASS (REJECT)',
            primary_reason: 'ARR customer concentration exceeds maximum safety limit (42% vs 30% standard).'
          }
        } else if (mcpConsoleTool === 'vault') {
          response = {
            query: parsedArgs.keyword || 'fintech',
            matches: [
              { company: 'NovaPay Inc', sector: 'fintech', verdict: 'PASS (REJECT)', risk: 8.8 },
              { company: 'NovaCard', sector: 'fintech', verdict: 'INVEST', risk: 3.1 }
            ]
          }
        } else if (mcpConsoleTool === 'learn') {
          response = {
            status: 'learned',
            keyword: parsedArgs.keyword || 'regulatory-clearance',
            added_to_diligence_graph: true
          }
        }
        setMcpConsoleOutput(JSON.stringify(response, null, 2))
      } catch (err: any) {
        setMcpConsoleOutput(`Error: Failed to parse input JSON arguments. ${err.message}`)
      }
    }, 800)
  }

  const updateConsoleToolSelection = (tool: 'chat' | 'deal' | 'verdict' | 'vault' | 'learn') => {
    setMcpConsoleTool(tool)
    if (tool === 'chat') {
      setMcpConsoleArgs('{\n  "message": "Evaluate NovaPay Inc raising Series A"\n}')
    } else if (tool === 'deal') {
      setMcpConsoleArgs('{\n  "incident_id": "DEAL-20260615-141022"\n}')
    } else if (tool === 'verdict') {
      setMcpConsoleArgs('{\n  "incident_id": "DEAL-20260615-141022"\n}')
    } else if (tool === 'vault') {
      setMcpConsoleArgs('{\n  "keyword": "fintech",\n  "limit": 5\n}')
    } else if (tool === 'learn') {
      setMcpConsoleArgs('{\n  "keyword": "healthcare-compliance",\n  "checklist": "Verify HIPAA certification + BAA contracts"\n}')
    }
  }

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !password) return
    
    setLoginStep(1)
    setTimeout(() => {
      setLoginStep(2)
      setTimeout(() => {
        setLoginStep(3)
        setTimeout(() => {
          onLogin()
        }, 1000)
      }, 1200)
    }, 1200)
  }

  const scrollTo = (id: string) => {
    const element = document.getElementById(id)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' })
    }
  }

  // 3D Card Hover Tilt hook
  const use3DTilt = () => {
    const cardRef = useRef<HTMLDivElement>(null)
    const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
      const el = cardRef.current
      if (!el) return
      const rect = el.getBoundingClientRect()
      const x = e.clientX - rect.left
      const y = e.clientY - rect.top
      const xc = rect.width / 2
      const yc = rect.height / 2
      const rotateX = ((yc - y) / yc) * 8
      const rotateY = ((x - xc) / xc) * 8
      el.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`
    }
    const handleMouseLeave = () => {
      const el = cardRef.current
      if (!el) return
      el.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)'
    }
    return { cardRef, handleMouseMove, handleMouseLeave }
  }

  // Individual hooks for 3D partner cards
  const cardManaging = use3DTilt()
  const cardFinancial = use3DTilt()
  const cardLegal = use3DTilt()
  const cardTechnical = use3DTilt()
  const cardMarket = use3DTilt()

  return (
    <div className="bg-bg-base text-text-primary min-h-screen relative overflow-y-auto font-sans selection:bg-accent/20 selection:text-accent transition-colors duration-300">
      
      {/* Immersive Glowing Spotlights */}
      <div 
        className="absolute pointer-events-none w-[800px] h-[800px] rounded-full bg-accent/5 dark:bg-accent/10 blur-[180px] transition-all duration-500 z-0"
        style={{
          left: `${mousePos.x - 400}px`,
          top: `${mousePos.y - 400}px`,
        }}
      />
      <div className="absolute top-[10%] right-[5%] pointer-events-none w-[600px] h-[600px] rounded-full bg-emerald-500/5 dark:bg-emerald-500/10 blur-[150px] z-0" />
      <div className="absolute top-[40%] left-[10%] pointer-events-none w-[700px] h-[700px] rounded-full bg-emerald-700/5 dark:bg-emerald-600/5 blur-[170px] z-0" />
 
      {/* Sticky Header with FUSION × Band AI Collaboration Logo */}
      <header className="fixed top-0 left-0 w-full z-40 bg-bg-base/85 backdrop-blur-md border-b border-border transition-colors duration-300">
        <div className="max-w-[1550px] mx-auto px-8 md:px-16 h-20 flex items-center justify-between">
          <div className="flex items-center gap-1 cursor-pointer hover:opacity-95 transition-opacity" onClick={() => window.location.reload()}>
            {/* Real Logos Collaboration Rendering - SVG components */}
            <div className="flex items-center gap-1">
              <FusionLogo className="h-8 sm:h-9" />
              <span className="text-neutral-400 dark:text-neutral-500 font-mono text-lg font-bold select-none px-0.5">×</span>
              <BandLogoFull className="h-8 sm:h-9" />
            </div>

          </div>

          {/* Right Shifted Nav Menu with rounded-rectangle button styling */}
          <nav className="hidden md:flex items-center gap-1.5 text-[9px] font-mono tracking-wider text-text-secondary font-bold ml-auto mr-4">
            <button onClick={() => scrollTo('overview-sec')} className="px-3 py-1.5 rounded-md border border-border bg-bg-card hover:bg-bg-muted hover:border-accent/30 hover:text-accent transition-all duration-300 cursor-pointer">Overview</button>
            <button onClick={() => scrollTo('roundtable-sec')} className="px-3 py-1.5 rounded-md border border-border bg-bg-card hover:bg-bg-muted hover:border-accent/30 hover:text-accent transition-all duration-300 cursor-pointer">Roundtable</button>
            <button onClick={() => scrollTo('swarm-sec')} className="px-3 py-1.5 rounded-md border border-border bg-bg-card hover:bg-bg-muted hover:border-accent/30 hover:text-accent transition-all duration-300 cursor-pointer">Band Board</button>
            <button onClick={() => scrollTo('pillars-sec')} className="px-3 py-1.5 rounded-md border border-border bg-bg-card hover:bg-bg-muted hover:border-accent/30 hover:text-accent transition-all duration-300 cursor-pointer">Specs</button>
            <button onClick={() => scrollTo('docs-sec')} className="px-3 py-1.5 rounded-md border border-border bg-bg-card hover:bg-bg-muted hover:border-accent/30 hover:text-accent transition-all duration-300 cursor-pointer">Docs & API</button>
          </nav>

          <div className="flex items-center gap-4">
            <button 
              onClick={toggleTheme}
              className="w-10 h-10 rounded-xl border border-border flex items-center justify-center text-text-secondary hover:text-text-primary hover:bg-bg-muted transition-all cursor-pointer"
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? <Sun className="w-4 h-4 text-accent" /> : <Moon className="w-4 h-4 text-emerald-600" />}
            </button>
            
            <button 
              onClick={() => setIsLoginOpen(true)}
              className="relative group overflow-hidden px-6 py-2.5 rounded-xl bg-accent text-black font-mono font-bold text-xs uppercase tracking-wider hover:shadow-[0_0_25px_rgba(91,191,82,0.45)] transition-all duration-300 cursor-pointer"
            >
              <span className="relative z-10 flex items-center gap-2">
                Enter Boardroom <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
              </span>
              <div className="absolute inset-0 bg-gradient-to-r from-emerald-400 to-accent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section - Full width fluid spacing */}
      <section id="overview-sec" className="relative max-w-[1550px] mx-auto px-8 md:px-16 pt-40 pb-24 md:pt-52 md:pb-36 flex flex-col lg:flex-row items-center gap-16 z-10">
        <div className="flex-1 flex flex-col items-start text-left max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-accent/10 border border-accent/20 text-[10px] font-mono text-accent mb-6 uppercase tracking-wider font-semibold">
            <Sparkles className="w-3.5 h-3.5" /> FUSION Swarm Operating System Live
          </div>
          
          <h1 className="text-5xl sm:text-6xl md:text-7xl font-extrabold tracking-tight leading-[1.05] text-text-primary">
            Autonomous VC <br />
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-accent via-emerald-400 to-emerald-500">
              Due Diligence Swarm
            </span>
          </h1>

          <p className="mt-8 text-base md:text-lg text-text-secondary leading-relaxed font-sans max-w-2xl">
            Admit five specialized AI partner agents into parallel roundtable deliberation. Driven by a deterministic calculations engine to ground financial math, connected dynamically via the Band AI WebSocket event bus, and queryable using standard Model Context Protocol (MCP) servers.
          </p>

          <div className="mt-12 flex flex-wrap gap-4 font-mono text-xs uppercase tracking-wider font-bold">
            <button 
              onClick={() => setIsLoginOpen(true)}
              className="px-8 py-4 rounded-xl bg-accent text-black hover:shadow-[0_0_30px_rgba(91,191,82,0.5)] transition-all duration-300 flex items-center gap-2.5 cursor-pointer"
            >
              <Play className="w-4 h-4 fill-current" /> Initialize Swarm Room
            </button>
            <button 
              onClick={() => scrollTo('roundtable-sec')}
              className="px-8 py-4 rounded-xl border border-border bg-bg-card text-text-secondary hover:bg-bg-muted hover:text-text-primary transition-all duration-300 flex items-center gap-2 cursor-pointer"
            >
              Explore Sandbox <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          <div className="mt-16 grid grid-cols-3 gap-8 border-t border-border pt-8 w-full max-w-2xl">
            <div>
              <span className="block font-mono text-4xl font-bold text-text-primary">5</span>
              <span className="text-[10px] text-text-muted font-mono tracking-wider uppercase">Diligence Partners</span>
            </div>
            <div>
              <span className="block font-mono text-4xl font-bold text-text-primary">100%</span>
              <span className="text-[10px] text-text-muted font-mono tracking-wider uppercase">Math Grounded</span>
            </div>
            <div>
              <span className="block font-mono text-4xl font-bold text-text-primary">&lt; 3 Min</span>
              <span className="text-[10px] text-text-muted font-mono tracking-wider uppercase">Consensus Verdict</span>
            </div>
          </div>
        </div>

        {/* Hero Right side: Live roundtable visual display */}
        <div className="flex-1 w-full lg:max-w-xl relative group z-10">
          <div className="absolute inset-0 bg-gradient-to-tr from-accent/20 to-emerald-500/20 rounded-3xl blur-3xl opacity-20 group-hover:opacity-35 transition-opacity" />
          
          <div className="relative border border-border bg-bg-card rounded-3xl p-6 shadow-2xl backdrop-blur-xl transition-all duration-500">
            <div className="flex items-center justify-between border-b border-border pb-4 mb-4">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
                <span className="w-3 h-3 rounded-full bg-amber-500" />
                <span className="w-3 h-3 rounded-full bg-accent" />
                <span className="text-[10px] font-mono text-text-muted ml-2">BAND_AI_BUS_MONITOR // online</span>
              </div>
              <div className="px-2.5 py-0.5 rounded bg-accent/10 text-[9px] font-mono text-accent border border-accent/20 uppercase tracking-widest font-bold">
                Live Console
              </div>
            </div>

            {/* Simulated Live feed */}
            <div className="space-y-4 font-mono text-xs max-h-[300px] overflow-y-auto noscrollbar text-left">
              <div className="p-3.5 rounded-xl border border-border bg-bg-subtle">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-accent text-[9px] uppercase font-bold tracking-wider">managing_partner</span>
                  <span className="text-[9px] text-text-muted">14:15:01</span>
                </div>
                <p className="text-text-secondary leading-relaxed">💼 Submitting target NovaPay Inc (Series A raising $8M) to the diligence swarm. Initializing partners.</p>
              </div>

              <div className="p-3.5 rounded-xl border border-border bg-bg-subtle">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-accent text-[9px] uppercase font-bold tracking-wider">financial_partner</span>
                  <span className="text-[9px] text-text-muted">14:15:08</span>
                </div>
                <p className="text-text-secondary leading-relaxed">💵 Financial audit completed. ARR=$5.0M, Gross Margin=72%. Flagging 42% ARR concentration on single customer Penn Medicine. Runway=13.1 months.</p>
              </div>

              <div className="p-3.5 rounded-xl border border-border bg-bg-subtle">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-accent text-[9px] uppercase font-bold tracking-wider">legal_partner</span>
                  <span className="text-[9px] text-text-muted">14:15:15</span>
                </div>
                <p className="text-text-secondary leading-relaxed">⚖️ IP audit matches: Delaware filings clean. Contractor code assignments verified. BAA privacy logs intact. No pending M&A litigation.</p>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-border flex items-center justify-between text-xs font-mono">
              <span className="text-text-muted">Boardroom Synthesis:</span>
              <span className="text-red-400 font-bold px-2 py-0.5 rounded bg-red-400/10 border border-red-400/20 uppercase">PASS (REJECT)</span>
            </div>
          </div>
        </div>
      </section>

      {/* Interactive Roundtable Deliberation Simulator - Full width fluid */}
      <section id="roundtable-sec" className="relative max-w-[1550px] mx-auto px-8 md:px-16 py-24 border-t border-border z-10">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-text-primary font-mono">
            Roundtable Deliberation Visualizer
          </h2>
          <p className="mt-4 text-text-secondary leading-relaxed text-sm max-w-xl mx-auto">
            Witness how FUSION coordinates specialist agents, validates metrics through calculations engines, and generates consensus decisions. Click "Start Swarm Deliberation" to run.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          
          {/* Left column: Roundtable SVG Map */}
          <div className="lg:col-span-7 flex justify-center relative bg-bg-card dark:bg-[#0a0f0a] border border-border rounded-3xl p-6 sm:p-10 shadow-2xl min-h-[480px] overflow-hidden">
            {/* Custom SVG Spin Animations and Glow Filters */}
            <style>{`
              @keyframes spinSlow {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
              }
              @keyframes spinReverse {
                from { transform: rotate(360deg); }
                to { transform: rotate(0deg); }
              }
              .animate-spin-slow {
                animation: spinSlow 15s linear infinite;
                transform-origin: 200px 200px;
              }
              .animate-spin-reverse {
                animation: spinReverse 25s linear infinite;
                transform-origin: 200px 200px;
              }
            `}</style>
            
            <svg viewBox="0 0 400 400" className="w-full max-w-[380px] h-auto relative z-10 select-none">
              <defs>
                {/* SVG Glow Filters */}
                <filter id="glow-accent" x="-30%" y="-30%" width="160%" height="160%">
                  <feGaussianBlur stdDeviation="5" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
                <filter id="glow-core" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="8" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              </defs>

              {/* Outer Event Bus ring */}
              <circle cx="200" cy="200" r="165" fill="none" stroke="currentColor" className="text-white/[0.02]" strokeWidth="2" />
              <circle cx="200" cy="200" r="120" fill="none" stroke="currentColor" className="text-white/[0.02]" strokeWidth="1" strokeDasharray="3 6" />
              
              {/* Event connection trails (glowing fiber-optic lines) */}
              {simSteps.map((s, idx) => {
                let coords = { x: 200, y: 200 }
                if (s.activeNode === 'managing') coords = { x: 200, y: 70 }
                if (s.activeNode === 'financial') coords = { x: 310, y: 150 }
                if (s.activeNode === 'legal') coords = { x: 270, y: 280 }
                if (s.activeNode === 'technical') coords = { x: 130, y: 280 }
                if (s.activeNode === 'market') coords = { x: 90, y: 150 }
                
                const active = simStepIdx >= idx && simState === 'running'
                
                return (
                  <g key={idx}>
                    {/* Glowing underlay line */}
                    {active && (
                      <line 
                        x1={coords.x} 
                        y1={coords.y} 
                        x2="200" 
                        y2="200" 
                        stroke="#5bbf52" 
                        strokeWidth="3.5" 
                        filter="url(#glow-accent)" 
                        className="opacity-70"
                      />
                    )}
                    {/* Solid connector line */}
                    <line 
                      x1={coords.x} 
                      y1={coords.y} 
                      x2="200" 
                      y2="200" 
                      stroke={active ? '#5bbf52' : 'rgba(255,255,255,0.04)'} 
                      strokeWidth={active ? '2' : '1'} 
                      strokeDasharray={active ? '5,5' : 'none'}
                      className={active ? 'animate-pulse' : ''}
                      style={active ? { animation: 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite' } : {}}
                    />
                  </g>
                )
              })}

              {/* Central Calculations Core (spinning gears, CPU paths) */}
              <g 
                onClick={() => setSelectedSimNode('core')}
                className="cursor-pointer group"
                transform="translate(200, 200)"
              >
                {/* Glow Core Underlay */}
                <circle 
                  cx="0" 
                  cy="0" 
                  r="36" 
                  fill="none" 
                  stroke="#5bbf52" 
                  strokeWidth="2" 
                  filter="url(#glow-core)"
                  className={`transition-opacity duration-500 ${selectedSimNode === 'core' || (simSteps[simStepIdx]?.activeNode === 'core' && simState === 'running') ? 'opacity-90' : 'opacity-10 group-hover:opacity-30'}`}
                />
                
                {/* Concentric spinning gear rings */}
                <circle 
                  cx="0" 
                  cy="0" 
                  r="45" 
                  fill="none" 
                  stroke="rgba(91, 191, 82, 0.25)" 
                  strokeWidth="1.5" 
                  strokeDasharray="6 8"
                  className="animate-spin-slow"
                />
                <circle 
                  cx="0" 
                  cy="0" 
                  r="52" 
                  fill="none" 
                  stroke="rgba(255, 255, 255, 0.04)" 
                  strokeWidth="1" 
                  strokeDasharray="4 12"
                  className="animate-spin-reverse"
                />

                {/* Main solid core circle */}
                <circle 
                  cx="0" 
                  cy="0" 
                  r="34" 
                  className={`transition-all duration-500 ${selectedSimNode === 'core' ? 'fill-black stroke-accent' : 'fill-black stroke-white/[0.15] group-hover:stroke-accent/50'}`}
                  strokeWidth="2.5" 
                />
                
                {/* CPU Microchip Path representation */}
                <rect x="-11" y="-11" width="22" height="22" rx="3.5" fill="none" stroke="#5bbf52" strokeWidth="1.5" className={simState === 'running' ? 'animate-pulse' : ''} />
                <path d="M-15 -5 L-11 -5 M-15 0 L-11 0 M-15 5 L-11 5 M11 -5 L15 -5 M11 0 L15 0 M11 5 L15 5 M-5 -15 L-5 -11 M0 -15 L0 -11 M5 -15 L5 -11 M-5 11 L-5 15 M0 11 L0 15 M5 11 L5 15" stroke="#5bbf52" strokeWidth="1" strokeLinecap="round" />
                <circle cx="0" cy="0" r="2" fill="#5bbf52" className={simState === 'running' ? 'animate-ping' : ''} />

                <text x="0" y="25" textAnchor="middle" className="text-[6px] font-mono font-bold fill-neutral-500 tracking-wider">CORE</text>
              </g>

              {/* Node: Managing Partner (MP) */}
              <g 
                onClick={() => setSelectedSimNode('managing')} 
                className="cursor-pointer group"
                transform="translate(200, 70)"
              >
                {/* Glow border on active */}
                <rect 
                  x="-28" 
                  y="-18" 
                  width="56" 
                  height="36" 
                  rx="8" 
                  fill="none" 
                  stroke="#5bbf52" 
                  strokeWidth="2.5" 
                  filter="url(#glow-accent)" 
                  className={`transition-opacity duration-300 ${selectedSimNode === 'managing' || (simSteps[simStepIdx]?.activeNode === 'managing' && simState === 'running') ? 'opacity-100' : 'opacity-0 group-hover:opacity-40'}`} 
                />
                {/* Solid Black card */}
                <rect 
                  x="-28" 
                  y="-18" 
                  width="56" 
                  height="36" 
                  rx="8" 
                  className={`transition-all duration-300 ${selectedSimNode === 'managing' ? 'fill-black stroke-accent' : 'fill-black stroke-white/[0.12] group-hover:stroke-white/[0.25]'}`} 
                  strokeWidth="1.5" 
                />
                {/* Abbreviation Text */}
                <text x="0" y="1" textAnchor="middle" className="text-[11px] font-mono font-bold fill-white tracking-wider">MP</text>
                {/* LED Status dot */}
                <circle cx="0" cy="9" r="2.5" className={`transition-all duration-300 ${(simSteps[simStepIdx]?.activeNode === 'managing' && simState === 'running') ? 'fill-accent animate-pulse' : 'fill-neutral-600'}`} />
                {/* Monospace section tag */}
                <text x="0" y="-25" textAnchor="middle" className="text-[8px] font-mono tracking-widest fill-neutral-400 font-bold uppercase">Managing</text>
              </g>

              {/* Node: Financial Partner (FP) */}
              <g 
                onClick={() => setSelectedSimNode('financial')} 
                className="cursor-pointer group"
                transform="translate(310, 150)"
              >
                <rect 
                  x="-28" 
                  y="-18" 
                  width="56" 
                  height="36" 
                  rx="8" 
                  fill="none" 
                  stroke="#5bbf52" 
                  strokeWidth="2.5" 
                  filter="url(#glow-accent)" 
                  className={`transition-opacity duration-300 ${selectedSimNode === 'financial' || (simSteps[simStepIdx]?.activeNode === 'financial' && simState === 'running') ? 'opacity-100' : 'opacity-0 group-hover:opacity-40'}`} 
                />
                <rect 
                  x="-28" 
                  y="-18" 
                  width="56" 
                  height="36" 
                  rx="8" 
                  className={`transition-all duration-300 ${selectedSimNode === 'financial' ? 'fill-black stroke-accent' : 'fill-black stroke-white/[0.12] group-hover:stroke-white/[0.25]'}`} 
                  strokeWidth="1.5" 
                />
                <text x="0" y="1" textAnchor="middle" className="text-[11px] font-mono font-bold fill-white tracking-wider">FP</text>
                <circle cx="0" cy="9" r="2.5" className={`transition-all duration-300 ${(simSteps[simStepIdx]?.activeNode === 'financial' && simState === 'running') ? 'fill-accent animate-pulse' : 'fill-neutral-600'}`} />
                <text x="0" y="-25" textAnchor="middle" className="text-[8px] font-mono tracking-widest fill-neutral-400 font-bold uppercase">Financial</text>
              </g>

              {/* Node: Legal Partner (LP) */}
              <g 
                onClick={() => setSelectedSimNode('legal')} 
                className="cursor-pointer group"
                transform="translate(270, 280)"
              >
                <rect 
                  x="-28" 
                  y="-18" 
                  width="56" 
                  height="36" 
                  rx="8" 
                  fill="none" 
                  stroke="#5bbf52" 
                  strokeWidth="2.5" 
                  filter="url(#glow-accent)" 
                  className={`transition-opacity duration-300 ${selectedSimNode === 'legal' || (simSteps[simStepIdx]?.activeNode === 'legal' && simState === 'running') ? 'opacity-100' : 'opacity-0 group-hover:opacity-40'}`} 
                />
                <rect 
                  x="-28" 
                  y="-18" 
                  width="56" 
                  height="36" 
                  rx="8" 
                  className={`transition-all duration-300 ${selectedSimNode === 'legal' ? 'fill-black stroke-accent' : 'fill-black stroke-white/[0.12] group-hover:stroke-white/[0.25]'}`} 
                  strokeWidth="1.5" 
                />
                <text x="0" y="1" textAnchor="middle" className="text-[11px] font-mono font-bold fill-white tracking-wider">LP</text>
                <circle cx="0" cy="9" r="2.5" className={`transition-all duration-300 ${(simSteps[simStepIdx]?.activeNode === 'legal' && simState === 'running') ? 'fill-accent animate-pulse' : 'fill-neutral-600'}`} />
                <text x="0" y="30" textAnchor="middle" className="text-[8px] font-mono tracking-widest fill-neutral-400 font-bold uppercase">Legal</text>
              </g>

              {/* Node: Technical Partner (TP) */}
              <g 
                onClick={() => setSelectedSimNode('technical')} 
                className="cursor-pointer group"
                transform="translate(130, 280)"
              >
                <rect 
                  x="-28" 
                  y="-18" 
                  width="56" 
                  height="36" 
                  rx="8" 
                  fill="none" 
                  stroke="#5bbf52" 
                  strokeWidth="2.5" 
                  filter="url(#glow-accent)" 
                  className={`transition-opacity duration-300 ${selectedSimNode === 'technical' || (simSteps[simStepIdx]?.activeNode === 'technical' && simState === 'running') ? 'opacity-100' : 'opacity-0 group-hover:opacity-40'}`} 
                />
                <rect 
                  x="-28" 
                  y="-18" 
                  width="56" 
                  height="36" 
                  rx="8" 
                  className={`transition-all duration-300 ${selectedSimNode === 'technical' ? 'fill-black stroke-accent' : 'fill-black stroke-white/[0.12] group-hover:stroke-white/[0.25]'}`} 
                  strokeWidth="1.5" 
                />
                <text x="0" y="1" textAnchor="middle" className="text-[11px] font-mono font-bold fill-white tracking-wider">TP</text>
                <circle cx="0" cy="9" r="2.5" className={`transition-all duration-300 ${(simSteps[simStepIdx]?.activeNode === 'technical' && simState === 'running') ? 'fill-accent animate-pulse' : 'fill-neutral-600'}`} />
                <text x="0" y="30" textAnchor="middle" className="text-[8px] font-mono tracking-widest fill-neutral-400 font-bold uppercase">Technical</text>
              </g>

              {/* Node: Market Partner (MKT) */}
              <g 
                onClick={() => setSelectedSimNode('market')} 
                className="cursor-pointer group"
                transform="translate(90, 150)"
              >
                <rect 
                  x="-28" 
                  y="-18" 
                  width="56" 
                  height="36" 
                  rx="8" 
                  fill="none" 
                  stroke="#5bbf52" 
                  strokeWidth="2.5" 
                  filter="url(#glow-accent)" 
                  className={`transition-opacity duration-300 ${selectedSimNode === 'market' || (simSteps[simStepIdx]?.activeNode === 'market' && simState === 'running') ? 'opacity-100' : 'opacity-0 group-hover:opacity-40'}`} 
                />
                <rect 
                  x="-28" 
                  y="-18" 
                  width="56" 
                  height="36" 
                  rx="8" 
                  className={`transition-all duration-300 ${selectedSimNode === 'market' ? 'fill-black stroke-accent' : 'fill-black stroke-white/[0.12] group-hover:stroke-white/[0.25]'}`} 
                  strokeWidth="1.5" 
                />
                <text x="0" y="1" textAnchor="middle" className="text-[11px] font-mono font-bold fill-white tracking-wider">MKT</text>
                <circle cx="0" cy="9" r="2.5" className={`transition-all duration-300 ${(simSteps[simStepIdx]?.activeNode === 'market' && simState === 'running') ? 'fill-accent animate-pulse' : 'fill-neutral-600'}`} />
                <text x="0" y="-25" textAnchor="middle" className="text-[8px] font-mono tracking-widest fill-neutral-400 font-bold uppercase">Market</text>
              </g>
            </svg>
          </div>

          {/* Right column: Interactive controls and results */}
          <div className="lg:col-span-5 text-left flex flex-col justify-between min-h-[480px]">
            <div>
              <span className="text-[10px] font-mono uppercase tracking-wider text-accent font-bold">Autoplay Simulator</span>
              <h3 className="text-2xl font-bold text-text-primary mt-1.5 font-mono">Diligence Boardroom Roundtable</h3>
              
              <p className="mt-4 text-xs text-text-secondary leading-relaxed font-sans">
                Each node corresponds to a running LangGraph agent. In a live run, agents converse across WebSocket rooms, publishing findings to the central core. Click a node on the map to inspect focus areas, or run the simulator below.
              </p>

              {/* Sim Details Area */}
              <div className="mt-6 p-5 rounded-2xl border border-border bg-bg-subtle shadow-inner">
                {selectedSimNode === 'core' && (
                  <div>
                    <h4 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                      <Cpu className="w-4 h-4 text-accent" /> Calculations Core Engine
                    </h4>
                    <p className="mt-2.5 text-xs text-text-secondary leading-relaxed">
                      Evaluates calculations and enforces thresholds: Cap Table sums, Runway checks, and rules-based overrides. Grounds LLM responses mathematically.
                    </p>
                  </div>
                )}
                {selectedSimNode === 'managing' && (
                  <div>
                    <h4 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                      🎯 Managing Partner (Committee Chair)
                    </h4>
                    <p className="mt-2.5 text-xs text-text-secondary leading-relaxed">
                      Orchestrates boardroom deliberations, triggers specialist partners, weights scorecards, and writes final verdict memos.
                    </p>
                  </div>
                )}
                {selectedSimNode === 'financial' && (
                  <div>
                    <h4 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                      📊 Financial Partner (Forensic CPA)
                    </h4>
                    <p className="mt-2.5 text-xs text-text-secondary leading-relaxed">
                      Analyzes MRR/ARR quality, cap tables, margins, burn rates, and customer concentrations. Checks LTV:CAC multiples.
                    </p>
                  </div>
                )}
                {selectedSimNode === 'legal' && (
                  <div>
                    <h4 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                      ⚖️ Legal Partner (M&A Counsel)
                    </h4>
                    <p className="mt-2.5 text-xs text-text-secondary leading-relaxed">
                      Reviews IP ownership records, active litigation history, HIPAA/BAA logs, FDA clearances, and contractor contracts.
                    </p>
                  </div>
                )}
                {selectedSimNode === 'technical' && (
                  <div>
                    <h4 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                      🔧 Technical Partner (CTO Audit)
                    </h4>
                    <p className="mt-2.5 text-xs text-text-secondary leading-relaxed">
                      Evaluates codebase safety, EOL dependencies, unpatched database vulnerabilities (CVE tables), and AWS failover redundancy.
                    </p>
                  </div>
                )}
                {selectedSimNode === 'market' && (
                  <div>
                    <h4 className="text-xs font-mono font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
                      📈 Market Partner (Market Analyst)
                    </h4>
                    <p className="mt-2.5 text-xs text-text-secondary leading-relaxed">
                      Validates TAM claims, competitor moats, pricing pressures, market headwinds, and sector funding momentum.
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Sim Logs feed */}
            <div className="mt-6">
              <div className="flex items-center justify-between text-[10px] font-mono text-text-muted uppercase tracking-widest mb-2">
                <span>Diligence Feed Logs</span>
                <span>{simStepIdx >= 0 ? `${simStepIdx + 1}/${simSteps.length}` : '0/7'}</span>
              </div>
              
              <div className="h-[120px] rounded-2xl border border-border bg-bg-card p-4 font-mono text-[11px] overflow-y-auto space-y-2 noscrollbar">
                {simLogs.length === 0 ? (
                  <span className="text-text-muted block italic">Ready to run. Click "Trigger Diligence Run" below.</span>
                ) : (
                  simLogs.map((log, i) => (
                    <div key={i} className="text-text-secondary leading-relaxed animate-fade-in-up">
                      {log}
                    </div>
                  ))
                )}
              </div>
              
              <div className="mt-5 flex gap-3 font-mono text-xs uppercase tracking-wider font-bold">
                {simState !== 'running' ? (
                  <button 
                    onClick={runRoundtableSim}
                    className="flex-1 py-3.5 rounded-xl bg-accent text-black hover:shadow-[0_0_20px_rgba(91,191,82,0.3)] transition-all cursor-pointer"
                  >
                    Trigger Diligence Run
                  </button>
                ) : (
                  <button 
                    disabled
                    className="flex-1 py-3.5 rounded-xl bg-bg-subtle text-text-muted border border-border cursor-not-allowed"
                  >
                    Deliberating...
                  </button>
                )}
                <button 
                  onClick={resetRoundtableSim}
                  className="px-6 py-3.5 rounded-xl border border-border bg-bg-card text-text-secondary hover:bg-bg-muted hover:text-text-primary transition-all cursor-pointer"
                >
                  Reset
                </button>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* Boardroom Specialists (detailed 3D Tilt Cards) */}
      <section id="swarm-sec" className="relative max-w-[1550px] mx-auto px-8 md:px-16 py-24 border-t border-border z-10">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <span className="text-[10px] font-mono uppercase tracking-wider text-accent font-bold">Boardroom specialists</span>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-text-primary mt-1.5 font-mono">The 5 Swarm Partners</h2>
          <p className="mt-4 text-text-secondary leading-relaxed text-sm">
            FUSION parallelizes due diligence audits across 5 specialists. Grounded mathematically and connected to the Band Event Bus.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 text-left">
          
          {/* Card: Managing Partner */}
          <div 
            ref={cardManaging.cardRef}
            onMouseMove={cardManaging.handleMouseMove}
            onMouseLeave={cardManaging.handleMouseLeave}
            style={{ transition: 'transform 0.1s ease-out' }}
            className="p-6 rounded-2xl border border-border bg-bg-card hover:border-accent/30 hover:bg-accent/[0.01] shadow-xl flex flex-col justify-between"
          >
            <div>
              <div className="w-12 h-12 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center text-accent mb-6">
                <Sparkles className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-text-primary text-base font-mono">Managing Partner</h4>
              <span className="text-[9px] text-accent font-mono uppercase tracking-wider mt-1 block">Committee Chair</span>
              
              <p className="mt-4 text-xs text-text-secondary leading-relaxed">
                Orchestrates boardroom meetings. Gathers and synthesizes partner checksheets, weighs scorecards, and writes final verdict memos.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-border">
              <span className="text-[9px] font-mono text-text-muted uppercase tracking-wider block mb-1">Diligence checklist</span>
              <div className="flex flex-wrap gap-1">
                <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-bg-subtle border border-border text-text-secondary">Verdict Synthesis</span>
                <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-bg-subtle border border-border text-text-secondary">Conflict Override</span>
              </div>
            </div>
          </div>

          {/* Card: Financial Partner */}
          <div 
            ref={cardFinancial.cardRef}
            onMouseMove={cardFinancial.handleMouseMove}
            onMouseLeave={cardFinancial.handleMouseLeave}
            style={{ transition: 'transform 0.1s ease-out' }}
            className="p-6 rounded-2xl border border-border bg-bg-card hover:border-accent/30 hover:bg-accent/[0.01] shadow-xl flex flex-col justify-between"
          >
            <div>
              <div className="w-12 h-12 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center text-accent mb-6">
                <Coins className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-text-primary text-base font-mono">Financial Partner</h4>
              <span className="text-[9px] text-accent font-mono uppercase tracking-wider mt-1 block">Forensic Analyst</span>
              
              <p className="mt-4 text-xs text-text-secondary leading-relaxed">
                Stress-tests revenue models, MRR/ARR quality, gross margins, CAC paybacks, runway reserves, and cap table allocations.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-border">
              <span className="text-[9px] font-mono text-text-muted uppercase tracking-wider block mb-1">Diligence checklist</span>
              <div className="flex flex-wrap gap-1">
                <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-bg-subtle border border-border text-text-secondary">ARR concentration</span>
                <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-bg-subtle border border-border text-text-secondary">Runway & Burn</span>
              </div>
            </div>
          </div>

          {/* Card: Legal Partner */}
          <div 
            ref={cardLegal.cardRef}
            onMouseMove={cardLegal.handleMouseMove}
            onMouseLeave={cardLegal.handleMouseLeave}
            style={{ transition: 'transform 0.1s ease-out' }}
            className="p-6 rounded-2xl border border-border bg-bg-card hover:border-accent/30 hover:bg-accent/[0.01] shadow-xl flex flex-col justify-between"
          >
            <div>
              <div className="w-12 h-12 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center text-accent mb-6">
                <Scale className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-text-primary text-base font-mono">Legal Partner</h4>
              <span className="text-[9px] text-accent font-mono uppercase tracking-wider mt-1 block">M&A General Counsel</span>
              
              <p className="mt-4 text-xs text-text-secondary leading-relaxed">
                Examines litigation records, Delaware filings, contractor compliance, GDPR/CCPA privacy logs, and money transmitter gaps.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-border">
              <span className="text-[9px] font-mono text-text-muted uppercase tracking-wider block mb-1">Diligence checklist</span>
              <div className="flex flex-wrap gap-1">
                <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-bg-subtle border border-border text-text-secondary">IP assignment</span>
                <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-bg-subtle border border-border text-text-secondary">HIPAA & BAA compliance</span>
              </div>
            </div>
          </div>

          {/* Card: Technical Partner */}
          <div 
            ref={cardTechnical.cardRef}
            onMouseMove={cardTechnical.handleMouseMove}
            onMouseLeave={cardTechnical.handleMouseLeave}
            style={{ transition: 'transform 0.1s ease-out' }}
            className="p-6 rounded-2xl border border-border bg-bg-card hover:border-accent/30 hover:bg-accent/[0.01] shadow-xl flex flex-col justify-between"
          >
            <div>
              <div className="w-12 h-12 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center text-accent mb-6">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-text-primary text-base font-mono">Technical Partner</h4>
              <span className="text-[9px] text-accent font-mono uppercase tracking-wider mt-1 block">CTO Advisor</span>
              
              <p className="mt-4 text-xs text-text-secondary leading-relaxed">
                Audits dependency stack safety, EOL package versions, unpatched database vulnerabilities (CVE tables), and AWS redundancy.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-border">
              <span className="text-[9px] font-mono text-text-muted uppercase tracking-wider block mb-1">Diligence checklist</span>
              <div className="flex flex-wrap gap-1">
                <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-bg-subtle border border-border text-text-secondary">EOL software</span>
                <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-bg-subtle border border-border text-text-secondary">Plaintext PII/SSNs</span>
              </div>
            </div>
          </div>

          {/* Card: Market Partner */}
          <div 
            ref={cardMarket.cardRef}
            onMouseMove={cardMarket.handleMouseMove}
            onMouseLeave={cardMarket.handleMouseLeave}
            style={{ transition: 'transform 0.1s ease-out' }}
            className="p-6 rounded-2xl border border-border bg-bg-card hover:border-accent/30 hover:bg-accent/[0.01] shadow-xl flex flex-col justify-between"
          >
            <div>
              <div className="w-12 h-12 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center text-accent mb-6">
                <Globe className="w-5 h-5" />
              </div>
              <h4 className="font-bold text-text-primary text-base font-mono">Market Partner</h4>
              <span className="text-[9px] text-accent font-mono uppercase tracking-wider mt-1 block">Market Director</span>
              
              <p className="mt-4 text-xs text-text-secondary leading-relaxed">
                Validates founder TAM claims, competitor moats, pricing pressures, market headwinds, and sector funding momentum.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-border">
              <span className="text-[9px] font-mono text-text-muted uppercase tracking-wider block mb-1">Diligence checklist</span>
              <div className="flex flex-wrap gap-1">
                <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-bg-subtle border border-border text-text-secondary">TAM validation</span>
                <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-bg-subtle border border-border text-text-secondary">Competitor Moats</span>
              </div>
            </div>
          </div>

        </div>
      </section>

      {/* Tech Spec Pillars Section */}
      <section id="pillars-sec" className="relative max-w-[1550px] mx-auto px-8 md:px-16 py-24 border-t border-border z-10">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <span className="text-[10px] font-mono uppercase tracking-wider text-accent font-bold">Architecture & Integrations</span>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-text-primary mt-1.5 font-mono">Core Architectural Specs</h2>
          <p className="mt-4 text-text-secondary leading-relaxed text-sm">
            FUSION's infrastructure leverages a deterministic calculations engine, the Band AI WebSocket bus, and MCP server standards.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 text-left">
          
          {/* Pillar 1: Calculations Engine */}
          <div className="p-8 rounded-3xl border border-border bg-bg-card flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-6 shadow-[0_0_15px_rgba(79,174,71,0.1)]">
                <Cpu className="w-5 h-5" />
              </div>
              <h4 className="text-lg font-bold text-text-primary font-mono">1. Calculations Engine</h4>
              <p className="mt-4 text-xs text-text-secondary leading-relaxed">
                Prevents LLM hallucinations on Cap Tables, ARR runway, and concentrations. Variables are processed deterministically via Python algorithms. FUSION also runs conflict recusal audits (FDA status, contractor proportions) to override AI assumptions.
              </p>
            </div>
            <div className="mt-8 p-4 rounded-xl border border-border bg-bg-subtle font-mono text-[10px] text-text-secondary">
              <span className="text-text-muted block mb-1">// calculations_engine.py</span>
              <span className="text-emerald-400">def</span> calculate_runway(cash, burn):<br />
              &nbsp;&nbsp;<span className="text-emerald-400">return</span> cash / burn if burn &gt; 0 else float('inf')
            </div>
          </div>

          {/* Pillar 2: Band AI Event Bus */}
          <div className="p-8 rounded-3xl border border-border bg-bg-card flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-6 shadow-[0_0_15px_rgba(79,174,71,0.1)]">
                <Network className="w-5 h-5" />
              </div>
              <h4 className="text-lg font-bold text-text-primary font-mono">2. Band AI Event Bus</h4>
              <p className="mt-4 text-xs text-text-secondary leading-relaxed">
                Enables real-time, asynchronous room communication. The Managing Partner distributes tasks to specialist partner channels over WebSockets. Once audits complete, events are aggregated to compile the unified committee verdict.
              </p>
            </div>
            <div className="mt-8 p-4 rounded-xl border border-border bg-bg-subtle font-mono text-[10px] text-text-secondary">
              <span className="text-text-muted block mb-1">// band_bus.py</span>
              await band_sdk.publish(<br />
              &nbsp;&nbsp;room=<span className="text-emerald-400">"#managing-partner-room"</span>,<br />
              &nbsp;&nbsp;event=<span className="text-emerald-400">"diligence_triggered"</span><br />
              )
            </div>
          </div>

          {/* Pillar 3: Model Context Protocol */}
          <div className="p-8 rounded-3xl border border-border bg-bg-card flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-6 shadow-[0_0_15px_rgba(79,174,71,0.1)]">
                <Plug className="w-5 h-5" />
              </div>
              <h4 className="text-lg font-bold text-text-primary font-mono">3. Open MCP Servers</h4>
              <p className="mt-4 text-xs text-text-secondary leading-relaxed">
                Exposes FUSION's intelligence database as structured tools for external LLM clients (Claude Desktop, Cursor, or CLI). Stdio and HTTP endpoints expose tools to retrieve verdicts, check deal status, or query vaults.
              </p>
            </div>
            <div className="mt-8 p-4 rounded-xl border border-border bg-bg-subtle font-mono text-[10px] text-text-secondary">
              <span className="text-text-muted block mb-1">// mcp_server.py config</span>
              "fusion": &#123;<br />
              &nbsp;&nbsp;"command": <span className="text-emerald-400">"python"</span>,<br />
              &nbsp;&nbsp;"args": [<span className="text-emerald-400">"mcp_server.py"</span>]<br />
              &#125;
            </div>
          </div>

        </div>
      </section>

      {/* GitHub Docs-Style Documentation Section */}
      <section id="docs-sec" className="relative max-w-[1550px] mx-auto px-8 md:px-16 py-24 border-t border-border z-10">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <span className="text-[10px] font-mono uppercase tracking-wider text-accent font-bold">Documentation & References</span>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-text-primary mt-1.5 font-mono">
            FUSION Swarm Manual
          </h2>
          <p className="mt-4 text-text-secondary leading-relaxed text-sm max-w-xl mx-auto">
            A comprehensive, interactive reference manual modeled after GitHub Docs, covering swarm concepts, calculations, events, and API specs.
          </p>
        </div>

        {/* Sidebar + Content Container */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 border border-border rounded-3xl bg-bg-card p-6 sm:p-10 shadow-2xl text-left min-h-[580px]">
          
          {/* Docs Left Navigation Sidebar */}
          <aside className="lg:col-span-3 border-r border-border pr-6 space-y-6">
            <div>
              <p className="text-[10px] font-mono uppercase tracking-widest text-text-muted font-bold mb-2.5">Getting Started</p>
              <div className="space-y-1">
                <button 
                  onClick={() => setDocCategory('welcome')} 
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs font-mono transition-colors cursor-pointer block ${docCategory === 'welcome' ? 'bg-accent/15 text-accent font-bold' : 'text-text-secondary hover:text-text-primary hover:bg-bg-muted'}`}
                >
                  🚀 Welcome to FUSION
                </button>
                <button 
                  onClick={() => setDocCategory('swarm')} 
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs font-mono transition-colors cursor-pointer block ${docCategory === 'swarm' ? 'bg-accent/15 text-accent font-bold' : 'text-text-secondary hover:text-text-primary hover:bg-bg-muted'}`}
                >
                  👥 Swarm Partners
                </button>
              </div>
            </div>

            <div>
              <p className="text-[10px] font-mono uppercase tracking-widest text-text-muted font-bold mb-2.5">Technical Specs</p>
              <div className="space-y-1">
                <button 
                  onClick={() => setDocCategory('calc')} 
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs font-mono transition-colors cursor-pointer block ${docCategory === 'calc' ? 'bg-accent/15 text-accent font-bold' : 'text-text-secondary hover:text-text-primary hover:bg-bg-muted'}`}
                >
                  ⚙️ Calculations Logic
                </button>
                <button 
                  onClick={() => setDocCategory('band')} 
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs font-mono transition-colors cursor-pointer block ${docCategory === 'band' ? 'bg-accent/15 text-accent font-bold' : 'text-text-secondary hover:text-text-primary hover:bg-bg-muted'}`}
                >
                  💬 Band AI Event Bus
                </button>
              </div>
            </div>

            <div>
              <p className="text-[10px] font-mono uppercase tracking-widest text-text-muted font-bold mb-2.5">Integrate & Deploy</p>
              <div className="space-y-1">
                <button 
                  onClick={() => setDocCategory('mcp')} 
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs font-mono transition-colors cursor-pointer block ${docCategory === 'mcp' ? 'bg-accent/15 text-accent font-bold' : 'text-text-secondary hover:text-text-primary hover:bg-bg-muted'}`}
                >
                  🔌 MCP Server Setup
                </button>
                <button 
                  onClick={() => setDocCategory('api')} 
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs font-mono transition-colors cursor-pointer block ${docCategory === 'api' ? 'bg-accent/15 text-accent font-bold' : 'text-text-secondary hover:text-text-primary hover:bg-bg-muted'}`}
                >
                  ⚡ REST API Reference
                </button>
              </div>
            </div>
          </aside>

          {/* Docs Right Content Area */}
          <main className="lg:col-span-9 pl-0 lg:pl-6 space-y-6">
            
            {/* Category: Welcome */}
            {docCategory === 'welcome' && (
              <div className="space-y-4 animate-fade-in-up">
                <h3 className="text-2xl font-bold text-text-primary font-mono">Welcome to FUSION</h3>
                <p className="text-xs text-text-secondary leading-relaxed font-sans">
                  FUSION is an AI-powered VC due diligence command center. Traditionally, evaluating a startup requires weeks of manual audits across finance, legal filings, codebase checks, and market moats. FUSION compresses this process to under three minutes by dispatching five specialist partner agents.
                </p>
                <div className="p-4 rounded-xl border border-accent/20 bg-accent/5 text-xs text-accent leading-relaxed font-mono">
                  💡 <strong>Key Advantage:</strong> By integrating the <strong>Band AI WebSocket bus</strong> for asynchronous agent cooperation and a <strong>deterministic calculations engine</strong>, FUSION ensures that all financial and legal metrics are grounded mathematically, eliminating hallucinations.
                </div>
                <h4 className="text-sm font-bold text-text-primary font-mono mt-6">Swarm Ingestion Flow</h4>
                <ol className="space-y-3 font-sans text-xs text-text-secondary list-decimal pl-4">
                  <li><strong>Deal Briefing:</strong> Venture partner uploads a pitch deck or target info.</li>
                  <li><strong>Calculations Ingestion:</strong> Core extracts cash, burn, gross margins, and founder metrics.</li>
                  <li><strong>Specialist Audit:</strong> Parallel agents check ARR, litigation databases, and database CVE tables.</li>
                  <li><strong>Consensus Verdict:</strong> Managing Partner weighs scores and delivers the final PASS/INVEST boardroom memo.</li>
                </ol>
              </div>
            )}

            {/* Category: Swarm Partners */}
            {docCategory === 'swarm' && (
              <div className="space-y-4 animate-fade-in-up">
                <h3 className="text-2xl font-bold text-text-primary font-mono">The 5 Swarm Partners</h3>
                <p className="text-xs text-text-secondary leading-relaxed">
                  FUSION partitions due diligence audits into five distinct domains. Every partner runs automated checks:
                </p>
                
                <div className="space-y-3 mt-4">
                  <div className="p-3.5 rounded-xl border border-border bg-bg-subtle">
                    <span className="font-bold text-text-primary text-xs font-mono">🎯 Managing Partner</span>
                    <p className="text-[11px] text-text-secondary mt-1">Chairs the committee, triggers evaluations, resolves conflicting metrics, and writes the synthesis decision memo.</p>
                  </div>
                  <div className="p-3.5 rounded-xl border border-border bg-bg-subtle">
                    <span className="font-bold text-text-primary text-xs font-mono">📊 Financial Partner</span>
                    <p className="text-[11px] text-text-secondary mt-1">Stress-tests MRR/ARR quality, cap tables, gross margins, CAC paybacks, runway reserves, and customer concentrations.</p>
                  </div>
                  <div className="p-3.5 rounded-xl border border-border bg-bg-subtle">
                    <span className="font-bold text-text-primary text-xs font-mono">⚖️ Legal Partner</span>
                    <p className="text-[11px] text-text-secondary mt-1">Audits Delaware corporate filings, contractor assignments, pending lawsuit risks, and regulatory licensing gaps.</p>
                  </div>
                  <div className="p-3.5 rounded-xl border border-border bg-bg-subtle">
                    <span className="font-bold text-text-primary text-xs font-mono">🔧 Technical Partner</span>
                    <p className="text-[11px] text-text-secondary mt-1">Scans dependancy stacks, unpatched CVE tables, PACS image security, and AWS failover redundancy configurations.</p>
                  </div>
                  <div className="p-3.5 rounded-xl border border-border bg-bg-subtle">
                    <span className="font-bold text-text-primary text-xs font-mono">📈 Market Partner</span>
                    <p className="text-[11px] text-text-secondary mt-1">Validates founder TAM claims, competitor moats, pricing pressures, market headwinds, and sector funding momentum.</p>
                  </div>
                </div>
              </div>
            )}

            {/* Category: Calculations */}
            {docCategory === 'calc' && (
              <div className="space-y-4 animate-fade-in-up">
                <h3 className="text-2xl font-bold text-text-primary font-mono">Deterministic Calculations Logic</h3>
                <p className="text-xs text-text-secondary leading-relaxed">
                  FUSION's calculations core overrides LLM hallucinations by computing critical startup metrics using pure Python scripts:
                </p>

                <h4 className="text-sm font-bold text-text-primary font-mono mt-6">Primary Formulas</h4>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-border text-text-muted text-left">
                        <th className="pb-2">Metric</th>
                        <th className="pb-2">Formula</th>
                        <th className="pb-2">Diligence Red Flag Threshold</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border text-text-secondary">
                      <tr>
                        <td className="py-2.5 font-mono">Runway</td>
                        <td className="py-2.5">Cash / Burn</td>
                        <td className="py-2.5 text-amber-600 dark:text-amber-400">&lt; 12 Months</td>
                      </tr>
                      <tr>
                        <td className="py-2.5 font-mono">ARR Concentration</td>
                        <td className="py-2.5">Top Client ARR / Total ARR</td>
                        <td className="py-2.5 text-red-600 dark:text-red-400">&gt; 30% on single client</td>
                      </tr>
                      <tr>
                        <td className="py-2.5 font-mono">LTV : CAC</td>
                        <td className="py-2.5">LTV / CAC</td>
                        <td className="py-2.5 text-amber-600 dark:text-amber-400">&lt; 3.0x ratio</td>
                      </tr>
                      <tr>
                        <td className="py-2.5 font-mono">Cap Table Sum</td>
                        <td className="py-2.5">Sum of all shareholder %</td>
                        <td className="py-2.5 text-red-600 dark:text-red-400">!= 100% total equity</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div className="p-4 rounded-xl border border-red-500/20 bg-red-500/5 text-xs text-red-600 dark:text-red-400 leading-relaxed font-mono">
                  ⚠️ <strong>Recusal Override Triggered:</strong> If any single customer concentration exceeds 40% (such as NovaPay's 42% on Penn Medicine), the calculations engine automatically triggers a PASS (REJECT) override, bypassing LLM voting.
                </div>
              </div>
            )}

            {/* Category: Band AI */}
            {docCategory === 'band' && (
              <div className="space-y-4 animate-fade-in-up">
                <h3 className="text-2xl font-bold text-text-primary font-mono">Band AI WebSocket Event Bus</h3>
                <p className="text-xs text-text-secondary leading-relaxed">
                  FUSION's multi-agent coordination routes across the Band Event Bus. Agents communicate on WebSocket channels to publish findings asynchronously.
                </p>

                <h4 className="text-sm font-bold text-text-primary font-mono mt-6">LangGraph Routing Sequence</h4>
                <div className="p-4 rounded-xl border border-border bg-bg-subtle font-mono text-[10px] text-text-secondary space-y-2">
                  <div>1. External message received in <strong>#managing-partner-room</strong></div>
                  <div>2. Managing Partner triggers parallel WebSockets events to:
                    <div className="pl-4 text-accent font-bold">
                      - #finance-partner-room<br />
                      - #legal-partner-room<br />
                      - #tech-partner-room<br />
                      - #market-partner-room
                    </div>
                  </div>
                  <div>3. Agents run checklist tools and reply to Managing Partner.</div>
                  <div>4. Synthesis result is broadcasted to the dashboard event bus.</div>
                </div>
              </div>
            )}

            {/* Category: MCP Server Setup */}
            {docCategory === 'mcp' && (
              <div className="space-y-4 animate-fade-in-up">
                <h3 className="text-2xl font-bold text-text-primary font-mono">Model Context Protocol Integration</h3>
                <p className="text-xs text-text-secondary leading-relaxed">
                  The FUSION MCP server exposes tools so local clients (e.g. Claude Desktop, Cursor) or remote HTTP hosts can interact with the Swarm.
                </p>

                {/* Interactive MCP Tool Console Trial */}
                <div className="p-5 rounded-2xl border border-border bg-bg-subtle shadow-lg">
                  <span className="text-[9px] font-mono uppercase tracking-wider text-accent font-bold">Interactive Sandbox</span>
                  <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider mt-1 mb-3">Test FUSION MCP Server Tools</h4>
                  
                  {/* Select Tool */}
                  <div className="flex flex-wrap gap-1.5 mb-4">
                    <button 
                      onClick={() => updateConsoleToolSelection('chat')}
                      className={`px-3 py-1.5 rounded-lg text-[10px] font-mono transition cursor-pointer ${mcpConsoleTool === 'chat' ? 'bg-accent text-black font-bold' : 'bg-bg-muted text-text-secondary hover:text-text-primary hover:bg-bg-card'}`}
                    >
                      chat_with_managing_partner()
                    </button>
                    <button 
                      onClick={() => updateConsoleToolSelection('deal')}
                      className={`px-3 py-1.5 rounded-lg text-[10px] font-mono transition cursor-pointer ${mcpConsoleTool === 'deal' ? 'bg-accent text-black font-bold' : 'bg-bg-muted text-text-secondary hover:text-text-primary hover:bg-bg-card'}`}
                    >
                      get_deal_record()
                    </button>
                    <button 
                      onClick={() => updateConsoleToolSelection('verdict')}
                      className={`px-3 py-1.5 rounded-lg text-[10px] font-mono transition cursor-pointer ${mcpConsoleTool === 'verdict' ? 'bg-accent text-black font-bold' : 'bg-bg-muted text-text-secondary hover:text-text-primary hover:bg-bg-card'}`}
                    >
                      get_boardroom_verdict()
                    </button>
                    <button 
                      onClick={() => updateConsoleToolSelection('vault')}
                      className={`px-3 py-1.5 rounded-lg text-[10px] font-mono transition cursor-pointer ${mcpConsoleTool === 'vault' ? 'bg-accent text-black font-bold' : 'bg-bg-muted text-text-secondary hover:text-text-primary hover:bg-bg-card'}`}
                    >
                      query_deal_vault()
                    </button>
                    <button 
                      onClick={() => updateConsoleToolSelection('learn')}
                      className={`px-3 py-1.5 rounded-lg text-[10px] font-mono transition cursor-pointer ${mcpConsoleTool === 'learn' ? 'bg-accent text-black font-bold' : 'bg-bg-muted text-text-secondary hover:text-text-primary hover:bg-bg-card'}`}
                    >
                      learn_risk_pattern()
                    </button>
                  </div>

                  {/* Terminal Trial Box */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Args Input */}
                    <div>
                      <div className="flex items-center justify-between px-3 py-1.5 rounded-t-xl bg-bg-base border-t border-x border-border">
                        <span className="text-[9px] font-mono uppercase tracking-wider text-text-muted">Arguments (JSON)</span>
                      </div>
                      <textarea 
                        value={mcpConsoleArgs}
                        onChange={e => setMcpConsoleArgs(e.target.value)}
                        className="w-full h-[150px] p-3 rounded-b-xl border border-border bg-bg-base font-mono text-[10.5px] text-accent outline-none focus:border-accent/40"
                      />
                    </div>

                    {/* Output Console */}
                    <div>
                      <div className="flex items-center justify-between px-3 py-1.5 rounded-t-xl bg-bg-base border-t border-x border-border">
                        <span className="text-[9px] font-mono uppercase tracking-wider text-text-muted">Result Output</span>
                        <button 
                          onClick={executeMcpToolSim}
                          className="px-2 py-0.5 rounded bg-accent/25 hover:bg-accent text-accent hover:text-black text-[9px] font-mono font-bold transition cursor-pointer"
                        >
                          Execute Tool
                        </button>
                      </div>
                      <pre className="w-full h-[150px] p-3 rounded-b-xl border border-border bg-bg-base font-mono text-[10px] text-text-secondary overflow-auto whitespace-pre noscrollbar">
                        {mcpConsoleOutput}
                      </pre>
                    </div>
                  </div>
                </div>

                <h4 className="text-sm font-bold text-text-primary font-mono mt-6">Registration Example</h4>
                <div className="rounded-xl border border-border bg-bg-subtle overflow-hidden font-mono text-[11px] text-text-secondary">
                  <div className="flex items-center justify-between px-3.5 py-2 border-b border-border bg-bg-base">
                    <span className="text-[9px] font-mono uppercase tracking-wider text-text-muted">claude_desktop_config.json</span>
                  </div>
                  <pre className="p-4 overflow-x-auto text-[10.5px] leading-relaxed">
{`{
  "mcpServers": {
    "fusion": {
      "command": "python",
      "args": ["/path/to/fusion/mcp_server.py"],
      "env": {
        "FUSION_API_URL": "http://localhost:8000"
      }
    }
  }
}`}
                  </pre>
                </div>
              </div>
            )}

            {/* Category: API Reference */}
            {docCategory === 'api' && (
              <div className="space-y-4 animate-fade-in-up">
                <h3 className="text-2xl font-bold text-text-primary font-mono">REST API Reference</h3>
                <p className="text-xs text-text-secondary leading-relaxed">
                  Endpoints run locally on <code className="text-accent font-mono text-xs">http://localhost:8000</code>.
                </p>

                <h4 className="text-sm font-bold text-text-primary font-mono mt-6">Diligence Control</h4>
                <div className="space-y-3 font-sans text-xs text-text-secondary">
                  <div className="p-3 rounded-xl border border-border bg-bg-subtle flex items-start gap-4">
                    <span className="text-[9px] font-mono font-bold bg-success-soft text-success px-2 py-0.5 rounded border border-success/20 shrink-0">POST</span>
                    <div>
                      <code className="text-[11px] font-mono text-text-primary">/api/trigger-deal</code>
                      <p className="text-text-muted mt-1">Triggers due diligence evaluation across the 5 partners for a pitch deck.</p>
                    </div>
                  </div>
                  <div className="p-3 rounded-xl border border-border bg-bg-subtle flex items-start gap-4">
                    <span className="text-[9px] font-mono font-bold bg-accent-soft text-accent px-2 py-0.5 rounded border border-accent/20 shrink-0">GET</span>
                    <div>
                      <code className="text-[11px] font-mono text-text-primary">/api/status</code>
                      <p className="text-text-muted mt-1">Fetches active deal status, parsed parameters, and boardroom logs.</p>
                    </div>
                  </div>
                </div>

                <h4 className="text-sm font-bold text-text-primary font-mono mt-6">Chat & Vault</h4>
                <div className="space-y-3 font-sans text-xs text-text-secondary">
                  <div className="p-3 rounded-xl border border-border bg-bg-subtle flex items-start gap-4">
                    <span className="text-[9px] font-mono font-bold bg-success-soft text-success px-2 py-0.5 rounded border border-success/20 shrink-0">POST</span>
                    <div>
                      <code className="text-[11px] font-mono text-text-primary">/api/v1/chat</code>
                      <p className="text-text-muted mt-1">Talk to the Managing Partner. Messages containing evaluation intents trigger Swarms.</p>
                    </div>
                  </div>
                  <div className="p-3 rounded-xl border border-border bg-bg-subtle flex items-start gap-4">
                    <span className="text-[9px] font-mono font-bold bg-accent-soft text-accent px-2 py-0.5 rounded border border-accent/20 shrink-0">GET</span>
                    <div>
                      <code className="text-[11px] font-mono text-text-primary">/api/v1/incident/&#123;id&#125;</code>
                      <p className="text-text-muted mt-1">Retrieves scorecard, timeline, and audit history log for a specific deal.</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

          </main>
        </div>
      </section>

      {/* Global Footer */}
      <footer className="relative border-t border-border bg-bg-card py-10 text-[11px] text-text-muted transition-colors z-10">
        <div className="max-w-[1550px] mx-auto px-8 md:px-16 grid grid-cols-1 md:grid-cols-4 gap-8 text-left">
          
          <div className="space-y-4">
            <div className="flex items-center gap-1">
              <FusionLogo className="h-7" />
              <span className="text-text-muted font-mono text-lg font-bold select-none px-0.5">×</span>
              <BandLogoFull className="h-7" />
            </div>
            <p className="text-[11px] text-text-secondary leading-relaxed font-sans">
              Collaborative multi-agent boardroom due diligence platform. Grounded mathematically using a python calculations engine.
            </p>
          </div>

          <div>
            <h5 className="font-mono text-text-primary uppercase tracking-wider font-bold mb-4">Roundtable Map</h5>
            <ul className="space-y-2 font-sans text-text-secondary">
              <li><button onClick={() => scrollTo('roundtable-sec')} className="hover:text-accent transition-colors">Visual Simulator</button></li>
              <li><button onClick={() => scrollTo('swarm-sec')} className="hover:text-accent transition-colors">Diligence Partners</button></li>
              <li><button onClick={() => scrollTo('pillars-sec')} className="hover:text-accent transition-colors">System Infrastructure</button></li>
            </ul>
          </div>

          <div>
            <h5 className="font-mono text-text-primary uppercase tracking-wider font-bold mb-4">Specs & Docs</h5>
            <ul className="space-y-2 font-sans text-text-secondary">
              <li><button onClick={() => { scrollTo('docs-sec'); setDocCategory('welcome') }} className="hover:text-accent transition-colors">Manual Overview</button></li>
              <li><button onClick={() => { scrollTo('docs-sec'); setDocCategory('calc') }} className="hover:text-accent transition-colors">Calculations Engine</button></li>
              <li><button onClick={() => { scrollTo('docs-sec'); setDocCategory('mcp') }} className="hover:text-accent transition-colors">MCP Tool Trial</button></li>
            </ul>
          </div>

          <div>
            <h5 className="font-mono text-text-primary uppercase tracking-wider font-bold mb-4">System Status</h5>
            <div className="flex items-center gap-2 font-mono text-[10px] text-accent uppercase tracking-wider font-bold">
              <span className="inline-block w-2.5 h-2.5 rounded-full bg-accent animate-ping" />
              Swarm Sockets Active
            </div>
            <p className="text-[10px] text-text-muted mt-2 font-sans">
              Ready to evaluate Series A and Seed startup structures.
            </p>
          </div>

        </div>
        
        <div className="max-w-[1550px] mx-auto px-8 md:px-16 border-t border-border mt-8 pt-6 text-center text-[9px] text-text-muted font-mono">
          &copy; 2026 FUSION Investment Swarm Boardroom. All rights reserved. Powered by Band AI event bus.
        </div>
      </footer>

      {/* Animated Login Modal (Fake Sign In Window) */}
      <AnimatePresence>
        {isLoginOpen && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-black/95 backdrop-blur-md"
          >
            <div className="absolute inset-0" onClick={() => loginStep === 0 && setIsLoginOpen(false)} />

            <motion.div 
              initial={{ scale: 0.95, y: 30 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 30 }}
              transition={{ type: 'spring', damping: 25, stiffness: 220 }}
              className="relative w-full max-w-md border border-white/[0.08] dark:border-border bg-[#0a0a0a] p-8 rounded-3xl shadow-2xl backdrop-blur-xl overflow-hidden z-10 text-left font-mono"
            >
              {/* Glowing header bar */}
              <div className="absolute top-0 left-0 w-full h-[3px] bg-gradient-to-r from-accent via-emerald-400 to-accent" />

              {loginStep === 0 ? (
                <>
                  <div className="text-center mb-6">
                    <div className="inline-flex w-12 h-12 rounded-xl bg-accent/10 border border-accent/20 items-center justify-center text-accent mb-4 shadow-[0_0_15px_rgba(79,174,71,0.2)]">
                      <Lock className="w-5 h-5" />
                    </div>
                    <h3 className="text-lg font-bold text-white">Boardroom Admission</h3>
                    <p className="mt-2 text-xs text-neutral-500 font-sans leading-relaxed">
                      Secure venture partner authentication interface. Access credentials verified mathematically.
                    </p>
                  </div>

                  <form onSubmit={handleLoginSubmit} className="space-y-4">
                    <div>
                      <label className="block text-[10px] uppercase tracking-wider text-neutral-500 mb-2 font-bold">Partner Email / ID</label>
                      <div className="relative">
                        <Mail className="absolute left-4 top-3.5 w-4 h-4 text-neutral-600" />
                        <input 
                          type="text" 
                          required
                          placeholder="venture_partner@fusion.vc" 
                          value={email}
                          onChange={e => setEmail(e.target.value)}
                          className="w-full pl-11 pr-4 py-3.5 rounded-xl border border-white/[0.06] dark:border-border bg-black text-xs text-white placeholder-neutral-700 focus:bg-white/[0.02] focus:border-accent/80 transition-all outline-none"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-[10px] uppercase tracking-wider text-neutral-500 mb-2 font-bold">Access Code</label>
                      <div className="relative">
                        <Key className="absolute left-4 top-3.5 w-4 h-4 text-neutral-600" />
                        <input 
                          type="password" 
                          required
                          placeholder="••••••••" 
                          value={password}
                          onChange={e => setPassword(e.target.value)}
                          className="w-full pl-11 pr-4 py-3.5 rounded-xl border border-white/[0.06] dark:border-border bg-black text-xs text-white placeholder-neutral-700 focus:bg-white/[0.02] focus:border-accent/80 transition-all outline-none"
                        />
                      </div>
                    </div>

                    <div className="pt-2">
                      <button 
                        type="submit" 
                        className="w-full py-3.5 rounded-xl bg-accent text-black font-bold text-xs uppercase tracking-wider hover:shadow-[0_0_20px_rgba(91,191,82,0.35)] transition-all duration-300 cursor-pointer"
                      >
                        Admit to Boardroom
                      </button>
                    </div>
                  </form>

                  <div className="mt-5 text-center text-[9px] text-neutral-600 border-t border-white/[0.05] pt-4 font-sans leading-relaxed">
                    💡 Any username and password will grant boardroom clearance for review.
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-center font-mono">
                  <RefreshCw className="w-8 h-8 text-accent animate-spin mb-6" />
                  
                  <h3 className="text-xs font-bold text-white tracking-wide uppercase mb-4">Establishing Bus Connections</h3>
                  
                  <div className="space-y-3.5 text-xs text-left max-w-xs w-full">
                    <div className="flex items-center gap-2 text-neutral-400">
                      <CheckCircle className="w-4 h-4 text-accent" />
                      <span>Verifying biometric key tokens...</span>
                    </div>
                    
                    {loginStep >= 2 ? (
                      <motion.div initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-2 text-neutral-400">
                        <CheckCircle className="w-4 h-4 text-accent" />
                        <span>Deploying Band AI WS Event Sockets...</span>
                      </motion.div>
                    ) : (
                      <div className="flex items-center gap-2 text-neutral-700">
                        <span className="w-4 h-4 rounded-full border border-neutral-800 flex items-center justify-center text-[8px]">•</span>
                        <span>Deploying Band AI WS Event Sockets...</span>
                      </div>
                    )}

                    {loginStep >= 3 ? (
                      <motion.div initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-2 text-accent font-bold">
                        <Sparkles className="w-4 h-4" />
                        <span>Redirecting to boardroom dashboard...</span>
                      </motion.div>
                    ) : (
                      <div className="flex items-center gap-2 text-neutral-700">
                        <span className="w-4 h-4 rounded-full border border-neutral-800 flex items-center justify-center text-[8px]">•</span>
                        <span>Initializing partner state engines...</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
