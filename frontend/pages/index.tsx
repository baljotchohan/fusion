// pages/index.tsx — FUSION VC Command Center (CIVION-inspired layout)
import React, { useState, useEffect, useRef, useCallback } from 'react'
import Head from 'next/head'
import { useAgentWebSocket, AgentUpdate, StoryBeat } from '@/hooks/useAgentWebSocket'
import { AGENTS, API_BASE } from '@/lib/agents'
import AgentGraph from '@/components/AgentGraph'
import LiveLog from '@/components/LiveLog'
import ExecutivePanel from '@/components/ExecutivePanel'
import ThreatGauge from '@/components/ThreatGauge'
import StoryTicker from '@/components/StoryTicker'
import AgentDetailPanel from '@/components/AgentDetailPanel'
import MemoryView from '@/components/MemoryView'
import SettingsView from '@/components/SettingsView'
import { IntegrationsView } from '@/components/IntegrationsView'
import { PartnersView } from '@/components/PartnersView'
import DocsView from '@/components/DocsView'
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
} from 'lucide-react'

type Tab = 'overview' | 'history' | 'insights' | 'integrations' | 'partners' | 'settings' | 'docs'

interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
  incidentId?: string
  intent?: string
}

const NAV_GROUPS = [
  {
    title: 'MAIN',
    items: [
      { id: 'overview' as Tab, label: 'Overview', Icon: LayoutDashboard },
    ],
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
    items: [
      { id: 'docs' as Tab, label: 'Documentation', Icon: BookOpen },
    ],
  },
]

function renderMarkdown(text: string) {
  if (!text) return null;
  const lines = text.split('\n');
  return lines.map((line, lineIdx) => {
    // Check for bullet points
    const bulletMatch = line.match(/^\s*[-*+]\s+(.*)$/);
    
    // Function to parse bold text (**text**)
    const parseBold = (str: string) => {
      const parts: React.ReactNode[] = [];
      let lastIndex = 0;
      const regex = /\*\*([^*]+)\*\*/g;
      let match;
      while ((match = regex.exec(str)) !== null) {
        if (match.index > lastIndex) {
          parts.push(str.substring(lastIndex, match.index));
        }
        parts.push(
          <strong key={match.index} className="font-bold text-text-primary dark:text-white">
            {match[1]}
          </strong>
        );
        lastIndex = regex.lastIndex;
      }
      if (lastIndex < str.length) {
        parts.push(str.substring(lastIndex));
      }
      return parts.length > 0 ? parts : str;
    };

    if (bulletMatch) {
      return (
        <li key={lineIdx} className="ml-4 list-disc pl-1 my-0.5 text-text-secondary dark:text-slate-300">
          {parseBold(bulletMatch[1])}
        </li>
      );
    }

    return (
      <div key={lineIdx} className={line.trim() === '' ? 'h-2' : 'my-0.5 text-text-secondary dark:text-slate-300'}>
        {parseBold(line)}
      </div>
    );
  });
}

