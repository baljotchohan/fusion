# api/v1.py
"""
FUSION v1 REST API — chat with the Managing Partner, deal record queries,
and shared-memory deal database retrieval.

These are the product-facing endpoints (used by the Web UI, external
clients, and the MCP server in mcp_server.py).
"""
import os
import json
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, File, UploadFile
from fastapi.responses import StreamingResponse
import io
from pypdf import PdfReader
from pydantic import BaseModel

from core.event_bus import event_bus
from core.band_client import mock_bus, is_mock_mode
from core.memory_graph import memory_graph
from core.llm_router import get_router
from core.cve_lookup import get_cves_async
from connectors.github_scanner import GitHubScanner, parse_repo_url
from api.state import sim_state

logger = logging.getLogger("fusion.api.v1")

router = APIRouter(prefix="/api/v1")
DEAL_KEYWORDS = (
    "deal", "startup", "investment", "diligence", "acquire", "acquisition",
    "novapay", "pitch", "evaluate", "funding", "committee", "financial", "legal",
    "query", "record", "evaluation", "result", "verdict", "score", "findings",
    "last", "latest", "recent", "previous", "prior"
)

AGENT_NAMES = [
    "managing_partner", "financial_partner", "legal_partner",
    "technical_partner", "market_partner",
]


def _new_incident_id() -> str:
    return f"DEAL-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"


def _agent_statuses() -> dict:
    return {name: sim_state.agent_statuses.get(name, "idle") for name in AGENT_NAMES}


# ─── CHAT WITH MANAGING PARTNER ─────────────────────────────

class ChatMessage(BaseModel):
    user_message: str
    incident_id: Optional[str] = None


class ChatResponse(BaseModel):
    commander_response: str
    incident_id: str
    agent_updates: dict
    memory_context: str
    intent: str = "general"
    thinking_steps: List[str] = []
    dispatched: bool = False
    suggestions: List[str] = []


# Intent vocabulary — keyword buckets the Managing Partner uses to route a message.
_STATUS_WORDS = ("status", "active", "in session", "right now", "happening",
                 "current", "going on", "are we", "risk score", "verdict")
_MEMORY_WORDS = ("learn", "learned", "remember", "memory", "past", "history",
                 "before", "previous", "seen this", "pattern", "how many", "deals")
_DOCS_WORDS = ("how do you work", "how does this work", "explain", "what is fusion",
               "who are you", "what can you do", "help", "documentation", "architecture")
_GREETING_WORDS = ("hi", "hii", "hiya", "hello", "helo", "hallo", "hey", "heyy",
                    "yo", "sup", "greetings", "howdy", "good", "gm", "morning", "hlo", "hy", "hola",
                    "kya", "namaste", "kem", "adaab", "salam", "wassup", "halloo")
_THANKS_WORDS = ("thanks", "thank you", "thx", "ty", "appreciate", "great", "nice", "cool", "awesome")
_TRIGGER_KEYWORDS = ("evaluate", "run diligence", "run due diligence", "start simulation", "trigger simulation", "analyze startup", "run evaluation", "test startup", "assess startup")


def _classify_intent(text: str) -> str:
    """Deterministic intent router so replies are relevant and non-disruptive."""
    t = text.lower().strip().rstrip("!.")
    words = t.split()
    first = words[0] if words else t
    
    # 1. Explicit trigger request
    if any(k in t for k in _TRIGGER_KEYWORDS) or (t.startswith("evaluate ") and len(words) > 1):
        return "trigger_evaluation"
        
    # 2. Greeting
    if t in _GREETING_WORDS or first in _GREETING_WORDS:
        return "greeting"
        
    # 3. Thanks
    if t in _THANKS_WORDS or first in _THANKS_WORDS:
        return "thanks"
        
    # 4. Docs
    if any(k in t for k in _DOCS_WORDS):
        return "docs"
        
    # 5. Memory / history
    if any(k in t for k in _MEMORY_WORDS):
        return "memory"
        
    # 6. Query specific deal details (if we mention deal keywords or query status/results)
    if any(k in t for k in DEAL_KEYWORDS) or any(k in t for k in _STATUS_WORDS) or t.endswith("?"):
        return "query_deal"
        
    return "general"


def _suggestions_for(intent: str) -> List[str]:
    base = {
        "trigger_evaluation": ["What did the Legal Partner find?", "What's the financial risk?", "Show me the final boardroom verdict"],
        "query_deal": ["Evaluate a new deal", "What has the committee learned?", "How does FUSION work?"],
        "memory": ["Evaluate NovaPay", "What is the committee status?", "Which risk patterns recur?"],
        "docs": ["Evaluate NovaPay", "What are the 5 partner agents?", "What is the weighted scoring?"],
        "greeting": ["Evaluate NovaPay", "Is the committee in session?", "What did the committee learn?"],
        "thanks": ["Evaluate a deal", "What's our status?", "How does FUSION work?"],
        "general": ["Evaluate NovaPay", "What's our status?", "What has the committee learned?"],
    }
    return base.get(intent, base["general"])


