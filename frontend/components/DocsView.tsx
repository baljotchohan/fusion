// components/DocsView.tsx — deep in-app documentation.
import React, { useState } from 'react'
import { AGENTS } from '@/lib/agents'

type Section = 'overview' | 'quickstart' | 'agents' | 'chat' | 'memory'
  | 'mcp' | 'api' | 'providers' | 'architecture' | 'glossary'

const NAV: { id: Section; label: string; icon: string; group: string }[] = [
  { id: 'overview', label: 'What is FUSION', icon: '💼', group: 'Start here' },
  { id: 'quickstart', label: 'Quick start', icon: '🚀', group: 'Start here' },
  { id: 'agents', label: 'The 5 partners', icon: '👔', group: 'Concepts' },
  { id: 'chat', label: 'Committee Chat', icon: '💬', group: 'Concepts' },
  { id: 'memory', label: 'Shared Deal Vault', icon: '🧠', group: 'Concepts' },
  { id: 'mcp', label: 'MCP integration', icon: '🔌', group: 'Integrate' },
  { id: 'api', label: 'API reference', icon: '⌘', group: 'Integrate' },
  { id: 'providers', label: 'AI providers', icon: '⚡', group: 'Operate' },
  { id: 'architecture', label: 'Architecture', icon: '🏗️', group: 'Operate' },
  { id: 'glossary', label: 'Glossary', icon: '📖', group: 'Operate' },
]

const GROUPS = ['Start here', 'Concepts', 'Integrate', 'Operate']

