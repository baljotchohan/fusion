// components/DocsView.tsx — deep in-app documentation.
import React, { useState } from 'react'
import { AGENTS } from '../lib/agents'

type Section = 'overview' | 'quickstart' | 'agents' | 'scenario' | 'chat' | 'memory'
  | 'mcp' | 'connectors' | 'api' | 'providers' | 'architecture' | 'glossary'

const NAV: { id: Section; label: string; icon: string; group: string }[] = [
  { id: 'overview', label: 'What is Fusion', icon: '🛡️', group: 'Start here' },
  { id: 'quickstart', label: 'Quick start', icon: '🚀', group: 'Start here' },
  { id: 'agents', label: 'The 9 agents', icon: '🤖', group: 'Concepts' },
  { id: 'scenario', label: 'Attack scenario', icon: '🎯', group: 'Concepts' },
  { id: 'chat', label: 'Talking to the Commander', icon: '💬', group: 'Concepts' },
  { id: 'memory', label: 'Shared memory graph', icon: '🧠', group: 'Concepts' },
  { id: 'mcp', label: 'MCP integration', icon: '🔌', group: 'Integrate' },
  { id: 'connectors', label: 'Connectors', icon: '🔗', group: 'Integrate' },
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
  ['run_security_scan', 'Scan a GitHub repo for secrets, vulnerable deps, and Dependabot alerts.'],
  ['analyze_threat', 'Analyze an IoC (IP / domain / hash) against live NVD CVEs and team memory.'],
  ['chat_with_commander', 'Talk to the Commander; reporting an attack recruits the full swarm.'],
  ['get_incident', 'Retrieve a past incident finding timeline and decision.'],
  ['get_team_decision', 'Get the Executive board verdict for an incident.'],
  ['query_team_memory', 'Find similar past incidents by MITRE technique or keyword.'],
  ['learn_attack_pattern', 'Teach the team a defense recipe for a MITRE technique.'],
]