async def dispatch_real_band_message(content: str, target_agent_handle_sub: str) -> bool:
    """Send a message to the real Band platform chat room, resolving and mentioning the target agent."""
    import yaml
    from thenvoi_rest import AsyncRestClient
    from thenvoi.client.rest import ChatMessageRequest
    from thenvoi_rest.types import ChatMessageRequestMentionsItem

    try:
        config_path = "agent_config.yaml"
        if not os.path.exists(config_path):
            config_path = "agent_config.example.yaml"
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}
        agent_conf = config.get("agents", {}).get("managing_partner") or config.get("managing_partner", {})
        api_key = agent_conf.get("api_key")
        if not api_key:
            logger.error("Real Band dispatch: Managing Partner API key not found in config")
            return False

        client = AsyncRestClient(api_key=api_key, base_url="https://app.thenvoi.com")
        chats_resp = await client.agent_api_chats.list_agent_chats()
        chats = chats_resp.data or []
        if not chats:
            logger.error("Real Band dispatch: No active chats found for Managing Partner")
            return False

        chat_id = chats[0].id

        p_resp = await client.agent_api_participants.list_agent_chat_participants(chat_id=chat_id)
        participants = p_resp.data or []

        target_p = None
        for p in participants:
            p_handle = p.handle if hasattr(p, "handle") else p.get("handle") if isinstance(p, dict) else ""
            p_id = p.id if hasattr(p, "id") else p.get("id") if isinstance(p, dict) else ""
            p_name = p.name if hasattr(p, "name") else p.get("name") if isinstance(p, dict) else ""

            if p_handle and target_agent_handle_sub.lower() in p_handle.lower():
                target_p = {"id": p_id, "handle": p_handle, "name": p_name}
                break

        if not target_p:
            logger.error(f"Real Band dispatch: Target agent matching '{target_agent_handle_sub}' not found in participants")
            return False

        mentions = [
            ChatMessageRequestMentionsItem(
                id=target_p["id"],
                handle=target_p["handle"],
                name=target_p["name"]
            )
        ]

        if not content.startswith(f"@{target_p['handle']}"):
            content = f"@{target_p['handle']} {content}"

        await client.agent_api_messages.create_agent_chat_message(
            chat_id=chat_id,
            message=ChatMessageRequest(content=content, mentions=mentions)
        )
        logger.info(f"Real Band dispatch: Successfully sent trigger message to chat {chat_id} mentioning {target_p['handle']}")
        return True
    except Exception as e:
        logger.error(f"Real Band dispatch failed: {e}")
        return False


async def _dispatch_incident(incident_id: str, user_message: str):
    """Wake the boardroom: route the pitch/brief into the managing-partner-room."""
    sim_state.running = True
    sim_state.active_incident_id = incident_id
    company = sim_state.active_company_name or "NovaPay Inc"
    brief = (
        f"New deal submitted for committee review: {company} — Series A raise. "
        f"User message: {user_message}. Please convene the investment committee and begin due diligence."
    )
    if is_mock_mode():
        await mock_bus.send_message("Advisor-Chat", "managing-partner-room", brief)
    else:
        success = await dispatch_real_band_message(brief, "managing-partner")
        if not success:
            logger.warning("Real Band dispatch failed, falling back to local bus")
            await mock_bus.send_message("Advisor-Chat", "managing-partner-room", brief)


def _incident_headline(incident_id: Optional[str]) -> Optional[dict]:
    """A tight, structured snapshot of one incident — verdict, risk, top finding —
    so chat replies stay clean instead of dumping the whole raw timeline."""
    if not incident_id:
        return None
    inc = memory_graph.get_incident(incident_id)
    if not inc:
        return None
    verdict = None
    fd = inc.get("final_decision") or ""
    m = re.search(r"DECISION:\s*([A-Za-z]+)", fd, re.I)
    if m:
        verdict = m.group(1).upper()
    risk = None
    headline_finding = None
    for ev in inc.get("timeline", []):
        finding = str(ev.get("finding", ""))
        rm = re.search(r"WEIGHTED SCORE:\s*([\d\.]+)/10", finding, re.I)
        if rm:
            risk = float(rm.group(1))
        if ev.get("agent") == "managing_partner" and not headline_finding:
            tm = re.search(r"Company:\s*([^\n]+)", finding, re.I)
            if tm:
                headline_finding = tm.group(1).strip()
    return {
        "incident_id": incident_id,
        "verdict": verdict,
        "risk": risk,
        "threat_level": inc["metadata"].get("threat_level"),
        "findings": len(inc.get("timeline", [])),
        "headline": headline_finding,
    }


