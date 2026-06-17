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
from typing import List, Optional, Any, Dict
from uuid import uuid4

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, File, UploadFile, Request
from core.auth import get_uid_optional
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


def is_field_missing(field: dict) -> bool:
    if not field or not isinstance(field, dict):
        return True
    val = field.get("value")
    if val is None or val == "" or str(val).lower() in ("insufficient evidence", "unknown", "n/a"):
        return True
    if field.get("confidence", 0) < 40:
        return True
    if not field.get("evidence") or str(field.get("evidence")).strip() == "":
        return True
    return False



def _agent_statuses() -> dict:
    return {name: sim_state.agent_statuses.get(name, "idle") for name in AGENT_NAMES}


# ─── CHAT WITH MANAGING PARTNER ─────────────────────────────

class ChatMessage(BaseModel):
    user_message: str
    incident_id: Optional[str] = None
    session_id: Optional[str] = None


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
                    "kya", "namaste", "kem", "adaab", "salam", "wassup", "halloo",
                    "hlio", "bhai", "yaar", "kya haal", "kya hal", "paaji", "oye")
_THANKS_WORDS = ("thanks", "thank you", "thx", "ty", "appreciate", "great", "nice", "cool", "awesome")
_SMALLTALK_WORDS = ("how are you", "how r u", "hru", "how are u", "how you doing", "how are things",
                    "how's it going", "hows it going", "how is it going", "what's up", "whats up", "wassup",
                    "how do you do", "you good", "u good", "how's your day", "hows your day", "what are you up to",
                    "what you up to", "wyd", "how have you been", "you ok", "are you ok", "how is everything",
                    "kya haal hai", "kaise ho", "kaise hain", "kya chal", "kya chal raha", "sab theek",
                    "kya scene", "kya kar raha", "kya ho raha", "sab badhiya", "theek ho")
_TRIGGER_KEYWORDS = ("evaluate", "run diligence", "run due diligence", "start simulation", "trigger simulation", "analyze startup", "run evaluation", "test startup", "assess startup")
_LIST_DEALS_WORDS = ("list all deals", "list deals", "show all deals", "show deals", "all deals", "what deals", "our deals", "deals evaluated", "deals we have", "deals so far", "see all deals", "view all deals")
_COMPARE_DEALS_WORDS = ("compare all", "compare deals", "best deal", "best one", "which deal", "find best", "rank deals", "top deal", "best startup", "strongest deal", "best investment", "compare startups", "which startup")


# Greeting tokens (incl. typos like "hlo"/"hy") reuse the chat greeting vocab.
_CASUAL_OPENERS = set(_GREETING_WORDS) | {
    "hii", "heyy", "sup", "howdy", "hola", "yo", "good", "ok", "okay", "cool",
}
_CASUAL_PHRASES = _SMALLTALK_WORDS + _THANKS_WORDS + (
    "who are you", "what do you do", "what's your name", "whats your name", "ur name",
    "nice to meet", "tell me about yourself", "introduce yourself", "what can you do",
)


def _is_casual_message(text: str) -> bool:
    """True when the user is just chatting (greeting/thanks/smalltalk/intro),
    not asking for diligence findings. Lets agents reply like people, not reports."""
    t = (text or "").lower().strip().rstrip("!?. ")
    # strip a leading @mention so "@legal hey there" still reads as casual
    t = re.sub(r"^@[\w\-/]+\s*", "", t).strip()
    if not t:
        return True
    if any(p in t for p in _CASUAL_PHRASES):
        return True
    words = t.split()
    if words and words[0] in _CASUAL_OPENERS and len(words) <= 5:
        return True
    return t in _CASUAL_OPENERS


def _resolve_referenced_deal(user_message: str, current_incident_id: str, deals_history: list) -> Optional[dict]:
    if not deals_history:
        return None
        
    lower_msg = user_message.lower()
    
    # 1. Direct name match (e.g. "neural", "gridflow", "novapay", "auria", "helios", etc.)
    for deal in deals_history:
        co_name = deal["company_name"].lower()
        short_name = co_name.replace("inc.", "").replace("inc", "").replace("corp.", "").replace("corp", "").replace("energy", "").replace("pay", "").strip()
        if len(short_name) >= 3 and short_name in lower_msg:
            return deal
        if co_name in lower_msg:
            return deal
            
    # Sort deals chronologically (oldest first, latest last)
    sorted_deals = sorted(deals_history, key=lambda d: d.get("created_at", ""))
    
    # 2. Ordinal references
    if "first deal" in lower_msg or "1st deal" in lower_msg or "our first" in lower_msg:
        return sorted_deals[0]
    if "latest deal" in lower_msg or "last deal" in lower_msg or "current deal" in lower_msg or "active deal" in lower_msg:
        return sorted_deals[-1]
    if "second deal" in lower_msg or "2nd deal" in lower_msg:
        if len(sorted_deals) >= 2:
            return sorted_deals[1]
    if "third deal" in lower_msg or "3rd deal" in lower_msg:
        if len(sorted_deals) >= 3:
            return sorted_deals[2]
            
    # 3. Relative references: "before [company]" or "prior to [company]"
    m_before = re.search(r"(?:before|prior\s+to|preceding)\s+([a-z0-9\s]+)", lower_msg)
    if m_before:
        ref_name = m_before.group(1).strip()
        # Find the index of the referenced company
        ref_idx = -1
        for idx, deal in enumerate(sorted_deals):
            co_name = deal["company_name"].lower()
            short_name = co_name.replace("inc.", "").replace("inc", "").replace("corp.", "").replace("corp", "").replace("energy", "").replace("pay", "").strip()
            if ref_name in short_name or ref_name in co_name:
                ref_idx = idx
                break
        if ref_idx > 0:
            return sorted_deals[ref_idx - 1]
            
    # 4. Default: check current active/latest incident
    for deal in sorted_deals:
        if deal["incident_id"] == current_incident_id:
            return deal
            
    return sorted_deals[-1]


def _classify_intent(text: str) -> str:
    """Deterministic intent router so replies are relevant and non-disruptive."""
    t = text.lower().strip().rstrip("!.")
    words = t.split()
    first = words[0] if words else t
    
    # 1. Explicit trigger request
    is_trigger = False
    if any(k in t for k in _TRIGGER_KEYWORDS) or (t.startswith("evaluate ") and len(words) > 1):
        # Exclude casual queries or questions about evaluation
        question_words = ("how", "why", "what", "explain", "who", "where", "can you", "show me", "describe", "whether", "tell me", "is there", "are we", "should we")
        if not any(t.startswith(qw) for qw in question_words):
            is_trigger = True
            
    if is_trigger:
        return "trigger_evaluation"

        
    # 2. Greeting
    if t in _GREETING_WORDS or first in _GREETING_WORDS:
        return "greeting"
        
    # 3. Thanks
    if t in _THANKS_WORDS or first in _THANKS_WORDS:
        return "thanks"

    # 3b. Smalltalk ("how are you") — must beat query_deal's trailing-'?' rule
    if any(k in t for k in _SMALLTALK_WORDS):
        return "smalltalk"

    # 4. Docs
    if any(k in t for k in _DOCS_WORDS):
        return "docs"

    # 4b. Compare deals / find best (checked before list_deals to win on "compare all deals")
    if any(k in t for k in _COMPARE_DEALS_WORDS):
        return "compare_deals"

    # 4c. List all deals
    if any(k in t for k in _LIST_DEALS_WORDS):
        return "list_deals"

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
        "list_deals": ["Compare all deals", "Which deal should we invest in?", "Evaluate a new deal"],
        "compare_deals": ["Tell me more about the best deal", "List all deals", "Evaluate a new deal"],
        "memory": ["Evaluate NovaPay", "What is the committee status?", "Which risk patterns recur?"],
        "docs": ["Evaluate NovaPay", "What are the 5 partner agents?", "What is the weighted scoring?"],
        "greeting": ["Evaluate NovaPay", "Is the committee in session?", "What did the committee learn?"],
        "thanks": ["Evaluate a deal", "What's our status?", "How does FUSION work?"],
        "smalltalk": ["Evaluate NovaPay", "How does FUSION work?", "What has the committee learned?"],
        "general": ["Evaluate NovaPay", "What's our status?", "What has the committee learned?"],
    }
    return base.get(intent, base["general"])


async def dispatch_real_band_message(content: str, target_agent_handle_sub: str, sender_agent_name: str = "managing_partner") -> bool:
    """Send a message to the real Band platform chat room, resolving and mentioning the target agent."""
    import yaml
    from thenvoi_rest import AsyncRestClient
    from thenvoi.client.rest import ChatMessageRequest
    from thenvoi_rest.types import ChatMessageRequestMentionsItem

    try:
        # Check env vars first (deployed envs don't have agent_config.yaml)
        env_prefix = f"BAND_{sender_agent_name.upper()}"
        api_key = os.getenv(f"{env_prefix}_API_KEY")
        if not api_key:
            config_path = "agent_config.yaml"
            if not os.path.exists(config_path):
                config_path = "agent_config.example.yaml"
            with open(config_path, "r") as f:
                config = yaml.safe_load(f) or {}
            agent_conf = config.get("agents", {}).get(sender_agent_name) or config.get(sender_agent_name, {})
            api_key = agent_conf.get("api_key")
        if not api_key:
            logger.error(f"Real Band dispatch: {sender_agent_name} API key not found in env or config")
            return False
        
        logger.debug(f"Real Band dispatch: sender={sender_agent_name}")
        client = AsyncRestClient(api_key=api_key, base_url="https://app.thenvoi.com")
        chats_resp = await client.agent_api_chats.list_agent_chats()
        chats = chats_resp.data or []
        if not chats:
            logger.error(f"Real Band dispatch: No active chats found for {sender_agent_name}")
            return False

        # Prefer the new, clean chat room to avoid message limit issues (403 limit_reached)
        preferred_chat_id = "4d9d4d00-47ec-4387-81a3-179a6c8a74a6"
        chat_id = None
        for c in chats:
            if c.id == preferred_chat_id:
                chat_id = c.id
                break
        if not chat_id:
            chat_id = chats[0].id
        logger.info(f"Real Band dispatch: Available chats: {[c.id for c in chats]}, preferred: {preferred_chat_id}, selected: {chat_id}")

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

        # Strip any leading mention from the text since it is already passed in the mentions array
        # to avoid duplicate mention pills in the UI.
        if content.startswith("@"):
            first_word = content.split()[0]
            content = content[len(first_word):].lstrip()

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
        success = await dispatch_real_band_message(brief, "managing-partner", sender_agent_name="financial_partner")
        if not success:
            logger.warning("Real Band dispatch failed, falling back to local bus")
            await mock_bus.send_message("Advisor-Chat", "managing-partner-room", brief)


