// lib/agents.ts — single source of truth for agent metadata across the UI.

export interface AgentMeta {
  name: string
  displayName: string
  icon: string
  role: string          // short professional title
  plain: string         // one-line plain-English "what it does for you"
  detail: string        // deeper description for Docs / detail view
  checklist: string[]   // representative due diligence checklist points
  room: string
  group: 'intake' | 'analysis' | 'command' | 'executive'
}

export const AGENTS: AgentMeta[] = [
  {
    name: 'managing_partner',
    displayName: 'Managing Partner',
    icon: '🎯',
    role: 'Committee Chair & Managing Partner',
    plain: 'Chairs the investment committee, dispatches deals, and synthesizes final verdicts.',
    detail: 'Coordinates the specialist partners, builds the deal timeline, runs the weighted risk model, debates conflicts, and delivers the final boardroom decision memo.',
    checklist: ['Deal Briefing', 'Scope Definition', 'Partner Mobilization', 'Conflict Resolution', 'Verdict Drafting', 'Boardroom Synthesis'],
    room: '#managing-partner-room',
    group: 'command',
  },
  {
    name: 'financial_partner',
    displayName: 'Financial Partner',
    icon: '📊',
    role: 'Forensic Accountant & Financial Analyst',
    plain: 'Stress-tests the revenue model, burn rate, and unit economics.',
    detail: 'Evaluates revenue quality, ARR/MRR customer concentration, gross margins, CAC payback, runway, and valuation multiples to identify financial risks.',
    checklist: ['ARR Concentration', 'Gross Margin Check', 'Runway & Burn Audit', 'LTV:CAC stress-test', 'Valuation Analysis', 'Cap Table Verification'],
    room: '#finance-partner-room',
    group: 'analysis',
  },
  {
    name: 'legal_partner',
    displayName: 'Legal Partner',
    icon: '⚖️',
    role: 'M&A Legal Counsel',
    plain: 'Audits contracts, IP ownership, regulatory compliance, and active lawsuits.',
    detail: 'Examines active litigation, money transmitter licensing gaps, CFPB and state regulatory compliance, CCPA/GDPR risk, and founder history for legal liabilities.',
    checklist: ['Litigation Review', 'Licensing Audit', 'Regulatory Alignment', 'IP Ownership Check', 'Data Privacy (GDPR/CCPA)', 'Founder Background Scan'],
    room: '#legal-partner-room',
    group: 'analysis',
  },
  {
    name: 'technical_partner',
    displayName: 'Technical Partner',
    icon: '🔧',
    role: 'CTO Advisor & Security Auditor',
    plain: 'Audits codebase, software lifecycles, and security posture.',
    detail: 'Evaluates software dependencies, EOL software runtimes, database security (e.g., plaintext credentials/SSNs), scalability constraints, and historical breaches.',
    checklist: ['EOL Runtime Audit', 'Plaintext PII/SSN Check', 'Penetration History', 'Scalability Architecture', 'MFA/Admin Security', 'Software Bill of Materials'],
    room: '#tech-partner-room',
    group: 'analysis',
  },
  {
    name: 'market_partner',
    displayName: 'Market Partner',
    icon: '📈',
    role: 'Market Research Director',
    plain: 'Validates market size (TAM), competitive landscape, and sector timing.',
    detail: 'Audits founder market size claims, competitive pressure from incumbents, sector growth rates, regulatory timing, and VC funding trends.',
    checklist: ['TAM Validation', 'Growth Trend Audit', 'Competitor Profiling', 'Moat & Defensibility Check', 'Sector Venture Funding Check', 'Regulatory Market Impact'],
    room: '#market-partner-room',
    group: 'analysis',
  },
]

export const AGENT_BY_NAME: Record<string, AgentMeta> =
  Object.fromEntries(AGENTS.map(a => [a.name, a]))

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

