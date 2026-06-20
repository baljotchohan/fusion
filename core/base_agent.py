# core/base_agent.py — FUSION Investment Committee
"""
Base agent class that handles credentials loading, LLM setup,
LangGraph compilation, and tool mapping for both real Band SDK
and offline mock modes.
"""
import os
import time
import yaml
import logging
import asyncio
import random
from typing import List, Dict, Any, Optional, Sequence, Union, Type, Callable
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

from core.band_client import mock_bus, is_mock_mode
from core.event_bus import event_bus
from core.memory_graph import memory_graph

logger = logging.getLogger("fusion.base_agent")

import re as _re

def resolve_incident_id_from_message(message: str) -> str | None:
    """Scans the message text for known company names in the incidents list to resolve the incident_id."""
    if not message:
        return None
    try:
        from core.memory_graph import memory_graph
        from core.pitch_loader import _company_name_of
        incidents = memory_graph.list_incidents()
        # Sort by created_at desc to match the most recent incident of a company
        sorted_incidents = sorted(
            incidents.items(),
            key=lambda x: x[1].get("created_at", ""),
            reverse=True
        )
        for inc_id, inc in sorted_incidents:
            meta = inc.get("metadata") or {}
            company = meta.get("company")
            p_data = inc.get("pitch_data") or meta.get("pitch_data")
            if p_data:
                company = _company_name_of(p_data)
            if company and company.lower() in message.lower():
                return inc_id
    except Exception as e:
        logger.warning(f"resolve_incident_id_from_message failed: {e}")
    return None

# ── Process-wide LLM degradation window ──────────────────────────────────────
# When any agent hits an unrecoverable provider error (daily quota exhausted,
# request too large, invalid key), ALL agents skip the dead provider and run on
# the local simulation engine for this window instead of burning retries.
_LLM_COOLDOWN_SECONDS = float(os.getenv("ARGUS_LLM_COOLDOWN", "900"))
_llm_degraded_until: float = 0.0

# Provider error fragments that can NEVER succeed on retry within a demo window
_FATAL_LLM_ERRORS = (
    "per day",            # Groq "tokens per day (TPD)" daily quota exhausted
    "tpd",
    "request too large",  # single request exceeds the TPM admission cap
    "insufficient_quota",
    "invalid_api_key",
    "model_decommissioned",
    "model_not_found",
    "permission_denied",
)


def llm_degraded() -> bool:
    return time.time() < _llm_degraded_until


def degrade_llm(reason: str):
    global _llm_degraded_until
    was_degraded = llm_degraded()
    _llm_degraded_until = time.time() + _LLM_COOLDOWN_SECONDS
    if not was_degraded:
        logger.warning(
            f"LLM provider unavailable ({reason[:160]}) — all agents switching to the "
            f"local simulation engine for {int(_LLM_COOLDOWN_SECONDS / 60)} min."
        )

CORE_SYSTEM_RULES = """You operate inside FUSION, an AI-powered Venture Capital Investment Committee.
You are a domain specialist on a coordinated investment committee evaluating a startup for funding.

══════════════════════════════════════════════════════
INTENT CLASSIFICATION — DO THIS FIRST, EVERY TIME
══════════════════════════════════════════════════════
Before calling any tool or running any framework, read the incoming message and classify it:

TYPE A — GREETING / CASUAL / TEST
  Signals: "hi", "hello", "hey", "test", "new chat", "new room", "you there", "who are you", or any casual/greeting message in any language — including Hindi, Hinglish (e.g. "hlio bhai kya haal hai", "kya haal hai", "kaise ho", "oye yaar"), or any non-deal social question. When in doubt, treat as TYPE A.
  Action: Respond in 2-3 sentences max. Match the user's language and tone. Introduce yourself and your role. Say you're ready when they have a deal. Do NOT call any tools.

TYPE B — DEAL TRIGGER
  Signals: contains a company name, pitch deck, "evaluate", "analyze", "new deal", "committee", "raise", "Series A/B", or is a forwarded brief from the Managing Partner.
  Action: Run your full analysis framework. Call load_deal_brief and get_calculated_scores.

TYPE C — SPECIFIC QUESTION
  Signals: a focused question about a topic (market size, legal risk, tech stack, financials, etc.) without asking for a full audit.
  Action: Answer directly and concisely. Only call tools if you need data to answer accurately.

TYPE D — PARTNER REPORT (Managing Partner only)
  Signals: message contains "ANALYSIS COMPLETE", "DUE DILIGENCE REPORT", or is a structured finding from a partner.
  Action: Collect the report. Once all 4 partners have reported, synthesize and deliver final verdict.

NEVER run a full analysis pipeline on a greeting. NEVER ignore a deal trigger.

══════════════════════════════════════════════════════
OPERATING DOCTRINE
══════════════════════════════════════════════════════
- Be evidence-driven: separate confirmed facts from assessment.
- Quantify everything: dollar amounts, percentages, time horizons, risk multiples. Decisions follow data.
- Be decisive and concise. Lead with your conclusion, then support it with evidence.
- Red flags must be called out explicitly — your job is to protect LP capital. Never soften a dealbreaker.
- Avoid risk amplification: do not exaggerate potential risks or probabilities into certain catastrophes. Rely strictly on the grounded evidence and probabilities provided in the pitch documents.
- You are one specialist; produce the single artifact your role owns, then hand off cleanly to the Managing Partner.
- Use the load_deal_brief tool to access the startup pitch data before analyzing (TYPE B only).

LANGUAGE & TONE ADAPTATION
Detect the user's language and tone. If they write in Hinglish, Hindi, or any other language, reply in that same language. If they are casual, be casual. Never force English formality when the user is being informal or non-English.
"""