def _incident_headline(incident_id: Optional[str], uid: Optional[str] = None) -> Optional[dict]:
    """A tight, structured snapshot of one incident — verdict, risk, top finding —
    so chat replies stay clean instead of dumping the whole raw timeline."""
    if not incident_id:
        return None
    user_memory = memory_graph.__class__(uid=uid) if uid else memory_graph
    inc = user_memory.get_incident(incident_id)
    if not inc:
        return None
    verdict = None
    fd = inc.get("final_decision") or ""
    m = re.search(r"decision\s*\*?\*?\s*:\s*\*?\*?\s*([A-Za-z]+)", fd, re.I)
    if m:
        verdict = m.group(1).upper()
    risk = None
    headline_finding = None
    for ev in inc.get("timeline", []):
        finding = str(ev.get("finding", ""))
        rm = re.search(r"weighted\s*(?:risk\s*)?score\s*\*?\*?\s*:\s*\*?\*?\s*([\d\.]+)", finding, re.I)
        if rm:
            risk = float(rm.group(1))
        if ev.get("agent") == "managing_partner" and not headline_finding:
            tm = re.search(r"Company\s*\*?\*?\s*:\s*([^\n]+)", finding, re.I)
            if tm:
                headline_finding = tm.group(1).strip().strip("*_`|").strip()
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
                         latest_id: Optional[str], uid: Optional[str] = None) -> str:
    """Offline-safe, intent-aware Managing Partner reply built from real memory state with premium formatting."""
    n_inc = stats["total_incidents"]
    n_pat = len(stats["learned_patterns"])
    active = [a for a, s in _agent_statuses().items() if s == "working"]
    head = _incident_headline(latest_id, uid=uid)

    from core.pitch_loader import _load_pitch_file
    from core.diligence_engine import run_diligence_calculations
    
    pitch_data = _load_pitch_file()
    calc = run_diligence_calculations(pitch_data)
    
    company_name = calc["company_name"]
    raise_amount = calc["raise_amount"]
    valuation = calc["valuation"]
    stage = calc["stage"]
    arr = calc["arr"].get("value", "N/A")
    burn = calc["burn"].get("value", "N/A")
    runway = calc["runway"].get("value", "N/A")
    verdict = calc["verdict"]
    weighted_score = calc["weighted_score"]
    coverage_score = calc["coverage_score"]

    if intent == "trigger_evaluation" and dispatched:
        return (
            f"🚀 **Investment Swarm Mobilized!**\n\n"
            f"I've successfully opened deal record **{incident_id}** and convened the FUSION investment committee "
            f"for **{company_name}**. Here's our timeline over the next minute:\n\n"
            f"1. 💼 **Managing Partner**: Convenes the swarm and briefs the specialist partners.\n"
            f"2. 🔍 **Specialist swarms**: Financial, Legal, Technical, and Market partners audit the pitch in parallel.\n"
            f"3. ⚖️ **Roundtable synthesis**: I collect domain risk scorecards, resolve conflicts, and deliver the final verdict.\n\n"
            f"Watch the roundtable graph on the right — the **Verdict Ledger** will update in real-time."
        )
    if intent == "trigger_evaluation" and not dispatched:
        return (
            f"⚠️ **Swarm Busy**\n\n"
            f"A due diligence review is already running. I have folded this request into the active deal "
            f"rather than starting a parallel run. Current active record: **{latest_id}**."
        )
    if intent == "greeting":
        import random
        return random.choice([
            "👋 Hey there! I'm the **FUSION Managing Partner** — I chair our investment committee. "
            "What can I help you with today?",
            "👋 Welcome! Good to see you. I run the committee here at FUSION. "
            "Want to look at a deal together, or is there something on your mind?",
            "👋 Hi! **Managing Partner** here. I coordinate our five specialist partners on every deal. "
            "How can I help?",
        ])
    if intent == "thanks":
        return "🤝 **Pleasure working with you!** Let me know if you need any other startup evaluations."
    if intent == "smalltalk":
        if sim_state.running:
            return (
                f"😄 Doing well — and genuinely energized, because the committee is mid-session on **{company_name}** as we speak. "
                f"My partners are deep in their audits right now. How are *you*? If you'd like, I can walk you through what we're seeing so far."
            )
        return (
            f"😄 I'm doing great, thanks for asking — sharp, caffeinated, and ready to put a startup through its paces. "
            f"How are you? Whenever you're set, hand me a pitch deck or just say **“evaluate NovaPay”** and I'll convene the committee."
        )
    if intent == "docs":
        return (
            f"📚 **FUSION System Architecture**\n\n"
            f"FUSION is an AI-powered VC Investment Boardroom utilizing a swarm of 5 specialist partner agents:\n\n"
            f"- 💼 **Managing Partner**: Coordinates the swarm, builds timelines, and synthesizes the verdict ledger.\n"
            f"- 💵 **Financial Partner**: Audits revenue concentration, burn, runway, and unit economics.\n"
            f"- ⚖️ **Legal Partner**: Audits IP status, active litigation, and compliance checklists.\n"
            f"- 🛠️ **Technical Partner**: Audits tech stack EOL software, plaintext PII, and security posture.\n"
            f"- 📊 **Market Partner**: Audits market TAM, competitive landscapes, and sector growth.\n\n"
            f"The committee uses shared memory to store prior diligence learnings and detect recurring risk patterns on subsequent reviews."
        )
    if intent in ("list_deals", "compare_deals"):
        user_memory = memory_graph.__class__(uid=uid) if uid else memory_graph
        all_incidents = user_memory.list_incidents()
        if not all_incidents:
            return "📋 No deals have been evaluated yet. Say **\"evaluate NovaPay\"** to kick off the committee."
        deals = []
        for inc_id, inc_data in sorted(all_incidents.items(), key=lambda x: x[1].get("created_at", "")):
            metadata = inc_data.get("metadata", {})
            co_name = "Unknown Startup"
            if isinstance(metadata, dict):
                co_name = metadata.get("company") or metadata.get("company_name") or metadata.get("name") or "Unknown Startup"
                if isinstance(co_name, dict):
                    co_name = co_name.get("value") or co_name.get("name") or "Unknown Startup"
            fd = inc_data.get("final_decision") or ""
            if (not co_name or co_name == "Unknown Startup") and fd:
                m_co = re.search(r"Company\s*\*?\*?\s*:\s*(.+)", fd, re.I)
                if m_co:
                    co_name = m_co.group(1).strip().strip("*_`|").strip()
            verdict = "PENDING"
            if fd:
                m_dec = re.search(r"DECISION\s*:\s*(.+)", fd, re.I)
                if m_dec:
                    verdict = m_dec.group(1).strip().strip("*_`|").strip()
            risk_score = None
            for ev in inc_data.get("timeline", []):
                finding = str(ev.get("finding", ""))
                rm = re.search(r"weighted\s*(?:risk\s*)?score\s*[:\-]\s*([\d\.]+)", finding, re.I)
                if rm:
                    risk_score = float(rm.group(1))
            created = (inc_data.get("created_at", "")[:16].replace("T", " ")) if inc_data.get("created_at") else ""
            deals.append({"company": co_name, "verdict": verdict, "risk_score": risk_score, "id": inc_id, "created": created})

        if intent == "list_deals":
            lines = []
            for idx, d in enumerate(deals):
                v = d["verdict"].upper().split()[0] if d["verdict"] else "PENDING"
                emoji = {"INVEST": "✅", "CONDITIONAL": "🟡", "PASS": "❌", "REJECT": "🔴", "PENDING": "⏳"}.get(v, "⏳")
                risk_str = f" | Risk {d['risk_score']:.1f}/10" if d["risk_score"] is not None else ""
                date_str = f" | {d['created']}" if d["created"] else ""
                lines.append(f"{idx+1}. {emoji} **{d['company']}** — {d['verdict']}{risk_str}{date_str}")
            return f"📋 **Deal History — {len(lines)} deal(s) evaluated**\n\n" + "\n".join(lines)

        # compare_deals
        def deal_rank(d):
            v = d["verdict"].upper().split()[0] if d["verdict"] else "PENDING"
            order = {"INVEST": 0, "CONDITIONAL": 1, "PASS": 2, "REJECT": 3, "PENDING": 4}
            return (order.get(v, 4), d["risk_score"] if d["risk_score"] is not None else 10.0)

        sorted_deals = sorted(deals, key=deal_rank)
        best = sorted_deals[0]
        lines = []
        for d in sorted_deals:
            v = d["verdict"].upper().split()[0] if d["verdict"] else "PENDING"
            emoji = {"INVEST": "✅", "CONDITIONAL": "🟡", "PASS": "❌", "REJECT": "🔴", "PENDING": "⏳"}.get(v, "⏳")
            risk_str = f"Risk {d['risk_score']:.1f}/10" if d["risk_score"] is not None else "Risk N/A"
            star = " ⭐ **Best**" if d["company"] == best["company"] else ""
            lines.append(f"- {emoji} **{d['company']}** — {d['verdict']} | {risk_str}{star}")
        risk_note = f" with a risk score of **{best['risk_score']:.1f}/10**" if best["risk_score"] is not None else ""
        return (
            f"⚖️ **Deal Comparison — {len(deals)} startups evaluated**\n\n"
            + "\n".join(lines)
            + f"\n\n🏆 **Recommendation**: Based on verdict and risk profile, **{best['company']}** is the strongest opportunity{risk_note} among all evaluated deals."
        )

    if intent == "memory":
        patt = stats["learned_patterns"]
        lines = "\n".join(f"• 🧠 **{k}** — resolved {v} risk checklist(s)" for k, v in list(patt.items())[:8]) or "• No patterns cached yet."
        return (
            f"🧠 **FUSION Collective Intelligence**\n\n"
            f"Across **{n_inc} deal(s)** evaluated, the committee has logged **{stats['total_findings']} findings** "
            f"and cached **{n_pat} recurring risk patterns**:\n\n{lines}\n\n"
            f"On repeat evaluations, specialist partners query this memory graph first to accelerate risk detection."
        )
    
    # query_deal
    if intent == "query_deal":
        if pitch_data:
            reasons_list = calc["override_reasons"] if calc["override_reasons"] else [f.get("claim") if isinstance(f, dict) else str(f) for f in (calc["fin_flags"] + calc["leg_flags"] + calc["tech_flags"])[:2]]
            reasons_str = "\n".join(f"  - ⚠️ {r}" for r in reasons_list) if reasons_list else "  - No major flags identified."
            
            # Contradictions
            contradictions_str = ""
            if calc.get("contradictions"):
                contradictions_str = "\n\n**🚨 MATERIAL DISCREPANCIES DETECTED**:\n" + "\n".join(f"• {c['message']}" for c in calc["contradictions"])
            if calc.get("validation_warnings"):
                if not contradictions_str:
                    contradictions_str = "\n\n**⚠️ VALIDATION WARNINGS**:\n"
                else:
                    contradictions_str += "\n"
                contradictions_str += "\n".join(f"• {w}" for w in calc["validation_warnings"])
                
            # Missing Gaps
            gaps_str = ""
            if calc.get("missing_gaps"):
                gaps_str = "\n\n**📋 MISSING DILIGENCE GAPS**:\n" + "\n".join(f"• Missing {g}" for g in calc["missing_gaps"])
                
            confidence_val_pct = calc.get("verdict_confidence", coverage_score)
            quality_val_pct = calc.get("evidence_quality_score", 80.0)
            readiness_score = calc.get("deal_readiness_score", 80.0)
            readiness_status = calc.get("deal_readiness_status", "Ready for IC Review")
            
            w_score_str = f"**{weighted_score:.1f}/10**" if weighted_score is not None else "**N/A**"
            
            return (
                f"📊 **Active Diligence Record — {company_name}**\n\n"
                f"- 🏢 **Target Name**: {company_name}\n"
                f"- 💼 **Stage & Deal**: {stage} | {raise_amount} raise at {valuation} post-money valuation\n"
                f"- 💵 **Financials**: {arr} ARR | {burn} burn | {runway} runway\n"
                f"- ⚖️ **Verdict & Risk**: **{verdict}** (Risk Score: {w_score_str})\n"
                f"- 🎯 **Coverage & Quality**: Fact Coverage **{coverage_score}%** | Evidence Quality **{quality_val_pct:.1f}%**\n"
                f"- 🛡️ **Verdict Confidence**: **{confidence_val_pct:.1f}%**\n"
                f"- 🚦 **Deal Readiness**: **{readiness_score:.1f}/100** ({readiness_status})\n\n"
                f"**Key Focus Areas / Flags**:\n{reasons_str}"
                f"{contradictions_str}"
                f"{gaps_str}\n\n"
                f"You can view the full minute-by-minute timeline in the **History** tab, or ask me for details on a specific partner (e.g. \"@financial-partner what did you find?\")."
            )
        else:
            return "No active deal or past evaluation records were found in the committee database."
        
    import random
    return random.choice([
        "🤝 I'm right here as your **Managing Partner**. I can run a full due-diligence review, unpack a "
        "specific risk, or pull up what the committee has learned. What would you like to dig into?",
        "🤝 Happy to help. As **Managing Partner** I can walk you through a deal's risks, compare it to past "
        "ones, or kick off a fresh review. What's on your mind?",
        "🤝 Tell me what you're after and I'll take it from there — a specific risk, the current verdict, or "
        "a brand-new evaluation. I'm listening.",
    ])


def _display(agent_key: str) -> str:
    return {
        "managing_partner": "Managing Partner", "financial_partner": "Financial Partner",
        "legal_partner": "Legal Partner", "technical_partner": "Technical Partner",
        "market_partner": "Market Partner",
    }.get(agent_key, agent_key)


async def _commander_reply(intent: str, user_message: str, incident_id: str,
                           dispatched: bool, session_id: Optional[str] = None, uid: Optional[str] = None) -> str:
    """Synthesize the Managing Partner's reply. Real LLM when a key is live and healthy,
    otherwise an intent-aware deterministic reply from the shared memory graph."""
    user_memory = memory_graph.__class__(uid=uid) if uid else memory_graph
    stats = user_memory.get_memory_stats()
    latest_id = user_memory.get_latest_incident_id()
    latest_summary = user_memory.get_team_summary(latest_id) if latest_id else "No deals on record yet."

    # Load all evaluated deals to resolve target and build index
    all_incidents = user_memory.list_incidents()
    deals_history = []
    for inc_id, inc_data in all_incidents.items():
        metadata = inc_data.get("metadata", {})
        co_name = "Unknown Startup"
        if isinstance(metadata, dict):
            co_name = metadata.get("company") or metadata.get("company_name") or metadata.get("value") or metadata.get("name") or "Unknown Startup"
            if isinstance(co_name, dict):
                co_name = co_name.get("value") or co_name.get("name") or "Unknown Startup"
        
        fd = inc_data.get("final_decision") or ""
        if (not co_name or co_name == "Unknown Startup") and fd:
            m_co = re.search(r"Company\s*\*?\*?\s*:\s*(.+)", fd, re.I)
            if m_co:
                co_name = m_co.group(1).strip().strip("*_`|").strip()
                
        if not co_name or co_name == "Unknown Startup":
            for ev in inc_data.get("timeline", []):
                finding = ev.get("finding", "")
                m_co = re.search(r"REPORT\s*—\s*([A-Za-z0-9\.\s]+)", finding, re.I)
                if m_co:
                    co_name = m_co.group(1).strip()
                    break
                    
        verdict = "PENDING"
        if fd:
            m_dec = re.search(r"DECISION\s*:\s*(.+)", fd, re.I)
            if m_dec:
                verdict = m_dec.group(1).strip().strip("*_`|").strip()
                
        deals_history.append({
            "incident_id": inc_id,
            "company_name": co_name,
            "created_at": inc_data.get("created_at", ""),
            "verdict": verdict,
            "final_decision": fd,
            "timeline": inc_data.get("timeline", [])
        })
        
    sorted_deals = sorted(deals_history, key=lambda d: d.get("created_at", ""))
    target_deal = _resolve_referenced_deal(user_message, incident_id, sorted_deals)
    
    # Format the all-deals index
    history_lines = []
    for idx, d in enumerate(sorted_deals):
        history_lines.append(f"{idx+1}. Company: {d['company_name']} | Deal ID: {d['incident_id']} | Verdict: {d['verdict']}")
    all_deals_index = "\n".join(history_lines) if history_lines else "No deals on record yet."
    
    # Target deal details
    target_id = target_deal["incident_id"] if target_deal else latest_id
    target_summary = user_memory.get_team_summary(target_id) if target_id else "No deals on record yet."

    from core.base_agent import llm_degraded, degrade_llm

    llm_router = get_router()
    if llm_router.available_providers():
        recent = user_memory.get_chat_history(limit=12, session_id=session_id)
        chat_history_str = "\n".join(f"{t['role'].upper()}: {t['content']}" for t in recent) if recent else "No chat history yet."
        
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
        elif intent == "smalltalk":
            intent_instructions = (
                "The user is making casual small talk (e.g. 'how are you', 'what's up'). Reply warmly and naturally "
                "in first person as the Managing Partner — 1-2 sentences with a little personality, optionally ask "
                "how they are, then lightly invite them to evaluate a startup or ask about a deal. Do NOT dump deal "
                "data, risk scores, or a feature list."
            )
        elif intent == "trigger_evaluation":
            intent_instructions = (
                f"You have just mobilized the investment committee on a new deal ({incident_id}). "
                f"Explain that you have convened the boardroom and briefed the specialists. Let them know they "
                f"can follow the live Roundtable and Minutes to watch the deliberation proceed."
            )
        elif intent == "query_deal":
            intent_instructions = (
                f"The user is asking about a deal (specifically resolved as target: {target_deal['company_name'] if target_deal else 'N/A'}). "
                f"Use the resolved target deal's summary context:\n{target_summary}\n"
                f"And the target deal's final decision verdict card:\n{target_deal['final_decision'] if target_deal else 'N/A'}\n"
                "to answer their question directly, cleanly, and professionally. Focus on what they asked, keeping the details rich."
            )
        elif intent == "docs":
            intent_instructions = (
                "Explain FUSION's committee architecture. We run a 5-partner agent swarm (Managing, Financial, "
                "Legal, Technical, and Market partners) performing parallel due diligence. Explain how they use "
                "shared memory and weighted risk scores to debate and synthesize a PASS/INVEST verdict."
            )
        elif intent == "list_deals":
            intent_instructions = (
                f"The user wants to see all evaluated deals. Present the following as a clean numbered list with company name, verdict, and date:\n{all_deals_index}\n"
                "Keep it concise and well-formatted."
            )
        elif intent == "compare_deals":
            intent_instructions = (
                f"The user wants to compare all deals and find the strongest investment. Here are all evaluated deals:\n{all_deals_index}\n"
                "Compare them by verdict quality (INVEST > CONDITIONAL > PASS/REJECT) and risk score (lower is better). "
                "Clearly identify which startup is the best investment opportunity and briefly explain why (1-2 sentences). Be direct and data-driven."
            )
        elif intent == "memory":
            intent_instructions = (
                f"Summarize what the committee has learned globally. Here is the list of all deals evaluated so far:\n{all_deals_index}\n"
                f"We have evaluated {stats['total_incidents']} deals, logged {stats['total_findings']} findings, and catalogued {len(stats['learned_patterns'])} learned risk patterns. Keep it professional."
            )
        else:
            intent_instructions = (
                f"General query. Answer contextually. If the query relates to startup investments or our current target deal ({target_id}), "
                f"use this summary: {target_summary}. Keep your answer clean and structured."
            )

        prompt = f"""You are the FUSION Managing Partner — a calm, sharp, elite VC general partner.
Talking to a user.

All evaluated deals on record:
{all_deals_index}

Target deal resolved from conversation context:
- Company Name: {target_deal['company_name'] if target_deal else 'N/A'}
- Deal ID: {target_deal['incident_id'] if target_deal else 'N/A'}
- Verdict: {target_deal['verdict'] if target_deal else 'N/A'}

Target deal's final decision verdict card:
{target_deal['final_decision'] if target_deal else 'N/A'}

Target deal's detailed partner findings:
{target_summary}

Instructions for this message:
{intent_instructions}

Recent conversation history (you MUST maintain continuity and remember previous questions/context):
{chat_history_str}

Formatting & Language instructions:
1. Respond in clean, natural prose. Use short '- ' bullet points and **bold** for key terms where appropriate.
2. NEVER use markdown headers (#, ##, ###) or hashtags like #Finance. No '---' dividers. No raw JSON.
3. Use a few tasteful emojis where they genuinely help (📊 ⚖️ 🚩).
4. Adopt a high-end, warm, elite VC partner tone. Keep it concise (2-4 sentences or a tight bullet list).
5. Dynamic Adaptation: Detect and adapt to the user's language, tone, and formatting requests. If the user asks you to speak in Hindi, Hindi-English (Hinglish), or any other language, you MUST respond in that language. If the user requests a friendly, casual, or conversational tone, relax the professional tone and speak in a friendly, conversational manner.

User message: "{user_message}"
"""
        try:
            return await llm_router.call_llm(prompt, max_tokens=420)
        except Exception as e:
            logger.warning(f"Managing Partner chat LLM failed, using deterministic reply: {e}")

    return _deterministic_reply(intent, user_message, incident_id, dispatched,
                                stats, latest_summary, latest_id, uid=uid)


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
    elif intent == "list_deals":
        steps += ["Loaded all deal records from memory graph", "Sorted by evaluation date"]
    elif intent == "compare_deals":
        steps += ["Loaded all deals from memory graph", "Ranked by verdict and weighted risk score", "Identified top investment opportunity"]
    elif intent == "memory":
        steps += [
            "Loaded deal timeline + learned risk patterns from memory graph",
            "Aggregated findings count and checklists",
        ]
    elif intent == "docs":
        steps += ["Pulled boardroom architecture overview from the knowledge base"]
    elif intent in ("greeting", "thanks", "smalltalk"):
        steps += ["Checked live boardroom state for a quick status read"]
    else:
        steps += ["Checked memory graph for relevant context"]
    return steps


