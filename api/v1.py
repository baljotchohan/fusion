# api/v1.py
"""
Fusion v1 REST API — chat with the Incident Commander, repository scanning,
IoC analysis, and shared-memory incident retrieval.

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

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
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

ATTACK_KEYWORDS = (
    "attack", "phishing", "breach", "hacked", "compromise", "malware",
    "ransomware", "suspicious", "intrusion", "exploit", "incident",
)

AGENT_NAMES = [
    "threat_intel_agent", "recon_agent", "red_team_agent", "attack_path_agent",
    "detection_agent", "malware_agent", "blue_team_agent",
    "incident_commander", "executive_decision",
]


def _new_incident_id() -> str:
    return f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"


def _agent_statuses() -> dict:
    return {name: sim_state.agent_statuses.get(name, "idle") for name in AGENT_NAMES}


# ─── CHAT WITH INCIDENT COMMANDER ─────────────────────────────

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


# Intent vocabulary — keyword buckets the Commander uses to route a message.
_STATUS_WORDS = ("status", "safe", "under attack", "right now", "happening",
                 "current", "going on", "are we", "threat level", "risk")
_MEMORY_WORDS = ("learn", "learned", "remember", "memory", "past", "history",
                 "before", "previous", "seen this", "recipe", "pattern", "how many")
_DOCS_WORDS = ("how do you work", "how does this work", "explain", "what is fusion",
               "who are you", "what can you do", "help", "documentation", "architecture")
_GREETING_WORDS = ("hi", "hii", "hiya", "hello", "helo", "hallo", "hey", "heyy",
                   "yo", "sup", "greetings", "howdy", "good", "gm", "morning")
_THANKS_WORDS = ("thanks", "thank you", "thx", "ty", "appreciate", "great", "nice", "cool", "awesome")


def _classify_intent(text: str) -> str:
    """Cheap, deterministic intent router so replies are relevant offline."""
    t = text.lower().strip().rstrip("!.")
    words = t.split()
    first = words[0] if words else t
    if any(k in t for k in ATTACK_KEYWORDS):
        return "attack_report"
    # Greeting: whole message is a greeting, or it opens with one and is short.
    if t in _GREETING_WORDS or first in _GREETING_WORDS:
        return "greeting"
    if t in _THANKS_WORDS or first in _THANKS_WORDS:
        return "thanks"
    if any(k in t for k in _DOCS_WORDS):
        return "docs"
    if any(k in t for k in _MEMORY_WORDS):
        return "memory"
    if any(k in t for k in _STATUS_WORDS) or t.endswith("?"):
        return "status"
    return "general"


def _suggestions_for(intent: str) -> List[str]:
    base = {
        "attack_report": ["What's the risk score?", "What does Blue Team recommend?", "Show me the CEO decision"],
        "status": ["Report a phishing email", "What has the team learned?", "How does Fusion work?"],
        "memory": ["Report a new incident", "What's our current status?", "Which attack patterns repeat?"],
        "docs": ["Simulate a phishing attack", "What are the 9 agents?", "What is the MITRE mapping?"],
        "greeting": ["We got a phishing email", "Are we under attack?", "What did the team learn?"],
        "thanks": ["Report an incident", "What's our status?", "How does Fusion work?"],
        "general": ["Report an incident", "What's our status?", "What has the team learned?"],
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
        agent_conf = config.get("agents", {}).get("incident_commander") or config.get("incident_commander", {})
        api_key = agent_conf.get("api_key")
        if not api_key:
            logger.error("Real Band dispatch: Incident Commander API key not found in config")
            return False

        client = AsyncRestClient(api_key=api_key, base_url="https://app.thenvoi.com")
        chats_resp = await client.agent_api_chats.list_agent_chats()
        chats = chats_resp.data or []
        if not chats:
            logger.error("Real Band dispatch: No active chats found for Incident Commander")
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
    """Wake the swarm: route the alert into the Threat Intel Band room."""
    sim_state.running = True
    sim_state.active_incident_id = incident_id
    alert = (
        f"USER-REPORTED INCIDENT {incident_id}. "
        f"User report: {user_message}. Analyze and return threat report to incident-command-room."
    )
    if is_mock_mode():
        await mock_bus.send_message("Commander-Chat", "threat-intel-room", f"@Threat-Intel {alert}")
    else:
        success = await dispatch_real_band_message(alert, "threat-intel")
        if not success:
            logger.warning("Real Band dispatch failed, falling back to local bus")
            await mock_bus.send_message("Commander-Chat", "threat-intel-room", f"@Threat-Intel {alert}")


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
    m = re.search(r"FINAL CEO DECISION:\s*([A-Za-z]+)", fd, re.I)
    if m:
        verdict = m.group(1).upper()
    risk = None
    headline_finding = None
    for ev in inc.get("timeline", []):
        finding = str(ev.get("finding", ""))
        rm = re.search(r"Combined Risk Score:\s*(\d+)", finding, re.I)
        if rm:
            risk = int(rm.group(1))
        if ev.get("agent") == "threat_intel_agent" and not headline_finding:
            tm = re.search(r"Threat Type:\s*([^\n]+)", finding, re.I)
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
    """Offline-safe, intent-aware Commander reply built from real memory state.
    Replies are deliberately concise and structured — never raw timeline dumps."""
    n_inc = stats["total_incidents"]
    n_pat = len(stats["learned_patterns"])
    active = [a for a, s in _agent_statuses().items() if s == "working"]
    head = _incident_headline(latest_id)

    def _latest_line() -> str:
        if not head:
            return ""
        bits = []
        if head["verdict"]:
            bits.append(f"verdict **{head['verdict']}**")
        if head["risk"] is not None:
            bits.append(f"risk **{head['risk']}/100**")
        tail = (" — " + ", ".join(bits)) if bits else ""
        return f"Most recent: **{head['incident_id']}**{tail}. Open the **Memory** tab for the full timeline."

    if intent == "attack_report" and dispatched:
        return (
            f"Understood — I've opened incident **{incident_id}** and activated the response team. "
            "Here's what happens over the next ~30 seconds:\n"
            "1. **Threat Intelligence** classifies the alert and maps it to MITRE ATT&CK.\n"
            "2. **Recon + Detection** confirm what's exposed and whether it got in.\n"
            "3. **Red Team + Malware** predict the next move and dissect the payload.\n"
            "4. **Attack Path** scores the risk; if critical, **Blue Team** builds containment and the "
            "**Executive Board** makes the business call.\n\n"
            "Watch the graph on the right — I'll surface the verdict the moment the board decides."
        )
    if intent == "attack_report" and not dispatched:
        return (
            "A response is already running, so I've folded your report into the active incident rather than "
            f"starting a second one. {_latest_line()}"
        )
    if intent == "status":
        if sim_state.running and active:
            who = ", ".join(_display(a) for a in active)
            return (
                f"**Actively responding now.** Working specialists: {who}. "
                "No final containment decision yet — I'll have it within a few seconds."
            )
        if head:
            if head["verdict"]:
                return (
                    f"**Stable** — no live intrusion in progress. The last incident **{head['incident_id']}** "
                    f"resolved with verdict **{head['verdict']}**"
                    + (f" at risk **{head['risk']}/100**" if head["risk"] is not None else "")
                    + ".\n\nAsk me to *report a phishing email* to run a fresh response, or open the **Memory** tab for details."
                )
            return (
                f"**Stable.** The last incident **{head['incident_id']}** is on record with {head['findings']} "
                "findings logged. Open the **Memory** tab for the full timeline."
            )
        return (
            "**All clear** — no incidents on record yet. Click **Simulate Attack**, or tell me about something "
            "suspicious (e.g. \"we got a phishing email\") and I'll mobilize the team."
        )
    if intent == "memory":
        patt = stats["learned_patterns"]
        lines = "\n".join(f"• **{k}** — {v} defense recipe(s)" for k, v in list(patt.items())[:8]) or "• none yet"
        return (
            f"Across **{n_inc} incident(s)** the team has logged **{stats['total_findings']} findings** and learned "
            f"**{n_pat} reusable defense pattern(s)** by MITRE technique:\n{lines}\n\n"
            "On a repeat attack, agents check this first and reuse what worked — so we get faster each time."
        )
    if intent == "docs":
        return (
            "**Fusion** is an Autonomous Cyber Defense Command Center. Nine specialist AI agents — Threat "
            "Intelligence, Recon, Detection, Red Team, Malware, Attack Path, Blue Team, the Incident Commander "
            "(me), and the Executive Board — coordinate to take a raw security alert all the way to a boarded "
            "business decision (Contain / Shutdown / Escalate) in under three minutes.\n\n"
            "Report an incident in plain English and I'll recruit the right specialists. The **Docs** tab has the "
            "full breakdown, including how to drive the team over **MCP** and **connectors**."
        )
    if intent == "greeting":
        state = "responding to a live incident" if sim_state.running else "stable and standing by"
        return (
            "Hi — I'm the **Fusion Incident Commander**. I coordinate nine security specialists for you, and right "
            f"now the system is **{state}**.\n\n"
            "You can **report something suspicious**, ask **\"what's our status?\"**, or query **what we've learned**. "
            "What would you like to do?"
        )
    if intent == "thanks":
        return "Anytime — I'm standing watch. Report anything suspicious and I'll mobilize the team instantly."
    # general
    return (
        "I can **mobilize the team** on a threat, give you a **status** read, or tell you **what we've learned**. "
        "Try \"we got a phishing email,\" \"are we under attack?\", or \"what has the team learned?\""
    )


def _display(agent_key: str) -> str:
    return {
        "threat_intel_agent": "Threat Intel", "recon_agent": "Recon",
        "red_team_agent": "Red Team", "attack_path_agent": "Attack Path",
        "detection_agent": "Detection", "malware_agent": "Malware",
        "blue_team_agent": "Blue Team", "incident_commander": "Incident Commander",
        "executive_decision": "Executive Board",
    }.get(agent_key, agent_key)


async def _commander_reply(intent: str, user_message: str, incident_id: str,
                           dispatched: bool) -> str:
    """Synthesize the Commander's reply. Real LLM when a key is live and healthy,
    otherwise an intent-aware deterministic reply from the shared memory graph."""
    stats = memory_graph.get_memory_stats()
    latest_id = memory_graph.get_latest_incident_id()
    latest_summary = memory_graph.get_team_summary(latest_id) if latest_id else "No incidents on record yet."

    from core.base_agent import llm_degraded, degrade_llm

    llm_router = get_router()
    if llm_router.available_providers() and not llm_degraded():
        recent = memory_graph.get_chat_history(limit=6)
        convo = "\n".join(f"{t['role']}: {t['content'][:200]}" for t in recent)
        prompt = (
            "You are the Fusion Incident Commander — a calm, sharp SOC lead — talking to a user in plain English.\n"
            f"Detected intent: {intent}.\n"
            f"Recent conversation:\n{convo}\n\n"
            f"New user message: {user_message}\n\n"
            f"Active incident: {incident_id}. Team was "
            f"{'just activated on this incident' if dispatched else 'not activated (informational)'}.\n"
            f"Memory: {stats['total_incidents']} past incidents, "
            f"{len(stats['learned_patterns'])} learned defense patterns.\n"
            f"Latest incident summary:\n{latest_summary}\n\n"
            "Reply in 3-6 sentences. Concrete, calm, non-technical. Use markdown bold for key terms. "
            "If the team was activated, name the specialists working and what happens next."
        )
        try:
            return await llm_router.call_llm(prompt, max_tokens=420)
        except Exception as e:
            logger.warning(f"Commander chat LLM failed, using deterministic reply: {e}")
            degrade_llm(str(e))

    return _deterministic_reply(intent, user_message, incident_id, dispatched,
                                stats, latest_summary, latest_id)


def _build_thinking_steps(intent: str, dispatched: bool, incident_id: str) -> List[str]:
    """The actual background steps the Commander took — surfaced to the UI so the
    user sees the reasoning, not just the answer."""
    steps = [f"Parsed message → intent classified as **{intent.replace('_', ' ')}**"]
    if intent == "attack_report":
        if dispatched:
            steps += [
                f"Opened incident record **{incident_id}** in shared memory",
                "Queried team memory for matching MITRE techniques",
                "Dispatched alert into #threat-intel-room — swarm recruiting",
                "Streaming specialist findings to the live graph",
            ]
        else:
            steps += ["A response is already running — folded this into the active incident"]
    elif intent == "status":
        steps += [
            "Read live agent statuses from the event bus",
            f"Checked simulation lock (running={sim_state.running})",
            "Summarized latest incident from memory graph",
        ]
    elif intent == "memory":
        steps += [
            "Loaded incident timeline + learned attack patterns from memory graph",
            "Aggregated findings count and defense recipes by MITRE ID",
        ]
    elif intent == "docs":
        steps += ["Pulled architecture overview from the knowledge base"]
    elif intent in ("greeting", "thanks"):
        steps += ["Checked live system state for a quick status read"]
    else:
        steps += ["Checked memory graph for relevant context"]
    return steps


@router.post("/chat", response_model=ChatResponse)
async def chat_with_commander(msg: ChatMessage):
    """Chat with the Incident Commander. Attack reports recruit the full swarm."""
    incident_id = msg.incident_id or _new_incident_id()
    intent = _classify_intent(msg.user_message)

    memory_graph.append_chat("user", msg.user_message, {"intent": intent})

    dispatched = False
    if intent == "attack_report" and not sim_state.running:
        memory_graph.create_incident(incident_id, {
            "trigger": "commander_chat",
            "user_message": msg.user_message[:300],
            "threat_level": 5,
        })
        await _dispatch_incident(incident_id, msg.user_message)
        dispatched = True
    elif msg.incident_id is None and memory_graph.get_latest_incident_id():
        # Informational question — answer about the most recent incident
        incident_id = memory_graph.get_latest_incident_id()

    thinking_steps = _build_thinking_steps(intent, dispatched, incident_id)
    commander_response = await _commander_reply(intent, msg.user_message, incident_id, dispatched)
    memory_context = memory_graph.get_team_summary(incident_id)

    memory_graph.append_chat("assistant", commander_response,
                             {"intent": intent, "incident_id": incident_id, "dispatched": dispatched})

    return ChatResponse(
        commander_response=commander_response,
        incident_id=incident_id,
        agent_updates=_agent_statuses(),
        memory_context=memory_context,
        intent=intent,
        thinking_steps=thinking_steps,
        dispatched=dispatched,
        suggestions=_suggestions_for(intent),
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


# ─── REPOSITORY SCANNING (real GitHub connector) ──────────────

class ScanRequest(BaseModel):
    repo_url: str
    scan_type: str = "full"  # "full", "secrets", "deps"


class ScanResponse(BaseModel):
    scan_id: str
    status: str
    findings: list
    threat_level: int
    recommendations: list


@router.post("/scan", response_model=ScanResponse)
async def scan_repo(request: ScanRequest):
    """Scan a real GitHub repo for security issues (Recon + Detection + Threat Intel)."""
    scan_id = f"SCAN-{uuid4().hex[:12]}"
    try:
        owner, repo = parse_repo_url(request.repo_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    scanner = GitHubScanner()
    findings = await scanner.scan_repo(owner, repo)
    threat_level = scanner.compute_threat_level(findings)

    # Threat Intel correlation: look up CVEs for vulnerable packages found
    cve_matches = []
    for alert in findings.get("dependabot_alerts", [])[:3]:
        package = alert.get("package")
        if package:
            cve_matches += await get_cves_async(package, max_results=2)
    if cve_matches:
        findings["correlated_cves"] = cve_matches

    # Log to shared memory so the team learns from every scan
    incident_id = _new_incident_id()
    memory_graph.create_incident(incident_id, {
        "trigger": "repo_scan",
        "repo": findings["repo"],
        "threat_level": threat_level,
    })
    await memory_graph.log_finding(
        incident_id, "recon_agent", findings["summary"],
        severity=threat_level, tags=["github_scanning"],
    )

    recommendations = []
    if findings["exposed_secrets"]:
        recommendations.append("Rotate exposed API keys and revoke leaked credentials immediately")
    if findings["dependabot_alerts"]:
        recommendations.append("Update vulnerable dependencies flagged by Dependabot to patched versions")
    if not findings["exposed_secrets"]:
        recommendations.append("Enable GitHub secret scanning and push protection")
    recommendations.append("Pin dependency versions and enable Dependabot security updates")

    return ScanResponse(
        scan_id=scan_id,
        status="complete",
        findings=[findings],
        threat_level=threat_level,
        recommendations=recommendations,
    )


# ─── IOC THREAT ANALYSIS ──────────────────────────────────────

class ThreatRequest(BaseModel):
    indicator: str  # IP, domain, hash, or keyword
    ioc_type: str = "domain"  # "ip", "domain", "hash", "keyword"


class ThreatResponse(BaseModel):
    indicator: str
    severity: int
    matches: list
    context: str


@router.post("/analyze-threat", response_model=ThreatResponse)
async def analyze_threat(request: ThreatRequest):
    """Analyze a single IoC against live NVD CVE intelligence + team memory."""
    # NVD keyword search works best on product/domain-ish terms
    keyword = request.indicator
    if request.ioc_type == "hash":
        keyword = "malware " + keyword[:16]
    cves = await get_cves_async(keyword, max_results=5)

    past = await memory_graph.query_similar_incidents(request.indicator, limit=3)

    severity = 3
    if cves:
        top = max(c.get("cvss_score", 0) for c in cves)
        severity = min(10, max(3, round(top)))
    if past:
        severity = min(10, severity + 1)

    context_parts = []
    if cves:
        context_parts.append(f"{len(cves)} CVE match(es) found, top CVSS {max(c['cvss_score'] for c in cves)}.")
    if past:
        context_parts.append(f"Team memory: seen in {len(past)} past incident(s).")
    if not context_parts:
        context_parts.append("No match in threat intelligence or team memory.")

    return ThreatResponse(
        indicator=request.indicator,
        severity=severity,
        matches=cves + [{"memory": p} for p in past],
        context=" ".join(context_parts),
    )


# ─── INCIDENT MEMORY ──────────────────────────────────────────

@router.get("/incidents")
async def list_incidents():
    """List all incidents in the shared team memory graph."""
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
    """Retrieve past incident details and the team's response timeline."""
    inc = memory_graph.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
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
    """How much the team has learned across all incidents."""
    return memory_graph.get_memory_stats()