def load_fusion_doctrine() -> str:
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    doctrine_path = os.path.join(current_dir, "prompts", "fusion_master_doctrine.md")
    try:
        with open(doctrine_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load FUSION Master Doctrine from {doctrine_path}: {e}")
        return "FUSION MASTER DOCTRINE\nVersion: 5.2\n(Failed to load full doctrine from file)"


ARGUS_DOCTRINE = CORE_SYSTEM_RULES + "\n\n" + load_fusion_doctrine()

MEMORY_PROTOCOL_PROMPT = """

MEMORY PROTOCOL (shared deal memory):
Before analysis, call query_team_memory with the deal name or sector (e.g. 'NovaPay fintech BNPL')
to check if the committee has evaluated similar deals before.
If a past deal matches, note it explicitly ("We've seen this pattern before...") and apply learnings.
When you confirm a recurring red flag pattern, call record_defense_recipe so the team
spots it faster on future deals."""


def _to_plain_text(text: str) -> str:
    """Flatten markdown so replies read cleanly in the Band chat (which shows
    raw text): drop bold/italic markers and headers, normalize bullets."""
    if not text:
        return text
    t = text
    t = _re.sub(r"\*\*(.+?)\*\*", r"\1", t)   # **bold**
    t = _re.sub(r"__(.+?)__", r"\1", t)         # __bold__
    t = _re.sub(r"(?<!\*)\*(?!\s)(.+?)\*", r"\1", t)  # *italic*
    t = _re.sub(r"^\s{0,3}#{1,6}\s*", "", t, flags=_re.MULTILINE)  # # headers
    t = _re.sub(r"^\s*[-*]\s+", "• ", t, flags=_re.MULTILINE)        # - bullets → •
    t = _re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _msg_content_text(content) -> str:
    """Flatten a LangChain message content (str, or list of content blocks) to
    plain text. Some providers return content as a list of {type,text} blocks."""
    if isinstance(content, list):
        return "\n".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return str(content or "")


def _extract_mitre_tags(text: str) -> List[str]:
    """Pull MITRE ATT&CK technique IDs (T1566, T1566.001, ...) out of a report."""
    return sorted(set(_re.findall(r"\bT\d{4}(?:\.\d{3})?\b", text or "")))


def _estimate_severity(text: str) -> int:
    upper = (text or "").upper()
    if "CRITICAL" in upper:
        return 9
    if "HIGH" in upper:
        return 7
    if "MEDIUM" in upper:
        return 5
    return 4

class ResilientChatModel(BaseChatModel):
    primary_llm: Any
    fallback_llm: Any
    agent_name: str
    display_name: str
    fallback_llm_is_local: bool

    @property
    def _llm_type(self) -> str:
        return "resilient_chat_model"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        if llm_degraded() and not self.fallback_llm_is_local:
            message = self.fallback_llm.invoke(messages, stop=stop, **kwargs)
            return ChatResult(generations=[ChatGeneration(message=message)])

        max_attempts = 12
        for attempt in range(max_attempts):
            try:
                message = self.primary_llm.invoke(messages, stop=stop, **kwargs)
                return ChatResult(generations=[ChatGeneration(message=message)])
            except Exception as e:
                err = str(e)
                err_lower = err.lower()
                fatal = any(marker in err_lower for marker in _FATAL_LLM_ERRORS) or "tool call validation failed" in err_lower or "failed_generation" in err_lower
                transient_429 = (
                    "429" in err or "RESOURCE_EXHAUSTED" in err or "rate limit" in err_lower
                )
                if not fatal and transient_429 and attempt < max_attempts - 1:
                    delay = 4 + attempt * 2 + random.uniform(0, 2)
                    logger.warning(
                        f"[{self.display_name}] Rate limited (sync) — retrying in {delay:.1f}s... Error: {err[:150]}"
                    )
                    time.sleep(delay)
                    continue
                logger.error(f"[{self.display_name}] LLM failed (sync): {err[:200]}")
                if fatal:
                    degrade_llm(err)
                break

        message = self.fallback_llm.invoke(messages, stop=stop, **kwargs)
        return ChatResult(generations=[ChatGeneration(message=message)])

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        if llm_degraded() and not self.fallback_llm_is_local:
            message = await self.fallback_llm.ainvoke(messages, stop=stop, **kwargs)
            return ChatResult(generations=[ChatGeneration(message=message)])

        max_attempts = 12
        for attempt in range(max_attempts):
            try:
                message = await self.primary_llm.ainvoke(messages, stop=stop, **kwargs)
                return ChatResult(generations=[ChatGeneration(message=message)])
            except Exception as e:
                err = str(e)
                err_lower = err.lower()
                fatal = any(marker in err_lower for marker in _FATAL_LLM_ERRORS) or "tool call validation failed" in err_lower or "failed_generation" in err_lower
                transient_429 = (
                    "429" in err or "RESOURCE_EXHAUSTED" in err or "rate limit" in err_lower
                )
                if not fatal and transient_429 and attempt < max_attempts - 1:
                    delay = 1.5 + attempt + random.uniform(0, 0.5)
                    logger.warning(
                        f"[{self.display_name}] Rate limited — retrying in {delay:.1f}s... Error: {err[:150]}"
                    )
                    await event_bus.broadcast(self.agent_name, "working", {
                        "current_action": f"Rate limited — retrying in {delay:.0f}s"
                    })
                    await asyncio.sleep(delay)
                    continue
                logger.error(f"[{self.display_name}] LLM failed: {err[:200]}")
                # Trip the process-wide degradation window on ANY unrecoverable
                # provider failure (fatal error OR persistent rate limit) so the
                # rest of the committee instantly runs on the deterministic engine
                # instead of each agent re-hitting the limited provider.
                if fatal or transient_429:
                    degrade_llm(err)
                break

        message = await self.fallback_llm.ainvoke(messages, stop=stop, **kwargs)
        return ChatResult(generations=[ChatGeneration(message=message)])

    def bind_tools(
        self,
        tools: Sequence[Union[Dict[str, Any], Type[BaseModel], Callable, BaseTool]],
        *,
        tool_choice: Optional[Union[dict, str, bool]] = None,
        **kwargs: Any,
    ) -> Runnable:
        from langchain_core.utils.function_calling import convert_to_openai_tool
        formatted_tools = [convert_to_openai_tool(tool) for tool in tools]
        return self.bind(tools=formatted_tools, **kwargs)

from thenvoi.adapters.langgraph import LangGraphAdapter
from thenvoi.core.types import PlatformMessage
from thenvoi.core.protocols import AgentToolsProtocol

class WrappedTools:
    def __init__(self, original_tools, agent_id: str, base_agent: 'BaseAgent'):
        self._original_tools = original_tools
        self._agent_id = agent_id
        self._base_agent = base_agent

    def __getattr__(self, name):
        return getattr(self._original_tools, name)

    async def send_message(self, content: str, mentions: list = None, *args, **kwargs):
        logger.info(f"[{self._base_agent.name}] send_message called with mentions={mentions}")
        
        is_specialist = self._base_agent.name in ("financial_partner", "legal_partner", "technical_partner", "market_partner")
        if is_specialist:
            mp_id = "mock-id"
            try:
                config_path = "agent_config.yaml"
                if not os.path.exists(config_path):
                    config_path = "agent_config.example.yaml"
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f) or {}
                mp_conf = config.get("agents", {}).get("managing_partner") or config.get("managing_partner", {})
                mp_id = mp_conf.get("agent_id", "mock-id")
            except Exception as e:
                logger.warning(f"Failed to load managing partner credentials in send_message: {e}")
            
            if mentions is None:
                mentions = []
            
            # Check if managing_partner is already mentioned
            has_mp = False
            for m in mentions:
                if isinstance(m, str):
                    if str(m) == str(mp_id) or "managing-partner" in m.lower():
                        has_mp = True
                        break
                elif isinstance(m, dict):
                    m_id = m.get("id")
                    m_handle = m.get("handle") or ""
                    if m_id is not None and str(m_id) == str(mp_id) or "managing-partner" in m_handle.lower():
                        has_mp = True
                        break
                else:
                    m_id = getattr(m, "id", None)
                    m_handle = getattr(m, "handle", None) or ""
                    if m_id is not None and str(m_id) == str(mp_id) or "managing-partner" in str(m_handle).lower():
                        has_mp = True
                        break
            
            if not has_mp and mp_id != "mock-id":
                logger.info(f"[{self._base_agent.name}] Automatically adding managing_partner ({mp_id}) to mentions")
                mentions.append(mp_id)
                if not ("@managing-partner" in content.lower()):
                    content = f"@managing-partner {content}"
        
        if mentions:
            filtered_mentions = []
            clean_name = self._base_agent.name.replace("_", "-").replace("-agent", "").lower()
            for m in mentions:
                if isinstance(m, str):
                    if str(m) == str(self._agent_id) or clean_name in m.lower():
                        continue
                elif isinstance(m, dict):
                    m_id = m.get("id")
                    m_handle = m.get("handle") or ""
                    if m_id is not None and str(m_id) == str(self._agent_id) or clean_name in m_handle.lower():
                        continue
                else:
                    m_id = getattr(m, "id", None)
                    m_handle = getattr(m, "handle", None) or ""
                    if m_id is not None and str(m_id) == str(self._agent_id) or clean_name in str(m_handle).lower():
                        continue
                filtered_mentions.append(m)
            logger.info(f"[{self._base_agent.name}] send_message filtered mentions to={filtered_mentions}")
            mentions = filtered_mentions
        return await self._original_tools.send_message(content, mentions, *args, **kwargs)