function H({ children }: { children: React.ReactNode }) {
  return <h2 className="text-[16px] font-bold text-slate-800 dark:text-white mb-3">{children}</h2>
}
function P({ children }: { children: React.ReactNode }) {
  return <p className="text-[12.5px] text-slate-600 dark:text-slate-300 leading-relaxed mb-3">{children}</p>
}
function B({ children }: { children: React.ReactNode }) {
  return <strong className="font-semibold text-slate-800 dark:text-white">{children}</strong>
}
function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-3 mb-3">
      <div className="w-6 h-6 rounded-lg bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 flex items-center justify-center text-[11px] font-bold font-mono shrink-0">{n}</div>
      <div>
        <p className="text-[12.5px] font-semibold text-slate-800 dark:text-slate-100">{title}</p>
        <p className="text-[12px] text-slate-500 dark:text-slate-400 leading-relaxed">{children}</p>
      </div>
    </div>
  )
}
function Code({ children, label }: { children: string; label?: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => { navigator.clipboard?.writeText(children); setCopied(true); setTimeout(() => setCopied(false), 1200) }
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950 my-3 overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-slate-800/80">
        <span className="text-[9px] font-mono uppercase tracking-wider text-slate-500">{label || 'shell'}</span>
        <button onClick={copy} className="text-[9px] font-mono text-slate-400 hover:text-cyan-400 transition">{copied ? '✓ copied' : 'copy'}</button>
      </div>
      <pre className="px-3.5 py-3 text-[11px] font-mono text-emerald-300/90 overflow-auto leading-relaxed whitespace-pre">{children}</pre>
    </div>
  )
}
function EndpointRow({ method, path, desc }: { method: string; path: string; desc: string }) {
  const color = method === 'GET' ? 'text-cyan-400 bg-cyan-500/10'
    : method === 'POST' ? 'text-emerald-400 bg-emerald-500/10'
    : method === 'DELETE' ? 'text-red-400 bg-red-500/10'
    : 'text-amber-400 bg-amber-500/10'
  return (
    <div className="flex items-start gap-3 py-2 border-b border-slate-200/50 dark:border-slate-800/50 last:border-0">
      <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded shrink-0 w-12 text-center ${color}`}>{method}</span>
      <div className="min-w-0">
        <code className="text-[11px] font-mono text-slate-700 dark:text-slate-200 break-all">{path}</code>
        <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-snug">{desc}</p>
      </div>
    </div>
  )
}

const MCP_TOOLS: [string, string][] = [
  ['chat_with_managing_partner', 'Talk to the Managing Partner; submitting a pitch recruits the specialist partners.'],
  ['get_deal_history', 'Retrieve past investment target timelines, decisions, and risk scorecard data.'],
  ['get_boardroom_verdict', 'Get the investment committee\'s final verdict for a startup deal.'],
  ['query_deal_vault', 'Find similar past startup evaluations by sector or risk pattern.'],
  ['learn_risk_pattern', 'Teach the committee a due diligence checklist or risk pattern.'],
]

const GLOSSARY: [string, string][] = [
  ['ARR (Annual Recurring Revenue)', 'Yearly subscription revenue. VC benchmark is high growth, quality, and low customer concentration.'],
  ['TAM (Total Addressable Market)', 'The total revenue opportunity available if a product achieves 100% market share.'],
  ['Due Diligence', 'The comprehensive process of auditing a potential investment target across financial, legal, technical, and market risk dimensions before closing a transaction.'],
  ['LTV:CAC', 'Lifetime Value to Customer Acquisition Cost ratio. VC standard for a Series A startup is usually greater than 3.0x.'],
  ['Runway & Burn', 'Runway is how many months the startup can survive on cash reserves before going out of business. Monthly burn rate is their net cash loss.'],
  ['Money Transmitter License', 'A state-level regulatory license required for entities that transmit money or process payments.'],
  ['EOL (End of Life)', 'Software runtimes or frameworks that are no longer officially supported, posing security and compliance liabilities.'],
  ['Cap Table', 'Capitalization table. A ledger documenting startup ownership percentages, equity dilutive options, and shareholder classes.'],
]

export function DocsView() {
  const [section, setSection] = useState<Section>('overview')

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">
      {/* nav */}
      <nav className="lg:col-span-1 space-y-3 lg:sticky lg:top-24 h-fit">
        {GROUPS.map(group => (
          <div key={group}>
            <p className="px-3 mb-1 text-[9px] font-mono uppercase tracking-widest text-slate-400 dark:text-slate-600">{group}</p>
            <div className="space-y-0.5">
              {NAV.filter(n => n.group === group).map(n => (
                <button
                  key={n.id}
                  onClick={() => setSection(n.id)}
                  className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-[12px] text-left transition ${
                    section === n.id
                      ? 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 font-semibold'
                      : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100/60 dark:hover:bg-slate-900/60'
                  }`}
                >
                  <span>{n.icon}</span>{n.label}
                </button>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* content */}
      <div className="lg:col-span-3 glassmorphic border border-slate-200/60 dark:border-slate-800/60 rounded-2xl p-6 shadow-sm">
        {section === 'overview' && (
          <div>
            <H>What is FUSION?</H>
            <P><B>FUSION</B> is an AI-Powered Venture Capital Investment Committee. When a startup deal is submitted for evaluation,
            conducting due diligence normally means weeks to months of manual effort across Finance, Legal, Tech, and Market Analysis. FUSION
            collapses that process into under three minutes using <B>five specialized partner agents</B> coordinating in real time.</P>
            <P>Each partner is a focused domain expert — the Financial Partner audits ARR and burn rate, the Legal Partner reviews IP and licensing liabilities,
            the Technical Partner performs system and security audits, the Market Partner profiles competition, and the Managing Partner runs the committee and issues the final boardroom verdict.</P>
            <P>The payoff: a raw pitch brief or deal structure goes in, and a complete, audit-logged investment decision comes out — automatically.</P>
            <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-4 mt-4">
              <p className="text-[12px] text-slate-600 dark:text-slate-300"><B>Try it:</B> open the Boardroom tab and click
              <B> Evaluate Startup Deal (NovaPay)</B>, or type in chat: &ldquo;Evaluate NovaPay Inc raising Series A.&rdquo;</p>
            </div>
          </div>
        )}

        {section === 'quickstart' && (
          <div>
            <H>Quick start</H>
            <P>FUSION consists of a Python backend and a Next.js dashboard. Two commands and you are live.</P>
            <Step n={1} title="Start the backend (5 partner agents + API)">Runs FastAPI on port 8000 and registers all 5 partner rooms on the Band mock bus.</Step>
            <Code label="backend">{`pip install -r requirements.txt
python run.py`}</Code>
            <Step n={2} title="Start the dashboard">Launches the Next.js boardroom dashboard on port 3000, talking to the backend over REST + WebSockets.</Step>
            <Code label="frontend">{`cd frontend
npm install
npx next dev --webpack`}</Code>
            <Step n={3} title="Run a deal evaluation">Open the Boardroom tab and click Evaluate Startup Deal, or tell the Managing Partner in chat &ldquo;Evaluate NovaPay Inc.&rdquo;</Step>
            <P>No API keys required — FUSION ships with a built-in mock LLM engine so the full chain runs offline out-of-the-box. Add provider
            keys in your <span className="font-mono">.env</span> to enable live LLM reasoning (see the AI providers section).</P>
          </div>
        )}

        {section === 'agents' && (
          <div>
            <H>The 5 specialist partner agents</H>
            <P>Each partner owns a domain-specific mandate and hands off findings to the Managing Partner. They run checklists across key evaluation metrics.</P>
            <div className="space-y-3 mt-4">
              {AGENTS.map(a => (
                <div key={a.name} className="rounded-xl border border-slate-200/60 dark:border-slate-800/60 p-3.5">
                  <div className="flex items-center gap-2.5">
                    <span className="text-lg">{a.icon}</span>
                    <div>
                      <p className="text-[12.5px] font-bold text-slate-800 dark:text-slate-100">{a.displayName} <span className="font-normal text-slate-400 text-[10px] font-mono ml-1">{a.role}</span></p>
                    </div>
                  </div>
                  <p className="text-[12px] text-slate-500 dark:text-slate-400 leading-relaxed mt-2">{a.detail}</p>
                  {a.checklist.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {a.checklist.map(t => <span key={t} className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500">✓ {t}</span>)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {section === 'chat' && (
          <div>
            <H>Talking to the Managing Partner</H>
            <P>The chat on the Boardroom tab routes directly to the <B>Managing Partner</B> in plain English. It classifies your intent to respond optimally:</P>
            <Step n={1} title="Submit a deal brief">Phrases like evaluate, pitch, deal, funding, or &ldquo;diligence this startup&rdquo; initiate the due diligence committee and spawn a new deal record.</Step>
            <Step n={2} title="Check active status">&ldquo;Show me our status&rdquo; checks if the committee is currently in session or gives a summary of the latest verdict memo.</Step>
            <Step n={3} title="Query Deal Vault">&ldquo;What have we evaluated?&rdquo; lists evaluated deals, risk categories, and decisions from shared memory.</Step>
            <Step n={4} title="Ask how FUSION works">&ldquo;How do you work?&rdquo; provides an architectural overview of FUSION.</Step>
            <P>Every reply shows a <B>Managing Partner reasoning trace</B> — detailing the exact background steps taken (intent classification, database check, room mobilization, synthesis) so the process is fully transparent.</P>
          </div>
        )}

        {section === 'memory' && (
          <div>
            <H>The shared Deal Vault</H>
            <P>All 5 partner agents read and write a <B>shared, on-disk memory graph</B> located in the `fusion_memory/` directory. Every startup evaluated has its due diligence timeline, scorecard, and reasons recorded. Countermeasures and mitigations are saved as risk recipes.</P>
            <P>On repeat evaluations, partners <B>query memory first</B> to apply prior learnings to current deals. The Deal Vault tab showcases every incident, checklist, and your full conversation history with the Managing Partner.</P>
          </div>
        )}

        {section === 'mcp' && (
          <div>
            <H>Model Context Protocol (MCP) integration</H>
            <P>FUSION ships with an <B>MCP server</B> so external AI clients (like Claude Desktop or Cursor) can invoke the investment committee or search past deals directly as tools.</P>
            <P><B>1. Start the MCP server</B> (stdio transport):</P>
            <Code label="shell">{`python mcp_server.py`}</Code>
            <P><B>2. Register it</B> in your MCP client configuration:</P>
            <Code label="claude_desktop_config.json">{`{
  "mcpServers": {
    "fusion": {
      "command": "python",
      "args": ["/path/to/fusion/mcp_server.py"],
      "env": { "FUSION_API_URL": "http://localhost:8000" }
    }
  }
}`}</Code>
            <P><B>3. Exposed Tools</B> available to your client:</P>
            <div className="rounded-xl border border-slate-200/60 dark:border-slate-800/60 divide-y divide-slate-200/50 dark:divide-slate-800/50">
              {MCP_TOOLS.map(([n, d]) => (
                <div key={n} className="flex items-start gap-3 p-2.5">
                  <code className="text-[11px] font-mono text-cyan-600 dark:text-cyan-400 shrink-0">{n}</code>
                  <span className="text-[11px] text-slate-500 dark:text-slate-400">{d}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {section === 'api' && (
          <div>
            <H>API reference</H>
            <P>All features are exposed via REST API endpoints on <span className="font-mono">http://localhost:8000</span>.</P>
            <p className="text-[10px] font-mono uppercase tracking-widest text-slate-400 mt-4 mb-1">Deal response & control</p>
            <div className="rounded-xl border border-slate-200/60 dark:border-slate-800/60 px-3.5 py-1">
              <EndpointRow method="POST" path="/api/trigger-deal" desc="Trigger due diligence simulation across all 5 partners." />
              <EndpointRow method="GET" path="/api/status" desc="Retrieve server health, mock state, and current active deal." />
              <EndpointRow method="POST" path="/api/reset" desc="Reset simulation state for a clean session." />
              <EndpointRow method="WS" path="/ws" desc="Real-time WebSocket event stream for dashboard updates." />
            </div>
            <p className="text-[10px] font-mono uppercase tracking-widest text-slate-400 mt-4 mb-1">Boardroom chat</p>
            <div className="rounded-xl border border-slate-200/60 dark:border-slate-800/60 px-3.5 py-1">
              <EndpointRow method="POST" path="/api/v1/chat" desc="Talk to the Managing Partner. Submitting pitches triggers evaluations." />
              <EndpointRow method="GET" path="/api/v1/chat/history" desc="Retrieve chatbot conversation log history." />
              <EndpointRow method="DELETE" path="/api/v1/chat/history" desc="Clear chatbot conversation log." />
            </div>
            <p className="text-[10px] font-mono uppercase tracking-widest text-slate-400 mt-4 mb-1">Deal Vault & memory</p>
            <div className="rounded-xl border border-slate-200/60 dark:border-slate-800/60 px-3.5 py-1">
              <EndpointRow method="GET" path="/api/v1/incidents" desc="List all evaluated startup deal records." />
              <EndpointRow method="GET" path="/api/v1/incident/{id}" desc="Retrieve specific deal timelines and scorecards." />
              <EndpointRow method="GET" path="/api/v1/memory/stats" desc="Read database aggregate audit counts and findings." />
              <EndpointRow method="GET" path="/api/v1/system/settings" desc="Retrieve AI providers, LLM configuration, and mock pace." />
            </div>
          </div>
        )}

        {section === 'providers' && (
          <div>
            <H>AI providers & automatic fallback</H>
            <P>FUSION is provider-agnostic, supporting <B>Gemini, Groq, Featherless, or AI/ML API</B> keys configured in <span className="font-mono">.env</span>.</P>
            <P>If live LLMs hit rate limits or fail, FUSION automatically falls back to its built-in <B>offline simulation engine</B> so evaluations and committee debates always resolve smoothly without stalling. Primary providers can be customized dynamically in Settings.</P>
            <Code label=".env">{`# Configure at least one provider to enable live LLM debate
GOOGLE_API_KEY=AIzaSy...
GROQ_API_KEY=gsk_...
ARGUS_LLM_PRIMARY=gemini # Model to try first`}</Code>
          </div>
        )}

        {section === 'architecture' && (
          <div>
            <H>Architecture</H>
            <P>FUSION's technical framework consists of:</P>
            <ul className="space-y-2 text-[12px] text-slate-600 dark:text-slate-300 mb-3">
              <li>• <B>FastAPI & Uvicorn</B> — REST API and real-time WebSockets.</li>
              <li>• <B>LangGraph React Agents</B> — Specialist partners equipped with memory and web tools.</li>
              <li>• <B>Band SDK Adapter</B> — Room-based agent-to-agent message transport.</li>
              <li>• <B>Shared Memory Graph</B> — JSON-based local database persistence.</li>
              <li>• <B>Event Bus</B> — Centralized async publisher streaming agent events to the UI.</li>
            </ul>
          </div>
        )}

        {section === 'glossary' && (
          <div>
            <H>Glossary</H>
            <dl className="space-y-3">
              {GLOSSARY.map(([t, d]) => (
                <div key={t}>
                  <dt className="text-[12.5px] font-bold text-slate-800 dark:text-slate-100">{t}</dt>
                  <dd className="text-[12px] text-slate-500 dark:text-slate-400 leading-relaxed">{d}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}
      </div>
    </div>
  )
}

export default DocsView