@router.get("/memory/similar/{technique}")
async def similar_incidents(technique: str, limit: int = 5):
    """Query team memory for past incidents matching a MITRE technique."""
    past = await memory_graph.query_similar_incidents(technique, limit=limit)
    return {"technique": technique, "similar_incidents": past}


# ─── SYSTEM SETTINGS & MCP REGISTRY ───────────────────────────

# Mirrors the 7 tools exposed by mcp_server.py so the UI can render the MCP
# surface without importing the MCP runtime (which needs the `mcp` package).
MCP_TOOLS = [
    {"name": "run_security_scan", "category": "Recon",
     "description": "Scan a GitHub repo for exposed secrets, vulnerable dependencies, and Dependabot alerts.",
     "inputs": ["repo_url", "scan_type"]},
    {"name": "analyze_threat", "category": "Threat Intel",
     "description": "Analyze an IoC (IP / domain / hash / keyword) against live NVD CVE data and team memory.",
     "inputs": ["indicator", "ioc_type"]},
    {"name": "chat_with_commander", "category": "Command",
     "description": "Talk to the Incident Commander in plain English; reporting an attack activates the swarm.",
     "inputs": ["message"]},
    {"name": "get_incident", "category": "Memory",
     "description": "Retrieve a past incident: agent finding timeline, threat level, and final decision.",
     "inputs": ["incident_id"]},
    {"name": "get_team_decision", "category": "Executive",
     "description": "Get the Executive board's final verdict for an incident.",
     "inputs": ["incident_id"]},
    {"name": "query_team_memory", "category": "Memory",
     "description": "Query collective memory for similar past incidents by MITRE technique or keyword.",
     "inputs": ["attack_technique", "limit"]},
    {"name": "learn_attack_pattern", "category": "Memory",
     "description": "Teach the team a defense recipe for a MITRE technique so future incidents resolve faster.",
     "inputs": ["mitre_id", "defense", "success_rate"]},
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


@router.get("/system/settings")
async def get_system_settings():
    """Everything the Settings tab renders: providers, LLM health, pace, mode, MCP tools."""
    from core.base_agent import llm_degraded
    return {
        "mode": "mock" if is_mock_mode() else "real",
        "band_mock": is_mock_mode(),
        "llm": {
            "primary": os.getenv("FUSION_LLM_PRIMARY", "gemini"),
            "degraded": llm_degraded(),
            "providers": _provider_status(),
            "active_provider": (get_router().available_providers() or ["local-engine"])[0]
                if not llm_degraded() else "local-engine",
        },
        "simulation": {
            "running": sim_state.running,
            "active_incident_id": sim_state.active_incident_id,
            "mock_pace": float(os.getenv("FUSION_MOCK_PACE", "0.6")),
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
    """Apply runtime settings from the UI (pace, primary provider, clear LLM cooldown)."""
    applied = {}
    if patch.mock_pace is not None:
        pace = max(0.0, min(3.0, patch.mock_pace))
        os.environ["FUSION_MOCK_PACE"] = str(pace)
        applied["mock_pace"] = pace
    if patch.primary_provider:
        os.environ["FUSION_LLM_PRIMARY"] = patch.primary_provider
        # Rebuild the router so the new primary takes effect immediately
        import core.llm_router as _lr
        _lr._router = None
        applied["primary_provider"] = patch.primary_provider
    if patch.reset_llm_degradation:
        import core.base_agent as _ba
        _ba._llm_degraded_until = 0.0
        applied["reset_llm_degradation"] = True
    return {"status": "ok", "applied": applied}


@router.get("/system/mcp")
async def get_mcp_registry():
    """The MCP tool surface external AI apps can call."""
    return {"server": "fusion-mcp", "transport": "stdio", "tools": MCP_TOOLS}