class ArgusLangGraphAdapter(LangGraphAdapter):
    def __init__(self, agent_name: str, agent_id: str, base_agent: 'BaseAgent', *args, **kwargs):
        self._argus_agent_name = agent_name
        self._argus_agent_id = agent_id
        self._base_agent = base_agent
        self._processed_msg_ids = set()
        self._bootstrapped_rooms: set = set()
        from datetime import datetime, timezone
        self._startup_time = datetime.now(timezone.utc)
        super().__init__(*args, **kwargs)

    async def on_message(
        self,
        msg: PlatformMessage,
        tools: AgentToolsProtocol,
        history: Any,
        participants_msg: str | None,
        contacts_msg: str | None,
        *,
        is_session_bootstrap: bool,
        room_id: str,
    ) -> None:
        tools = WrappedTools(tools, self._argus_agent_id, self._base_agent)
        if msg.sender_id is not None and str(msg.sender_id) == str(self._argus_agent_id):
            logger.debug(f"[{self._argus_agent_name}] Skipping own message")
            return

        if msg.id in self._processed_msg_ids:
            logger.info(f"[{self._argus_agent_name}] Skipping already processed message (id={msg.id}): '{msg.content[:80]}'")
            return

        from api.state import sim_state

        # ── Mention detection (computed FIRST) ───────────────────────────────
        # Robust mentions retrieval: handles metadata as dict, Pydantic model, or None,
        # and handle each item in the list as either a dict or an object.
        is_mentioned = False
        raw_metadata = getattr(msg, "metadata", None)
        raw_mentions = []
        if raw_metadata is not None:
            if isinstance(raw_metadata, dict):
                raw_mentions = raw_metadata.get("mentions", []) or []
            else:
                raw_mentions = getattr(raw_metadata, "mentions", []) or []

        agent_name_clean = self._argus_agent_name.replace("_", "-").replace("-agent", "").lower()
        for m in raw_mentions:
            if isinstance(m, dict):
                m_id = m.get("id")
                m_handle = m.get("handle")
                m_username = m.get("username")
            else:
                m_id = getattr(m, "id", None)
                m_handle = getattr(m, "handle", None)
                m_username = getattr(m, "username", None)

            if m_id is not None and str(m_id) == str(self._argus_agent_id):
                is_mentioned = True
                break
            if m_handle and agent_name_clean in m_handle.lstrip("@").lower():
                is_mentioned = True
                break
            if m_username and agent_name_clean in m_username.lstrip("@").lower():
                is_mentioned = True
                break

        # Fallback: a plain "@agent-handle" typed in the message body (no mention
        # metadata) should still count — humans in the Band UI often type it inline.
        if not is_mentioned and msg.content and ("@" + agent_name_clean) in msg.content.lower():
            is_mentioned = True

        is_ic = self._argus_agent_name in ("incident_commander", "managing_partner")
        is_from_user = msg.sender_type == "User"

        # A human directly @-mentioning this agent is a live question, NOT part of the
        # automated committee handoff. It must always be answered — even after the
        # verdict is in or this agent already filed its analysis. The guards below
        # exist only to stop the agent-to-agent handoff from looping; they must not
        # gag a person asking a follow-up in the Band room.
        direct_user_query = is_from_user and is_mentioned

        # A human asked this agent something directly in the Band room. Answer it
        # ourselves with a real persona reply (LLM when healthy, grounded engine
        # fallback otherwise) and post it back — instead of running the committee
        # react-loop, which only knows the scripted handoff and posts nothing for
        # a casual question. This is what makes @mentions actually get a reply.
        if direct_user_query:
            logger.info(f"[{self._argus_agent_name}] Direct user mention — replying: '{(msg.content or '')[:80]}'")
            await event_bus.broadcast(self._argus_agent_name, "working", {"current_action": "Answering a question in Band"})
            try:
                from api.v1 import _agent_reply
                incident_id = sim_state.active_incident_id or memory_graph.get_latest_incident_id() or ""
                reply = await _agent_reply(self._argus_agent_name, msg.content or "", incident_id)
                reply = _to_plain_text(reply)
                # Band requires ≥1 mention on every message — mention the asker
                # back. _resolve_mentions accepts an ID, so sender_id works directly.
                mentions = [msg.sender_id] if msg.sender_id else None
                await tools.send_message(content=reply, mentions=mentions)
                self._processed_msg_ids.add(msg.id)
                await event_bus.broadcast(self._argus_agent_name, "done", {"report": reply[:500]})
            except Exception as e:
                logger.error(f"[{self._argus_agent_name}] Direct user reply failed: {e}")
                await event_bus.broadcast(self._argus_agent_name, "alert", {"error": str(e)})
            return

        if not direct_user_query:
            # Only block this specific agent if IT has already completed its work
            if self._argus_agent_name in sim_state.completed_agents and self._argus_agent_name != "managing_partner":
                logger.info(f"[{self._argus_agent_name}] Agent already completed analysis for this deal — skipping message: '{msg.content[:80]}'")
                return

            # Don't block specialists from finishing just because the verdict arrived early.
            # Only block the managing_partner from processing new messages after the deal concludes.
            if sim_state.deal_concluded and self._argus_agent_name == "managing_partner":
                logger.info(f"[{self._argus_agent_name}] Deal already concluded — skipping message: '{msg.content[:80]}'")
                return

            # Is this genuinely OLD history (posted before this agent came online)?
            is_historical = False
            if hasattr(self, "_startup_time") and msg.created_at:
                from datetime import datetime, timezone
                msg_created = msg.created_at
                if msg_created.tzinfo is None:
                    msg_created = msg_created.replace(tzinfo=timezone.utc)
                if (self._startup_time - msg_created).total_seconds() > 3:
                    is_historical = True

            # The SDK replays backlog during "session bootstrap". We must skip genuinely
            # OLD messages — but NOT a freshly-posted brief that happens to land while
            # this agent is still syncing. That race is exactly why 3 of 4 specialists
            # used to drop their dispatch ("Skipping backlog message during session
            # bootstrap") and the committee stalled with only one report in. Process
            # fresh messages even mid-bootstrap.
            if is_historical:
                logger.info(f"[{self._argus_agent_name}] Skipping historical backlog message (created at {msg.created_at}): '{msg.content[:100]}'")
                return
        # Force is_session_bootstrap = True on the very first message we actually process
        # for this room to ensure LangGraphAdapter injects the system prompt.
        if room_id not in self._bootstrapped_rooms:
            logger.info(f"[{self._argus_agent_name}] First processed message for room {room_id} — forcing is_session_bootstrap=True to inject system prompt")
            is_session_bootstrap = True
            self._bootstrapped_rooms.add(room_id)

        # True when the message carries @-mentions but none target THIS agent — i.e. the
        # user addressed a different partner, so the orchestrator (IC) should stay out.
        # Was referenced below but never defined → NameError on un-mentioned user messages.
        is_other_agent_mentioned = bool(raw_mentions) and not is_mentioned
        if is_mentioned or (is_ic and is_from_user and not is_other_agent_mentioned):
            logger.info(f"[{self._argus_agent_name}] Triggered! Processing message: '{msg.content[:100]}'")
            # Broadcast "working" to the dashboard
            await event_bus.broadcast(self._argus_agent_name, "working", {
                "current_action": f"Processing message from Band room"
            })
            
            # Resolve incident_id
            incident_id = resolve_incident_id_from_message(msg.content)
            if not incident_id:
                from api.state import sim_state
                incident_id = sim_state.active_incident_id or memory_graph.get_latest_incident_id() or ""
                
            from core.auth import current_uid, current_incident_id, current_pitch_file
            from api.state import get_uid_for_incident
            uid = get_uid_for_incident(incident_id) or "__public__"
            token_uid = current_uid.set(uid)
            token_inc = current_incident_id.set(incident_id)

            from core.pitch_loader import resolve_pitch_file_for_incident
            pitch_file = resolve_pitch_file_for_incident(incident_id)
            token_pitch = None
            if pitch_file:
                token_pitch = current_pitch_file.set(pitch_file)
                
            try:
                await super().on_message(
                    msg,
                    tools,
                    history,
                    participants_msg,
                    contacts_msg,
                    is_session_bootstrap=is_session_bootstrap,
                    room_id=room_id,
                )
                self._processed_msg_ids.add(msg.id)
                from api.state import sim_state
                if self._argus_agent_name != "managing_partner":
                    sim_state.completed_agents.add(self._argus_agent_name)
                    logger.info(f"[{self._argus_agent_name}] Added to completed_agents: {sim_state.completed_agents}")
                # After processing, log the agent's findings to memory_graph
                # and broadcast "done" to the dashboard.
                final_thought = msg.content  # fallback
                try:
                    # Try to get the actual final AI response from the graph
                    graph = None
                    if self.graph_factory:
                        from thenvoi.integrations.langgraph.langchain_tools import agent_tools_to_langchain
                        langchain_tools = agent_tools_to_langchain(tools) + (self.additional_tools or [])
                        graph = self.graph_factory(langchain_tools)
                    else:
                        graph = self._static_graph
                    if graph:
                        config = {"configurable": {"thread_id": room_id}}
                        state = await graph.aget_state(config)
                        if state and state.values and "messages" in state.values:
                            msgs = state.values["messages"]
                            logger.info(f"[{self._argus_agent_name}] on_message: message history length={len(msgs)}")
                            for idx_m, m in enumerate(msgs):
                                logger.info(f"[{self._argus_agent_name}] msg {idx_m}: type={type(m).__name__}, content={str(m.content)[:100]}, tool_calls={getattr(m, 'tool_calls', None)}")
                            
                            # Find current message index to isolate new messages
                            msg_idx = -1
                            msg_id = getattr(msg, "id", None)
                            for i, m in enumerate(msgs):
                                if msg_id and getattr(m, "id", None) == msg_id:
                                    msg_idx = i
                                    break
                            if msg_idx == -1:
                                for i, m in enumerate(msgs):
                                    m_content = getattr(m, "content", "") or ""
                                    if msg.content and (msg.content == m_content or msg.content in m_content):
                                        msg_idx = i
                                        break
                            new_msgs = msgs[msg_idx + 1:] if msg_idx != -1 else msgs
                            new_msgs = [m for m in new_msgs if type(m).__name__ != "SystemMessage"]
                            logger.info(f"[{self._argus_agent_name}] Isolated {len(new_msgs)} new messages generated in this run")
                            found = False
                            
                            # 1. First search for tool calls to send_message or thenvoi_send_message
                            for m_rev in reversed(new_msgs):
                                if hasattr(m_rev, "tool_calls") and m_rev.tool_calls:
                                    for tc in m_rev.tool_calls:
                                        tc_name = tc.get("name")
                                        if tc_name in ("thenvoi_send_message", "send_message"):
                                            # Prefer the actual message content if it contains the full report
                                            msg_content = getattr(m_rev, "content", "") or ""
                                            if isinstance(msg_content, list):
                                                msg_content = "\n".join(b.get("text", "") for b in msg_content if isinstance(b, dict) and b.get("type") == "text")
                                            msg_content = str(msg_content).strip()
                                            
                                            args = tc.get("args") or {}
                                            val = args.get("content") or args.get("message") or ""
                                            
                                            final_val = msg_content if len(msg_content) > 100 else val
                                            if final_val:
                                                if self._argus_agent_name == "managing_partner":
                                                    if "DECISION:" in str(final_val).upper():
                                                        final_thought = final_val
                                                        found = True
                                                        break
                                                else:
                                                    final_thought = final_val
                                                    found = True
                                                    break
                                    if found:
                                        break
      
                            # 2. If not found, search for plain content messages
                            if not found:
                                for m_rev in reversed(new_msgs):
                                    is_tool_msg = hasattr(m_rev, "tool_call_id") and m_rev.tool_call_id
                                    is_tool_call_msg = hasattr(m_rev, "tool_calls") and m_rev.tool_calls
                                    if not is_tool_msg and not is_tool_call_msg and hasattr(m_rev, "content") and m_rev.content:
                                        m_content = getattr(m_rev, "content", "") or ""
                                        if isinstance(m_content, list):
                                            m_content = "\n".join(b.get("text", "") for b in m_content if isinstance(b, dict) and b.get("type") == "text")
                                        m_content = str(m_content).strip()
                                        
                                        if self._argus_agent_name == "managing_partner":
                                            if "DECISION:" in m_content.upper():
                                                final_thought = m_content
                                                found = True
                                                break
                                        else:
                                            final_thought = m_content
                                            found = True
                                            break
     
                            # 3. Last resort fallback for managing_partner: check cached card in sim_state
                            if self._argus_agent_name == "managing_partner" and not ("DECISION:" in str(final_thought).upper()):
                                if getattr(sim_state, "final_verdict_card", None):
                                    final_thought = sim_state.final_verdict_card
                                    found = True
                                    logger.info(f"[{self._argus_agent_name}] Extracted decision card from sim_state cache fallback")
                                else:
                                    final_thought = "Managing Partner: awaiting findings from partners."
                            elif not found:
                                final_thought = "Standing by."
                except Exception as e:
                    logger.warning(f"[{self._argus_agent_name}] Could not extract final thought from graph state: {e}", exc_info=True)
     
                should_log = True
                if self._argus_agent_name == "managing_partner":
                    if not ("DECISION:" in str(final_thought).upper()):
                        should_log = False
                        logger.info(f"[{self._argus_agent_name}] Skipping memory logging for non-verdict message")
                    
                if should_log:
                    await self._base_agent._log_to_memory(final_thought, incident_id)
                await event_bus.broadcast(self._argus_agent_name, "done", {"report": final_thought})
            except Exception as e:
                err_str = str(e)
                # If only Band message-send failed (403 room limit), still mark
                # the specialist "done" via the internal event bus so the
                # orchestrator can proceed to verdict synthesis. Only broadcast
                # "alert" for genuine agent failures (LLM down, bad tool, etc.).
                is_band_limit = any(x in err_str for x in ("limit_reached", "403", "message limit"))
                if is_band_limit:
                    logger.warning(f"[{self._argus_agent_name}] Band room limit hit — generating fallback report via diligence engine.")
                    try:
                        from core.pitch_loader import _load_pitch_file
                        from core.diligence_engine import run_diligence_calculations
                        pitch_data = _load_pitch_file() or {}
                        calc = run_diligence_calculations(pitch_data) if pitch_data else {}
                        domain_map = {
                            "financial_partner": ("financial_risk_score", "Financial"),
                            "legal_partner": ("legal_risk_score", "Legal"),
                            "technical_partner": ("technical_risk_score", "Technical"),
                            "market_partner": ("market_risk_score", "Market"),
                        }
                        score_key, domain = domain_map.get(self._argus_agent_name, ("weighted_score", "Analysis"))
                        score = calc.get(score_key, "N/A")
                        red_flags = calc.get("red_flags", [])
                        fallback = (
                            f"{domain.upper()} ANALYSIS COMPLETE (fallback — Band room full). "
                            f"Risk Score: {score}/10. "
                            f"Top flags: {'; '.join(str(f) for f in red_flags[:3]) or 'see diligence report'}."
                        )
                        sim_state.completed_agents.add(self._argus_agent_name)
                        await self._base_agent._log_to_memory(fallback, incident_id)
                        await event_bus.broadcast(self._argus_agent_name, "done", {"report": fallback})
                    except Exception as fe:
                        logger.error(f"[{self._argus_agent_name}] Fallback report generation failed: {fe}")
                        await event_bus.broadcast(self._argus_agent_name, "alert", {"error": err_str})
                else:
                    logger.error(f"[{self._argus_agent_name}] Error during on_message: {e}")
                    await event_bus.broadcast(self._argus_agent_name, "alert", {"error": err_str})
            finally:
                current_uid.reset(token_uid)
                current_incident_id.reset(token_inc)
                if token_pitch:
                    current_pitch_file.reset(token_pitch)
        else:
            logger.debug(f"[{self._argus_agent_name}] Ignoring message (not mentioned): '{msg.content[:60]}'")

