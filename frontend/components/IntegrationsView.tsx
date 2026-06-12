// components/IntegrationsView.tsx — Connected Workspace SaaS cards with interactive toggles
import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { MessageSquare, Cloud, FolderOpen, FileSignature, HardDrive, BarChart3, type LucideIcon, Plug, CheckCircle2, XCircle } from 'lucide-react'

interface Integration {
  id: string
  name: string
  description: string
  Icon: LucideIcon
  colorClass: string
  bgClass: string
  connected: boolean
}

const INITIAL_INTEGRATIONS: Integration[] = [
  { id: 'slack', name: 'Slack', description: 'Get deal alerts and partner updates in real-time in your channels', Icon: MessageSquare, colorClass: 'text-purple-600 dark:text-purple-400', bgClass: 'bg-purple-50 dark:bg-purple-950/30 border-purple-200/50 dark:border-purple-800/30', connected: true },
  { id: 'salesforce', name: 'Salesforce', description: 'Sync startup deal pipelines and contact records automatically', Icon: Cloud, colorClass: 'text-sky-600 dark:text-sky-400', bgClass: 'bg-sky-50 dark:bg-sky-950/30 border-sky-200/50 dark:border-sky-800/30', connected: false },
  { id: 'gdrive', name: 'Google Drive', description: 'Ingest pitch decks and financial spreadsheets directly', Icon: FolderOpen, colorClass: 'text-amber-600 dark:text-amber-400', bgClass: 'bg-amber-50 dark:bg-amber-950/30 border-amber-200/50 dark:border-amber-800/30', connected: true },
  { id: 'docusign', name: 'DocuSign', description: 'Manage and sign investment term sheets and advisory agreements', Icon: FileSignature, colorClass: 'text-emerald-600 dark:text-emerald-400', bgClass: 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200/50 dark:border-emerald-800/30', connected: false },
  { id: 'dropbox', name: 'Dropbox', description: 'Securely sync and mount shared due diligence pitch folders', Icon: HardDrive, colorClass: 'text-indigo-600 dark:text-indigo-400', bgClass: 'bg-indigo-50 dark:bg-indigo-950/30 border-indigo-200/50 dark:border-indigo-800/30', connected: false },
  { id: 'hubspot', name: 'HubSpot', description: 'Track co-investor networks and outbound startup sourcing', Icon: BarChart3, colorClass: 'text-rose-600 dark:text-rose-400', bgClass: 'bg-rose-50 dark:bg-rose-950/30 border-rose-200/50 dark:border-rose-800/30', connected: false },
]

export function IntegrationsView() {
  const [integrations, setIntegrations] = useState<Integration[]>(INITIAL_INTEGRATIONS)

  const toggleConnection = (id: string) => {
    setIntegrations(prev =>
      prev.map(item =>
        item.id === id ? { ...item, connected: !item.connected } : item
      )
    )
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto py-4">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1.5">
          <Plug className="w-5 h-5 text-accent" />
          <h1 className="text-2xl font-bold text-text-primary tracking-tight">Connected Workspace</h1>
        </div>
        <p className="text-text-secondary text-[13px]">
          Connect your VC tech stack tools to stream deal flow and pipeline data.
        </p>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {integrations.map((item, idx) => {
          const on = item.connected
          return (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05, duration: 0.3 }}
              className="rounded-2xl bg-bg-card border border-border/80 shadow-sm hover:shadow-md hover:border-border transition-all duration-200 p-5 flex flex-col justify-between"
            >
              <div>
                {/* Icon & Toggle Status Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className={`w-10 h-10 rounded-xl border flex items-center justify-center ${item.bgClass}`}>
                    <item.Icon className={`w-5 h-5 ${item.colorClass}`} />
                  </div>
                  
                  {/* Glowing Connection Badge */}
                  <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold transition ${
                    on
                      ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                      : 'bg-bg-muted text-text-muted'
                  }`}>
                    <span className={`w-1 h-1 rounded-full ${on ? 'bg-emerald-500 animate-pulse' : 'bg-text-muted'}`} />
                    {on ? 'Connected' : 'Offline'}
                  </span>
                </div>

                <h3 className="text-[14px] font-bold text-text-primary">{item.name}</h3>
                <p className="text-[11.5px] text-text-secondary mt-1 leading-relaxed min-h-[36px]">
                  {item.description}
                </p>
              </div>

              {/* Toggle switch bar */}
              <div className="mt-5 pt-4 border-t border-border/50 flex items-center justify-between">
                <span className="text-[10px] uppercase font-bold tracking-wider text-text-muted">
                  {on ? 'Active' : 'Disabled'}
                </span>
                
                {/* Interactive switch button */}
                <button
                  onClick={() => toggleConnection(item.id)}
                  className={`
                    relative inline-flex w-[46px] h-[24px] rounded-full transition-colors duration-300 focus:outline-none cursor-pointer
                    ${on ? 'bg-accent' : 'bg-bg-muted'}
                  `}
                  aria-label={`Toggle ${item.name} connection`}
                >
                  <motion.span
                    layout
                    className="absolute top-[3px] w-[18px] h-[18px] rounded-full bg-white shadow-sm"
                    animate={{ left: on ? 25 : 3 }}
                    transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                  />
                </button>
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