const GLOSSARY: [string, string][] = [
  ['MITRE ATT&CK', 'A public catalog of real attacker techniques, each with an ID like T1566.001 (spear-phishing attachment). Agents tag findings with these so defenses map to known behavior.'],
  ['IOC (Indicator of Compromise)', 'A piece of forensic evidence an attack happened — a malicious domain, file hash, or IP.'],
  ['C2 (Command & Control)', 'The attacker remote servers that infected machines phone home to for instructions.'],
  ['Kill chain', 'The stages of an intrusion: recon, delivery, exploitation, installation, C2, then actions on objectives.'],
  ['Lateral movement', 'When an attacker spreads from the first compromised machine to others, toward the real target.'],
  ['Dwell time', 'How long an attacker stays undetected inside a network.'],
  ['CVSS', 'A 0–10 severity score for a vulnerability; 9.0+ is critical.'],
  ['Containment', 'Stopping an active attack from spreading (isolate machines, block domains) without necessarily shutting everything down.'],
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
            <H>What is Fusion?</H>
            <P><B>Fusion</B> is an Autonomous Cyber Defense Command Center. When a security alert fires, responding to it
            normally means a human scramble across Security, IT, Legal, Finance and the C-Suite that takes hours. Fusion
            collapses that into under three minutes using <B>nine specialized AI agents</B> that coordinate in real time.</P>
            <P>Each agent is a focused expert — one classifies the threat, one maps your network, one predicts the
            attacker next move, one builds the defense, and a final boardroom makes the <B>business decision</B>
            (Contain, Shutdown, or Escalate) backed by financial, legal and operational assessments.</P>
            <P>The payoff: a raw technical signal goes in, and a defensible, audit-logged executive decision comes out —
            automatically.</P>
            <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-4 mt-4">
              <p className="text-[12px] text-slate-600 dark:text-slate-300"><B>Try it:</B> open the War Room tab and click
              <B> Simulate Attack</B>, or just tell the Commander &ldquo;we got a phishing email.&rdquo;</p>
            </div>
          </div>
        )}

        {section === 'quickstart' && (
          <div>
            <H>Quick start</H>
            <P>Fusion is a Python backend plus a Next.js dashboard. Two commands and you are live.</P>
            <Step n={1} title="Start the backend (9 agents + API)">Runs FastAPI on port 8000 and registers all nine agents on the Band mock bus.</Step>
            <Code label="backend">{`pip install -r requirements.txt
python run.py`}</Code>
            <Step n={2} title="Start the dashboard">This War Room UI on port 3000, talking to the backend over REST + WebSocket.</Step>
            <Code label="frontend">{`cd frontend
npm install
npm run dev`}</Code>
            <Step n={3} title="Run a response">Open the War Room tab and click Simulate Attack, or tell the Commander &ldquo;we got a phishing email.&rdquo;</Step>
            <P>No API keys required — Fusion ships a built-in local engine so the full chain runs offline. Add a provider
            key in <span className="font-mono">.env</span> for live LLM reasoning (see the AI providers section).</P>
          </div>
        )}

        {section === 'agents' && (
          <div>
            <H>The 9 specialist agents</H>
            <P>Each agent owns one job and hands off cleanly to the next. They reason along the cyber kill chain and map
            findings to <B>MITRE ATT&CK</B> — the industry catalog of real attacker techniques.</P>
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
                  {a.mitre.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {a.mitre.map(t => <span key={t} className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500">{t}</span>)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {section === 'scenario' && (
          <div>
            <H>The attack scenario</H>
            <P>The built-in simulation models a realistic <B>spear-phishing to ransomware-precursor</B> attack against
            &ldquo;TechCorp Inc,&rdquo; a mid-size enterprise digital twin:</P>
            <Step n={1} title="Delivery">A hacker emails the CEO a fake invoice from <span className="font-mono">invoices@corp-billing.xyz</span> with <span className="font-mono">Invoice_2026_0891.exe</span> attached — malware disguised as a document.</Step>
            <Step n={2} title="Exploitation">The CEO opens the attachment. It executes at 08:47, infecting the workstation (which has admin rights — a high-value foothold).</Step>
            <Step n={3} title="Installation & C2">The trojan (an Emotet variant) installs persistence and phones home to attacker-controlled command-and-control domains.</Step>
            <Step n={4} title="Objective">The attacker goal is the customer database (full of PII) — reachable from the CEO machine within hours.</Step>
            <P>Fusion detects this, predicts the path, builds containment, and the board decides — all before the attacker reaches the database.</P>
          </div>
        )}

        {section === 'chat' && (
          <div>
            <H>Talking to the Commander</H>
            <P>The chat on the War Room tab talks to the <B>Incident Commander</B> in plain English. It first classifies
            what you want, then acts:</P>
            <Step n={1} title="Report an attack">Words like phishing, breach, ransomware, or &ldquo;we got hacked&rdquo; mobilize the full 9-agent swarm and open an incident.</Step>
            <Step n={2} title="Ask for status">&ldquo;Are we safe?&rdquo; reads live agent states and gives a tight verdict + risk summary of the current incident.</Step>
            <Step n={3} title="Query memory">&ldquo;What have we learned?&rdquo; pulls incident history and learned defense recipes from the shared memory graph.</Step>
            <Step n={4} title="Ask how it works">&ldquo;How does Fusion work?&rdquo; explains the system. There is deeper detail right here in Docs.</Step>
            <P>Every reply shows a <B>Commander reasoning</B> trace — the actual background steps it took (classify intent,
            check memory, dispatch swarm, stream findings) so nothing feels like a black box.</P>
          </div>
        )}

        {section === 'memory' && (
          <div>
            <H>The shared memory graph</H>
            <P>All nine agents read and write a <B>shared, on-disk memory graph</B>. Every incident is recorded with a
            timeline of who found what, tagged by MITRE technique. When Blue Team confirms a working countermeasure, it is
            saved as a <B>defense recipe</B>.</P>
            <P>On the next attack, agents <B>query memory first</B>. If they have seen the technique before, they say
            &ldquo;we have handled this&rdquo; and reuse what worked — so the team measurably speeds up on repeat attacks.
            The Memory tab shows every incident, learned recipe, and your full Commander chat history.</P>
            <P>This is what turns Fusion from a one-shot script into a system that <B>learns</B>.</P>
          </div>
        )}

        {section === 'mcp' && (
          <div>
            <H>MCP integration</H>
            <P>Fusion ships a <B>Model Context Protocol (MCP) server</B> so any MCP-aware app — Claude Desktop, IDE
            assistants, or your own agents — can drive the entire nine-agent security team as a set of callable tools.</P>
            <P><B>1. Start the MCP server</B> (stdio transport):</P>
            <Code label="shell">{`python mcp_server.py`}</Code>
            <P><B>2. Register it</B> in your MCP client. For Claude Desktop, add this to
            <span className="font-mono"> claude_desktop_config.json</span>:</P>
            <Code label="claude_desktop_config.json">{`{
  "mcpServers": {
    "fusion": {
      "command": "python",
      "args": ["/path/to/fusion/mcp_server.py"],
      "env": { "FUSION_API_URL": "http://localhost:8000" }
    }
  }
}`}</Code>
            <P><B>3. The 7 tools</B> your AI app can now call:</P>
            <div className="rounded-xl border border-slate-200/60 dark:border-slate-800/60 divide-y divide-slate-200/50 dark:divide-slate-800/50">
              {MCP_TOOLS.map(([n, d]) => (
                <div key={n} className="flex items-start gap-3 p-2.5">
                  <code className="text-[11px] font-mono text-cyan-600 dark:text-cyan-400 shrink-0">{n}</code>
                  <span className="text-[11px] text-slate-500 dark:text-slate-400">{d}</span>
                </div>
              ))}
            </div>
            <P>The live tool registry is also on the <B>Settings</B> tab.</P>
          </div>
        )}

        {section === 'connectors' && (
          <div>
            <H>Connectors</H>
            <P>Connectors pull <B>real-world signal</B> into Fusion so the team works on live data, not just the demo
            scenario. Findings flow into the same shared memory graph every agent reads.</P>

            <div className="rounded-xl border border-slate-200/60 dark:border-slate-800/60 p-4 mb-3">
              <p className="text-[13px] font-bold text-slate-800 dark:text-slate-100">🐙 GitHub security scanner</p>
              <p className="text-[12px] text-slate-500 dark:text-slate-400 leading-relaxed mt-1">
                Scans any repo for <B>exposed secrets</B>, <B>vulnerable dependencies</B>, and <B>Dependabot alerts</B>,
                then correlates flagged packages against live NVD CVEs. Recon and Threat Intel review the results.
              </p>
              <Code label="POST /api/v1/scan">{`curl -X POST http://localhost:8000/api/v1/scan \\
  -H "Content-Type: application/json" \\
  -d '{"repo_url": "owner/repo", "scan_type": "full"}'`}</Code>
              <p className="text-[11px] text-slate-400 dark:text-slate-500">Set <span className="font-mono">GITHUB_TOKEN</span> in <span className="font-mono">.env</span> for private repos and higher rate limits.</p>
            </div>

            <div className="rounded-xl border border-slate-200/60 dark:border-slate-800/60 p-4 mb-3">
              <p className="text-[13px] font-bold text-slate-800 dark:text-slate-100">🧪 IoC threat analyzer</p>
              <p className="text-[12px] text-slate-500 dark:text-slate-400 leading-relaxed mt-1">
                Check a single indicator (IP, domain, file hash, or keyword) against live <B>NVD CVE</B> intelligence and
                everything the team has seen before.
              </p>
              <Code label="POST /api/v1/analyze-threat">{`curl -X POST http://localhost:8000/api/v1/analyze-threat \\
  -H "Content-Type: application/json" \\
  -d '{"indicator": "corp-billing.xyz", "ioc_type": "domain"}'`}</Code>
            </div>

            <div className="rounded-xl border border-slate-200/60 dark:border-slate-800/60 p-4">
              <p className="text-[13px] font-bold text-slate-800 dark:text-slate-100">📚 Built-in intelligence</p>
              <ul className="text-[12px] text-slate-500 dark:text-slate-400 leading-relaxed mt-1 space-y-1">
                <li>• <B>NVD CVE API</B> — live vulnerability lookups (rate-limit aware).</li>
                <li>• <B>MITRE ATT&CK</B> — local technique database for offline mapping.</li>
                <li>• <B>Digital twin</B> — the TechCorp company/network model the agents reason over.</li>
              </ul>
            </div>
          </div>
        )}

        {section === 'api' && (
          <div>
            <H>API reference</H>
            <P>Every feature is a REST endpoint on <span className="font-mono">http://localhost:8000</span>. The dashboard,
            MCP server, and connectors all use these.</P>
            <p className="text-[10px] font-mono uppercase tracking-widest text-slate-400 mt-4 mb-1">Response & control</p>
            <div className="rounded-xl border border-slate-200/60 dark:border-slate-800/60 px-3.5 py-1">
              <EndpointRow method="POST" path="/api/trigger-attack" desc="Run the built-in phishing simulation through all 9 agents." />
              <EndpointRow method="GET" path="/api/status" desc="Health, mode, registered rooms, active incident." />
              <EndpointRow method="POST" path="/api/reset" desc="Clear simulation state for a fresh run." />
              <EndpointRow method="WS" path="/ws" desc="Live agent status stream the dashboard subscribes to." />
            </div>
            <p className="text-[10px] font-mono uppercase tracking-widest text-slate-400 mt-4 mb-1">Commander chat</p>
            <div className="rounded-xl border border-slate-200/60 dark:border-slate-800/60 px-3.5 py-1">
              <EndpointRow method="POST" path="/api/v1/chat" desc="Plain-English chat; attack reports recruit the swarm. Returns intent + reasoning steps." />
              <EndpointRow method="GET" path="/api/v1/chat/history" desc="Persisted conversation log." />
              <EndpointRow method="DELETE" path="/api/v1/chat/history" desc="Clear the conversation log." />
            </div>
            <p className="text-[10px] font-mono uppercase tracking-widest text-slate-400 mt-4 mb-1">Connectors & intel</p>
            <div className="rounded-xl border border-slate-200/60 dark:border-slate-800/60 px-3.5 py-1">
              <EndpointRow method="POST" path="/api/v1/scan" desc="GitHub repo security scan." />
              <EndpointRow method="POST" path="/api/v1/analyze-threat" desc="Analyze a single IoC against CVEs + memory." />
            </div>
            <p className="text-[10px] font-mono uppercase tracking-widest text-slate-400 mt-4 mb-1">Memory & system</p>
            <div className="rounded-xl border border-slate-200/60 dark:border-slate-800/60 px-3.5 py-1">
              <EndpointRow method="GET" path="/api/v1/incidents" desc="List all incidents in shared memory." />
              <EndpointRow method="GET" path="/api/v1/incident/{id}" desc="One incident: timeline, decision, summary." />
              <EndpointRow method="GET" path="/api/v1/memory/stats" desc="Findings count + learned defense recipes." />
              <EndpointRow method="GET" path="/api/v1/memory/similar/{technique}" desc="Past incidents by MITRE technique." />
              <EndpointRow method="GET" path="/api/v1/system/settings" desc="Providers, LLM health, pace, MCP tools." />
              <EndpointRow method="POST" path="/api/v1/system/settings" desc="Set pace / primary provider / reset LLM cooldown." />
            </div>
          </div>
        )}

        {section === 'providers' && (
          <div>
            <H>AI providers & automatic fallback</H>
            <P>Agents can run on <B>Gemini, Groq, Featherless, or AI/ML API</B> — whichever keys you set in
            <span className="font-mono"> .env</span>. Fusion tries your primary provider first and walks down the chain on
            any error.</P>
            <P>If <B>every</B> provider is rate-limited or down, Fusion does not stall: the whole swarm drops to a built-in
            <B> local simulation engine</B> for a cooldown window, so a live demo always completes with a clean CEO verdict.
            You can change the primary provider or retry live providers from the Settings tab.</P>
            <Code label=".env">{`# any one of these enables live LLM reasoning
GROQ_API_KEY=...
GOOGLE_API_KEY=...
FEATHERLESS_API_KEY=...
AIMLAPI_KEY=...
FUSION_LLM_PRIMARY=gemini   # which to try first`}</Code>
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 mt-2">
              <p className="text-[12px] text-slate-600 dark:text-slate-300"><B>Note:</B> free tiers have daily token caps —
              roughly one full real-LLM run per day on a free Groq key. The local engine is the safety net for everything after that.</p>
            </div>
          </div>
        )}

        {section === 'architecture' && (
          <div>
            <H>Architecture</H>
            <P>Fusion is a Python backend plus a Next.js dashboard:</P>
            <ul className="space-y-2 text-[12px] text-slate-600 dark:text-slate-300 mb-3">
              <li>• <B>FastAPI + Uvicorn</B> — REST + WebSocket server (<span className="font-mono">api/</span>).</li>
              <li>• <B>LangGraph React agents</B> — each specialist is a tool-using agent (<span className="font-mono">agents/</span>).</li>
              <li>• <B>Band SDK</B> — the chat-room message bus agents coordinate over (mock bus offline).</li>
              <li>• <B>Memory graph</B> — shared JSON incident store (<span className="font-mono">core/memory_graph.py</span>).</li>
              <li>• <B>Event bus to WebSocket</B> — streams every status change to this dashboard live.</li>
              <li>• <B>MCP server</B> — exposes the team to external AI apps (<span className="font-mono">mcp_server.py</span>).</li>
            </ul>
            <P>When an alert fires, the Commander dispatches specialists into their rooms over Band; each runs its LangGraph
            flow, logs findings to memory, and broadcasts status to the event bus, which this UI renders in real time.</P>
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