class BaseAgent:
    def __init__(
        self,
        name: str,
        display_name: str,
        room: str,
        system_prompt: str,
        tools: Optional[List[Any]] = None,
        model_name: str = "gpt-4o-mini"
    ):
        self.name = name
        self.display_name = display_name
        self.room = room
        self.system_prompt = CORE_SYSTEM_RULES + "\n\n" + load_fusion_doctrine() + "\n\n" + system_prompt + MEMORY_PROTOCOL_PROMPT
        
        # Enforce domain-scoping of tools for specialist agents
        self.custom_tools = []
        for t in (tools or []):
            if hasattr(t, "name") and t.name == "load_deal_brief":
                self.custom_tools.append(self._make_scoped_load_deal_brief(t))
            elif hasattr(t, "name") and t.name == "get_red_flags":
                self.custom_tools.append(self._make_scoped_get_red_flags(t))
            else:
                self.custom_tools.append(t)
                
        from core.pitch_loader import get_calculated_scores
        if get_calculated_scores not in self.custom_tools:
            self.custom_tools.append(get_calculated_scores)
        self.custom_tools.extend(self._get_memory_tools())
        
        self.model_name = model_name
        self._is_busy = False  # Re-entrancy guard
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._queue_processor_running = False  # True while the drain-loop is active
        
        load_dotenv(override=True)
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = None
        self._setup_llm()
        self.agent_executor = None
        self._local_executor = None

    def _make_scoped_load_deal_brief(self, original_tool):
        agent_name = self.name
        from core.pitch_loader import load_deal_brief
        
        @tool("load_deal_brief")
        def scoped_load_deal_brief(section: str = "all") -> str:
            """Load the startup pitch data for due diligence analysis.

            Args:
                section: Which section to retrieve. Options:
                    'all'        - Full pitch (use sparingly — large)
                    'company'    - Company overview and claims
                    'financials' - Revenue, burn, unit economics, customer breakdown
                    'legal'      - Litigation, IP, regulatory compliance
                    'technical'  - Tech stack, security posture, architecture
                    'market'     - Market size, competitors, regulatory trends
                    'team'       - Founding team backgrounds and gaps
                    'deal_summary' - Raise amount, valuation, use of funds

            Returns:
                JSON string of the requested pitch section.
            """
            # Enforce domain scoping for specialists
            if agent_name == "financial_partner":
                if section in ("all", "legal", "technical", "market"):
                    section = "financials"
            elif agent_name == "legal_partner":
                if section in ("all", "financials", "technical", "market"):
                    section = "legal"
            elif agent_name == "technical_partner":
                if section in ("all", "financials", "legal", "market"):
                    section = "technical"
            elif agent_name == "market_partner":
                if section in ("all", "financials", "legal", "technical"):
                    section = "market"
            return load_deal_brief.invoke({"section": section})
            
        return scoped_load_deal_brief

    def _make_scoped_get_red_flags(self, original_tool):
        agent_name = self.name
        from core.pitch_loader import get_red_flags
        
        @tool("get_red_flags")
        def scoped_get_red_flags(domain: str = "all") -> str:
            """Get the pre-catalogued red flags for a specific domain.

            Args:
                domain: 'financials', 'legal', 'technical', 'market', or 'all'

            Returns:
                List of red flag strings for the specified domain.
            """
            if agent_name == "financial_partner":
                domain = "financials"
            elif agent_name == "legal_partner":
                domain = "legal"
            elif agent_name == "technical_partner":
                domain = "technical"
            elif agent_name == "market_partner":
                domain = "market"
            return get_red_flags.invoke({"domain": domain})
            
        return scoped_get_red_flags
    def _build_provider_llm(self, provider: str):
        """Construct a provider chat model (OpenAI-compatible tool calling) so it
        slots into the LangGraph react agent directly. Both hackathon partner
        APIs are supported:
          - aiml        AIML API (https://api.aimlapi.com)
          - featherless Featherless native API (https://api.featherless.ai).
                        If you only have a HuggingFace hf_ token instead of a
                        native rc_ key, set ARGUS_FEATHERLESS_BASE_URL=
                        https://router.huggingface.co/featherless-ai/v1
        """
        if provider == "aiml":
            return ChatOpenAI(
                base_url=os.getenv("ARGUS_AIMLAPI_BASE_URL", "https://api.aimlapi.com/v1"),
                api_key=os.getenv("AIMLAPI_KEY"),
                model=os.getenv("ARGUS_AIMLAPI_MODEL", "gpt-4o-mini"),
                temperature=0.1,
                max_tokens=1500,
                max_retries=2,
            )
        if provider == "featherless":
            # Qwen2.5-72B: fast (~2s), strong, reliable tool-calling, NON-gated.
            # (Meta Llama is gated on Featherless → 403; DeepSeek-Pro is a slow
            # reasoner that stalled agents.) 1800 tokens is ample for a report.
            return ChatOpenAI(
                base_url=os.getenv("ARGUS_FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1"),
                api_key=os.getenv("FEATHERLESS_API_KEY"),
                model=os.getenv("ARGUS_FEATHERLESS_MODEL", "Qwen/Qwen2.5-72B-Instruct"),
                temperature=0.1,
                max_tokens=1800,
                max_retries=3,
            )
        raise ValueError(f"Unknown provider: {provider}")

    def _wrap_resilient(self, primary, fallback, fallback_is_local: bool):
        return ResilientChatModel(
            primary_llm=primary,
            fallback_llm=fallback,
            agent_name=self.name,
            display_name=self.display_name,
            fallback_llm_is_local=fallback_is_local,
        )

    def _setup_llm(self):
        """Set up the agent LLM — the committee's *analysis* brain.

        Both hackathon partner APIs are wired. Analysis runs on AIML as PRIMARY
        because the 5 agents analyze in parallel and Featherless plans cap
        concurrency at ~1 request (4 parallel agents → 429). Featherless stays as
        the secondary real fallback so the partner is still used on AIML outages.

        Provider chain for analysis:
          PRIMARY  : AIML API (gpt-4o-mini) — fast, cheap, handles concurrency
          FALLBACK : Featherless (Qwen2.5-72B) — secondary real provider
          LAST NET : this server's deterministic /mock-llm engine (no cost)
        Wired as AIML → Featherless → local via nested ResilientChatModel.
        """
        def _valid(key: str) -> bool:
            return bool(key) and "your-" not in (key or "")

        # Analysis prefers AIML (concurrency-safe); Featherless is the secondary
        # real fallback.
        available = []
        if _valid(os.getenv("AIMLAPI_KEY")):
            available.append("aiml")
        if _valid(os.getenv("FEATHERLESS_API_KEY")):
            available.append("featherless")

        self.llm_is_local = False
        if not available:
            logger.warning(f"[{self.display_name}] No analysis API key configured. Running on the local engine.")
            self.llm = self._make_local_llm()
            self.llm_is_local = True
            return

        primary_provider = available[0]
        secondary_provider = available[1] if len(available) > 1 else None
        primary_llm = self._build_provider_llm(primary_provider)
        logger.info(
            f"[{self.display_name}] analysis LLM primary={primary_provider}, "
            f"fallback={secondary_provider or 'local-engine'}"
        )

        local_llm = self._make_local_llm()
        if secondary_provider:
            # secondary real API, with the local engine as its own safety net
            fallback = self._wrap_resilient(
                self._build_provider_llm(secondary_provider), local_llm, fallback_is_local=True
            )
            self.llm = self._wrap_resilient(primary_llm, fallback, fallback_is_local=False)
        else:
            self.llm = self._wrap_resilient(primary_llm, local_llm, fallback_is_local=True)

    def _make_local_llm(self):
        """LLM client pointed at this server's deterministic /mock-llm engine."""
        port = os.getenv("PORT", "8000")
        import httpx
        
        class DynamicHeaderClient(httpx.Client):
            def send(self, request, *args, **kwargs):
                try:
                    from core.auth import current_uid, current_incident_id
                    uid = current_uid.get(None)
                    inc_id = current_incident_id.get(None)
                    if uid and uid not in ("__mcp_client__", "__public__"):
                        request.headers["X-FUSION-UID"] = uid
                    if inc_id:
                        request.headers["X-FUSION-Incident-ID"] = inc_id
                except Exception:
                    pass
                return super().send(request, *args, **kwargs)

        class DynamicHeaderAsyncClient(httpx.AsyncClient):
            async def send(self, request, *args, **kwargs):
                try:
                    from core.auth import current_uid, current_incident_id
                    uid = current_uid.get(None)
                    inc_id = current_incident_id.get(None)
                    if uid and uid not in ("__mcp_client__", "__public__"):
                        request.headers["X-FUSION-UID"] = uid
                    if inc_id:
                        request.headers["X-FUSION-Incident-ID"] = inc_id
                except Exception:
                    pass
                return await super().send(request, *args, **kwargs)

        return ChatOpenAI(
            base_url=f"http://127.0.0.1:{port}/mock-llm",
            api_key="dummy",
            model=f"mock-{self.name}",
            default_headers={"X-Agent-Name": self.name},
            http_client=DynamicHeaderClient(),
            http_async_client=DynamicHeaderAsyncClient()
        )

    def load_credentials(self) -> tuple[str, str]:
        """Loads agent_id and api_key from env vars or agent_config.yaml."""
        # Env var override: BAND_<NAME>_AGENT_ID / BAND_<NAME>_API_KEY
        # e.g. BAND_MANAGING_PARTNER_AGENT_ID for self.name="managing_partner"
        env_prefix = f"BAND_{self.name.upper()}"
        env_agent_id = os.getenv(f"{env_prefix}_AGENT_ID")
        env_api_key = os.getenv(f"{env_prefix}_API_KEY")
        if env_agent_id and env_api_key:
            logger.info(f"[{self.display_name}] Loaded credentials from environment variables: name={self.name}, agent_id={env_agent_id}, api_key_prefix={env_api_key[:25]}...")
            return env_agent_id, env_api_key

        config_path = "agent_config.yaml"
        if not os.path.exists(config_path):
            config_path = "agent_config.example.yaml"

        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f) or {}
            # New shape nests agents under 'agents:'; old shape was flat.
            agent_conf = config.get("agents", {}).get(self.name) or config.get(self.name, {})
            agent_id = agent_conf.get("agent_id", "mock-id")
            api_key = agent_conf.get("api_key", "mock-key")
            logger.info(f"[{self.display_name}] Loaded credentials: name={self.name}, agent_id={agent_id}, api_key_prefix={api_key[:25]}...")
            return agent_id, api_key
        except Exception as e:
            logger.error(f"[{self.display_name}] Error loading configuration: {e}")
            return "mock-id", "mock-key"

    def _schedule_async(self, coro):
        """Safely schedule a coroutine onto the running event loop from a sync context."""
        try:
            loop = getattr(self, "loop", None)
            if loop is None or loop.is_closed():
                loop = asyncio.get_event_loop()
            
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(coro, loop)
            else:
                loop.run_until_complete(coro)
        except Exception as e:
            logger.warning(f"[{self.display_name}] Could not schedule async task: {e}")

    def _get_memory_tools(self) -> List[Any]:
        """Shared memory graph tools available to every agent in every mode."""
        agent_name = self.name

        @tool("query_team_memory")
        async def query_team_memory(attack_technique: str) -> str:
            """Query the team's shared memory graph for similar past incidents
            by MITRE ATT&CK technique ID (e.g. 'T1566.002') or keyword.
            Returns past findings so you can reuse what worked before."""
            import json as _json
            past = await memory_graph.query_similar_incidents(attack_technique)
            if not past:
                return _json.dumps({"similar_incidents": [], "note": "No past incidents match — this is new territory."})
            return _json.dumps({"similar_incidents": past, "note": f"Team has seen this {len(past)} time(s) before."})

        @tool("get_defense_recipe")
        async def get_defense_recipe(mitre_id: str) -> str:
            """Retrieve the team's best-known defense recipe for a MITRE
            technique ID (e.g. 'T1566.001'), learned from past incidents."""
            import json as _json
            recipe = await memory_graph.get_defense_recipe(mitre_id)
            return _json.dumps(recipe or {"note": "No learned defense yet for this technique."})

        @tool("record_defense_recipe")
        async def record_defense_recipe(mitre_id: str, detection_method: str, defense_action: str, success_rate: float = 0.8) -> str:
            """Record a defense that worked for a MITRE technique so the whole
            team responds faster on the next similar incident."""
            await memory_graph.record_attack_pattern(mitre_id, detection_method, defense_action, success_rate)
            return f"Defense recipe for {mitre_id} recorded in shared team memory."

        return [query_team_memory, get_defense_recipe, record_defense_recipe]

    def _get_mock_tools(self) -> List[Any]:
        """Creates mock versions of Band SDK platform tools for offline testing."""

        @tool("thenvoi_send_message")
        async def mock_thenvoi_send_message(
            room: Optional[str] = None,
            message: Optional[str] = None,
            content: Optional[str] = None,
            mentions: Optional[List[str]] = None,
        ) -> str:
            """Send a message to another agent room on the Band platform.
            Use this to @mention and collaborate with other agents."""
            target_room = room
            msg_content = message
            
            if content is not None:
                msg_content = content
                
            if target_room is None and mentions:
                target_room = mentions[0] if mentions else ""
                
            if target_room is None:
                target_room = "managing-partner-room"
                
            if msg_content is None:
                msg_content = ""
                
            from core.auth import current_incident_id
            inc_id = current_incident_id.get() or None
            await mock_bus.send_message(self.display_name, target_room, msg_content, incident_id=inc_id)
            return f"Message sent successfully to room {target_room}."

        @tool("thenvoi_send_event")
        async def mock_thenvoi_send_event(event: str, data: Optional[Dict[str, Any]] = None) -> str:
            """Broadcast an operational status update or thought to the war room dashboard.
            Use this to report progress, findings, or completed steps."""
            logger.info(f"[{self.display_name}] Operation Event: {event}")
            await event_bus.broadcast(self.name, "working", {"event": event, "data": data or {}})
            return "Event reported successfully."

        @tool("thenvoi_lookup_peers")
        def mock_thenvoi_lookup_peers() -> List[str]:
            """Retrieve the list of active agent rooms available on the platform."""
            return list(mock_bus.rooms.keys())

        @tool("thenvoi_add_participant")
        def mock_thenvoi_add_participant(room: str, agent: str) -> str:
            """Add/recruit a specialist agent to the active chat room dynamically."""
            logger.info(f"[{self.display_name}] Recruited agent {agent} into room {room}")
            return f"Successfully added agent {agent} to room {room}."

        return [mock_thenvoi_send_message, mock_thenvoi_send_event, mock_thenvoi_lookup_peers, mock_thenvoi_add_participant]

    def compile_agent(self):
        """Compiles the LangGraph agent executor."""
        # Stable agent-id marker so the offline mock-LLM endpoint can route
        # deterministically by id instead of fragile system-prompt keyword matching.
        # Harmless metadata for the real LLM (AIML API).
        prompt = f"{self.system_prompt}\n\n[ARGUS_AGENT: {self.name}]"

        if is_mock_mode():
            # In mock mode, combine custom tools with our mock Band tools
            all_tools = self.custom_tools + self._get_mock_tools()
            self._all_tools = all_tools
            self._agent_prompt = prompt
            self._local_executor = None
            self.agent_executor = self._build_executor(self.llm, all_tools, prompt)

        else:
            # Real mode — uses thenvoi-sdk v0.2.11 LangGraphAdapter + Agent
            # Pattern: PlatformRuntime(agent_id, api_key) → Agent(runtime, adapter)
            from thenvoi.agent import Agent
            from thenvoi.runtime.platform_runtime import PlatformRuntime
            agent_id, api_key = self.load_credentials()

            self.adapter = ArgusLangGraphAdapter(
                agent_name=self.name,
                agent_id=agent_id,
                base_agent=self,
                llm=self.llm,
                checkpointer=InMemorySaver(),
                additional_tools=self.custom_tools,
                custom_section=prompt,   # injected as "## Developer Instructions" by SDK
            )
            self.runtime = PlatformRuntime(
                agent_id=agent_id,
                api_key=api_key,
                ws_url="wss://app.thenvoi.com/api/v1/socket/websocket",
                rest_url="https://app.thenvoi.com",
            )
            self.real_agent = Agent(
                runtime=self.runtime,
                adapter=self.adapter,
            )

    def _build_executor(self, llm, tools, prompt):
        try:
            return create_react_agent(model=llm, tools=tools, prompt=prompt)
        except TypeError:
            return create_react_agent(model=llm, tools=tools, state_modifier=prompt)

    def _get_local_executor(self):
        """Executor wired to the deterministic local /mock-llm engine. Built
        lazily so it costs nothing while the real provider is healthy."""
        if self.llm_is_local:
            return self.agent_executor
        if self._local_executor is None:
            self._local_executor = self._build_executor(
                self._make_local_llm(), self._all_tools, self._agent_prompt
            )
        return self._local_executor

    async def _invoke_resilient(self, inputs: dict, config: dict):
        """Invoke the agent. Since ResilientChatModel handles all retries and fallbacks internally,
        we can call the agent executor directly."""
        return await asyncio.wait_for(self.agent_executor.ainvoke(inputs, config=config), timeout=120.0)

    def _should_handle_mock_message(self, sender: str, message: str) -> bool:
        """Hook: should this agent run on a mock-bus message? Default yes.
        The Managing Partner overrides this so it only synthesizes the verdict
        when the orchestrator explicitly triggers it (all 4 specialists done),
        instead of running prematurely on each specialist's report."""
        return True

    async def handle_mock_message(self, sender: str, message: str, incident_id: Optional[str] = None):
        """Handles a message arriving in Mock Mode.

        Messages are queued and drained sequentially so that specialist
        reports arriving near-simultaneously are NEVER silently dropped.
        Previously a 40-second polling timeout would discard late arrivals
        and wedge the pipeline on 'Deliberating' forever.
        """
        if not self._should_handle_mock_message(sender, message):
            logger.info(f"[{self.display_name}] Ignoring mock message (gated): '{message[:60]}'")
            return
            
        from core.auth import current_uid, current_incident_id
        uid = current_uid.get("__public__")
        if not incident_id:
            incident_id = current_incident_id.get("")
        if not incident_id:
            incident_id = "default"
            
        if uid in ("__public__", "__mcp_client__") and incident_id and incident_id != "default":
            from api.state import get_uid_for_incident
            mapped_uid = get_uid_for_incident(incident_id)
            if mapped_uid:
                uid = mapped_uid
        
        if not hasattr(self, "_message_queues"):
            self._message_queues = {}
        if not hasattr(self, "_queue_processors"):
            self._queue_processors = {}

        queue_key = (uid, incident_id)
        if queue_key not in self._message_queues:
            self._message_queues[queue_key] = asyncio.Queue()

        logger.info(f"[{self.display_name}] Enqueueing message for {uid}:{incident_id} from '{sender}': {message[:80]}...")
        await self._message_queues[queue_key].put((sender, message))

        # Kick off the drain loop if it isn't already running.
        if not self._queue_processors.get(queue_key):
            self._queue_processors[queue_key] = True
            asyncio.create_task(self._drain_message_queue_for_key(queue_key))

    async def _drain_message_queue_for_key(self, queue_key):
        """Process queued messages for a specific user and incident one at a time."""
        from core.auth import current_uid, current_username, current_incident_id, current_pitch_file
        
        uid, incident_id = queue_key
        username = uid
        if uid == "__public__":
            username = "guest"
            
        token_ctx = current_uid.set(uid)
        username_ctx = current_username.set(username)
        incident_ctx = current_incident_id.set(incident_id)
        
        from core.pitch_loader import resolve_pitch_file_for_incident
        pitch_file = resolve_pitch_file_for_incident(incident_id)
        token_pitch = None
        if pitch_file:
            token_pitch = current_pitch_file.set(pitch_file)
        
        try:
            queue = self._message_queues.get(queue_key)
            if queue:
                while not queue.empty():
                    sender, message = await queue.get()
                    await self._handle_single_message(sender, message)
        except Exception as e:
            logger.error(f"[{self.display_name}] Queue drain error for {uid}:{incident_id}: {e}")
        finally:
            self._queue_processors[queue_key] = False
            current_uid.reset(token_ctx)
            current_username.reset(username_ctx)
            current_incident_id.reset(incident_ctx)
            if token_pitch:
                current_pitch_file.reset(token_pitch)


    async def _handle_single_message(self, sender: str, message: str):
        """Process one message: run the LangGraph executor and broadcast updates."""
        self._is_busy = True
        logger.info(f"[{self.display_name}] Processing message from '{sender}': {message[:80]}...")

        # Broadcast "working" state to event bus/dashboard
        await event_bus.broadcast(self.name, "working", {"current_action": f"Analyzing input from {sender}"})

        # ponytail: add a small artificial delay so the yellow edge glow animation is visible on the UI,
        # otherwise in mock mode the agent completes in milliseconds and the animation never shows.
        await asyncio.sleep(1.5)

        inputs = {"messages": [("user", f"Message from {sender}: {message}")]}
        try:
            from core.auth import current_uid as _cuid, current_incident_id as _cinc
            _tid_uid = _cuid.get("__public__")
            _tid_inc = _cinc.get("") or "default"
        except Exception:
            _tid_uid, _tid_inc = "__public__", "default"
        config = {"configurable": {"thread_id": f"{self.name}:{_tid_uid}:{_tid_inc}"}}

        try:
            response = await self._invoke_resilient(inputs, config)
            msgs = response.get("messages", []) if isinstance(response, dict) else []
            final_thought = _msg_content_text(msgs[-1].content) if msgs else ""

            # The Managing Partner may emit the DECISION card and THEN a closing
            # event message, so the LAST message isn't always the card. Scan all
            # messages for the verdict card and prefer it (and cache it so the
            # report/PDF and dashboard always have the full card).
            if self.name == "managing_partner":
                for m in reversed(msgs):
                    text = _msg_content_text(getattr(m, "content", ""))
                    if "DECISION:" in text.upper():
                        final_thought = text
                        try:
                            from api.state import sim_state
                            sim_state.final_verdict_card = text
                        except Exception:
                            pass
                        break

            logger.info(f"[{self.display_name}] Completed task. Final Thought: {final_thought[:100]}...")

            # Log the finding to the shared memory graph for future incidents
            await self._log_to_memory(final_thought)

            # Broadcast "done" state with final report
            await event_bus.broadcast(self.name, "done", {"report": final_thought})
        except Exception as e:
            logger.error(f"[{self.display_name}] Error running agent: {e}")
            await event_bus.broadcast(self.name, "alert", {"error": str(e)})
        finally:
            self._is_busy = False

    async def _log_to_memory(self, report: str, incident_id: Optional[str] = None):
        """Persist this agent's final report into the active shared incident."""
        try:
            if not incident_id:
                from core.auth import current_incident_id
                incident_id = current_incident_id.get(None) or memory_graph.get_latest_incident_id()
            if not incident_id:
                return
            await memory_graph.log_finding(
                incident_id,
                self.name,
                report or "",
                severity=_estimate_severity(report),
                tags=_extract_mitre_tags(report),
            )
            # The executive verdict closes the incident record
            if self.name == "managing_partner" and "DECISION" in (report or "").upper():
                memory_graph.set_final_decision(incident_id, report or "")

            # Legal partner findings become learned risk patterns for future deals
            if self.name == "legal_partner":
                inc = memory_graph.get_incident(incident_id) or {}
                techniques = {
                    tag
                    for event in inc.get("timeline", [])
                    for tag in event.get("tags", [])
                    if _re.fullmatch(r"T\d{4}(?:\.\d{3})?", str(tag))
                }
                for mitre_id in techniques:
                    await memory_graph.record_attack_pattern(
                        mitre_id,
                        detection_method="Correlated IoCs across team reports",
                        defense_action=(report or "")[:300],
                        success_rate=0.85,
                    )
        except Exception as e:
            logger.warning(f"[{self.display_name}] Memory logging failed: {e}")

    async def run(self):
        """Starts the agent. In mock mode registers with the bus; in real mode runs the WebSocket."""
        self.compile_agent()
        
        if is_mock_mode():
            # Register to Mock Bus
            mock_bus.register(self.room, self)
            # Run forever waiting on tasks
            while True:
                await asyncio.sleep(1)
        else:
            delay = 5
            while True:
                try:
                    logger.info(
                        f"[{self.display_name}] Connecting to Band via WebSocket "
                        f"(agent_id={self.runtime._agent_id[:8]}...)"
                    )
                    await self.real_agent.run()
                    break  # clean exit — don't reconnect
                except Exception as e:
                    logger.warning(
                        f"[{self.display_name}] Band disconnected: {e}. "
                        f"Reconnecting in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 120)  # cap at 2 min