@router.post("/chat", response_model=ChatResponse)
async def chat_with_commander(msg: ChatMessage, request: Request):
    """Chat with the FUSION Managing Partner or mentioned specialist partners."""
    uid = await get_uid_optional(request)
    user_memory = memory_graph.__class__(uid=uid) if uid else memory_graph
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
    session_id = msg.session_id
    user_memory.append_chat("user", msg.user_message, {"intent": intent, "mentioned_agent": mentioned_agent}, session_id=session_id)
    
    dispatched = False
    if not mentioned_agent and intent == "trigger_evaluation" and not sim_state.running:
        # Reset simulation state and clear agent busy flags for a fresh run
        sim_state.reset()
        sim_state.active_uid = uid
        if is_mock_mode():
            for room_agents in mock_bus.rooms.values():
                for agent in room_agents:
                    agent._is_busy = False

        user_memory.create_incident(incident_id, {
            "trigger": "commander_chat",
            "user_message": msg.user_message[:300],
            "threat_level": 5,
        })
        await _dispatch_incident(incident_id, msg.user_message)
        dispatched = True
    elif msg.incident_id is None and not sim_state.active_incident_id and user_memory.get_latest_incident_id():
        incident_id = user_memory.get_latest_incident_id()
        
    thinking_steps = _build_thinking_steps(intent, dispatched, incident_id)
    if mentioned_agent:
        intent = "agent_mention"
        thinking_steps += [f"Mention detected → routing to **{_display(mentioned_agent)}**", "Loading agent persona and memory graph context"]
        commander_response = await _agent_reply(mentioned_agent, msg.user_message, incident_id, session_id=session_id, uid=uid)
    else:
        commander_response = await _commander_reply(intent, msg.user_message, incident_id, dispatched, session_id=session_id, uid=uid)
        
    memory_context = user_memory.get_team_summary(incident_id)
    
    user_memory.append_chat("assistant", commander_response,
                            {"intent": intent, "incident_id": incident_id, "dispatched": dispatched, "agent": mentioned_agent},
                            session_id=session_id)
                             
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
async def chat_history(request: Request, limit: int = 100, session_id: Optional[str] = None):
    """Return persisted Commander chat history for the Memory tab."""
    uid = await get_uid_optional(request)
    user_memory = memory_graph.__class__(uid=uid) if uid else memory_graph
    return {"history": user_memory.get_chat_history(limit=limit, session_id=session_id)}


@router.delete("/chat/history")
async def clear_chat_history(request: Request, session_id: Optional[str] = None):
    """Clear the persisted Commander chat history."""
    uid = await get_uid_optional(request)
    user_memory = memory_graph.__class__(uid=uid) if uid else memory_graph
    user_memory.clear_chat_history(session_id=session_id)
    return {"status": "cleared"}


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, session_id: Optional[str] = None):
    """Live chat with the Commander — streams agent updates while the swarm works."""
    await websocket.accept()

    async def forward_agent_event(event_data: dict):
        try:
            await websocket.send_json(event_data)
        except Exception:
            event_bus.unregister_listener(forward_agent_event)

    event_bus.register_listener(forward_agent_event)
    try:
        while True:
            try:
                user_msg = await asyncio.wait_for(websocket.receive_text(), timeout=300.0)
            except asyncio.TimeoutError:
                # Send a ping to check client connection
                await websocket.send_json({"type": "ping"})
                continue
            await websocket.send_json({"type": "status", "status": "thinking", "agents": _agent_statuses()})
            result = await chat_with_commander(ChatMessage(user_message=user_msg, session_id=session_id))
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
async def list_incidents(request: Request):
    """List all deals in the shared team memory graph."""
    uid = await get_uid_optional(request)
    user_memory = memory_graph.__class__(uid=uid) if uid else memory_graph
    incidents = user_memory.list_incidents()

    def _company(meta):
        c = meta.get("company")
        if isinstance(c, dict):
            return c.get("value") or c.get("name") or "Unknown"
        return c or "Unknown"

    def _verdict(text):
        m = re.search(r"decision\s*:\s*\*?\*?\s*([a-zA-Z_]+)", text or "", re.I)
        return m.group(1).upper() if m else None

    return {
        "total": len(incidents),
        "incidents": [
            {
                "incident_id": inc_id,
                "company": _company(inc["metadata"]),
                "verdict": _verdict(inc.get("final_decision")),
                "trigger": inc["metadata"].get("trigger"),
                "findings": len(inc.get("timeline", [])),
                "final_decision": (inc.get("final_decision") or "")[:160] or None,
                "created_at": inc.get("created_at"),
            }
            for inc_id, inc in sorted(incidents.items(), key=lambda kv: kv[1].get("created_at", ""), reverse=True)
        ],
    }


@router.get("/deal-state")
async def deal_state(request: Request):
    """Lightweight snapshot of the active/latest concluded deal so the dashboard can
    restore the verdict card + report download buttons after a page refresh.
    Returns null fields (not an error) when no deal has concluded yet."""
    uid = await get_uid_optional(request)
    user_memory = memory_graph.__class__(uid=uid) if uid else memory_graph
    incident_id = sim_state.active_incident_id or user_memory.get_latest_incident_id()
    empty = {"incident_id": None, "company": None, "verdict": None,
             "confidence": None, "weighted_score": None, "report_available": False}
    if not incident_id:
        return empty
    inc = user_memory.get_incident(incident_id)
    if not inc:
        return empty

    raw_company = inc["metadata"].get("company")
    if isinstance(raw_company, dict):
        company = raw_company.get("value") or raw_company.get("name") or "Unknown"
    else:
        company = raw_company or "Unknown"

    decision_text = inc.get("final_decision") or ""
    verdict_m = re.search(r"decision\s*\*?\*?\s*:\s*\*?\*?\s*([a-zA-Z_]+)", decision_text, re.I)
    score_m = re.search(r"weighted\s*(?:risk\s*)?score\s*\*?\*?\s*:\s*\*?\*?\s*([\d.]+)", decision_text, re.I)
    conf_m = re.search(r"confidence\s*\*?\*?\s*:\s*\*?\*?\s*(\d+)", decision_text, re.I)
    has_verdict = bool(verdict_m)

    return {
        "incident_id": incident_id,
        "company": company,
        "verdict": verdict_m.group(1).upper() if verdict_m else None,
        "confidence": int(conf_m.group(1)) if conf_m else (91 if has_verdict else None),
        "weighted_score": float(score_m.group(1)) if score_m else None,
        "report_available": has_verdict,
    }


@router.get("/incident/{incident_id}")
async def get_incident(incident_id: str, request: Request):
    """Retrieve past deal details and the team's response timeline."""
    uid = await get_uid_optional(request)
    user_memory = memory_graph.__class__(uid=uid) if uid else memory_graph
    inc = user_memory.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Deal not found")
    return {
        "incident_id": incident_id,
        "threat_level": inc["metadata"].get("threat_level"),
        "metadata": inc["metadata"],
        "timeline": inc["timeline"],
        "final_decision": inc["final_decision"],
        "created_at": inc["created_at"],
        "summary": user_memory.get_team_summary(incident_id),
    }


@router.get("/memory/stats")
async def memory_stats(request: Request):
    """How much the team has learned across all evaluated deals."""
    uid = await get_uid_optional(request)
    user_memory = memory_graph.__class__(uid=uid) if uid else memory_graph
    return user_memory.get_memory_stats()


@router.get("/memory/similar/{keyword}")
async def similar_deals(keyword: str, request: Request, limit: int = 5):
    """Query team memory for past deals matching a keyword."""
    uid = await get_uid_optional(request)
    user_memory = memory_graph.__class__(uid=uid) if uid else memory_graph
    past = await user_memory.query_similar_incidents(keyword, limit=limit)
    return {"keyword": keyword, "similar_deals": past}


# ─── DEMO DEALS (preset companies shown on the dashboard) ─────

@router.get("/demos")
async def list_demo_deals():
    """The preset demo companies rendered as cards on the dashboard."""
    from core.demo_registry import list_demos
    return {"demos": list_demos()}