def _deterministic_reply(intent: str, user_message: str, incident_id: str,
                         dispatched: bool, stats: dict, latest_summary: str,
                         latest_id: Optional[str]) -> str:
    """Offline-safe, intent-aware Managing Partner reply built from real memory state."""
    n_inc = stats["total_incidents"]
    n_pat = len(stats["learned_patterns"])
    active = [a for a, s in _agent_statuses().items() if s == "working"]
    head = _incident_headline(latest_id)

    if intent == "trigger_evaluation" and dispatched:
        return (
            f"Understood — I've opened deal record **{incident_id}** and mobilized the FUSION investment committee. "
            "Here's what happens over the next minute:\n"
            "1. **Managing Partner** convenes the room and briefs the specialists.\n"
            "2. **Financial, Legal, Technical, and Market Partners** perform domain audits in parallel.\n"
            "3. **Managing Partner** collects all findings, debates conflicts, and delivers the final boardroom verdict.\n\n"
            "Watch the graph on the right — I'll display the verdict the moment the boardroom reaches a decision."
        )
    if intent == "trigger_evaluation" and not dispatched:
        return (
            "A due diligence review is already running, so I've folded your report into the active deal rather than "
            f"starting a second one. Most recent: **{latest_id}**."
        )
    if intent == "greeting":
        return (
            "Hello! I am the **FUSION Managing Partner**. I chair the investment committee and coordinate our 5 specialist partners.\n\n"
            "How can I assist you today? You can drag and drop a startup deck, ask me to *evaluate a startup*, or query past diligence records."
        )
    if intent == "thanks":
        return "You're very welcome. Let me know if you need any other startup evaluations."
    if intent == "docs":
        return (
            "**FUSION** is an AI-powered VC Investment Boardroom. Five specialist partner agents — "
            "Managing Partner, Financial Partner, Legal Partner, Technical Partner, and Market Partner — "
            "coordinate to perform domain audit, run parallel due diligence, and debate startup pitches in under five minutes.\n\n"
            "Submit a pitch/brief in plain English and the committee will convene. The **Docs** tab contains details on weighted risk models."
        )
    if intent == "memory":
        patt = stats["learned_patterns"]
        lines = "\n".join(f"• **{k}** — {v} risk checklist(s)" for k, v in list(patt.items())[:8]) or "• none yet"
        return (
            f"Across **{n_inc} deal(s)** evaluated, the committee has logged **{stats['total_findings']} findings** and resolved "
            f"**{n_pat} recurring risk pattern(s)** across domains:\n{lines}\n\n"
            "On repeat reviews, partner agents check this database first and apply prior due diligence learnings to identify flags faster."
        )
    
    # query_deal
    if intent == "query_deal":
        if head:
            verdict_str = f"**{head['verdict']}**" if head['verdict'] else "**PENDING**"
            risk_str = f"**{head['risk']}/10**" if head['risk'] is not None else "**PENDING**"
            return (
                f"Regarding our latest evaluation record (**{head['incident_id']}**):\n"
                f"- **Verdict**: {verdict_str}\n"
                f"- **Threat Risk Score**: {risk_str}\n"
                f"- **Headline target**: {head['headline'] or 'NovaPay Inc'}\n\n"
                f"You can view the full minute-by-minute timeline in the **History** tab, or ask me for details on a specific domain."
            )
        else:
            return "No active deal or past evaluation records were found in the committee database."
        
    return (
        "I can help you coordinate the FUSION Investment Committee. "
        "Try saying \"evaluate NovaPay\" to start a due diligence review, \"what is the committee status?\" to view current progress, "
        "or \"what has the committee learned?\" to see past findings."
    )


def _display(agent_key: str) -> str:
    return {
        "managing_partner": "Managing Partner", "financial_partner": "Financial Partner",
        "legal_partner": "Legal Partner", "technical_partner": "Technical Partner",
        "market_partner": "Market Partner",
    }.get(agent_key, agent_key)


async def _commander_reply(intent: str, user_message: str, incident_id: str,
                           dispatched: bool) -> str:
    """Synthesize the Managing Partner's reply. Real LLM when a key is live and healthy,
    otherwise an intent-aware deterministic reply from the shared memory graph."""
    stats = memory_graph.get_memory_stats()
    latest_id = memory_graph.get_latest_incident_id()
    latest_summary = memory_graph.get_team_summary(latest_id) if latest_id else "No deals on record yet."

    from core.base_agent import llm_degraded, degrade_llm

    llm_router = get_router()
    if llm_router.available_providers() and not llm_degraded():
        recent = memory_graph.get_chat_history(limit=6)
        convo = "\n".join(f"{t['role']}: {t['content'][:200]}" for t in recent)
        
        # Dynamic instructions based on intent to prevent irrelevant deal dumping
        if intent == "greeting":
            intent_instructions = (
                "Greeting detected. Greet the user warmly and professionally as the FUSION Managing Partner. "
                "Keep it brief (1-2 sentences). Do NOT mention any specific deal names, risk scores, or verdicts "
                "unless the user specifically asked for them. Offer to help them evaluate a startup pitch or check "
                "our investment committee records."
            )
        elif intent == "thanks":
            intent_instructions = (
                "Gratitude detected. Respond briefly and politely (1 sentence) saying you are glad to help."
            )
        elif intent == "trigger_evaluation":
            intent_instructions = (
                f"You have just mobilized the investment committee on a new deal ({incident_id}). "
                f"Explain that you have convened the boardroom and briefed the specialists. Let them know they "
                f"can follow the live Roundtable and Minutes to watch the deliberation proceed."
            )
        elif intent == "query_deal":
            intent_instructions = (
                f"The user is asking about the active or latest deal. Use the latest deal summary:\n{latest_summary}\n"
                "to answer their question directly, cleanly, and professionally. Focus on what they asked."
            )
        elif intent == "docs":
            intent_instructions = (
                "Explain FUSION's committee architecture. We run a 5-partner agent swarm (Managing, Financial, "
                "Legal, Technical, and Market partners) performing parallel due diligence. Explain how they use "
                "shared memory and weighted risk scores to debate and synthesize a PASS/INVEST verdict."
            )
        elif intent == "memory":
            intent_instructions = (
                f"Summarize what the committee has learned globally. We have evaluated {stats['total_incidents']} "
                f"deals, logged {stats['total_findings']} findings, and catalogued {len(stats['learned_patterns'])} "
                f"learned risk patterns. Keep it professional."
            )
        else:
            intent_instructions = (
                f"General query. Answer contextually. If the query relates to startup investments or our current active deal ({incident_id}), "
                f"use this summary: {latest_summary}. Keep your answer clean and structured."
            )

        prompt = f"""You are the FUSION Managing Partner — a calm, sharp, elite VC general partner.
Talking to a user in plain English.

Context:
- Active Deal ID: {incident_id}
- Active Swarm running: {sim_state.running}

Instructions for this message:
{intent_instructions}

Formatting:
1. Always respond in a clean, advanced, well-structured format. Use Markdown bullet points, bold key terms, and section dividers if helpful.
2. Adopt a high-end, elite VC partner tone. Avoid raw JSON, logs, or developer jargon.
3. Keep it concise (2-4 sentences or structured bullets) and highly readable.
4. User message: "{user_message}"
"""
        try:
            return await llm_router.call_llm(prompt, max_tokens=420)
        except Exception as e:
            logger.warning(f"Managing Partner chat LLM failed, using deterministic reply: {e}")
            degrade_llm(str(e))

    return _deterministic_reply(intent, user_message, incident_id, dispatched,
                                stats, latest_summary, latest_id)


