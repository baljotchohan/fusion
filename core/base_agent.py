# core/base_agent.py
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

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

from core.band_client import mock_bus, is_mock_mode
from core.event_bus import event_bus
from core.memory_graph import memory_graph

logger = logging.getLogger("fusion.base_agent")

import re as _re

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

OPERATING DOCTRINE:
- Be evidence-driven: separate confirmed facts from assessment.
- Quantify everything: dollar amounts, percentages, time horizons, risk multiples. Decisions follow data.
- Be decisive and concise. Lead with your conclusion, then support it with evidence.
- Red flags must be called out explicitly — your job is to protect LP capital. Never soften a dealbreaker.
- You are one specialist; produce the single artifact your role owns, then hand off cleanly to the Managing Partner.
- Use the load_deal_brief tool to access the startup pitch data before analyzing.
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

        for attempt in range(6):
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
                if not fatal and transient_429 and attempt < 5:
                    delay = 4 + random.uniform(0, 2)
                    logger.warning(
                        f"[{self.display_name}] Rate limited (sync) — retrying in {delay:.1f}s... Error: {err[:150]}"
                    )
                    time.sleep(delay)
                    continue
                logger.error(f"[{self.display_name}] LLM failed (sync): {err[:200]}")
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

        for attempt in range(6):
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
                if not fatal and transient_429 and attempt < 5:
                    delay = 4 + random.uniform(0, 2)
                    logger.warning(
                        f"[{self.display_name}] Rate limited — retrying in {delay:.1f}s... Error: {err[:150]}"
                    )
                    await event_bus.broadcast(self.agent_name, "working", {
                        "current_action": f"Rate limited — retrying in {delay:.0f}s"
                    })
                    await asyncio.sleep(delay)
                    continue
                logger.error(f"[{self.display_name}] LLM failed: {err[:200]}")
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