export default function FUSION() {
  const {
    agentStates, agentOutputs, logEvents, storyFeed, threatScore, ceoDecision, isConnected, resetAll,
  } = useAgentWebSocket()

  const [tab, setTab] = useState<Tab>('overview')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [chatCollapsed, setChatCollapsed] = useState(false)
  const [isSimulating, setIsSimulating] = useState(false)
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')

  const [activeIncidentId, setActiveIncidentId] = useState<string | null>(null)
  const [maxFileSizeMb, setMaxFileSizeMb] = useState<number>(10)

  // Load max file size and config on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/v1/system/settings`)
      .then(r => r.json())
      .then(d => {
        if (d.simulation && typeof d.simulation.max_file_size_mb === 'number') {
          setMaxFileSizeMb(d.simulation.max_file_size_mb)
        }
      })
      .catch(() => {})
  }, [])

  // File Upload State
  const [isDragging, setIsDragging] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'processing' | 'complete'>('idle')
  const [uploadedFile, setUploadedFile] = useState<{ name: string; size: number } | null>(null)
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
  const inputRef = useRef<HTMLInputElement>(null)

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
    const fileSizeMb = file.size / (1024 * 1024)
    if (fileSizeMb > maxFileSizeMb) {
      alert(`File size exceeds limit of ${maxFileSizeMb}MB (got ${fileSizeMb.toFixed(1)}MB)`)
      return
    }

    setUploadedFile({ name: file.name, size: file.size })
    setUploadStatus('uploading')

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(`${API_BASE}/api/v1/upload-pitch`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Upload failed')
      }

      const data = await response.json()
      setActiveIncidentId(data.incident_id)
      setUploadStatus('complete')
      triggerDealSimulation(data.company_name)
    } catch (err: any) {
      setUploadStatus('idle')
      alert(err.message || 'Error uploading file')
    }
  }

  const triggerDealSimulation = async (companyName: string = 'NovaPay Inc') => {
    setIsSimulating(true); setTab('overview')
    try {
      const res = await fetch(`${API_BASE}/api/trigger-deal?company=${encodeURIComponent(companyName)}`, { method: 'POST' })
      const data = await res.json()
      if (data.deal_id) {
        setActiveIncidentId(data.deal_id)
      }
    } catch {
      setIsSimulating(false)
      setUploadStatus('idle')
    }
  }

  const resetSimulation = async () => {
    setIsSimulating(false); setUploadStatus('idle'); setUploadedFile(null); setActiveIncidentId(null); resetAll()
    try { await fetch(`${API_BASE}/api/reset`, { method: 'POST' }) } catch {}
  }

  const toggleTheme = () => setTheme(prev => { const next = prev === 'dark' ? 'light' : 'dark'; localStorage.setItem('theme', next); return next })

  const triggerMockUpload = () => {
    setUploadedFile({ name: 'novapay_pitch.json', size: 9481 }); setUploadStatus('uploading')
    setTimeout(() => {
      setUploadStatus('complete')
      triggerDealSimulation('NovaPay Inc')
    }, 1000)
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
        body: JSON.stringify({
          user_message: text,
          incident_id: activeIncidentId || undefined
        })
      })
      const data = await response.json()
      if (data.incident_id) {
        setActiveIncidentId(data.incident_id)
      }
      if (data.dispatched) { setIsSimulating(true); setUploadStatus('processing') }
      setChatHistory(prev => [...prev, { role: 'assistant', content: data.commander_response, incidentId: data.incident_id, intent: data.intent }])
    } catch {
      setChatHistory(prev => [...prev, { role: 'assistant', content: 'Cannot reach the Managing Partner — is the FUSION backend running?' }])
    } finally { setChatThinking(false) }
  }, [chatInput, chatThinking, activeIncidentId])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value; setChatInput(val)
    const pos = e.target.selectionStart || 0; setCursorPosition(pos)
    const textBeforeCursor = val.slice(0, pos); const words = textBeforeCursor.split(/\s/); const lastWord = words[words.length - 1]
    if (lastWord.startsWith('@')) { setShowMentionPopup(true); setMentionSearch(lastWord); setMentionIndex(0) } else { setShowMentionPopup(false) }
  }

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (showMentionPopup) {
      if (e.key === 'ArrowDown') { e.preventDefault(); setMentionIndex(prev => (prev + 1) % filteredAgents.length) }
      else if (e.key === 'ArrowUp') { e.preventDefault(); setMentionIndex(prev => (prev - 1 + filteredAgents.length) % filteredAgents.length) }
      else if (e.key === 'Enter') { e.preventDefault(); if (filteredAgents[mentionIndex]) insertMention(filteredAgents[mentionIndex].handle) }
      else if (e.key === 'Escape') { setShowMentionPopup(false) }
    } else if (e.key === 'Enter') { sendChatMessage() }
  }

  const insertMention = (handle: string) => {
    const val = chatInput; const pos = cursorPosition; const textBeforeCursor = val.slice(0, pos); const textAfterCursor = val.slice(pos)
    const words = textBeforeCursor.split(/\s/); words[words.length - 1] = handle; const newTextBeforeCursor = words.join(' ') + ' '
    setChatInput(newTextBeforeCursor + textAfterCursor); setShowMentionPopup(false)
    setTimeout(() => { if (inputRef.current) { inputRef.current.focus(); const newPos = newTextBeforeCursor.length; inputRef.current.setSelectionRange(newPos, newPos) } }, 10)
  }

  const isActive = (tid: Tab) => tab === tid

  return (
    <div className="flex h-screen w-screen bg-bg-base text-text-primary font-sans antialiased overflow-hidden">
      <Head>
        <title>FUSION — AI-Powered Investment Committee</title>
        <meta name="description" content="Five specialized AI partner agents that orchestrate startup due diligence and deliver unified investment verdicts." />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      {/* ═══════════ LEFT SIDEBAR ═══════════ */}
      <aside className={`relative h-screen bg-bg-subtle border-r border-border transition-all duration-300 flex flex-col z-40 ${sidebarCollapsed ? 'w-16' : 'w-[220px]'}`}>
        {/* Logo */}
        <div className="h-[52px] flex items-center border-b border-border pl-5 gap-2.5">
          <div className="relative w-7 h-7 shrink-0 rounded-lg bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center text-xs text-white shadow-sm font-bold">F</div>
          {!sidebarCollapsed && (
            <span className="font-bold text-[15px] tracking-tight text-text-primary whitespace-nowrap">FUSION</span>
          )}
        </div>

        {/* Nav Groups */}
        <div className="flex-1 overflow-y-auto py-4 noscrollbar">
          {NAV_GROUPS.map((group, idx) => (
            <div key={idx} className="mb-5">
              {!sidebarCollapsed && (
                <div className="px-4 mb-2 text-[11px] font-bold text-text-muted tracking-wider">{group.title}</div>
              )}
              <ul className="space-y-0.5">
                {group.items.map((item) => {
                  const active = isActive(item.id)
                  return (
                    <li key={item.id} className="px-2">
                      <button
                        onClick={() => setTab(item.id)}
                        className={`w-full flex items-center gap-3 px-2.5 py-2 rounded-lg transition-colors group relative text-[13px] ${
                          active
                            ? 'bg-accent-soft text-accent font-semibold'
                            : 'text-text-secondary hover:bg-bg-muted hover:text-text-primary'
                        }`}
                        title={sidebarCollapsed ? item.label : undefined}
                      >
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

        {/* Bottom: Settings + Collapse */}
        <div className="p-2 border-t border-border space-y-1">
          <button
            onClick={() => setTab('settings')}
            className={`w-full flex items-center gap-3 px-2.5 py-2 rounded-lg transition-colors text-[13px] ${
              isActive('settings')
                ? 'bg-accent-soft text-accent font-semibold'
                : 'text-text-secondary hover:bg-bg-muted hover:text-text-primary'
            }`}
          >
            <Settings className={`w-[18px] h-[18px] shrink-0 ${isActive('settings') ? 'text-accent' : 'text-text-muted'}`} />
            {!sidebarCollapsed && <span>Settings</span>}
          </button>
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="w-full p-2 flex items-center justify-center text-text-muted hover:text-text-primary hover:bg-bg-muted rounded-lg transition-colors"
            title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <ChevronLeft className={`w-[18px] h-[18px] transition-transform duration-300 ${sidebarCollapsed ? 'rotate-180' : ''}`} />
          </button>
        </div>
      </aside>

      {/* ═══════════ MAIN CONTENT ═══════════ */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <header className="h-[52px] border-b border-border flex items-center justify-between px-6 shrink-0 bg-bg-card/80 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <h1 className="font-bold text-[15px] capitalize text-text-primary">{tab}</h1>
            <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wider ${
              isConnected ? 'bg-accent-green-soft text-accent-green' : 'bg-danger-soft text-danger'
            }`}>
              <span className={`h-1.5 w-1.5 rounded-full ${isConnected ? 'bg-accent-green animate-pulse' : 'bg-danger'}`} />
              {isConnected ? 'Online' : 'Offline'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {tab === 'overview' && (isSimulating || uploadedFile) && (
              <button onClick={resetSimulation} className="h-8 px-3 rounded-lg text-[11px] font-semibold border border-border text-text-secondary hover:text-text-primary hover:bg-bg-muted transition">
                Reset Evaluation
              </button>
            )}
            <button
              onClick={() => setChatCollapsed(prev => !prev)}
              className={`w-8 h-8 rounded-lg border flex items-center justify-center transition cursor-pointer ${
                chatCollapsed
                  ? 'border-border text-text-muted hover:bg-bg-muted hover:text-text-primary'
                  : 'border-accent-soft bg-accent-soft/45 text-accent hover:bg-accent-soft/70'
              }`}
              title={chatCollapsed ? 'Show Chat' : 'Hide Chat'}
            >
              <MessageSquare className="w-4 h-4" />
            </button>
            <button onClick={toggleTheme} className="w-8 h-8 rounded-lg border border-border flex items-center justify-center hover:bg-bg-muted text-text-muted hover:text-text-primary transition cursor-pointer">
              {theme === 'dark' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
            </button>
          </div>
        </header>

        {/* Content + Persistent Chat Panel */}
        <div className="flex-1 flex overflow-hidden">
          {/* Main Content Area */}
          <main className="flex-1 overflow-y-auto overflow-x-hidden relative">
            <div className="p-6 lg:p-8 max-w-full w-full">

              {/* ═══ OVERVIEW TAB ═══ */}
              {tab === 'overview' && (
                <div className="space-y-6">
                  {/* When idle: show uploader */}
                  {uploadStatus === 'idle' && !isSimulating && !timelineHasElements(logEvents) ? (
                    <div className="flex flex-col items-center justify-center min-h-[60vh] max-w-[600px] mx-auto text-center space-y-6">
                      <div
                        onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
                        onDragLeave={() => setIsDragging(false)}
                        onDrop={handleFileDrop}
                        onClick={() => fileInputRef.current?.click()}
                        className={`w-full border-2 border-dashed rounded-2xl p-10 cursor-pointer transition flex flex-col items-center gap-4 ${
                          isDragging ? 'border-accent bg-accent-soft' : 'border-border hover:border-accent/50 hover:bg-bg-subtle'
                        }`}
                      >
                        <div className="w-14 h-14 rounded-full bg-bg-muted flex items-center justify-center text-2xl">📁</div>
                        <div>
                          <h3 className="text-[15px] font-bold text-text-primary">Upload Startup Document</h3>
                          <p className="text-[12px] text-text-secondary mt-1.5 leading-relaxed max-w-sm">
                            Drag and drop a pitch deck, financials brief, or memo. FUSION will mobilize the partner agents for due diligence.
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          {['JSON', 'TXT', 'PDF', 'MD'].map(ext => (
                            <span key={ext} className="text-[10px] font-semibold px-2 py-0.5 rounded bg-bg-muted text-text-muted">{ext}</span>
                          ))}
                        </div>
                      </div>
                      <p className="text-[12px] text-text-muted">
                        No files?{' '}
                        <button onClick={triggerMockUpload} className="text-accent font-semibold hover:underline">
                          Load mock pitch brief (NovaPay Inc)
                        </button>{' '}to simulate.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {/* Upload status banner */}
                      {(uploadStatus === 'uploading' || uploadStatus === 'processing') && (
                        <div className="rounded-xl bg-accent-soft border border-accent/20 p-4 flex items-center justify-between gap-4">
                          <div className="flex items-center gap-3">
                            <div className="text-xl">📤</div>
                            <div>
                              <h4 className="text-[12px] font-bold text-accent">
                                {uploadStatus === 'uploading' ? 'Uploading deal document...' : 'Running due diligence audits...'}
                              </h4>
                              <p className="text-[10px] text-text-muted mt-0.5">File: {uploadedFile?.name || 'pitch_deck.json'}</p>
                            </div>
                          </div>
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-accent/10 text-accent uppercase tracking-wider">
                            {uploadStatus === 'uploading' ? 'Intaking' : 'Analyzing'}
                          </span>
                        </div>
                      )}

                      {/* Story Ticker */}
                      <StoryTicker beats={storyFeed} isSimulating={isSimulating} hasDecision={!!ceoDecision} />

                      {/* Scores Row */}
                      <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
                        <div className="md:col-span-5"><ThreatGauge score={threatScore} /></div>
                        <div className="md:col-span-7">
                          <ExecutivePanel
                            decision={ceoDecision}
                            threatScore={threatScore}
                            isSimulating={isSimulating}
                            onDownloadReport={activeIncidentId ? () => {
                              window.open(`${API_BASE}/api/v1/generate-report?incident_id=${activeIncidentId}`, '_blank')
                            } : undefined}
                          />
                        </div>
                      </div>

                      {/* Roundtable */}
                      <div>
                        <h2 className="text-[11px] font-bold text-text-muted tracking-wider uppercase mb-3">Deliberation Roundtable</h2>
                        <AgentGraph agentStates={agentStates} theme={theme} heightClass="h-[360px]" />
                      </div>

                      {/* Minutes */}
                      <div>
                        <h2 className="text-[11px] font-bold text-text-muted tracking-wider uppercase mb-3">Deliberation Minutes</h2>
                        <div className="h-[320px]"><LiveLog events={logEvents} /></div>
                      </div>

                      {/* Binders */}
                      <div>
                        <h2 className="text-[11px] font-bold text-text-muted tracking-wider uppercase mb-3">Diligence Binders</h2>
                        <AgentDetailPanel agentStates={agentStates} agentOutputs={agentOutputs} devMode={false} />
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

          {/* ═══════════ PERSISTENT CHAT PANEL (Right Side) ═══════════ */}
          <div className={`w-[320px] h-full flex flex-col border-l border-border bg-bg-card shrink-0 transition-all duration-300 ${chatCollapsed ? 'hidden' : 'hidden lg:flex'}`}>
            {/* Chat Header */}
            <div className="flex items-center gap-3 p-4 border-b border-border">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center text-xs text-white shadow-sm">🎯</div>
              <div>
                <h3 className="font-semibold text-text-primary text-[13px]">Managing Partner</h3>
                <div className="flex items-center gap-1.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-accent-green' : 'bg-text-muted'}`} />
                  <span className="text-[10px] font-medium text-text-secondary">{isConnected ? 'Ready' : 'Offline'}</span>
                </div>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3 bg-bg-base">
              {chatHistory.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center px-4">
                  <div className="w-12 h-12 rounded-full bg-bg-muted flex items-center justify-center text-xl mb-3 opacity-30">🎯</div>
                  <h4 className="text-[13px] font-medium text-text-primary mb-1">Managing Partner</h4>
                  <p className="text-[11px] text-text-secondary mb-5">Ask about deal financials, lawsuits, tech vulnerabilities, or market validation.</p>
                  <div className="flex flex-col gap-1.5 w-full">
                    <button onClick={() => sendChatMessage('Evaluate NovaPay Inc')} className="text-[11px] text-left px-3 py-2 bg-bg-subtle border border-border rounded-lg hover:border-text-muted transition-colors">
                      Evaluate NovaPay Inc
                    </button>
                    <button onClick={() => sendChatMessage('What should I look for in this deal?')} className="text-[11px] text-left px-3 py-2 bg-bg-subtle border border-border rounded-lg hover:border-text-muted transition-colors">
                      What should I look for in this deal?
                    </button>
                  </div>
                </div>
              ) : (
                chatHistory.map((m, i) => (
                  <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[90%] rounded-xl px-3.5 py-2.5 text-[12px] leading-relaxed ${
                      m.role === 'user'
                        ? 'bg-accent text-white'
                        : 'bg-bg-subtle border border-border text-text-primary'
                    }`}>
                      {m.role === 'user' ? (
                        <p className="whitespace-pre-wrap">{m.content}</p>
                      ) : (
                        <div className="space-y-1">{renderMarkdown(m.content)}</div>
                      )}
                    </div>
                  </div>
                ))
              )}
              {chatThinking && (
                <div className="flex justify-start">
                  <div className="bg-bg-subtle border border-border rounded-xl px-3 py-2 flex gap-1">
                    <span className="w-1.5 h-1.5 bg-text-muted rounded-full animate-pulse" />
                    <span className="w-1.5 h-1.5 bg-text-muted rounded-full animate-pulse" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 bg-text-muted rounded-full animate-pulse" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Chat Input */}
            <div className="p-3 bg-bg-card border-t border-border">
              {/* Mention Popup */}
              {showMentionPopup && filteredAgents.length > 0 && (
                <div className="mb-2 bg-bg-card border border-border rounded-xl shadow-lg overflow-hidden">
                  <div className="px-3 py-1.5 border-b border-border text-[10px] font-semibold text-text-muted uppercase tracking-wider">Mention Partner</div>
                  {filteredAgents.map((a, i) => (
                    <button
                      key={a.handle}
                      onClick={() => insertMention(a.handle)}
                      className={`w-full flex items-center gap-2.5 px-3 py-2 text-left text-[11px] transition ${
                        i === mentionIndex ? 'bg-accent-soft text-accent font-semibold' : 'text-text-secondary hover:bg-bg-subtle'
                      }`}
                    >
                      <span className="text-[13px]">{a.icon}</span>
                      <div>
                        <div className="font-semibold text-[11px]">{a.handle}</div>
                        <div className="text-[9px] text-text-muted">{a.name}</div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="w-8 h-8 rounded-lg bg-bg-subtle border border-border hover:bg-bg-muted text-text-muted flex items-center justify-center transition"
                  title="Upload document"
                >
                  <Plus className="w-4 h-4" />
                </button>
                <input
                  ref={inputRef}
                  type="text"
                  value={chatInput}
                  onChange={handleInputChange}
                  onKeyDown={handleInputKeyDown}
                  placeholder="Ask your partner..."
                  className="flex-1 bg-bg-subtle border border-border rounded-lg pl-3 pr-3 py-2 text-[12px] focus:outline-none focus:border-accent transition-all text-text-primary placeholder:text-text-muted"
                  disabled={chatThinking}
                />
                <button
                  onClick={() => sendChatMessage()}
                  disabled={!chatInput.trim() || chatThinking}
                  className={`w-8 h-8 flex items-center justify-center rounded-lg transition ${
                    chatInput.trim() && !chatThinking
                      ? 'bg-accent text-white hover:bg-accent-hover'
                      : 'bg-bg-muted text-text-muted cursor-not-allowed'
                  }`}
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Hidden file input (for upload from chat panel) */}
      <input type="file" ref={fileInputRef} onChange={handleFileSelect} className="hidden" accept=".json,.txt,.pdf,.md" />
    </div>
  )
}

function timelineHasElements(events: any[]): boolean {
  return Array.isArray(events) && events.length > 0
}