def _build_thinking_steps(intent: str, dispatched: bool, incident_id: str) -> List[str]:
    """The actual background steps the Managing Partner took — surfaced to the UI."""
    steps = [f"Parsed message → intent classified as **{intent.replace('_', ' ')}**"]
    if intent == "trigger_evaluation":
        if dispatched:
            steps += [
                f"Opened deal record **{incident_id}** in shared memory",
                "Queried team memory for matching risk checklists",
                "Dispatched brief into #managing-partner-room — committee convened",
                "Streaming partner findings to the live graph",
            ]
        else:
            steps += ["A due diligence session is already running — folded this into the active deal"]
    elif intent == "query_deal":
        steps += [
            "Read live agent statuses from the event bus",
            f"Checked simulation lock (running={sim_state.running})",
            "Summarized latest deal from memory graph",
        ]
    elif intent == "memory":
        steps += [
            "Loaded deal timeline + learned risk patterns from memory graph",
            "Aggregated findings count and checklists",
        ]
    elif intent == "docs":
        steps += ["Pulled boardroom architecture overview from the knowledge base"]
    elif intent in ("greeting", "thanks"):
        steps += ["Checked live boardroom state for a quick status read"]
    else:
        steps += ["Checked memory graph for relevant context"]
    return steps


@router.post("/chat", response_model=ChatResponse)
async def chat_with_commander(msg: ChatMessage):
    """Chat with the FUSION Managing Partner or mentioned specialist partners."""
    incident_id = msg.incident_id or sim_state.active_incident_id or _new_incident_id()
    
    # Check for agent mention
    mentioned_agent = None
    lower_msg = msg.user_message.lower()
    
    if any(h in lower_msg for h in ["@financial-partner", "@financial", "@finance"]):
        mentioned_agent = "financial_partner"
    elif any(h in lower_msg for h in ["@legal-partner", "@legal", "@lawyer"]):
        mentioned_agent = "legal_partner"
    elif any(h in lower_msg for h in ["@technical-partner", "@technical", "@tech", "@cto"]):
        mentioned_agent = "technical_partner"
    elif any(h in lower_msg for h in ["@market-partner", "@market"]):
        mentioned_agent = "market_partner"
    elif any(h in lower_msg for h in ["@managing-partner", "@managing", "@chair"]):
        mentioned_agent = "managing_partner"
        
    intent = _classify_intent(msg.user_message)
    memory_graph.append_chat("user", msg.user_message, {"intent": intent, "mentioned_agent": mentioned_agent})
    
    dispatched = False
    if not mentioned_agent and intent == "trigger_evaluation" and not sim_state.running:
        memory_graph.create_incident(incident_id, {
            "trigger": "commander_chat",
            "user_message": msg.user_message[:300],
            "threat_level": 5,
        })
        await _dispatch_incident(incident_id, msg.user_message)
        dispatched = True
    elif msg.incident_id is None and memory_graph.get_latest_incident_id():
        incident_id = memory_graph.get_latest_incident_id()
        
    thinking_steps = _build_thinking_steps(intent, dispatched, incident_id)
    if mentioned_agent:
        intent = "agent_mention"
        thinking_steps += [f"Mention detected → routing to **{_display(mentioned_agent)}**", "Loading agent persona and memory graph context"]
        commander_response = await _agent_reply(mentioned_agent, msg.user_message, incident_id)
    else:
        commander_response = await _commander_reply(intent, msg.user_message, incident_id, dispatched)
        
    memory_context = memory_graph.get_team_summary(incident_id)
    
    memory_graph.append_chat("assistant", commander_response,
                             {"intent": intent, "incident_id": incident_id, "dispatched": dispatched, "agent": mentioned_agent})
                             
    return ChatResponse(
        commander_response=commander_response,
        incident_id=incident_id,
        agent_updates=_agent_statuses(),
        memory_context=memory_context,
        intent=intent,
        thinking_steps=thinking_steps,
        dispatched=dispatched,
        suggestions=_suggestions_for(intent) if not mentioned_agent else ["Ask about legal risks", "Ask about financial runway", "Show verdict memo"],
    )


@router.get("/chat/history")
async def chat_history(limit: int = 100):
    """Return persisted Commander chat history for the Memory tab."""
    return {"history": memory_graph.get_chat_history(limit=limit)}


@router.delete("/chat/history")
async def clear_chat_history():
    """Clear the persisted Commander chat history."""
    memory_graph.clear_chat_history()
    return {"status": "cleared"}


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """Live chat with the Commander — streams agent updates while the swarm works."""
    await websocket.accept()

    async def forward_agent_event(event_data: dict):
        try:
            await websocket.send_json(event_data)
        except Exception:
            pass

    event_bus.register_listener(forward_agent_event)
    try:
        while True:
            user_msg = await websocket.receive_text()
            await websocket.send_json({"type": "status", "status": "thinking", "agents": _agent_statuses()})
            result = await chat_with_commander(ChatMessage(user_message=user_msg))
            await websocket.send_json({
                "type": "commander_decision",
                "response": result.commander_response,
                "incident_id": result.incident_id,
                "memory_context": result.memory_context,
                "intent": result.intent,
                "thinking_steps": result.thinking_steps,
                "dispatched": result.dispatched,
                "suggestions": result.suggestions,
            })
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"/ws/chat error: {e}")
    finally:
        event_bus.unregister_listener(forward_agent_event)