class ArgusLangGraphAdapter(LangGraphAdapter):
    def __init__(self, agent_name: str, agent_id: str, *args, **kwargs):
        self._argus_agent_name = agent_name
        self._argus_agent_id = agent_id
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
        if msg.sender_id == self._argus_agent_id:
            logger.debug(f"[{self._argus_agent_name}] Skipping own message")
            return

        is_mentioned = False
        
        # Robust mentions retrieval: handles metadata as dict, Pydantic model, or None,
        # and handle each item in the list as either a dict or an object.
        raw_metadata = getattr(msg, "metadata", None)
        raw_mentions = []
        if raw_metadata is not None:
            if isinstance(raw_metadata, dict):
                raw_mentions = raw_metadata.get("mentions", []) or []
            else:
                raw_mentions = getattr(raw_metadata, "mentions", []) or []

        for m in raw_mentions:
            if isinstance(m, dict):
                m_id = m.get("id")
                m_handle = m.get("handle")
                m_username = m.get("username")
            else:
                m_id = getattr(m, "id", None)
                m_handle = getattr(m, "handle", None)
                m_username = getattr(m, "username", None)

            if m_id == self._argus_agent_id:
                is_mentioned = True
                break

            agent_name_clean = self._argus_agent_name.replace("_", "-").replace("-agent", "").lower()
            if m_handle:
                m_handle_clean = m_handle.lstrip("@").lower()
                if agent_name_clean in m_handle_clean:
                    is_mentioned = True
                    break
            if m_username:
                m_username_clean = m_username.lstrip("@").lower()
                if agent_name_clean in m_username_clean:
                    is_mentioned = True
                    break

        is_ic = self._argus_agent_name == "incident_commander"
        is_from_user = msg.sender_type == "User"

        # If any other agent is mentioned in the message, the Incident Commander should
        # stay silent and let that agent handle it, unless the IC is also mentioned.
        is_other_agent_mentioned = False
        if is_ic and is_from_user and raw_mentions:
            for m in raw_mentions:
                m_id = m.get("id") if isinstance(m, dict) else getattr(m, "id", None)
                if m_id != self._argus_agent_id:
                    is_other_agent_mentioned = True
                    break

        if is_mentioned or (is_ic and is_from_user and not is_other_agent_mentioned):
            logger.info(f"[{self._argus_agent_name}] Triggered! Processing message: '{msg.content[:100]}'")
            await super().on_message(
                msg,
                tools,
                history,
                participants_msg,
                contacts_msg,
                is_session_bootstrap=is_session_bootstrap,
                room_id=room_id,
            )
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
        model_name: str = "gemini-2.0-flash"
    ):
        self.name = name
        self.display_name = display_name
        self.room = room
        self.system_prompt = CORE_SYSTEM_RULES + "\n\n" + load_fusion_doctrine() + "\n\n" + system_prompt + MEMORY_PROTOCOL_PROMPT
        self.custom_tools = (tools or []) + self._get_memory_tools()
        self.model_name = model_name
        self._is_busy = False  # Re-entrancy guard — drop duplicate wakeups
        
        load_dotenv()
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = None
        self._setup_llm()
        self.agent_executor = None
        self._local_executor = None

    def _setup_llm(self):
        """Set up LLM with priority based on the requested model name and available credentials."""
        google_key = os.getenv("GOOGLE_API_KEY")
        featherless_key = os.getenv("FEATHERLESS_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")
        self.llm_is_local = False

        model_lower = self.model_name.lower()

        # 1. Groq Models (Primary for this session since Gemini free tier is exhausted and Featherless is unauthorized)
        if groq_key and groq_key not in ("your-groq-api-key-here", ""):
            groq_model = self.model_name
            # Strip prefixes
            if groq_model.lower().startswith("groq:"):
                groq_model = groq_model[5:]
            elif groq_model.lower().startswith("groq/"):
                groq_model = groq_model[5:]

            # Map all models to llama-3.3-70b-versatile due to limits/exhaustion of other options
            groq_model = "llama-3.3-70b-versatile"

            logger.info(f"[{self.display_name}] Routing to Groq model: {groq_model}")
            self.llm = ChatGroq(
                api_key=groq_key,
                model=groq_model,
                temperature=0.1,
                max_tokens=1024,
                max_retries=6,
            )
        # 2. Gemini Models (Fallback)
        elif "gemini" in model_lower and google_key and google_key not in ("your-gemini-api-key-here", ""):
            logger.info(f"[{self.display_name}] Using Gemini model: {self.model_name}")
            self.llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=google_key,
                temperature=0.1,
                max_output_tokens=1024,
                max_retries=6,
            )
        # 3. Featherless OS Models (Fallback)
        elif any(x in model_lower for x in ("llama", "qwen", "mistral")) and not model_lower.startswith("groq") and featherless_key and featherless_key not in ("your-featherless-api-key-here", ""):
            logger.info(f"[{self.display_name}] Using Featherless OS model: {self.model_name}")
            self.llm = ChatOpenAI(
                base_url="https://api.featherless.ai/v1",
                api_key=featherless_key,
                model=self.model_name,
                temperature=0.1
            )
        # 4. Fallback to Gemini if key exists but model was not matched
        elif google_key and google_key not in ("your-gemini-api-key-here", ""):
            logger.info(f"[{self.display_name}] Using Gemini model (fallback): {self.model_name}")
            self.llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=google_key,
                temperature=0.1,
                max_output_tokens=1024,
                max_retries=6,
            )
        # 5. Fallback to AI/ML API
        elif (aimlapi_key := os.getenv("AIMLAPI_KEY")) and "your-" not in aimlapi_key:
            aiml_model = os.getenv("ARGUS_AIMLAPI_MODEL", "gpt-4o")
            logger.info(f"[{self.display_name}] Using AI/ML API model: {aiml_model}")
            self.llm = ChatOpenAI(
                base_url="https://api.aimlapi.com/v1",
                api_key=aimlapi_key,
                model=aiml_model,
                temperature=0.1
            )
        # 6. Fallback to mock/local
        else:
            logger.warning(f"[{self.display_name}] No API key configured. Running with dummy mock model.")
            self.llm = self._make_local_llm()
            self.llm_is_local = True

        if not self.llm_is_local:
            fallback_llm = self._make_local_llm()
            self.llm = ResilientChatModel(
                primary_llm=self.llm,
                fallback_llm=fallback_llm,
                agent_name=self.name,
                display_name=self.display_name,
                fallback_llm_is_local=self.llm_is_local
            )

    def _make_local_llm(self):
        """LLM client pointed at this server's deterministic /mock-llm engine."""
        port = os.getenv("PORT", "8000")
        return ChatOpenAI(
            base_url=f"http://localhost:{port}/mock-llm",
            api_key="dummy",
            model="mock-model"
        )

    def load_credentials(self) -> tuple[str, str]:
        """Loads agent_id and api_key from agent_config.yaml."""
        config_path = "agent_config.yaml"
        if not os.path.exists(config_path):
            config_path = "agent_config.example.yaml"
            
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f) or {}
            # New shape nests agents under 'agents:'; old shape was flat.
            agent_conf = config.get("agents", {}).get(self.name) or config.get(self.name, {})
            return agent_conf.get("agent_id", "mock-id"), agent_conf.get("api_key", "mock-key")
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
        def query_team_memory(attack_technique: str) -> str:
            """Query the team's shared memory graph for similar past incidents
            by MITRE ATT&CK technique ID (e.g. 'T1566.002') or keyword.
            Returns past findings so you can reuse what worked before."""
            import concurrent.futures
            import json as _json
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                past = ex.submit(
                    asyncio.run, memory_graph.query_similar_incidents(attack_technique)
                ).result(timeout=10)
            if not past:
                return _json.dumps({"similar_incidents": [], "note": "No past incidents match — this is new territory."})
            return _json.dumps({"similar_incidents": past, "note": f"Team has seen this {len(past)} time(s) before."})

        @tool("get_defense_recipe")
        def get_defense_recipe(mitre_id: str) -> str:
            """Retrieve the team's best-known defense recipe for a MITRE
            technique ID (e.g. 'T1566.001'), learned from past incidents."""
            import concurrent.futures
            import json as _json
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                recipe = ex.submit(
                    asyncio.run, memory_graph.get_defense_recipe(mitre_id)
                ).result(timeout=10)
            return _json.dumps(recipe or {"note": "No learned defense yet for this technique."})

        @tool("record_defense_recipe")
        def record_defense_recipe(mitre_id: str, detection_method: str, defense_action: str, success_rate: float = 0.8) -> str:
            """Record a defense that worked for a MITRE technique so the whole
            team responds faster on the next similar incident."""
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                ex.submit(
                    asyncio.run,
                    memory_graph.record_attack_pattern(mitre_id, detection_method, defense_action, success_rate),
                ).result(timeout=10)
            return f"Defense recipe for {mitre_id} recorded in shared team memory."

        return [query_team_memory, get_defense_recipe, record_defense_recipe]

    def _get_mock_tools(self) -> List[Any]:
        """Creates mock versions of Band SDK platform tools for offline testing."""

        @tool("thenvoi_send_message")
        def mock_thenvoi_send_message(room: str, message: str) -> str:
            """Send a message to another agent room on the Band platform.
            Use this to @mention and collaborate with other agents."""
            self._schedule_async(mock_bus.send_message(self.display_name, room, message))
            return f"Message sent successfully to room {room}."

        @tool("thenvoi_send_event")
        def mock_thenvoi_send_event(event: str, data: Optional[Dict[str, Any]] = None) -> str:
            """Broadcast an operational status update or thought to the war room dashboard.
            Use this to report progress, findings, or completed steps."""
            logger.info(f"[{self.display_name}] Operation Event: {event}")
            self._schedule_async(event_bus.broadcast(self.name, "working", {"event": event, "data": data or {}}))
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
        # Harmless metadata for real LLMs (Groq/Gemini/Featherless).
        prompt = f"{self.system_prompt}\n\n[ARGUS_AGENT: {self.name}]"
        is_groq = False
        if hasattr(self.llm, "primary_llm"):
            is_groq = self.llm.primary_llm.__class__.__name__ == "ChatGroq"
        else:
            is_groq = self.llm.__class__.__name__ == "ChatGroq"

        if is_groq:
            prompt = (
                f"{prompt}\n\n"
                f"CRITICAL GROQ TOOL CALLING RULES:\n"
                f"1. You MUST use standard tool calling. Never output XML tags like <function=...> or </function>.\n"
                f"2. For thenvoi_send_message, the 'mentions' parameter MUST be a list/array of strings (e.g., ['@baljotchohan23/threat-intel']), NEVER a single string.\n"
                f"3. For thenvoi_send_event, the 'message_type' MUST be exactly one of: 'thought', 'error', 'task'. Never use any other value.\n"
                f"4. For thenvoi_send_event, the 'metadata' parameter MUST be a dictionary/object (e.g., {{}}), NEVER a string."
            )

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
        return await self.agent_executor.ainvoke(inputs, config=config)

    async def handle_mock_message(self, sender: str, message: str):
        """Handles a message arriving in Mock Mode, runs LangGraph executor, and broadcasts updates."""
        # Wait if we are already processing a message — prevents infinite cascades while ensuring no reports are dropped
        for _ in range(60):  # Wait up to 30 seconds
            if not self._is_busy:
                break
            await asyncio.sleep(0.5)

        if self._is_busy:
            logger.info(f"[{self.display_name}] Timeout waiting for agent to become free — dropping duplicate wakeup from '{sender}'")
            return
        self._is_busy = True

        logger.info(f"[{self.display_name}] Wakeup! Message from '{sender}': {message[:80]}...")

        # Broadcast "working" state to event bus/dashboard
        await event_bus.broadcast(self.name, "working", {"current_action": f"Analyzing input from {sender}"})

        inputs = {"messages": [("user", f"Message from {sender}: {message}")]}
        config = {"configurable": {"thread_id": self.name}}

        try:
            response = await self._invoke_resilient(inputs, config)
            final_thought = response["messages"][-1].content
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

    async def _log_to_memory(self, report: str):
        """Persist this agent's final report into the active shared incident."""
        try:
            incident_id = memory_graph.get_latest_incident_id()
            if not incident_id:
                return
            await memory_graph.log_finding(
                incident_id,
                self.name,
                (report or "")[:1000],
                severity=_estimate_severity(report),
                tags=_extract_mitre_tags(report),
            )
            # The executive verdict closes the incident record
            if self.name == "managing_partner" and "DECISION" in (report or "").upper():
                memory_graph.set_final_decision(incident_id, (report or "")[:500])

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
            logger.info(
                f"[{self.display_name}] Connecting to Band via WebSocket "
                f"(agent_id={self.runtime._agent_id[:8]}...)"
            )
            await self.real_agent.run()