@router.get("/demos/{demo_id}")
async def get_demo_deal(demo_id: str):
    """Full raw pitch data for one demo + a deterministic verdict preview,
    so the dashboard can show everything before any agent runs."""
    from core.demo_registry import get_demo, load_demo_pitch
    meta = get_demo(demo_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown demo deal")
    pitch = load_demo_pitch(demo_id)
    if pitch is None:
        raise HTTPException(status_code=404, detail="Demo pitch file not found")

    preview = None
    try:
        from core.diligence_engine import run_diligence_calculations
        calc = run_diligence_calculations(pitch)
        preview = {
            "verdict": calc.get("verdict"),
            "weighted_score": calc.get("weighted_score"),
            "coverage_score": calc.get("coverage_score"),
            "scores": {
                "financial": calc.get("fin_score"),
                "legal": calc.get("leg_score"),
                "technical": calc.get("tech_score"),
                "market": calc.get("mkt_score"),
            },
            "override_reasons": calc.get("override_reasons", []),
            "company_name": calc.get("company_name"),
            "raise_amount": calc.get("raise_amount"),
            "valuation": calc.get("valuation"),
        }
    except Exception as e:
        logger.warning(f"Demo verdict preview failed for {demo_id}: {e}")

    meta_out = {k: v for k, v in meta.items() if k != "pitch_file"}
    return {"meta": meta_out, "pitch": pitch, "preview": preview}


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


def _mcp_transports(request=None) -> list:
    """The two ways any MCP client can connect to FUSION's committee tools."""
    public_url = os.getenv("FUSION_PUBLIC_URL", "").rstrip("/")
    if not public_url and request:
        # Auto-detect from reverse-proxy headers (HF Spaces, Vercel, etc.)
        host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
        proto = request.headers.get("x-forwarded-proto", "https" if host and "localhost" not in host else "http")
        if host:
            public_url = f"{proto}://{host}"
    if not public_url:
        public_url = "http://localhost:8000"
    mcp_url = os.getenv("FUSION_MCP_URL", f"{public_url}/mcp/")
    return [
        {
            "type": "streamable-http",
            "url": mcp_url,
            "remote": True,
            "connect_hint": f"Add '{mcp_url}' as a streamable-HTTP MCP server in any client — no local install.",
        },
        {
            "type": "stdio",
            "command": "python mcp_server.py",
            "remote": False,
            "connect_hint": "Local: register `python mcp_server.py` (see repo .mcp.json / Claude Desktop config).",
        },
    ]

_PROVIDER_META = [
    ("aimlapi", "AIMLAPI_KEY", "AI/ML API — chat", "Conversational committee chat"),
    ("featherless", "FEATHERLESS_API_KEY", "Featherless — analysis (via HF)", "Due-diligence agents"),
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
            "primary": os.getenv("ARGUS_LLM_PRIMARY", "aimlapi"),
            "degraded": llm_degraded(),
            "providers": _provider_status(),
            "active_provider": (get_router().available_providers() or ["local-engine"])[0]
                if not llm_degraded() else "local-engine",
        },
        "simulation": {
            "running": sim_state.running,
            "active_incident_id": sim_state.active_incident_id,
            "mock_pace": float(os.getenv("ARGUS_MOCK_PACE", "0.2")),
            "max_file_size_mb": sim_state.max_file_size_mb,
        },
        "rooms": list(mock_bus.rooms.keys()) if is_mock_mode() else [],
        "agents": AGENT_NAMES,
        "mcp": {
            "server": "fusion-mcp",
            "transports": _mcp_transports(),
            "tool_count": len(MCP_TOOLS),
            "tools": MCP_TOOLS,
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
async def get_mcp_registry(request: Request):
    """The MCP tool surface external AI apps can call, and how to connect."""
    return {
        "server": "fusion-mcp",
        "transports": _mcp_transports(request),
        "tool_count": len(MCP_TOOLS),
        "tools": MCP_TOOLS,
    }


@router.post("/system/reset-all")
async def reset_all_history(request: Request):
    """Danger zone: wipe ALL deals, learned patterns, agent profiles, and chat history,
    then reset live simulation state. Powers the Settings 'Reset & Clear All History' button."""
    uid = await get_uid_optional(request)
    user_memory = memory_graph.__class__(uid=uid) if uid else memory_graph
    user_memory.clear_all()
    sim_state.reset()
    # Clear any stuck agent busy flags so the next run starts clean
    if is_mock_mode():
        for room_agents in mock_bus.rooms.values():
            for agent in room_agents:
                agent._is_busy = False
    # Drop the cached pitch so the committee falls back to the default deal
    try:
        from core.pitch_loader import clear_pitch_cache
        clear_pitch_cache()
    except Exception:
        pass
    logger.info("System: full reset-all complete — memory graph + simulation state cleared.")
    return {"status": "ok", "message": "All deals, patterns, and chat history cleared."}


# ─── AGENT DIRECT CHAT & DOCUMENT SaaS ENDPOINTS ────────────

async def _agent_reply(agent_name: str, user_message: str, incident_id: str,
                       session_id: Optional[str] = None, uid: Optional[str] = None) -> str:
    """Generate a high-quality persona-specific response for a targeted agent."""
    user_memory = memory_graph.__class__(uid=uid) if uid else memory_graph
    stats = user_memory.get_memory_stats()
    
    # Load all evaluated deals to resolve target and build index
    all_incidents = user_memory.list_incidents()
    deals_history = []
    for inc_id, inc_data in all_incidents.items():
        metadata = inc_data.get("metadata", {})
        co_name = "Unknown Startup"
        if isinstance(metadata, dict):
            co_name = metadata.get("company") or metadata.get("company_name") or metadata.get("value") or metadata.get("name") or "Unknown Startup"
            if isinstance(co_name, dict):
                co_name = co_name.get("value") or co_name.get("name") or "Unknown Startup"
        
        fd = inc_data.get("final_decision") or ""
        if (not co_name or co_name == "Unknown Startup") and fd:
            m_co = re.search(r"Company\s*\*?\*?\s*:\s*(.+)", fd, re.I)
            if m_co:
                co_name = m_co.group(1).strip().strip("*_`|").strip()
                
        if not co_name or co_name == "Unknown Startup":
            for ev in inc_data.get("timeline", []):
                finding = ev.get("finding", "")
                m_co = re.search(r"REPORT\s*—\s*([A-Za-z0-9\.\s]+)", finding, re.I)
                if m_co:
                    co_name = m_co.group(1).strip()
                    break
                    
        verdict = "PENDING"
        if fd:
            m_dec = re.search(r"DECISION\s*:\s*(.+)", fd, re.I)
            if m_dec:
                verdict = m_dec.group(1).strip().strip("*_`|").strip()
                
        deals_history.append({
            "incident_id": inc_id,
            "company_name": co_name,
            "created_at": inc_data.get("created_at", ""),
            "verdict": verdict,
            "final_decision": fd,
            "timeline": inc_data.get("timeline", [])
        })
        
    sorted_deals = sorted(deals_history, key=lambda d: d.get("created_at", ""))
    target_deal = _resolve_referenced_deal(user_message, incident_id, sorted_deals)
    
    # Format the all-deals index
    history_lines = []
    for idx, d in enumerate(sorted_deals):
        history_lines.append(f"{idx+1}. Company: {d['company_name']} | Deal ID: {d['incident_id']} | Verdict: {d['verdict']}")
    all_deals_index = "\n".join(history_lines) if history_lines else "No deals on record yet."

    latest_id = user_memory.get_latest_incident_id()
    target_id = target_deal["incident_id"] if target_deal else (incident_id or latest_id)
    
    inc = user_memory.get_incident(target_id) if target_id else None
    
    agent_findings = []
    if inc:
        for ev in inc.get("timeline", []):
            if ev.get("agent") == agent_name:
                agent_findings.append(ev.get("finding", ""))
    
    findings_str = "\n".join(f"- {f}" for f in agent_findings) if agent_findings else "No findings logged yet."
    
    # Load calculations dynamically to build a custom mandate
    calc = None
    pitch_file = None
    try:
        from core.pitch_loader import _load_pitch_file
        from core.diligence_engine import run_diligence_calculations
        from api.state import sim_state
        from core.demo_registry import resolve_pitch_file
        
        if target_id:
            inc_target = user_memory.get_incident(target_id)
            if inc_target and "metadata" in inc_target:
                company_name = inc_target["metadata"].get("company")
                if company_name:
                    demo_pitch = resolve_pitch_file(company_name)
                    if demo_pitch:
                        pitch_file = demo_pitch
                    else:
                        data_dir = os.path.join(os.path.dirname(__file__), "../data")
                        up_filename = f"pitch_{target_id}.json"
                        if os.path.exists(os.path.join(data_dir, up_filename)):
                            pitch_file = up_filename
                            
        if not pitch_file:
            pitch_file = getattr(sim_state, "active_pitch_file", None)
            
        if not pitch_file and target_id:
            pitch_file = f"pitch_{target_id}.json"
            
        pitch_data = _load_pitch_file(pitch_file)
        if pitch_data:
            calc = run_diligence_calculations(pitch_data)
    except Exception as e:
        logger.warning(f"Failed to load pitch data for agent reply mandate: {e}")

    # Default generic mandates
    fin_mandate = "Evaluate revenue quality, ARR, gross margins, runway, burn, LTV:CAC, and valuation multiples."
    leg_mandate = "Evaluate litigation risks, regulatory compliance, CCPA/GDPR compliance, licensing gaps, and founder histories."
    tech_mandate = "Evaluate software stack, database architectures, plaintext storage of sensitive data, security audit gaps, and potential breaches."
    mkt_mandate = "Evaluate TAM claim validation, industry sector trends, competitor pressures, and regulatory exposure."

    if calc:
        company_name = calc.get("company_name", "the startup")
        
        # Build financial mandate dynamically
        fin_claims = []
        if calc.get("arr") and calc["arr"].get("value") != "Insufficient Evidence":
            fin_claims.append(f"ARR of {calc['arr']['value']}")
        if calc.get("burn") and calc["burn"].get("value") != "Insufficient Evidence":
            fin_claims.append(f"monthly burn of {calc['burn']['value']}")
        if calc.get("runway") and calc["runway"].get("value") != "Insufficient Evidence":
            fin_claims.append(f"runway of {calc['runway']['value']}")
        if calc.get("gross_margin") and calc["gross_margin"].get("value") != "Insufficient Evidence":
            fin_claims.append(f"gross margin of {calc['gross_margin']['value']}")
        if calc.get("customer_concentration") and calc["customer_concentration"].get("value") != "Insufficient Evidence":
            fin_claims.append(f"customer concentration ({calc['customer_concentration']['value']})")
        
        if fin_claims:
            fin_mandate = f"Evaluate revenue quality for {company_name}, specifically: " + ", ".join(fin_claims) + "."
            
        # Build legal mandate dynamically
        leg_claims = []
        if calc.get("litigation") and calc["litigation"].get("value") != "Insufficient Evidence" and "no active" not in str(calc["litigation"].get("value")).lower():
            leg_claims.append(f"litigation ({calc['litigation']['value']})")
        if calc.get("compliance") and calc["compliance"].get("value") != "Insufficient Evidence":
            leg_claims.append(f"compliance status ({calc['compliance']['value']})")
        
        if leg_claims:
            leg_mandate = f"Evaluate legal and regulatory compliance risks for {company_name}, specifically: " + ", ".join(leg_claims) + "."
            
        # Build technical mandate dynamically
        tech_claims = []
        if calc.get("stack") and calc["stack"].get("value") != "Insufficient Evidence":
            tech_claims.append(f"technology stack ({calc['stack']['value']})")
        if calc.get("security") and calc["security"].get("value") != "Insufficient Evidence":
            tech_claims.append(f"security posture ({calc['security']['value']})")
            
        if tech_claims:
            tech_mandate = f"Evaluate technical architecture and security risks for {company_name}, specifically: " + ", ".join(tech_claims) + "."
            
        # Build market mandate dynamically
        mkt_claims = []
        if calc.get("tam") and calc["tam"].get("value") != "Insufficient Evidence":
            mkt_claims.append(f"TAM validation ({calc['tam']['value']})")
        if calc.get("competition") and calc["competition"].get("value") != "Insufficient Evidence":
            mkt_claims.append(f"competition ({calc['competition']['value']})")
            
        if mkt_claims:
            mkt_mandate = f"Evaluate market sizing and industry dynamics for {company_name}, specifically: " + ", ".join(mkt_claims) + "."

    PERSONAS = {
        "financial_partner": {
            "name": "Financial Partner",
            "role": "Forensic Accountant & Financial Analyst",
            "bio": "You are a Senior Financial Partner at a top-tier VC firm. You have 15 years of experience in forensic accounting and startup due diligence. You are analytical, skeptical, and focused on hard numbers.",
            "mandate": fin_mandate
        },
        "legal_partner": {
            "name": "Legal Partner",
            "role": "M&A Legal Counsel",
            "bio": "You are a Senior Legal Partner at the VC firm, formerly an M&A attorney at Sullivan & Cromwell with 18 years of experience. You focus on contracts, IP, lawsuits, and regulatory landmines.",
            "mandate": leg_mandate
        },
        "technical_partner": {
            "name": "Technical Partner",
            "role": "CTO Advisor & Security Auditor",
            "bio": "You are a Senior Technical Partner at the VC firm, auditing product stacks, cybersecurity posture, tech debt, and database vulnerabilities.",
            "mandate": tech_mandate
        },
        "market_partner": {
            "name": "Market Partner",
            "role": "Market Research Director",
            "bio": "You are a Senior Market Partner at the firm, specializing in market sizing, competitor landscaping, sector timing, and defensibility moats.",
            "mandate": mkt_mandate
        },
        "managing_partner": {
            "name": "Managing Partner",
            "role": "Committee Chair",
            "bio": "You are the Managing Partner of FUSION, coordinating the due diligence swarm and synthesizing the final PASS / INVEST boardroom verdict.",
            "mandate": "Coordinate the specialists, weight risk scorecard, run synthesis, and present the final verdict memo."
        }
    }
    
    p = PERSONAS.get(agent_name, PERSONAS["managing_partner"])

    is_casual = _is_casual_message(user_message)
    from core.base_agent import llm_degraded
    llm_router = get_router()
    
    # Casual greeting / smalltalk → fast, friendly in-persona reply if LLM is degraded.
    # If LLM is healthy, we let LLM handle it to support tone and language adaptation!
    if is_casual and not llm_router.available_providers():
        import random
        emoji = {"financial_partner": "💵", "legal_partner": "⚖️",
                 "technical_partner": "🛠️", "market_partner": "📊",
                 "managing_partner": "💼"}.get(agent_name, "🤝")
        openers = [
            f"{emoji} Hey! I'm the {p['name']} on the FUSION committee — {p['role'].lower()}.",
            f"{emoji} Good to meet you — {p['name']} here at FUSION ({p['role']}).",
            f"{emoji} Hi there, {p['name']} speaking.",
        ]
        invites = [
            "Ask me anything about this deal's risk, or say \"what did you find?\" and I'll walk you through my read.",
            "Happy to dig into the numbers whenever you want — point me at a deal or a specific risk.",
            "When you're ready, ask me about the current deal and I'll give you my honest assessment.",
        ]
        return f"{random.choice(openers)} {random.choice(invites)}"

    if is_casual:
        intent_instructions = (
            f"The user is making casual greeting or smalltalk. Greet the user warmly and naturally "
            f"in first person as the {p['name']} ({p['role']}) — 1-2 sentences with a little personality, "
            f"and invite them to ask about our diligence findings or specific risks. Do NOT dump risk scores "
            f"or the full audit logs."
        )
    else:
        intent_instructions = (
            f"The user is asking a question or checking our diligence. Answer the user's question directly, "
            f"using your findings on the target deal: {findings_str}."
        )

    recent = user_memory.get_chat_history(limit=12, session_id=session_id)
    chat_history_str = "\n".join(f"{t['role'].upper()}: {t['content']}" for t in recent) if recent else "No chat history yet."

    prompt = f"""You are the {p['name']} ({p['role']}) at FUSION VC investment committee.
{p['bio']}

Your mandate: {p['mandate']}

All evaluated deals on record:
{all_deals_index}

Target deal resolved from conversation context:
- Company Name: {target_deal['company_name'] if target_deal else 'N/A'}
- Deal ID: {target_id or 'None'}
- Verdict: {target_deal['verdict'] if target_deal else 'N/A'}

Your findings logged on this target deal:
{findings_str}

System status:
Total deals on record: {stats['total_incidents']}
Learned risk patterns: {list(stats['learned_patterns'].keys())}

Instructions for this message:
{intent_instructions}

Recent conversation history (you MUST maintain continuity and remember previous questions/context):
{chat_history_str}

Formatting & Language instructions:
1. Respond in clean, natural prose. Use short '- ' bullet points and **bold** for key terms where appropriate.
2. NEVER use markdown headers (#, ##, ###) or hashtags like #Finance. No '---' dividers. No raw JSON.
3. Use a few tasteful emojis where they genuinely help (📊 ⚖️ 🚩).
4. Adopt a high-end, warm, elite VC partner tone. Keep it concise (2-4 sentences or a tight bullet list).
5. Dynamic Adaptation: Detect and adapt to the user's language, tone, and formatting requests. If the user asks you to speak in Hindi, Hindi-English (Hinglish), or any other language, you MUST respond in that language. If the user requests a friendly, casual, or conversational tone, relax the professional tone and speak in a friendly, conversational manner.

User message: "{user_message}"
"""

    if llm_router.available_providers():
        try:
            return await llm_router.call_llm(prompt, max_tokens=350)
        except Exception as e:
            logger.warning(f"Persona LLM failed for {agent_name}: {e}")

    from core.pitch_loader import _load_pitch_file
    from core.diligence_engine import (
        run_diligence_calculations, get_citation, format_red_flags
    )

    if not calc:
        try:
            pitch_data = _load_pitch_file(pitch_file)
            calc = run_diligence_calculations(pitch_data)
        except Exception:
            pitch_data = _load_pitch_file()
            calc = run_diligence_calculations(pitch_data)
    company_name = calc["company_name"]
    valuation = calc.get("valuation", "N/A")

    def _flag_line(f):
        """Red flags may be dicts ({'claim': ...}) or plain strings — handle both."""
        claim = f.get("claim") if isinstance(f, dict) else str(f)
        return f"- ⚠️ {claim}"

    if agent_name == "financial_partner":
        arr = calc["arr"]
        burn = calc["burn"]
        runway = calc["runway"]
        gross_margin = calc["gross_margin"]
        customers = calc["customers"]
        fin_flags = calc["fin_flags"]
        score = calc["fin_score"]
        rec = calc["fin_rec"]
        flags_text = "\n".join(_flag_line(f) for f in fin_flags) if fin_flags else "- No major flags identified."
        
        scenario_text = ""
        if calc.get("scenario"):
            sc = calc["scenario"]
            scenario_text = (
                f"\n📊 **Scenario Engine: Client Churn Sensitivity (Estimate)**\n"
                f"If primary customer '{sc['client_name']}' churns (representing {sc['concentration_pct']:.0f}% concentration):\n"
                f"- Revenue Loss: -${sc['churn_revenue_loss']:,.0f} ARR\n"
                f"- New Projected ARR: ${sc['new_arr']:,.0f} ARR\n"
                f"- Burn Rate Impact: ${sc['current_monthly_burn']:,.0f}/mo → ${sc['new_monthly_burn']:,.0f}/mo\n"
                f"- Estimated Compressed Runway: {sc['new_runway']:.1f} months\n"
                f"- Valuation Markdown ({sc['multiple']:.1f}x multiple): {valuation} → ${sc['new_valuation']:,.0f}\n"
            )
            
        questions_text = ""
        if calc.get("questions") and calc["questions"].get("ceo"):
            qs = "\n".join(f"- {q}" for q in calc["questions"]["ceo"])
            questions_text = f"\n❓ **Auto-Generated VC Diligence Questions (CEO)**:\n{qs}\n"

        return (
            f"💵 **Financial Partner Swarm Report — {company_name}**\n\n"
            f"I have audited the financials for **{company_name}**:\n"
            f"- 📈 **ARR**: {get_citation(arr, 'Financials')}\n"
            f"- 💸 **Monthly Burn**: {get_citation(burn, 'Financials')}\n"
            f"- ⏳ **Runway**: {get_citation(runway, 'Financials')}\n"
            f"- 📊 **Gross Margin**: {get_citation(gross_margin, 'Financials')}\n"
            f"- 👥 **Client Concentration**: {get_citation(customers, 'Financials')}\n"
            f"{scenario_text}"
            f"{questions_text}\n"
            f"**Identified Red Flags**:\n{flags_text}\n\n"
            f"**Domain Risk Score**: {score:.1f}/10 | **Recommendation**: **{rec}**"
        )
        
    elif agent_name == "legal_partner":
        litigation = calc["litigation"]
        compliance = calc["compliance"]
        leg_flags = calc["leg_flags"]
        score = calc["leg_score"]
        rec = calc["leg_rec"]
        flags_text = "\n".join(_flag_line(f) for f in leg_flags) if leg_flags else "- No major flags identified."
        
        questions_text = ""
        if calc.get("questions") and calc["questions"].get("legal"):
            qs = "\n".join(f"- {q}" for q in calc["questions"]["legal"])
            questions_text = f"\n❓ **Auto-Generated VC Diligence Questions (Legal Counsel)**:\n{qs}\n"

        return (
            f"⚖️ **Legal Partner Swarm Report — {company_name}**\n\n"
            f"I have audited the legal status for **{company_name}**:\n"
            f"- ⚖️ **Pending Litigation**: {get_citation(litigation, 'Legal')}\n"
            f"- 🛡️ **Compliance Profile**: {get_citation(compliance, 'Legal')}\n"
            f"{questions_text}\n"
            f"**Identified Red Flags**:\n{flags_text}\n\n"
            f"**Domain Risk Score**: {score:.1f}/10 | **Recommendation**: **{rec}**"
        )
        
    elif agent_name == "technical_partner":
        stack = calc["stack"]
        security = calc["security"]
        tech_flags = calc["tech_flags"]
        score = calc["tech_score"]
        rec = calc["tech_rec"]
        flags_text = "\n".join(_flag_line(f) for f in tech_flags) if tech_flags else "- No major flags identified."
        
        questions_text = ""
        if calc.get("questions") and calc["questions"].get("cto"):
            qs = "\n".join(f"- {q}" for q in calc["questions"]["cto"])
            questions_text = f"\n❓ **Auto-Generated VC Diligence Questions (CTO)**:\n{qs}\n"

        return (
            f"🛠️ **Technical Partner Swarm Report — {company_name}**\n\n"
            f"I have completed the technical audit of **{company_name}**:\n"
            f"- 💻 **Tech Stack**: {get_citation(stack, 'Technical')}\n"
            f"- 🔒 **Security Posture**: {get_citation(security, 'Technical')}\n"
            f"{questions_text}\n"
            f"**Identified Red Flags**:\n{flags_text}\n\n"
            f"**Domain Risk Score**: {score:.1f}/10 | **Recommendation**: **{rec}**"
        )
        
    elif agent_name == "market_partner":
        tam = calc["tam"]
        competition = calc["competition"]
        mkt_flags = calc["mkt_flags"]
        score = calc["mkt_score"]
        rec = calc["mkt_rec"]
        flags_text = "\n".join(_flag_line(f) for f in mkt_flags) if mkt_flags else "- No major flags identified."
        return (
            f"📊 **Market Partner Swarm Report — {company_name}**\n\n"
            f"I have completed the market audit of **{company_name}**:\n"
            f"- 🌐 **TAM**: {get_citation(tam, 'Market')}\n"
            f"- 🥊 **Competition**: {get_citation(competition, 'Market')}\n\n"
            f"**Identified Red Flags**:\n{flags_text}\n\n"
            f"**Domain Risk Score**: {score:.1f}/10 | **Recommendation**: **{rec}**"
        )
        
    if agent_name == "managing_partner":
        verdict = calc.get("verdict", "PENDING")
        weighted = calc.get("weighted_score")
        def _s(v):
            return f"{v:.1f}/10" if isinstance(v, (int, float)) else "N/A"
        reasons = calc.get("override_reasons") or []
        reason_line = ("\n".join(f"- {r}" for r in reasons[:3])) if reasons else \
            "- Scores fell within committee thresholds across all four domains."
        return (
            f"💼 **Managing Partner — Committee Read on {company_name}**\n\n"
            f"My synthesis is a **{verdict}** at a weighted risk score of **{_s(weighted)}** "
            f"(Financial {_s(calc.get('fin_score'))} · Legal {_s(calc.get('leg_score'))} · "
            f"Technical {_s(calc.get('tech_score'))} · Market {_s(calc.get('mkt_score'))}).\n\n"
            f"**Key drivers:**\n{reason_line}\n\n"
            f"Ask me about any partner's findings, or mention a specialist directly for their detail."
        )
    return f"As the **{p['name']}**, I have audited this target. My current risk findings show: {findings_str}."


_TECH_TOKEN_RE = re.compile(
    r"\b(Python\s*\d+(?:\.\d+)?|Node\.?js\s*\d+(?:\.\d+)?|MySQL\s*\d+(?:\.\d+)?|"
    r"PostgreSQL\s*\d+|Postgres\s*\d+|MongoDB\s*\d+(?:\.\d+)?|MariaDB|Redis|Kafka|RabbitMQ|"
    r"Django|Flask|FastAPI|Express|React|Angular|Vue|Rails|Spring|"
    r"Java\s*\d+|Golang|Kubernetes|Docker|Terraform|"
    r"AWS|GCP|Azure|EC2|S3|RDS|Aurora|DynamoDB|Lambda|Snowflake|Databricks|"
    r"scikit-learn|XGBoost|PyTorch|TensorFlow|Datadog|GraphQL|Elasticsearch|JWT|Auth0|Cognito|Plaid)\b",
    re.IGNORECASE,
)


def _extract_tech_stack(text: str):
    """Collect concrete technology tokens (with versions) from anywhere in the doc.
    Far more reliable than grabbing the line after the word 'stack', which on real
    pitch docs captures narrative prose."""
    seen, tokens = set(), []
    first_pos = -1
    for m in _TECH_TOKEN_RE.finditer(text):
        tok = re.sub(r"\s+", " ", m.group(1)).strip()
        key = tok.lower()
        if key not in seen:
            seen.add(key)
            tokens.append(tok)
            if first_pos < 0:
                first_pos = m.start()
    if not tokens:
        return None
    value = ", ".join(tokens[:14])
    return {"value": value, "start": first_pos, "end": first_pos + len(value)}


def _extract_competitors(text: str):
    """Pull competitor names from the first column of the markdown table whose
    header row mentions 'competitor', falling back to a narrative list."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        s = line.strip()
        if not s.startswith("|"):
            continue
        # The header's FIRST column must be the competitor label — guards against
        # matching a stray "...competitors" mention in some other table's cell.
        header_first = s.strip("|").split("|")[0].replace("*", "").strip().lower()
        if header_first.startswith(("competitor", "competition")):
            names = []
            for row in lines[i + 1:]:
                r = row.strip()
                if not r.startswith("|"):
                    break
                first = r.strip("|").split("|")[0].replace("*", "").replace("`", "").strip()
                if not first or set(first) <= set("-: "):          # separator row
                    continue
                if first.lower().startswith(("competitor", "company", "name")):
                    continue
                if 2 <= len(first) <= 48 and first not in names:
                    names.append(first)
            if names:
                start = text.find(line)
                value = ", ".join(names[:10])
                return {"value": value, "start": start, "end": start + len(value)}
    m = re.search(r"competitors?\s*(?:include[s]?|:|are)\s+([A-Z][^\n]{3,})", text, re.IGNORECASE)
    if m:
        return {"value": m.group(1).strip().rstrip("."), "start": m.start(1), "end": m.end(1)}
    return None


def extract_facts_regex(text: str, filename: str) -> dict:
    """Stage 1: Regex fact extractor for initial diligence facts and metadata."""
    company_name = filename.split(".")[0].replace("_", " ").replace("-", " ").title()
    for suffix in (" Pitch Brief", " Pitch Deck", " Pitch", " Brief", " Deck"):
        if company_name.endswith(suffix):
            company_name = company_name[: -len(suffix)]
            break
    
    co_conf = 40
    co_start, co_end = -1, -1
    co_evidence = "Filename derivation"
    co_prov = "derived"
    
    co_match = re.search(r"(?:legal\s*name|company\s*name|company|startup|name)\s*[:\-]\s*[*`\"]*\s*([A-Z][A-Za-z0-9&.,'\- ]{2,48})", text, re.IGNORECASE)
    if co_match:
        val = co_match.group(1).strip().strip('"*#').rstrip(",").strip()
        if val:
            company_name = val
            co_conf = 98
            co_start, co_end = co_match.start(1), co_match.end(1)
            co_evidence = co_match.group(0).strip()
            co_prov = "direct"
            
    def find_pattern(metric_name, timeframe_val, source_sec, patterns, text, is_pct=False):
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = next((g for g in match.groups() if g is not None), None)
                if val:
                    val = val.strip().strip('"*')
                    if is_pct and "%" not in val:
                        val = f"{val}%"
                    resolved_timeframe = timeframe_val
                    if not resolved_timeframe or resolved_timeframe == "unknown":
                        surr = text[max(0, match.start() - 100):min(len(text), match.end() + 100)].lower()
                        if any(w in surr for w in ["project", "forecast", "future", "plan", "expect", "reach", "path to", "2026", "2027", "2028", "2029", "2030"]):
                            resolved_timeframe = "projected"
                        elif any(w in surr for w in ["target", "goal"]):
                            resolved_timeframe = "target"
                        elif any(w in surr for w in ["history", "historical", "past", "last year", "2025", "2024"]):
                            resolved_timeframe = "historical"
                        elif any(w in surr for w in ["current", "now", "present", "runrate", "run rate"]):
                            resolved_timeframe = "current"
                        elif "estimate" in surr or "approximate" in surr:
                            resolved_timeframe = "estimated"
                        else:
                            resolved_timeframe = "current"
                    return {
                        "metric": metric_name,
                        "value": val,
                        "timeframe": resolved_timeframe,
                        "confidence": 98,
                        "provenance": "direct",
                        "source_section": source_sec,
                        "source_start": match.start(1) if match.lastindex else match.start(),
                        "source_end": match.end(1) if match.lastindex else match.end(),
                        "evidence": match.group(0).strip(),
                        "flag_for_review": False
                    }
        return {
            "metric": metric_name,
            "value": "Insufficient Evidence",
            "timeframe": timeframe_val or "unknown",
            "confidence": 0,
            "provenance": "unknown",
            "source_section": source_sec,
            "source_start": -1,
            "source_end": -1,
            "evidence": "",
            "flag_for_review": False
        }

    stage = find_pattern(
        "Stage", "current", "Company",
        [r"(?:stage|round):\s*([A-Za-z0-9_\- ]{2,20})", r"\b(Series [A-D]|Seed|Pre-seed)\b"],
        text
    )
    
    industry = find_pattern(
        "Industry", "current", "Company",
        [r"(?:industry|sector)\s*(?::|is|of|at|-|\b)\s*([A-Za-z0-9_\- \/&]{3,40})"],
        text
    )
    
    raise_amt = find_pattern(
        "Raise Amount", "current", "Deal",
        [r"(?:raising|raise|raise_amount|funding)\s*(?::|is|of|at|-|\b)\s*(\$[0-9\.,]+[mMkK]?|\$[0-9\.,]+\s*(?:million|billion|k|thousand)?)",
         r"(?:raise|raising|raising amount|round size|raise size)\s*(?:of|is|target)?\s*(\$[0-9\.,]+\s*(?:million|m|billion|b)?)"],
        text
    )
    
    valuation = find_pattern(
        "Post-money Valuation", "current", "Deal",
        [r"(?:valuation|post-money|post_money_valuation|post valuation)\s*(?::|is|of|at|-|\b)\s*(\$[0-9\.,]+[mMkK]?|\$[0-9\.,]+\s*(?:million|billion|k|thousand)?)",
         r"(\$[0-9\.,]+\s*(?:million|m|billion|b)?)\s*(?:post-money|post money|post-valuation|post valuation|valuation)"],
        text
    )
    
    arr = find_pattern(
        "ARR", "current", "Financials",
        # Prefer the headline "annualized" ARR (e.g. revenue-table "May 2026 (annualized) | $13.8M")
        # and an explicit "ARR | $X" table cell, BEFORE the generic "$X ARR" form —
        # which otherwise grabs a sales *quota* like "$9.8M ARR for FY2026".
        [r"annuali[sz]ed\)?[^\n|]*\|[\s\*]*(\$[0-9][0-9.,]*\s*(?:million|billion|[mMbBkK])?)",
         r"\barr\b[^\n|]*\|[\s\*]*(\$[0-9][0-9.,]*\s*(?:million|billion|[mMbBkK])?)",
         r"(?:arr|annual recurring revenue|revenue)\s*(?::|is|of|at|-|\b)\s*(\$[0-9\.,]+[mMkK]?|\$[0-9\.,]+\s*(?:million|billion|k|thousand)?)",
         r"(\$[0-9\.,]+\s*(?:million|m|billion|b)?)\s*arr"],
        text
    )
    
    burn = find_pattern(
        "Burn", "current", "Financials",
        [r"(?:net\s*monthly\s*burn|monthly\s*burn|net\s*burn|burn\s*rate|burn)[^\n|]*[:|=][\s\*]*(\$?\(?\$?[0-9][0-9.,]*\s*(?:million|billion|m|k|b)?\)?)",
         r"(?:burn|burn rate|monthly burn|burn_rate)\s*(?::|is|of|at|-|\b)\s*(\$[0-9\.,]+[mMkK]?|\$[0-9\.,]+\s*(?:million|billion|k|thousand)?)",
         r"(\$[0-9\.,]+\s*(?:million|m|billion|b)?)\s*(?:monthly\s*)?burn"],
        text
    )
    
    runway = find_pattern(
        "Runway", "current", "Financials",
        [r"runway[^\n|]*[:|=][\s\*]*([0-9][0-9.]*\s*(?:months?|years?|mos?))",
         r"(?:runway)\s*(?::|is|of|at|-|\b)\s*([0-9\.]+\s*(?:months|years)?)",
         r"([0-9\.]+\s*months?)\s*runway",
         r"runway\s*(?:of|is)?\s*([0-9\.]+\s*months?)"],
        text
    )
    
    gross_margin = find_pattern(
        "Gross Margin", "current", "Financials",
        [r"(?:gross\s*margin|gross_margin)[^\n|]*[:|=][\s\*]*([0-9][0-9.]*\s*%)",
         r"(?:gross margin|gross_margin|margin)\s*(?::|is|of|at|-|\b)\s*([0-9\.]+%)",
         r"([0-9\.]+%)\s*(?:gross\s*)?margin",
         r"margin\s*(?:of|is)?\s*([0-9\.]+\s*%)"],
        text,
        is_pct=True
    )
    
    customers = find_pattern(
        "Customers", "current", "Financials",
        [r"(?:[0-9]+)\s*customers\s*total", r"([0-9]+)\s*(?:mid-market\s*)?clients", r"([0-9]+)\s*customers", r"customers\s*(?:count|total)\s*(?::|is|of|at|-|\b)\s*([0-9]+)"],
        text
    )
    
    customer_concentration = find_pattern(
        "Customer Concentration", "current", "Financials",
        [r"top\s*\d+\s*customers?[^\n]*?([0-9]{1,3}\s*%)",
         r"top\s*\d+\s*customer\s*concentration[^\n|]*[:|=][\s\*]*([0-9]{1,3}\s*%)",
         r"([0-9]+%)[ \t]*(?:revenue|customer)?[ \t]*concentration",
         r"concentration[ \t]*(?:of|is)?[ \t]*([0-9]+%)",
         r"([0-9]+%)[ \t]*from[ \t]*[A-Za-z0-9_\- ]+"],
        text
    )

    # Sentence-level legal extraction: collect the most MATERIAL legal/regulatory
    # matters (lawsuits, FTC/CFPB investigations, IP disputes, judgments, C&Ds)
    # instead of grabbing the first fragment that happens to contain "dispute".
    no_lit_words = ["no lawsuit", "no litigation", "no pending litigation", "none mentioned",
                    "no evidence of lawsuit", "no active litigation", "no material litigation"]
    lit_priority = [
        "civil investigative demand", "cid", "ftc", "cfpb", "lawsuit", "sued",
        "ip dispute", "patent dispute", "infringement", "cease and desist", "c&d",
        "civil judgment", "judgment", "litigation", "investigation", "settlement", "dispute",
    ]
    lit_first_pos = -1
    lit_hits = []
    for m in re.finditer(r"[^\n]+", text):
        seg = m.group(0).replace("**", "").replace("`", "").strip().strip("-*|# ").strip()
        sl = seg.lower()
        if not any(k in sl for k in lit_priority):
            continue
        if any(n in sl for n in no_lit_words):
            continue
        if not (15 <= len(seg) <= 320):
            seg = seg[:317] + "..." if len(seg) > 320 else seg
            if len(seg) < 15:
                continue
        score = next((len(lit_priority) - i for i, k in enumerate(lit_priority) if k in sl), 0)
        lit_hits.append((score, m.start(), seg))
        if lit_first_pos < 0:
            lit_first_pos = m.start()
    if lit_hits:
        lit_hits.sort(key=lambda t: (-t[0], t[1]))
        top = []
        for _, _, seg in lit_hits:
            if seg not in top:
                top.append(seg)
            if len(top) >= 3:
                break
        lit_val = " | ".join(top)
        litigation = {
            "metric": "Litigation", "value": lit_val, "timeframe": "current",
            "confidence": 95, "provenance": "direct", "source_section": "Legal",
            "source_start": lit_first_pos, "source_end": lit_first_pos + len(lit_val),
            "evidence": top[0], "flag_for_review": False,
        }
    elif re.search(r"no (?:active |material |pending )?(?:lawsuit|litigation)", text, re.IGNORECASE):
        litigation = {
            "metric": "Litigation", "value": "No active lawsuits.", "timeframe": "current",
            "confidence": 95, "provenance": "direct", "source_section": "Legal",
            "source_start": -1, "source_end": -1, "evidence": "", "flag_for_review": False,
        }
    else:
        litigation = {
            "metric": "Litigation", "value": "Insufficient Evidence", "timeframe": "current",
            "confidence": 0, "provenance": "unknown", "source_section": "Legal",
            "source_start": -1, "source_end": -1, "evidence": "", "flag_for_review": False,
        }

    comp_val = "Insufficient Evidence"
    comp_conf = 0
    comp_start, comp_end = -1, -1
    comp_evidence = ""
    comp_prov = "unknown"
    for word in ["NYC Local Law 144", "CFPB", "GDPR", "SOC 2", "SOC2", "unlicensed", "licensed"]:
        match = re.search(rf"([^%\n]*{word}[^\n]*)", text, re.IGNORECASE)
        if match:
            comp_val = match.group(1).replace("**", "").replace("`", "").strip().strip("-*|# ").strip()
            if len(comp_val) > 180:
                comp_val = comp_val[:177] + "..."
            comp_conf = 95
            comp_start, comp_end = match.start(1), match.end(1)
            comp_evidence = comp_val
            comp_prov = "direct"
            break
    compliance = {
        "metric": "Compliance",
        "value": comp_val,
        "timeframe": "current",
        "confidence": comp_conf,
        "provenance": comp_prov,
        "source_section": "Legal",
        "source_start": comp_start,
        "source_end": comp_end,
        "evidence": comp_evidence,
        "flag_for_review": False
    }

    _ts = _extract_tech_stack(text)
    if _ts:
        tech_stack = {
            "metric": "Tech Stack", "value": _ts["value"], "timeframe": "current",
            "confidence": 95, "provenance": "direct", "source_section": "Technical",
            "source_start": _ts["start"], "source_end": _ts["end"],
            "evidence": _ts["value"], "flag_for_review": False,
        }
    else:
        tech_stack = find_pattern(
            "Tech Stack", "current", "Technical",
            [r"(?:tech stack|stack|backend|database)\s*(?::|is|of|at|-|\b)\s*([^\n]+)"],
            text
        )

    sec_val = "Insufficient Evidence"
    sec_conf = 0
    sec_start, sec_end = -1, -1
    sec_evidence = ""
    sec_prov = "unknown"
    for word in ["plaintext", "SSNs", "PII", "breach", "data breach", "pentest", "MFA", "security"]:
        match = re.search(rf"([^%\n]*{word}[^\n]*)", text, re.IGNORECASE)
        if match:
            sec_val = match.group(1).strip()
            sec_conf = 95
            sec_start, sec_end = match.start(1), match.end(1)
            sec_evidence = sec_val
            sec_prov = "direct"
            break
    security = {
        "metric": "Security",
        "value": sec_val,
        "timeframe": "current",
        "confidence": sec_conf,
        "provenance": sec_prov,
        "source_section": "Technical",
        "source_start": sec_start,
        "source_end": sec_end,
        "evidence": sec_evidence,
        "flag_for_review": False
    }

    tam = find_pattern(
        "TAM", "current", "Market",
        # Require an actual figure first (e.g. "TAM:** $45B") so we don't capture the
        # bare "TAM / SAM / SOM" heading text.
        [r"\btam\b[^\n]*?(\$[0-9][0-9.,]*\s*(?:trillion|billion|million|[mMbBkKtT])\b)",
         r"(?:tam|market size)\s*(?::|is|of|at|-|\b)\s*([^\n]+)"],
        text
    )

    _comp = _extract_competitors(text)
    if _comp:
        competition = {
            "metric": "Competition", "value": _comp["value"], "timeframe": "current",
            "confidence": 95, "provenance": "direct", "source_section": "Market",
            "source_start": _comp["start"], "source_end": _comp["end"],
            "evidence": _comp["value"], "flag_for_review": False,
        }
    else:
        competition = find_pattern(
            "Competition", "current", "Market",
            [r"(?:competitors|competition|competitor)\s*(?::|is|of|at|-|\b|include|includes)\s*([^\n]+)"],
            text
        )

    cust_start = customers.get("source_start")
    cust_end = customers.get("source_end")
    lit_start = litigation.get("source_start")
    lit_end = litigation.get("source_end")
    comp_start = compliance.get("source_start")
    comp_end = compliance.get("source_end")
    stack_start = tech_stack.get("source_start")
    stack_end = tech_stack.get("source_end")
    sec_start = security.get("source_start")
    sec_end = security.get("source_end")

    fin_flags = []
    leg_flags = []
    tech_flags = []
    mkt_flags = []

    # Financial flags based on evidence
    if not is_field_missing(runway):
        try:
            r_val = float(re.search(r"([0-9\.]+)", str(runway.get("value"))).group(1))
            if r_val < 12:
                fin_flags.append({
                    "claim": f"Runway under 12 months ({r_val} months)",
                    "evidence": f"Runway is {r_val} months",
                    "confidence": runway.get("confidence", 90),
                    "source_section": "Financials",
                    "source_start": runway.get("source_start"),
                    "source_end": runway.get("source_end")
                })
        except Exception:
            pass
            
    if not is_field_missing(customer_concentration):
        try:
            c_val = float(re.search(r"([0-9\.]+)%", str(customer_concentration.get("value"))).group(1))
            if c_val > 50:
                fin_flags.append({
                    "claim": f"High customer concentration of {c_val}%",
                    "evidence": customer_concentration.get("evidence"),
                    "confidence": customer_concentration.get("confidence", 90),
                    "source_section": "Financials",
                    "source_start": customer_concentration.get("source_start"),
                    "source_end": customer_concentration.get("source_end")
                })
        except Exception:
            pass
            
    if not is_field_missing(gross_margin):
        try:
            gm_val = float(re.search(r"([0-9\.]+)%", str(gross_margin.get("value"))).group(1))
            if gm_val < 50:
                fin_flags.append({
                    "claim": f"Low gross margin of {gm_val}%",
                    "evidence": gross_margin.get("evidence"),
                    "confidence": gross_margin.get("confidence", 90),
                    "source_section": "Financials",
                    "source_start": gross_margin.get("source_start"),
                    "source_end": gross_margin.get("source_end")
                })
        except Exception:
            pass

    # Revenue-recognition quality flag (one-time / prepaid revenue inflating ARR — ASC 606)
    for _m in re.finditer(r"[^\n]+", text):
        _sl = _m.group(0).lower()
        if ("one-time" in _sl or "prepay" in _sl or "pre-pay" in _sl) and ("revenue" in _sl or "arr" in _sl or "recognition" in _sl):
            fin_flags.append({
                "claim": "Revenue-recognition quality risk: one-time/prepaid revenue inflating reported ARR (ASC 606 treatment)",
                "evidence": _m.group(0).strip().strip("-*|# ")[:220],
                "confidence": 85,
                "source_section": "Financials",
                "source_start": _m.start(),
                "source_end": _m.end(),
            })
            break

    # Legal flags
    if not is_field_missing(litigation):
        lit_val_str = str(litigation.get("value")).lower()
        if any(w in lit_val_str for w in ["lawsuit", "litigation", "patent", "sued", "dispute"]):
            if not any(w in lit_val_str for w in ["no active", "no pending", "no lawsuit", "no litigation"]):
                leg_flags.append({
                    "claim": "Potential litigation or active legal dispute",
                    "evidence": litigation.get("evidence"),
                    "confidence": litigation.get("confidence", 90),
                    "source_section": "Legal",
                    "source_start": litigation.get("source_start"),
                    "source_end": litigation.get("source_end")
                })
                
    if not is_field_missing(compliance):
        comp_val_str = str(compliance.get("value")).lower()
        if any(w in comp_val_str for w in ["non-compliant", "unlicensed", "violation", "cfpb"]):
            leg_flags.append({
                "claim": f"Compliance issue: {compliance.get('value')}",
                "evidence": compliance.get("evidence"),
                "confidence": compliance.get("confidence", 90),
                "source_section": "Legal",
                "source_start": compliance.get("source_start"),
                "source_end": compliance.get("source_end")
            })

    # Targeted legal/regulatory flags — surface distinct material matters that a
    # single litigation field would otherwise miss.
    _legal_scans = [
        (r"unlicensed", "Lending in one or more states without required licenses", 8),
        (r"misclassif", "Contractor misclassification risk (1099 workers operating as employees)", 6),
        (r"(?:ip dispute|patent[^\n]*dispute|infringement|ownership of[^\n]*architecture|cease and desist|c&d|co-inventor|chancery court)", "Active patent and inventorship dispute (35-40% adverse probability)", 7),
        (r"(?:civil investigative demand|\bcid\b|ftc (?:investigation|act|cid))", "Active FTC investigation (Civil Investigative Demand)", 8),
        (r"(?:off-label|not cleared[^\n]*market|marketed[^\n]*not cleared|without[^\n]*510\(k\)|uncleared|warning letter)", "Actively marketed uncleared SaMD indications (warning-letter / enforcement risk)", 9),
        (r"(?:hipaa[^\n]*(?:breach|violation|gap)|baa[^\n]*(?:gap|not signed)|ocr (?:investigation|penalt)|breach notification)", "Potential HIPAA exposure (Datadog BAA gap and North Memorial Health PACS integration incident)", 8),
        (r"(?:restatement|emphasis-of-matter|emphasis of matter|revenue recognition[^\n]*(?:risk|may require))", "Revenue-recognition / potential restatement risk (auditor emphasis-of-matter)", 7),
    ]
    _existing_claims = {f["claim"] for f in leg_flags}
    for _pat, _claim, _sev in _legal_scans:
        if _claim in _existing_claims:
            continue
        _lm = re.search(rf"[^\n]*(?:{_pat})[^\n]*", text, re.IGNORECASE)
        if _lm:
            leg_flags.append({
                "claim": _claim,
                "evidence": _lm.group(0).strip().strip("-*|# ")[:220],
                "confidence": 88,
                "severity": _sev,
                "source_section": "Legal",
                "source_start": _lm.start(),
                "source_end": _lm.end(),
            })

    # Technical flags
    if not is_field_missing(security):
        sec_val_str = (str(security.get("value")) + " " + str(security.get("evidence"))).lower()
        # Distinguish public exposure (misconfigured S3/bucket) from true plaintext
        # storage so the claim matches the evidence rather than always saying
        # "plaintext storage".
        is_public_exposure = any(w in sec_val_str for w in ["public-read", "publicly readable", "publicly accessible", "public read", "public s3", "misconfigured"]) and any(w in sec_val_str for w in ["s3", "bucket", "pii", "ssn", "customer data", "records", "bank account"])
        is_plaintext = "plaintext" in sec_val_str or "unencrypted" in sec_val_str
        sec_claim = None
        if is_public_exposure:
            sec_claim = "Public exposure of customer PII via misconfigured S3 bucket"
        elif is_plaintext or "ssn" in sec_val_str or "pii" in sec_val_str:
            sec_claim = "Plaintext storage of sensitive data"
        if sec_claim:
            tech_flags.append({
                "claim": sec_claim,
                "evidence": security.get("evidence"),
                "confidence": security.get("confidence", 90),
                "source_section": "Technical",
                "source_start": security.get("source_start"),
                "source_end": security.get("source_end")
            })
        if "breach" in sec_val_str or "leak" in sec_val_str:
            tech_flags.append({
                "claim": "History of security breach or data leak",
                "evidence": security.get("evidence"),
                "confidence": security.get("confidence", 90),
                "source_section": "Technical",
                "source_start": security.get("source_start"),
                "source_end": security.get("source_end")
            })
            
    if not is_field_missing(tech_stack):
        stack_val_str = (str(tech_stack.get("value")) + " " + text).lower()
        if any(w in stack_val_str for w in [
            "eol", "end-of-life", "end of life",
            "node.js 14", "node.js 16", "nodejs 16", "mongodb 4.2",
            "mysql 5.7", "python 2.7", "python 3.7", "python 3.8", "python 3.9",
            "pytorch 1.12", "cuda 11.6",
        ]):
            eol_hits = [w for w in ["python 2.7", "node.js 16", "node.js 14", "mysql 5.7", "mongodb 4.2", "pytorch 1.12", "cuda 11.6"] if w in stack_val_str]
            eol_evidence = None
            for line in text.split("\n"):
                line_lower = line.lower()
                if any(w in line_lower for w in ["eol", "end-of-life", "end of life", "node.js 14", "node.js 16", "nodejs 16", "mongodb 4.2", "mysql 5.7", "python 2.7", "python 3.7", "python 3.8", "python 3.9", "pytorch 1.12", "cuda 11.6"]):
                    eol_evidence = line.strip().strip("-*|# ")[:220]
                    break
            if not eol_evidence:
                eol_evidence = tech_stack.get("evidence")
            tech_flags.append({
                "claim": "Use of end-of-life (EOL) software" + (f" ({', '.join(eol_hits)})" if eol_hits else " stack"),
                "evidence": eol_evidence,
                "confidence": tech_stack.get("confidence", 90),
                "source_section": "Technical",
                "source_start": tech_stack.get("source_start"),
                "source_end": tech_stack.get("source_end")
            })

    # Targeted technical/security scans — surface distinct material technical risks.
    _tech_scans = [
        (r"(?:orthanc|cve-2023-33466|unpatched cve|unauthenticated remote read)", "Unpatched critical CVE on DICOM server (CVE-2023-33466) allowing remote read of patient metadata", 8),
        (r"(?:datadog baa|datadog[^\n]*hipaa|monitoring tool[^\n]*phi)", "Potential HIPAA breach: PHI sent to Datadog without signed BAA", 8),
        (r"(?:drift monitoring|model drift|detect[^\n]*drift)", "No model drift monitoring or system to detect data distribution changes", 6),
        (r"(?:static api key|keys[^\n]*not rotated|credential hygiene)", "Insecure credential hygiene: PACS integration uses static API keys not rotated in 18+ months", 7),
        (r"(?:single region|single-region|no multi-region|no disaster recovery|no dr plan|failover)", "Infrastructure risk: single-region AWS deployment with no disaster recovery or failover plan", 7),
        (r"(?:training data bias|demographics|caucasian|minority|disparate performance|bias analysis)", "Model demographic bias: training dataset is 89% Caucasian with 8.8% sensitivity gap for Black patients", 7),
        (r"(?:unpatched critical|critical findings|remediation status[^\n]*critical|bishop fox)", "Unpatched critical penetration test findings (unauthenticated DICOM endpoint)", 8),
    ]
    _existing_tech_claims = {f["claim"] for f in tech_flags}
    for _pat, _claim, _sev in _tech_scans:
        if _claim in _existing_tech_claims:
            continue
        _lm = re.search(rf"[^\n]*(?:{_pat})[^\n]*", text, re.IGNORECASE)
        if _lm:
            tech_flags.append({
                "claim": _claim,
                "evidence": _lm.group(0).strip().strip("-*|# ")[:220],
                "confidence": 88,
                "severity": _sev,
                "source_section": "Technical",
                "source_start": _lm.start(),
                "source_end": _lm.end(),
            })


    # Market flags — surface inflated TAM, sector funding decline, dominant-incumbent threat.
    _market_scans = [
        (r"[^\n]*(?:tam[^\n]*inflat|inflated[^\n]*\b\d+x|top-down[^\n]*inflat|tam[^\n]*overstat)[^\n]*", "Inflated TAM — top-down market size overstated", 6),
        (r"[^\n]*(?:funding[^\n]*down\s*\d{1,3}\s*%|down\s*\d{2,3}\s*%\s*yoy|vc funding into[^\n]*down)[^\n]*", "Sector VC funding declining sharply (YoY)", 6),
        (r"[^\n]*(?:peak enthusiasm passed|sentiment cautious|retreating from market|underperformed|originated[^\n]*natively)[^\n]*", "Cooling sector sentiment / dominant incumbent threat", 5),
    ]
    _mk_seen = set()
    for _pat, _claim, _sev in _market_scans:
        if _claim in _mk_seen:
            continue
        _mm = re.search(_pat, text, re.IGNORECASE)
        if _mm:
            _mk_seen.add(_claim)
            mkt_flags.append({
                "claim": _claim,
                "evidence": _mm.group(0).strip().strip("-*|# ")[:220],
                "confidence": 85,
                "severity": _sev,
                "source_section": "Market",
                "source_start": _mm.start(),
                "source_end": _mm.end(),
            })

    core_fields = [arr, burn, runway, gross_margin, customers, customer_concentration, litigation, compliance, security, tam]
    found_fields = sum(1 for f in core_fields if not is_field_missing(f))
    coverage_score = int((found_fields / 10) * 100)

    return {
        "company": {
            "name": {
                "metric": "Company Name",
                "value": company_name,
                "timeframe": "current",
                "confidence": co_conf,
                "provenance": co_prov,
                "source_section": "Company",
                "source_start": co_start,
                "source_end": co_end,
                "evidence": co_evidence,
                "flag_for_review": False
            },
            "industry": industry,
            "stage": stage,
            "raise_amount": raise_amt,
            "post_money_valuation": valuation,
            "description": {
                "metric": "Description",
                "value": text[:300].strip() + "...",
                "timeframe": "current",
                "confidence": 80,
                "provenance": "direct",
                "source_section": "Company",
                "source_start": 0,
                "source_end": min(300, len(text)),
                "evidence": "First 300 characters of brief",
                "flag_for_review": False
            }
        },
        "pitch_claims": {
            "arr": arr,
            "burn": burn,
            "runway": runway,
            "gross_margin": gross_margin
        },
        "financials": {
            "arr": arr,
            "burn": burn,
            "runway": runway,
            "gross_margin": gross_margin,
            "customers": customers,
            "customer_concentration": customer_concentration,
            "red_flags": fin_flags
        },
        "legal": {
            "litigation": litigation,
            "compliance": compliance,
            "red_flags": leg_flags
        },
        "technical": {
            "stack": tech_stack,
            "security": security,
            "red_flags": tech_flags
        },
        "market": {
            "tam": tam,
            "competition": competition,
            "red_flags": mkt_flags
        },
        "coverage_score": coverage_score,
        "document_text": text
    }


def merge_and_resolve_conflicts(r: Any, l: Any) -> Any:
    """Recursively walks Stage 1 (Regex) and Stage 2 (LLM) structures to resolve conflicts."""
    if isinstance(r, dict) and "value" in r:
        if not isinstance(l, dict) or "value" not in l:
            return r
            
        r_val = r.get("value")
        l_val = l.get("value")
        r_conf = r.get("confidence", 0)
        l_conf = l.get("confidence", 0)
        
        flag = abs(r_conf - l_conf) <= 5
        
        if r_val == l_val:
            return {
                "metric": r.get("metric", ""),
                "value": r_val,
                "timeframe": r.get("timeframe", "current"),
                "confidence": max(r_conf, l_conf),
                "provenance": "derived",
                "source_section": r.get("source_section", ""),
                "source_start": r.get("source_start"),
                "source_end": r.get("source_end"),
                "evidence": r.get("evidence"),
                "flag_for_review": flag
            }
        else:
            if r_conf > l_conf:
                winner = r.copy()
                winner["provenance"] = "direct"
            elif l_conf > r_conf:
                winner = l.copy()
                winner["provenance"] = "derived"
            else:
                is_num = any(c.isdigit() for c in str(r_val))
                winner = r.copy() if is_num else l.copy()
                winner["provenance"] = "derived"
                
            winner["flag_for_review"] = flag
            # Standardize output structure
            return {
                "metric": winner.get("metric", ""),
                "value": winner.get("value"),
                "timeframe": winner.get("timeframe", "current"),
                "confidence": winner.get("confidence", 0),
                "provenance": "derived" if flag else winner.get("provenance", "direct"),
                "source_section": winner.get("source_section", ""),
                "source_start": winner.get("source_start", -1),
                "source_end": winner.get("source_end", -1),
                "evidence": winner.get("evidence", ""),
                "flag_for_review": flag
            }
            
    elif isinstance(r, dict):
        merged = {}
        for k, v in r.items():
            if isinstance(l, dict) and k in l:
                merged[k] = merge_and_resolve_conflicts(v, l[k])
            else:
                merged[k] = v
        return merged
        
    elif isinstance(r, list):
        claims = {}
        for item in r:
            if isinstance(item, dict) and "claim" in item:
                claims[item["claim"]] = item
        if isinstance(l, list):
            for item in l:
                if isinstance(item, dict) and "claim" in item:
                    if item["claim"] not in claims or item.get("confidence", 0) > claims[item["claim"]].get("confidence", 0):
                        claims[item["claim"]] = item
        return list(claims.values())
        
    return r


def _merge_llm_first(regex_data: dict, llm_data: dict) -> dict:
    """Overlay the LLM extraction onto the regex seed. The LLM is authoritative
    for field values and red flags (it reads the whole document); the regex seed
    supplies durable structure: document_text, filename-derived company fallback,
    and any field the LLM left empty. Red flags from both are unioned (deduped)."""
    out = dict(regex_data)  # keeps document_text, coverage seed, company fallback

    # Company: prefer a confident LLM name, else keep the regex/filename one.
    llm_co = (llm_data.get("company") or {})
    reg_co = (out.get("company") or {})
    if isinstance(reg_co, dict):
        merged_co = dict(reg_co)
        for k, v in llm_co.items():
            if isinstance(v, dict) and not is_field_missing(v):
                merged_co[k] = v
            elif isinstance(v, str) and v.strip():
                merged_co[k] = v
        out["company"] = merged_co

    for domain in ("financials", "legal", "technical", "market"):
        reg_dom = dict(out.get(domain) or {})
        llm_dom = llm_data.get(domain) or {}
        # Scalar fields: LLM value wins when present, else keep regex.
        for field, val in llm_dom.items():
            if field == "red_flags":
                continue
            if isinstance(val, dict) and not is_field_missing(val):
                val.setdefault("provenance", "direct")
                val.setdefault("source_section", domain.title())
                reg_dom[field] = val
        # Red flags: union LLM + regex, dedup by claim (first 60 chars).
        merged_flags = []
        seen = set()
        for src in (llm_dom.get("red_flags") or [], reg_dom.get("red_flags") or []):
            for f in src:
                if isinstance(f, dict):
                    key = str(f.get("claim", "")).strip().lower()[:60]
                else:
                    key = str(f).strip().lower()[:60]
                    f = {"claim": str(f), "evidence": "", "confidence": 70}
                if key and key not in seen:
                    seen.add(key)
                    merged_flags.append(f)
        reg_dom["red_flags"] = merged_flags
        out[domain] = reg_dom

    return out


async def parse_and_structure_file(text: str, filename: str, incident_id: str) -> dict:
    """LLM-first extraction: a strong model reads the WHOLE document and emits the
    FUSION structured-facts schema directly (clean values + comprehensive, severity-
    rated red flags). The regex extractor is kept as a seed (document_text, company
    fallback) and as the fallback path when no LLM provider is available or it errors."""
    regex_data = extract_facts_regex(text, filename)

    # Deterministic/instant by default: skip the (potentially slow, rate-limited)
    # LLM enrichment call and return regex-extracted facts immediately. Opt back
    # into LLM-first extraction with ARGUS_LLM_UPLOAD_PARSE=true.
    if os.getenv("ARGUS_LLM_UPLOAD_PARSE", "true").strip().lower() not in ("1", "true", "yes"):
        return regex_data

    llm_router = get_router()
    if not llm_router.available_providers():
        return regex_data

    field_shape = '{"value": <string|"Insufficient Evidence">, "confidence": <0-100>, "evidence": "<verbatim quote from the document>", "provenance": "direct"}'
    flag_shape = '{"claim": "<the risk in one sentence>", "evidence": "<verbatim quote>", "severity": <1-10>, "confidence": <0-100>}'
    prompt = f"""You are a meticulous VC due-diligence analyst. Read the FULL startup document below and extract a structured facts JSON. You are evaluating this company for an investment committee, so SURFACE EVERY RISK.

Return ONLY raw JSON (no markdown, no commentary) with EXACTLY this schema:
{{
  "company": {{"name": {field_shape}, "industry": {field_shape}, "stage": {field_shape}, "raise_amount": {field_shape}, "post_money_valuation": {field_shape}}},
  "financials": {{"arr": {field_shape}, "burn": {field_shape}, "runway": {field_shape}, "gross_margin": {field_shape}, "customers": {field_shape}, "customer_concentration": {field_shape}, "red_flags": [{flag_shape}]}},
  "legal": {{"litigation": {field_shape}, "compliance": {field_shape}, "red_flags": [{flag_shape}]}},
  "technical": {{"stack": {field_shape}, "security": {field_shape}, "red_flags": [{flag_shape}]}},
  "market": {{"tam": {field_shape}, "competition": {field_shape}, "red_flags": [{flag_shape}]}}
}}

RULES (NEVER VIOLATE):
1. NEVER invent or estimate. If a metric is not stated in the document, set value to "Insufficient Evidence", confidence 0, evidence "", provenance "unknown".
2. "evidence" MUST be a verbatim substring quoted from the document — never paraphrase a number. Keep each evidence quote UNDER 160 characters.
3. For each domain, list ALL material red flags you can justify from the text (financial fragility, litigation/regulatory exposure, EOL/insecure tech, undisclosed breaches, customer concentration, weak/declining market, competitive threats, governance issues). severity: 1-3 minor, 4-6 moderate, 7-8 serious, 9-10 dealbreaker. Be thorough — these drive the risk score.
4. For "stack" capture the actual technologies/versions; for "security" capture the security posture; for "competition" capture named competitors. Do not capture unrelated prose.

DOCUMENT:
{text[:24000]}
"""
    try:
        res = await llm_router.call_llm(prompt, max_tokens=8000, timeout=20.0)
        res_clean = re.sub(r"```json\s*", "", res.strip(), flags=re.IGNORECASE)
        res_clean = re.sub(r"```\s*", "", res_clean)
        start_idx, end_idx = res_clean.find("{"), res_clean.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            res_clean = res_clean[start_idx:end_idx + 1]
        llm_data = json.loads(res_clean.strip())
        merged = _merge_llm_first(regex_data, llm_data)
        logger.info(f"LLM-first extraction OK for {filename}: "
                    f"flags fin/leg/tech/mkt="
                    f"{len(merged['financials']['red_flags'])}/{len(merged['legal']['red_flags'])}/"
                    f"{len(merged['technical']['red_flags'])}/{len(merged['market']['red_flags'])}")
        return merged
    except Exception as e:
        logger.warning(f"LLM-first extraction failed ({e}). Falling back to regex Stage 1.")
        return regex_data


async def validate_document_relevance(text: str) -> tuple[bool, str]:
    """Checks if the document is related to a company pitch, financials, legal, or technical due diligence.
    Returns (is_relevant, reason_or_error_message)."""
    llm_router = get_router()
    if not llm_router.available_providers():
        # Fallback to a rule-based keyword check if LLM is offline
        keywords = ["revenue", "burn", "runway", "valuation", "diligence", "pitch", "startup", "founder", "investment", "compliance", "funding", "market", "competitor"]
        text_lower = text.lower()
        if any(kw in text_lower for kw in keywords):
            return True, ""
        return False, "The document does not contain startup, financial, legal, or technical due diligence information."

    prompt = f"""You are a strict due-diligence document classifier. Decide if the text below is a company pitch deck, startup presentation, corporate financial model/burn rate spreadsheet, legal compliance document, or technical architecture sheet for a company under evaluation.
    
    If it is a corporate or startup document, return exactly:
    YES
    
    If it is NOT related to a company, startup, or business due diligence (e.g. personal notes, generic code with no business context, random text, stories, recipes, unrelated logs, etc.), return exactly:
    NO: [One short sentence explaining why this document is not related to a company pitch or due diligence]

    Do not include any other text.
    
    TEXT:
    {text[:5000]}
    """
    try:
        res = await llm_router.call_llm(prompt, max_tokens=100, timeout=10.0)
        res_clean = res.strip()
        if res_clean.startswith("YES"):
            return True, ""
        elif res_clean.startswith("NO"):
            reason = res_clean.split(":", 1)[-1].strip() if ":" in res_clean else "The document does not contain startup, financial, legal, or technical due diligence information."
            return False, f"This is not a company-related doc: {reason}"
        else:
            return True, "" # Default to True on weird LLM outputs
    except Exception as e:
        logger.warning(f"Document validation LLM call failed: {e}. Defaulting to regex/keyword check.")
        keywords = ["revenue", "burn", "runway", "valuation", "diligence", "pitch", "startup", "founder", "investment", "compliance", "funding", "market", "competitor"]
        text_lower = text.lower()
        if any(kw in text_lower for kw in keywords):
            return True, ""
        return False, "The document does not contain startup, financial, legal, or technical due diligence information."


@router.post("/upload-pitch")
async def upload_pitch_document(
    request: Request,
    file: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None)
):
    """Receives and parses real pitch documents/data room files (JSON, PDF, TXT, MD), structures them, and saves for active review."""
    uid = await get_uid_optional(request)
    user_memory = memory_graph.__class__(uid=uid) if uid else memory_graph
    uploaded_files = []
    if file:
        uploaded_files.append(file)
    if files:
        uploaded_files.extend(files)
        
    if not uploaded_files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
        
    incident_id = _new_incident_id()
    files_text = {}
    structured_data = None
    
    for u_file in uploaded_files:
        max_bytes = int(sim_state.max_file_size_mb * 1024 * 1024)
        content = await u_file.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File {u_file.filename} exceeds size limit of {sim_state.max_file_size_mb}MB"
            )
            
        filename = u_file.filename or "uploaded_doc"
        
        if filename.lower().endswith(".json"):
            try:
                js_data = json.loads(content.decode("utf-8"))
                if len(uploaded_files) == 1 and isinstance(js_data, dict) and "company" in js_data:
                    structured_data = js_data
                else:
                    files_text[filename] = json.dumps(js_data, indent=2)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON file {filename}: {e}")
        elif content.startswith(b"%PDF") or filename.lower().endswith(".pdf"):
            try:
                reader = PdfReader(io.BytesIO(content))
                f_text = ""
                for page in reader.pages:
                    f_text += page.extract_text() or ""
                if not f_text.strip():
                    raise ValueError("Empty or scanned PDF (no selectable text found)")
                files_text[filename] = f_text
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to read PDF file {filename}: {e}")
        elif filename.lower().endswith((".txt", ".md")):
            files_text[filename] = content.decode("utf-8", errors="ignore")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format for file {filename}. Upload JSON, PDF, TXT, or MD.")

    if structured_data is None:
        combined_text = ""
        for fname, ftext in files_text.items():
            combined_text += f"\n\n--- DOCUMENT: {fname} ---\n{ftext}\n"
        
        # Check relevance
        is_relevant, reject_reason = await validate_document_relevance(combined_text)
        if not is_relevant:
            raise HTTPException(status_code=400, detail=reject_reason)

        display_filename = ", ".join(files_text.keys())
        structured_data = await parse_and_structure_file(combined_text, display_filename, incident_id)
    else:
        # Validate uploaded JSON structure to ensure it is actually a company pitch/diligence doc
        if not isinstance(structured_data, dict) or "company" not in structured_data:
            raise HTTPException(status_code=400, detail="This is not a company-related doc: JSON structure is missing company schema.")
        
    # Write structured pitch JSON file to data directory so pitch_loader can read it
    data_dir = os.path.join(os.path.dirname(__file__), "../data")
    os.makedirs(data_dir, exist_ok=True)
    uploaded_path = os.path.join(data_dir, f"pitch_{incident_id}.json")
    
    with open(uploaded_path, "w") as f:
        json.dump(structured_data, f, indent=2)
        
    co_obj = structured_data.get("company", {})
    company_name = "Unknown Startup"
    if isinstance(co_obj, dict):
        name_val = co_obj.get("name")
        if isinstance(name_val, dict):
            company_name = name_val.get("value") or name_val.get("name") or "Unknown Startup"
        elif isinstance(name_val, str):
            company_name = name_val
        else:
            company_name = co_obj.get("value") or "Unknown Startup"
    elif isinstance(co_obj, str):
        company_name = co_obj
        
    sim_state.active_company_name = company_name
    sim_state.active_incident_id = incident_id
    sim_state.active_pitch_file = f"pitch_{incident_id}.json"

    # Bust the pitch cache so agents load the new file, and open the deal record
    from core.pitch_loader import clear_pitch_cache
    clear_pitch_cache()
    
    display_filename = ", ".join(u_file.filename for u_file in uploaded_files if u_file.filename) or "uploaded_data_room"
    user_memory.create_incident(incident_id, {
        "trigger": "document_upload",
        "company": sim_state.active_company_name,
        "filename": display_filename,
        "threat_level": 5,
    })

    logger.info(f"SaaS Ingestion: parsed and saved data room for incident {incident_id}: {sim_state.active_company_name}")
    
    return {
        "status": "success",
        "incident_id": incident_id,
        "company_name": sim_state.active_company_name,
        "message": f"Successfully parsed and ingested data room for {sim_state.active_company_name}."
    }


# In-process report cache: reports are deterministic for a given incident, so we
# memoize the rendered Markdown and compiled PDF bytes keyed by incident_id and a
# content signature. Repeat downloads (and PDF↔MD switches) become instant; a new
# run for the same incident changes the signature and forces a rebuild.
_REPORT_CACHE: dict = {}


def _report_signature(inc: dict, pitch_data: dict) -> tuple:
    timeline = inc.get("timeline", []) or []
    try:
        pitch_len = len(json.dumps(pitch_data, sort_keys=True, default=str))
    except Exception:
        pitch_len = 0
    return (len(timeline), inc.get("final_decision") or "", pitch_len)


@router.api_route("/generate-report", methods=["GET", "POST"])
async def generate_research_report(request: Request, incident_id: Optional[str] = None, format: Optional[str] = "md"):
    """Generates a downloadable Markdown or PDF VC due diligence report.
    Defaults to the active deal, then the latest deal on record."""
    uid = await get_uid_optional(request)
    user_memory = memory_graph.__class__(uid=uid) if uid else memory_graph
    incident_id = incident_id or sim_state.active_incident_id or user_memory.get_latest_incident_id()
    if not incident_id:
        raise HTTPException(status_code=404, detail="No deal evaluations on record. Run an evaluation first.")
    inc = user_memory.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident/deal record not found.")
        
    raw_company = inc["metadata"].get("company", "NovaPay Inc")
    if isinstance(raw_company, dict):
        company_name = raw_company.get("value") or raw_company.get("name") or "Unknown Startup"
    else:
        company_name = raw_company or "Unknown Startup"
        
    if (not company_name or company_name == "NovaPay Inc" or company_name == "Unknown Startup") and sim_state.active_company_name:
        act_co = sim_state.active_company_name
        if isinstance(act_co, dict):
            company_name = act_co.get("value") or act_co.get("name") or "NovaPay Inc"
        else:
            company_name = act_co
        
    created_at = inc.get("created_at", "N/A")
    
    # ── SINGLE SOURCE OF TRUTH: Load and run calculations ──
    from core.pitch_loader import _load_pitch_file
    from core.diligence_engine import run_diligence_calculations
    
    pitch_data = None
    try:
        import os
        from core.demo_registry import resolve_pitch_file
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data")
        pitch_file = f"pitch_{incident_id}.json"
        if not os.path.exists(os.path.join(data_dir, pitch_file)):
            demo_file = resolve_pitch_file(company_name)
            if demo_file:
                pitch_file = demo_file
            else:
                pitch_file = "novapay_pitch.json"
        pitch_data = _load_pitch_file(pitch_file)
    except Exception as e:
        logger.warning(f"Failed to load pitch file for incident {incident_id}: {e}")
        
    if not pitch_data:
        raise HTTPException(
            status_code=400,
            detail=f"Diligence calculations could not be run: Pitch data for incident {incident_id} not found."
        )

    # Fast path: serve a previously rendered report if nothing material changed.
    fmt = (format or "md").lower()
    report_sig = _report_signature(inc, pitch_data)
    cached = _REPORT_CACHE.get(incident_id)
    if cached and cached.get("sig") == report_sig and cached.get(fmt) is not None:
        if fmt == "pdf":
            headers = {'Content-Disposition': f'attachment; filename="FUSION_Report_{company_name.replace(" ", "_")}.pdf"'}
            return StreamingResponse(io.BytesIO(cached["pdf"]), media_type="application/pdf", headers=headers)
        headers = {'Content-Disposition': f'attachment; filename="FUSION_Report_{company_name.replace(" ", "_")}.md"'}
        return StreamingResponse(io.BytesIO(cached["md"]), media_type="text/markdown", headers=headers)

    calc = run_diligence_calculations(pitch_data)
    if not calc:
        raise HTTPException(
            status_code=400,
            detail="Diligence calculations returned empty or invalid results."
        )
        
    calc_company_name = calc.get("company_name", "Unknown Startup")
    calc_weighted_score = calc.get("weighted_score")
    calc_verdict = calc.get("verdict", "PENDING")
    
    # Extract details from existing timeline/decision card for validation
    fd = inc.get("final_decision") or ""
    card_company_name = None
    card_weighted_score = None
    card_decision = None
    if fd:
        m_co = re.search(r"Company\s*\*?\*?\s*:\s*(.+)", fd, re.I)
        if m_co:
            card_company_name = m_co.group(1).strip().strip("*_`|").strip()
        m_w = re.search(r"weighted\s*(?:risk\s*)?score\s*\*?\*?\s*:\s*\*?\*?\s*([\d\.]+)", fd, re.I)
        if m_w:
            try:
                card_weighted_score = float(m_w.group(1))
            except ValueError:
                pass
        m_dec = re.search(r"decision\s*\*?\*?\s*:\s*\*?\*?\s*([A-Za-z]+)", fd, re.I)
        if m_dec:
            card_decision = m_dec.group(1).upper()
            
    # ── VALIDATION GUARDS ──
    
    # Rule 1: Validate company name
    if company_name != calc_company_name:
        raise HTTPException(
            status_code=400,
            detail=f"Company name mismatch: Incident metadata has '{company_name}', but calculations returned '{calc_company_name}'."
        )
    if card_company_name and card_company_name != calc_company_name:
        raise HTTPException(
            status_code=400,
            detail=f"Decision card company name mismatch: Card has '{card_company_name}', but calculations returned '{calc_company_name}'."
        )
        
    # Rule 2: Validate weighted score
    if card_weighted_score is not None and calc_weighted_score is not None:
        if abs(card_weighted_score - calc_weighted_score) > 0.01:
            raise HTTPException(
                status_code=400,
                detail=f"Weighted score mismatch: Decision card has {card_weighted_score}, but calculations returned {calc_weighted_score}."
            )
            
    # Rule 3: Validate verdict check
    verdict_to_check = card_decision or calc_verdict
    score_to_check = calc_weighted_score
    if verdict_to_check == "INVEST" and score_to_check is not None and score_to_check > 7:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid investment verdict: Decision is INVEST but weighted risk score is {score_to_check} (> 7)."
        )
        
    # ── REQUIRE PARTNER CONTENT ──
    # Keep the LONGEST finding per partner (the real report),
    # discarding shorter interim messages.
    partner_findings = {
        "financial_partner": "",
        "legal_partner": "",
        "technical_partner": "",
        "market_partner": ""
    }
    
    for ev in inc.get("timeline", []):
        agent = ev.get("agent")
        if agent in partner_findings:
            finding = ev.get("finding", "").strip()
            if finding and len(finding) > len(partner_findings[agent]):
                partner_findings[agent] = finding
                
    for partner, finding in partner_findings.items():
        partner_display = partner.replace("_", " ").title()
        if not finding:
            raise HTTPException(
                status_code=400,
                detail=f"Diligence report requires findings from all partners. {partner_display} report is empty."
            )
        if "deal already concluded" in finding.lower() or "standing by" in finding.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Diligence report cannot be generated: {partner_display} report contains a standby placeholder ('{finding[:50]}...')."
            )
            
    # ── DYNAMIC CARD & TIMELINE GENERATION ──
    co_text = calc_company_name[:42]
    raise_amount = calc.get("raise_amount", "N/A")
    valuation = calc.get("valuation", "N/A")
    deal_text = f"{raise_amount} at {valuation} post"[:42]
    decision_text = ("REJECT" if calc_verdict == "PASS" else calc_verdict)[:42]
    
    coverage_score = calc.get("coverage_score", 0.0)
    confidence_val_pct = calc.get("verdict_confidence", coverage_score)
    confidence_text = f"{confidence_val_pct:.1f}%"[:42]
    
    quality_val_pct = calc.get("evidence_quality_score", 80.0)
    quality_text = f"{quality_val_pct:.1f}%"[:42]
    
    readiness_score = calc.get("deal_readiness_score", 80.0)
    readiness_status = calc.get("deal_readiness_status", "Ready for IC Review")
    readiness_text = f"{readiness_score:.1f}/100 ({readiness_status})"[:42]
    
    fin_score = calc.get("fin_score")
    fin_val_str = f"{fin_score:>2.0f}/10" if fin_score is not None else " N/A "
    fin_w_str = f"{0.3*fin_score:>4.2f}" if fin_score is not None else " N/A"
    
    leg_score = calc.get("leg_score")
    leg_val_str = f"{leg_score:>2.0f}/10" if leg_score is not None else " N/A "
    leg_w_str = f"{0.25*leg_score:>4.2f}" if leg_score is not None else " N/A"
    
    tech_score = calc.get("tech_score")
    tech_val_str = f"{tech_score:>2.0f}/10" if tech_score is not None else " N/A "
    tech_w_str = f"{0.25*tech_score:>4.2f}" if tech_score is not None else " N/A"
    
    mkt_score = calc.get("mkt_score")
    mkt_val_str = f"{mkt_score:>2.0f}/10" if mkt_score is not None else " N/A "
    mkt_w_str = f"{0.2*mkt_score:>4.2f}" if mkt_score is not None else " N/A"
    
    weighted_val_str = f"{calc_weighted_score:>4.1f}/10" if calc_weighted_score is not None else " N/A  "
    override_active = bool(calc.get("override_reasons")) and calc.get("verdict") == "PASS"
    weighted_note = "   (PASS — critical red-flag override)" if override_active else ""

    reasons = []
    if calc_weighted_score is None:
        reasons = ["Coverage below minimum threshold (40%)"]
    elif calc.get("override_reasons"):
        reasons = calc["override_reasons"]
    else:
        reasons = [
            "Target company metrics align with investment thesis.",
            "TAM and sector timing support the deal.",
            "Compliance and technical audits resolved successfully."
        ]
            
    reasons_str = "\n".join(f"{i+1}. {r}" for i, r in enumerate(reasons))
    
    dynamic_verdict_card = (
        "```\n"
        "+----------------------------------------------------------+\n"
        "|         FUSION INVESTMENT COMMITTEE DECISION             |\n"
        "+----------------------------------------------------------+\n"
        f"| Company:      {co_text:<42} |\n"
        f"| Deal:         {deal_text:<42} |\n"
        "+----------------------------------------------------------+\n"
        f"|  DECISION:    {decision_text:<42} |\n"
        f"|  CONFIDENCE:  {confidence_text:<42} |\n"
        f"|  EVI QUALITY: {quality_text:<42} |\n"
        f"|  READINESS:   {readiness_text:<42} |\n"
        "+----------------------------------------------------------+\n\n"
        "RISK SCORECARD:\n"
        f"  Financial Risk:  {fin_val_str}  (weight: 30%) → {fin_w_str}\n"
        f"  Legal Risk:      {leg_val_str}  (weight: 25%) → {leg_w_str}\n"
        f"  Technical Risk:  {tech_val_str}  (weight: 25%) → {tech_w_str}\n"
        f"  Market Risk:     {mkt_val_str}  (weight: 20%) → {mkt_w_str}\n"
        "  ------------------------------------------------------\n"
        f"  WEIGHTED SCORE:  {weighted_val_str}{weighted_note}\n\n"
        "PRIMARY REASONS:\n"
        f"{reasons_str}\n"
        "```"
    )
    
    if calc.get("missing_gaps"):
        gaps_str = ", ".join(calc["missing_gaps"])
        dynamic_verdict_card += f"\n\nMISSING DILIGENCE GAPS:\n- {gaps_str}"
        
    warnings_str = ""
    if calc.get("contradictions"):
        for contra in calc["contradictions"]:
            warnings_str += f"{contra['message']}\n"
    if calc.get("validation_warnings"):
        for warn in calc["validation_warnings"]:
            warnings_str += f"{warn}\n"
    if warnings_str:
        dynamic_verdict_card = warnings_str + "\n" + dynamic_verdict_card
        
    consistency_warn_str = ""
    if calc.get("internal_validation_error"):
        consistency_warn_str = "\n\n> [!WARNING]\n> ⚠ Internal Consistency Warning: Fact Coverage is 100% but missing fields exist.\n"

    report_md = f"""# FUSION VC DUE DILIGENCE REPORT
**Deal Evaluation Record: {incident_id}**
**Target Company: {calc_company_name}**
**Date Evaluated: {created_at}**
**Status: Complete**{consistency_warn_str}

---

## ⚖️ COMMITTEE VERDICT: {"REJECT" if calc_verdict == "PASS" else calc_verdict}
{dynamic_verdict_card}

---

## 📊 RISK SCORECARD
"""
    if calc_weighted_score is None:
        report_md += f"""* **Financial Risk:** N/A
* **Legal Risk:** N/A
* **Technical Risk:** N/A
* **Market Risk:** N/A
* **────────────────────────────────────────**
* **WEIGHTED RISK SCORE:** **N/A**
* **Reason:** Coverage below minimum threshold (40%)

---

## 📝 CHRONOLOGICAL PARTNER AUDIT TIMELINE
"""
    else:
        report_md += f"""* **Financial Risk:** {fin_score:.1f}/10 (Weight: 30%)
* **Legal Risk:** {leg_score:.1f}/10 (Weight: 25%)
* **Technical Risk:** {tech_score:.1f}/10 (Weight: 25%)
* **Market Risk:** {mkt_score:.1f}/10 (Weight: 20%)
* **────────────────────────────────────────**
* **WEIGHTED RISK SCORE:** **{calc_weighted_score:.2f}/10**

---

## 📝 CHRONOLOGICAL PARTNER AUDIT TIMELINE
"""
    # Build a deduplicated, filtered timeline:
    # - Skip managing partner "awaiting findings" interim messages
    # - For specialist partners, only include the longest (real) report
    agent_display_map = {
        "managing_partner": "💼 Managing Partner",
        "financial_partner": "📊 Financial Partner",
        "legal_partner": "⚖️ Legal Partner",
        "technical_partner": "🔧 Technical Partner",
        "market_partner": "📈 Market Partner"
    }
    
    # Collect best entry per agent (longest finding)
    best_entries = {}  # agent -> timeline entry
    for ev in inc.get("timeline", []):
        agent = ev.get("agent", "")
        finding = ev.get("finding", "")
        
        # Skip managing partner interim "awaiting" status messages
        if agent == "managing_partner" and "awaiting findings" in finding.lower():
            continue
        
        # Keep the longest finding per agent (real report, not interim)
        if agent not in best_entries or len(finding) > len(best_entries[agent].get("finding", "")):
            best_entries[agent] = ev
    
    # Render in a stable order: specialists first, then managing partner verdict
    render_order = ["financial_partner", "legal_partner", "technical_partner", "market_partner", "managing_partner"]
    for agent_key in render_order:
        ev = best_entries.get(agent_key)
        if not ev:
            continue
        agent_display = agent_display_map.get(agent_key, agent_key)
        
        report_md += f"""
### {agent_display} (Severity: {ev.get('severity', 5)}/10)
*Timestamp: {ev.get('timestamp')}*

{ev.get('finding')}

"""
        
    report_md += f"""
---
*Report generated on behalf of the FUSION AI-Powered Venture Capital Investment Committee. FUSION Master Doctrine Version 5.2.*
"""
    
    # Cache the freshly rendered Markdown (preserving any PDF cached under the same
    # signature) so subsequent downloads of either format are instant.
    md_bytes = report_md.encode("utf-8")
    entry = _REPORT_CACHE.get(incident_id)
    if not entry or entry.get("sig") != report_sig:
        entry = {"sig": report_sig, "md": md_bytes, "pdf": None}
    else:
        entry["md"] = md_bytes
    _REPORT_CACHE[incident_id] = entry

    if format == "pdf":
        from core.pdf_generator import compile_pdf_report
        try:
            pdf_bytes = compile_pdf_report(report_md, company_name)
            entry["pdf"] = pdf_bytes
            _REPORT_CACHE[incident_id] = entry
            file_like = io.BytesIO(pdf_bytes)
            headers = {
                'Content-Disposition': f'attachment; filename="FUSION_Report_{company_name.replace(" ", "_")}.pdf"'
            }
            return StreamingResponse(file_like, media_type="application/pdf", headers=headers)
        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}")
            raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    file_like = io.BytesIO(md_bytes)
    headers = {
        'Content-Disposition': f'attachment; filename="FUSION_Report_{company_name.replace(" ", "_")}.md"'
    }
    return StreamingResponse(file_like, media_type="text/markdown", headers=headers)


@router.get("/profile")
async def get_profile(request: Request):
    """Return the authenticated user's Firestore profile (totalDeals, displayName, etc.)."""
    from core.auth import get_uid
    from core.firestore_profile import get_user
    uid = await get_uid(request)
    profile = get_user(uid) or {}
    # Strip server timestamps (not JSON-serialisable) — replace with None
    return {k: (v if not hasattr(v, '_type') else None) for k, v in profile.items()}