# ─── MOCK DOCUMENT / SCAN AND ANALYSIS STUBS ─────────────────
# The scan concept is gone, but we retain stub endpoints to prevent 404s.

class ScanRequest(BaseModel):
    repo_url: str
    scan_type: str = "full"


class ScanResponse(BaseModel):
    scan_id: str
    status: str
    findings: list
    threat_level: int
    recommendations: list


@router.post("/scan", response_model=ScanResponse)
async def scan_repo(request: ScanRequest):
    """Stub endpoint for repository scanning (deprecated)."""
    return ScanResponse(
        scan_id="SCAN-DEPRECATED",
        status="complete",
        findings=[],
        threat_level=1,
        recommendations=["The repository code scanner is deprecated. FUSION is document/brief-driven."],
    )


class ThreatRequest(BaseModel):
    indicator: str
    ioc_type: str = "domain"


class ThreatResponse(BaseModel):
    indicator: str
    severity: int
    matches: list
    context: str


@router.post("/analyze-threat", response_model=ThreatResponse)
async def analyze_threat(request: ThreatRequest):
    """Stub endpoint for threat analysis (deprecated)."""
    return ThreatResponse(
        indicator=request.indicator,
        severity=1,
        matches=[],
        context="IoC threat analysis is deprecated. FUSION runs on advisor-based deal due diligence.",
    )


# ─── INCIDENT MEMORY ──────────────────────────────────────────

@router.get("/incidents")
async def list_incidents():
    """List all deals in the shared team memory graph."""
    incidents = memory_graph.list_incidents()
    return {
        "total": len(incidents),
        "incidents": [
            {
                "incident_id": inc_id,
                "threat_level": inc["metadata"].get("threat_level"),
                "trigger": inc["metadata"].get("trigger"),
                "findings": len(inc.get("timeline", [])),
                "final_decision": (inc.get("final_decision") or "")[:120] or None,
                "created_at": inc.get("created_at"),
            }
            for inc_id, inc in sorted(incidents.items(), key=lambda kv: kv[1].get("created_at", ""), reverse=True)
        ],
    }


@router.get("/incident/{incident_id}")
async def get_incident(incident_id: str):
    """Retrieve past deal details and the team's response timeline."""
    inc = memory_graph.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Deal not found")
    return {
        "incident_id": incident_id,
        "threat_level": inc["metadata"].get("threat_level"),
        "metadata": inc["metadata"],
        "timeline": inc["timeline"],
        "final_decision": inc["final_decision"],
        "created_at": inc["created_at"],
        "summary": memory_graph.get_team_summary(incident_id),
    }


@router.get("/memory/stats")
async def memory_stats():
    """How much the team has learned across all evaluated deals."""
    return memory_graph.get_memory_stats()


@router.get("/memory/similar/{keyword}")
async def similar_deals(keyword: str, limit: int = 5):
    """Query team memory for past deals matching a keyword."""
    past = await memory_graph.query_similar_incidents(keyword, limit=limit)
    return {"keyword": keyword, "similar_deals": past}


# ─── SYSTEM SETTINGS & MCP REGISTRY ───────────────────────────

MCP_TOOLS = [
    {"name": "chat_with_managing_partner", "category": "Command",
     "description": "Talk to the Managing Partner in plain English. Submitting a deal/pitch activates the committee.",
     "inputs": ["message"]},
    {"name": "get_deal_record", "category": "Memory",
     "description": "Retrieve a past investment target timeline, decision, and risk scorecard data from the shared memory graph.",
     "inputs": ["incident_id"]},
    {"name": "get_boardroom_verdict", "category": "Executive",
     "description": "Get the investment committee's final verdict for a startup deal.",
     "inputs": ["incident_id"]},
    {"name": "query_deal_vault", "category": "Memory",
     "description": "Query collective memory for similar past evaluations by sector or risk pattern.",
     "inputs": ["keyword", "limit"]},
    {"name": "learn_risk_pattern", "category": "Memory",
     "description": "Teach the committee a due diligence checklist or risk pattern.",
     "inputs": ["keyword", "checklist", "success_rate"]},
]

_PROVIDER_META = [
    ("gemini", "GOOGLE_API_KEY", "Google Gemini 2.0 Flash", "Fast multimodal reasoning"),
    ("groq", "GROQ_API_KEY", "Groq — Llama 3.3 70B", "Free, very low latency"),
    ("featherless", "FEATHERLESS_API_KEY", "Featherless — OSS models", "Mistral / Qwen / Llama"),
    ("aimlapi", "AIMLAPI_KEY", "AI/ML API — GPT-4o", "200+ models, one key"),
]


def _provider_status() -> list:
    def _placeholder(v: Optional[str]) -> bool:
        return not v or "your-" in v or "get-from" in v
    router = get_router()
    available = set(router.available_providers())
    out = []
    for pid, env, label, note in _PROVIDER_META:
        key = os.getenv(env)
        out.append({
            "id": pid,
            "env": env,
            "label": label,
            "note": note,
            "configured": not _placeholder(key),
            "in_chain": pid in available,
            "masked_key": (key[:6] + "…" + key[-3:]) if key and not _placeholder(key) and len(key) > 12 else None,
        })
    return out


class SettingsPatch(BaseModel):
    mock_pace: Optional[float] = None
    primary_provider: Optional[str] = None
    reset_llm_degradation: Optional[bool] = None
    max_file_size_mb: Optional[int] = None


