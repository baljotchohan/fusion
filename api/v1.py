# api/v1.py
"""
ARGUS v1 REST API — chat with the Incident Commander, repository scanning,
IoC analysis, and shared-memory incident retrieval.

These are the product-facing endpoints (used by the Web UI, external
clients, and the MCP server in mcp_server.py).
"""
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

logger = logging.getLogger("argus.api.v1")

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


async def _dispatch_incident(incident_id: str, user_message: str):
    """Wake the swarm: route the alert into the Threat Intel Band room."""
    sim_state.running = True
    sim_state.active_incident_id = incident_id
    alert = (
        f"@Threat-Intel USER-REPORTED INCIDENT {incident_id}. "
        f"User report: {user_message}. Analyze and return threat report to incident-command-room."
    )
    if is_mock_mode():
        await mock_bus.send_message("Commander-Chat", "threat-intel-room", alert)
    else:
        import os
        import httpx
        try:
            band_api_key = os.getenv("BAND_API_KEY", "")
            async with httpx.AsyncClient(timeout=15.0) as client:
                await client.post(
                    "https://api.band.ai/v1/rooms/threat-intel-room/messages",
                    headers={"Authorization": f"Bearer {band_api_key}"},
                    json={"content": alert, "sender": "Commander-Chat"},
                )
        except Exception as e:
            logger.error(f"Real Band dispatch failed, falling back to local bus: {e}")
            await mock_bus.send_message("Commander-Chat", "threat-intel-room", alert)


async def _commander_reply(user_message: str, incident_id: str, dispatched: bool) -> str:
    """Synthesize the Commander's plain-English reply.

    Uses a real LLM when keys are configured; otherwise builds a
    deterministic reply from the shared memory graph so offline demos work.
    """
    stats = memory_graph.get_memory_stats()
    latest_id = memory_graph.get_latest_incident_id()
    latest_summary = memory_graph.get_team_summary(latest_id) if latest_id else "No incidents on record yet."

    llm_router = get_router()
    if llm_router.available_providers():
        prompt = (
            "You are the ARGUS Incident Commander talking to a user in plain English.\n"
            f"User message: {user_message}\n\n"
            f"Active incident: {incident_id}\n"
            f"Team was {'just activated on this incident' if dispatched else 'not activated (informational question)'}.\n"
            f"Team memory stats: {json.dumps(stats['learned_patterns'])} learned defenses, "
            f"{stats['total_incidents']} past incidents.\n"
            f"Latest incident summary:\n{latest_summary}\n\n"
            "Reply in 3-6 sentences. Be concrete, calm, and non-technical. "
            "If the team was activated, explain which specialists are working and what happens next."
        )
        try:
            return await llm_router.call_llm(prompt, max_tokens=400)
        except Exception as e:
            logger.warning(f"Commander chat LLM failed, using deterministic reply: {e}")

    if dispatched:
        return (
            f"Understood — I've opened incident {incident_id} and activated the response team. "
            "Threat Intelligence is analyzing your report now; Recon, Detection, Red Team, and "
            "Blue Team will engage automatically as findings come in. If risk crosses the "
            "critical threshold, the executive board convenes for a business decision. "
            "Watch the agent cards for live status."
        )
    return (
        "Here's where we stand. "
        f"The team has handled {stats['total_incidents']} incident(s) and learned "
        f"{len(stats['learned_patterns'])} defense pattern(s) so far.\n\n{latest_summary}"
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_with_commander(msg: ChatMessage):
    """Chat with the Incident Commander. Attack reports recruit the full swarm."""
    incident_id = msg.incident_id or _new_incident_id()
    text = msg.user_message.lower()

    is_attack_report = any(k in text for k in ATTACK_KEYWORDS)
    dispatched = False
    if is_attack_report and not sim_state.running:
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

    commander_response = await _commander_reply(msg.user_message, incident_id, dispatched)
    memory_context = memory_graph.get_team_summary(incident_id)

    return ChatResponse(
        commander_response=commander_response,
        incident_id=incident_id,
        agent_updates=_agent_statuses(),
        memory_context=memory_context,
    )


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