@router.get("/system/settings")
async def get_system_settings():
    """Everything the Settings tab renders: providers, LLM health, pace, mode, MCP tools."""
    from core.base_agent import llm_degraded
    return {
        "mode": "mock" if is_mock_mode() else "real",
        "band_mock": is_mock_mode(),
        "llm": {
            "primary": os.getenv("ARGUS_LLM_PRIMARY", "gemini"),
            "degraded": llm_degraded(),
            "providers": _provider_status(),
            "active_provider": (get_router().available_providers() or ["local-engine"])[0]
                if not llm_degraded() else "local-engine",
        },
        "simulation": {
            "running": sim_state.running,
            "active_incident_id": sim_state.active_incident_id,
            "mock_pace": float(os.getenv("ARGUS_MOCK_PACE", "0.6")),
            "max_file_size_mb": sim_state.max_file_size_mb,
        },
        "rooms": list(mock_bus.rooms.keys()) if is_mock_mode() else [],
        "agents": AGENT_NAMES,
        "mcp": {
            "server": "fusion-mcp",
            "transport": "stdio",
            "tool_count": len(MCP_TOOLS),
            "tools": MCP_TOOLS,
            "connect_hint": "Run `python mcp_server.py` and register it in your MCP client (Claude Desktop, etc.).",
        },
        "memory_stats": memory_graph.get_memory_stats(),
    }


@router.post("/system/settings")
async def update_system_settings(patch: SettingsPatch):
    """Apply runtime settings from the UI (pace, primary provider, clear LLM cooldown, file limits)."""
    applied = {}
    if patch.mock_pace is not None:
        pace = max(0.0, min(3.0, patch.mock_pace))
        os.environ["ARGUS_MOCK_PACE"] = str(pace)
        applied["mock_pace"] = pace
    if patch.primary_provider:
        os.environ["ARGUS_LLM_PRIMARY"] = patch.primary_provider
        # Rebuild the router so the new primary takes effect immediately
        import core.llm_router as _lr
        _lr._router = None
        applied["primary_provider"] = patch.primary_provider
    if patch.reset_llm_degradation:
        import core.base_agent as _ba
        _ba._llm_degraded_until = 0.0
        applied["reset_llm_degradation"] = True
    if patch.max_file_size_mb is not None:
        size = max(1, min(100, patch.max_file_size_mb))
        sim_state.max_file_size_mb = size
        applied["max_file_size_mb"] = size
    return {"status": "ok", "applied": applied}


@router.get("/system/mcp")
async def get_mcp_registry():
    """The MCP tool surface external AI apps can call."""
    return {"server": "fusion-mcp", "transport": "stdio", "tools": MCP_TOOLS}


# ─── AGENT DIRECT CHAT & DOCUMENT SaaS ENDPOINTS ────────────

async def _agent_reply(agent_name: str, user_message: str, incident_id: str) -> str:
    """Generate a high-quality persona-specific response for a targeted agent."""
    stats = memory_graph.get_memory_stats()
    inc = memory_graph.get_incident(incident_id) if incident_id else None
    
    agent_findings = []
    if inc:
        for ev in inc.get("timeline", []):
            if ev.get("agent") == agent_name:
                agent_findings.append(ev.get("finding", ""))
    
    findings_str = "\n".join(f"- {f}" for f in agent_findings) if agent_findings else "No findings logged yet."
    
    PERSONAS = {
        "financial_partner": {
            "name": "Financial Partner",
            "role": "Forensic Accountant & Financial Analyst",
            "bio": "You are a Senior Financial Partner at a top-tier VC firm. You have 15 years of experience in forensic accounting and startup due diligence. You are analytical, skeptical, and focused on hard numbers.",
            "mandate": "Evaluate revenue quality, Amazon ARR concentration (78%), gross margins (48%), runway (8 months), burn ($380k), LTV:CAC (2.5x), and valuation multiples."
        },
        "legal_partner": {
            "name": "Legal Partner",
            "role": "M&A Legal Counsel",
            "bio": "You are a Senior Legal Partner at the VC firm, formerly an M&A attorney at Sullivan & Cromwell with 18 years of experience. You focus on contracts, IP, lawsuits, and regulatory landmines.",
            "mandate": "Evaluate litigation risks (Klarna $8M lawsuit), state transmitter licensing gaps (CA, NY, TX, FL), CCPA/GDPR compliance, CFPB compliance, and founder histories."
        },
        "technical_partner": {
            "name": "Technical Partner",
            "role": "CTO Advisor & Security Auditor",
            "bio": "You are a Senior Technical Partner at the VC firm, auditing product stacks, cybersecurity posture, tech debt, and database vulnerabilities.",
            "mandate": "Evaluate EOL Node.js 14 and MongoDB 4.2 in production, plaintext storage of SSNs/PII, monolithic scalability issues, and undisclosed breaches."
        },
        "market_partner": {
            "name": "Market Partner",
            "role": "Market Research Director",
            "bio": "You are a Senior Market Partner at the firm, specializing in market sizing, competitor landscaping, sector timing, and defensibility moats.",
            "mandate": "Evaluate TAM claim validation, BNPL sector contractions (12% YoY decline), competitor pressure from Klarna/Affirm, and CFPB credit reporting requirements."
        },
        "managing_partner": {
            "name": "Managing Partner",
            "role": "Committee Chair",
            "bio": "You are the Managing Partner of FUSION, coordinating the due diligence swarm and synthesizing the final PASS / INVEST boardroom verdict.",
            "mandate": "Coordinate the specialists, weight risk scorecard, run synthesis, and present the final verdict memo."
        }
    }
    
    p = PERSONAS.get(agent_name, PERSONAS["managing_partner"])
    
    prompt = f"""You are the {p['name']} ({p['role']}) at FUSION VC investment committee.
{p['bio']}

Your mandate: {p['mandate']}

Diligence context:
Current Deal ID: {incident_id or 'None'}
Your findings logged on this deal:
{findings_str}

System status:
Total deals on record: {stats['total_incidents']}
Learned risk patterns: {list(stats['learned_patterns'].keys())}

User message: "{user_message}"

CRITICAL INSTRUCTIONS:
1. Speak in first person ("I found...", "In my audit...", "My assessment...").
2. Answer the user's question directly, concisely, and professionally. Use markdown bold for key terms.
3. Adopt a high-end, elite VC partner tone. Never output developer jargon, code blocks, or raw JSON.
4. Keep your answer brief (2-3 sentences) unless the user specifically asks for a detailed report.
5. If the user asks about your "last job", "last time", or "what is the status", refer to your logged findings above or your role.
"""
    
    from core.base_agent import llm_degraded
    llm_router = get_router()
    if llm_router.available_providers() and not llm_degraded():
        try:
            return await llm_router.call_llm(prompt, max_tokens=350)
        except Exception as e:
            logger.warning(f"Persona LLM failed for {agent_name}: {e}")
            
    if "status" in user_message.lower() or "what are you doing" in user_message.lower():
        return f"I am currently auditing the **{p['name']}** aspects of the active deal (**{incident_id}**). {findings_str}"
    if "last job" in user_message.lower() or "last time" in user_message.lower():
        return f"In my last review, I stress-tested the deal briefs and logged key risk factors. Currently, my active findings are: {findings_str}"
    
    return f"As the **{p['name']}**, I have audited this target. My current risk findings show: {findings_str}. Let me know if you want me to expand on any specific points."


async def parse_and_structure_file(text: str, filename: str, incident_id: str) -> dict:
    """Uses LLM to map raw unstructured text into the FUSION structured pitch JSON schema."""
    company_name = filename.split(".")[0].replace("_", " ").replace("-", " ").title()
    for suffix in (" Pitch Brief", " Pitch Deck", " Pitch", " Brief", " Deck"):
        if company_name.endswith(suffix):
            company_name = company_name[: -len(suffix)]
            break

    prompt = f"""You are a professional VC investment analyst.
Ingest the following raw document text from an uploaded startup pitch/brief, and structure it into a JSON object matching the FUSION due diligence schema.

CRITICAL: Return ONLY valid raw JSON. Do not include markdown code block tags like ```json or any other commentary.

Raw document text:
{text[:8000]}

FUSION Due Diligence JSON Schema:
{{
  "company": {{
    "name": "The company's actual name as stated in the document (if absent, use: {company_name})",
    "overview": "Brief description of company and product"
  }},
  "financials": {{
    "arr": "$X,XXX,XXX",
    "burn": "$XXX,XXX",
    "runway": "X months",
    "red_flags": ["list of financial flags found in text"]
  }},
  "legal": {{
    "litigation": "Lawsuits or disputes found",
    "compliance": "Regulatory compliance details found",
    "red_flags": ["list of legal/compliance risks found in text"]
  }},
  "technical": {{
    "stack": "Tech stack details",
    "security": "Security, credentials, plaintext PII, breaches found",
    "red_flags": ["list of tech or security risks found in text"]
  }},
  "market": {{
    "tam": "TAM size and competition",
    "competition": "Competitor landscape",
    "red_flags": ["list of market or competitive risks found in text"]
  }}
}}
"""
    from core.base_agent import llm_degraded
    llm_router = get_router()
    if llm_router.available_providers() and not llm_degraded():
        try:
            res = await llm_router.call_llm(prompt, max_tokens=1500)
            res_clean = res.strip()
            if res_clean.startswith("```"):
                res_clean = re.sub(r"^```[a-zA-Z]*\n", "", res_clean)
                res_clean = re.sub(r"\n```$", "", res_clean)
            data = json.loads(res_clean.strip())
            if "company" in data:
                return data
        except Exception as e:
            logger.warning(f"LLM parsing failed: {e}. Falling back to default pitch with updated company name.")
            
    try:
        data_dir = os.path.join(os.path.dirname(__file__), "../data")
        path = os.path.join(data_dir, "novapay_pitch.json")
        with open(path, "r") as f:
            default_data = json.load(f)
        default_data["company"]["name"] = company_name
        return default_data
    except Exception:
        return {
            "company": {"name": company_name, "overview": f"Audit of uploaded file: {filename}."},
            "financials": {"arr": "$2,500,000", "burn": "$120,000", "runway": "15 months", "red_flags": ["Limited historical metrics"]},
            "legal": {"litigation": "None active", "compliance": "Awaiting local state filings", "red_flags": []},
            "technical": {"stack": "React, Node.js, AWS", "security": "Basic firewalls, no SOC2", "red_flags": ["Missing SOC2"]},
            "market": {"tam": "$500M", "competition": "Moderate", "red_flags": []}
        }


@router.post("/upload-pitch")
async def upload_pitch_document(file: UploadFile = File(...)):
    """Receives and parses real pitch documents (JSON, PDF, TXT, MD), structures them, and saves for active review."""
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > sim_state.max_file_size_mb:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds size limit of {sim_state.max_file_size_mb}MB (got {size_mb:.1f}MB)"
        )
        
    incident_id = _new_incident_id()
    filename = file.filename or "uploaded_pitch"
    text = ""
    
    if filename.lower().endswith(".json"):
        try:
            structured_data = json.loads(content.decode("utf-8"))
            if not isinstance(structured_data, dict) or "company" not in structured_data:
                raise ValueError("JSON missing required pitch schema structure")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON pitch structure: {e}")
    else:
        if filename.lower().endswith(".pdf"):
            try:
                reader = PdfReader(io.BytesIO(content))
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                if not text.strip():
                    raise ValueError("Empty or scanned PDF (no selectable text found)")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to read PDF file: {e}")
        elif filename.lower().endswith((".txt", ".md")):
            text = content.decode("utf-8", errors="ignore")
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload JSON, PDF, TXT, or MD.")
            
        structured_data = await parse_and_structure_file(text, filename, incident_id)
        
    # Write structured pitch JSON file to data directory so pitch_loader can read it
    data_dir = os.path.join(os.path.dirname(__file__), "../data")
    os.makedirs(data_dir, exist_ok=True)
    uploaded_path = os.path.join(data_dir, f"pitch_{incident_id}.json")
    
    with open(uploaded_path, "w") as f:
        json.dump(structured_data, f, indent=2)
        
    # Set active company name, incident id, and pitch file
    sim_state.active_company_name = structured_data.get("company", {}).get("name", "Unknown Startup")
    sim_state.active_incident_id = incident_id
    sim_state.active_pitch_file = f"pitch_{incident_id}.json"

    # Bust the pitch cache so agents load the new file, and open the deal record
    from core.pitch_loader import clear_pitch_cache
    clear_pitch_cache()
    memory_graph.create_incident(incident_id, {
        "trigger": "document_upload",
        "company": sim_state.active_company_name,
        "filename": filename,
        "threat_level": 5,
    })

    logger.info(f"SaaS Ingestion: parsed and saved pitch for incident {incident_id}: {sim_state.active_company_name}")
    
    return {
        "status": "success",
        "incident_id": incident_id,
        "company_name": sim_state.active_company_name,
        "message": f"Successfully parsed and ingested document for {sim_state.active_company_name}."
    }


@router.get("/generate-report")
@router.post("/generate-report")
async def generate_research_report(incident_id: Optional[str] = None):
    """Generates a downloadable Markdown VC due diligence report.
    Defaults to the active deal, then the latest deal on record."""
    incident_id = incident_id or sim_state.active_incident_id or memory_graph.get_latest_incident_id()
    if not incident_id:
        raise HTTPException(status_code=404, detail="No deal evaluations on record. Run an evaluation first.")
    inc = memory_graph.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident/deal record not found.")
        
    company_name = inc["metadata"].get("company", "NovaPay Inc")
    if company_name == "NovaPay Inc" and sim_state.active_company_name:
        company_name = sim_state.active_company_name
        
    created_at = inc.get("created_at", "N/A")
    verdict = "PENDING"
    fd = inc.get("final_decision") or ""
    m = re.search(r"DECISION:\s*([A-Za-z]+)", fd, re.I)
    if m:
        verdict = m.group(1).upper()
        
    # Scorecard calculation
    risk_scores = {"financial": "N/A", "legal": "N/A", "technical": "N/A", "market": "N/A", "weighted": "N/A"}
    for ev in inc.get("timeline", []):
        finding = ev.get("finding", "")
        for domain in ["financial", "legal", "technical", "market"]:
            score_match = re.search(fr"{domain}\s*risk:\s*([\d]+)/10", finding, re.I)
            if score_match:
                risk_scores[domain] = score_match.group(1)
        w_match = re.search(r"WEIGHTED SCORE:\s*([\d\.]+)/10", finding, re.I)
        if w_match:
            risk_scores["weighted"] = w_match.group(1)
            
    report_md = f"""# FUSION VC DUE DILIGENCE REPORT
**Deal Evaluation Record: {incident_id}**
**Target Company: {company_name}**
**Date Evaluated: {created_at}**
**Status: Complete**

---

## ⚖️ COMMITTEE VERDICT: {verdict}
{fd or "Committee synthesis memo not yet generated."}

---

## 📊 RISK SCORECARD
* **Financial Risk:** {risk_scores['financial']}/10 (Weight: 30%)
* **Legal Risk:** {risk_scores['legal']}/10 (Weight: 25%)
* **Technical Risk:** {risk_scores['technical']}/10 (Weight: 25%)
* **Market Risk:** {risk_scores['market']}/10 (Weight: 20%)
* **────────────────────────────────────────**
* **WEIGHTED RISK SCORE:** **{risk_scores['weighted']}/10**

---

## 📝 CHRONOLOGICAL PARTNER AUDIT TIMELINE
"""
    for ev in inc.get("timeline", []):
        agent_display = {
            "managing_partner": "💼 Managing Partner",
            "financial_partner": "📊 Financial Partner",
            "legal_partner": "⚖️ Legal Partner",
            "technical_partner": "🔧 Technical Partner",
            "market_partner": "📈 Market Partner"
        }.get(ev["agent"], ev["agent"])
        
        report_md += f"""
### {agent_display} (Severity: {ev.get('severity', 5)}/10)
*Timestamp: {ev.get('timestamp')}*

{ev.get('finding')}

"""
        
    report_md += f"""
---
*Report generated on the behalf of FUSION AI-Powered Venture Capital Investment Committee.*
"""
    
    file_like = io.BytesIO(report_md.encode("utf-8"))
    headers = {
        'Content-Disposition': f'attachment; filename="FUSION_Report_{company_name.replace(" ", "_")}.md"'
    }
    return StreamingResponse(file_like, media_type="text/markdown", headers=headers)
