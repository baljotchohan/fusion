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
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

from core.band_client import mock_bus, is_mock_mode
from core.event_bus import event_bus
from core.memory_graph import memory_graph

logger = logging.getLogger("argus.base_agent")

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

ARGUS_DOCTRINE = """You operate inside ARGUS, an autonomous Security Operations Center (SOC).
You are an elite, real-world cyber operator — not a chatbot. Hold yourself to
Tier-1 SOC / DFIR professional standards at all times.

OPERATING DOCTRINE
- Reason along the Cyber Kill Chain (Recon → Weaponization → Delivery →
  Exploitation → Installation → C2 → Actions on Objectives) and map every
  observation to MITRE ATT&CK tactics and technique IDs (Txxxx / Txxxx.yyy).
- Be evidence-driven: separate confirmed facts (from your tools / data) from
  assessment, and state confidence as HIGH / MEDIUM / LOW. Never invent IOCs.
- Quantify impact: CVSS for vulnerabilities, blast radius for compromise,
  dwell time, and business risk. Decisions follow evidence, not vibes.
- Be decisive and concise. Lead with the conclusion, then the support.
- You are one specialist in a coordinated team; produce the single artifact your
  role owns, then hand off cleanly. Do not do another agent's job.

ASSUMED ENVIRONMENT (TechCorp Inc digital twin): a mid-size enterprise — Microsoft
AD domain, Exchange/mail server, customer database holding PII, C-Suite endpoints
with admin rights, 192.168.1.0/24 internal subnet. Defend it as if it were real."""

MEMORY_PROTOCOL_PROMPT = """

MEMORY PROTOCOL (shared team memory graph):
Before deep analysis, call query_team_memory with the relevant MITRE technique
ID (e.g. T1566.002) to check if the team has handled a similar incident before.
If a past incident matches, say so explicitly ("We've seen this before...") and
reuse what worked. When you confirm an effective countermeasure, call
record_defense_recipe so the whole team responds faster next time."""


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
        self.system_prompt = ARGUS_DOCTRINE + "\n\n" + system_prompt + MEMORY_PROTOCOL_PROMPT
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
        """Set up LLM with priority: Featherless (OSS) → Groq (free/fast) → Gemini (fallback)."""
        google_key = os.getenv("GOOGLE_API_KEY")
        featherless_key = os.getenv("FEATHERLESS_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")
        self.llm_is_local = False

        # Featherless handles open-source models (Mistral, Llama, Qwen) unless prefixed with groq: or groq/
        # If groq_key is set, we bypass Featherless to run all agents on Groq for reliability
        use_featherless = any(x in self.model_name.lower() for x in ("llama", "qwen", "mistral")) and not self.model_name.lower().startswith("groq") and not groq_key

        if use_featherless and featherless_key:
            logger.info(f"[{self.display_name}] Using Featherless OS model: {self.model_name}")
            self.llm = ChatOpenAI(
                base_url="https://api.featherless.ai/v1",
                api_key=featherless_key,
                model=self.model_name,
                temperature=0.1
            )
        elif groq_key and groq_key not in ("your-groq-api-key-here", ""):
            # Determine groq model
            groq_model = self.model_name
            if groq_model.lower().startswith("groq:"):
                groq_model = groq_model[5:]
            elif groq_model.lower().startswith("groq/"):
                groq_model = groq_model[5:]
                
            if not any(x in groq_model.lower() for x in ("llama", "mixtral", "gemma", "qwen", "groq", "canopy", "allam", "openai")):
                groq_model = "llama-3.3-70b-versatile"
            
            logger.info(f"[{self.display_name}] Using Groq model: {groq_model} (free tier)")
            # max_tokens keeps each response within report size and stops the
            # free-tier TPM/TPD admission control from overcounting requests.
            self.llm = ChatGroq(
                api_key=groq_key,
                model=groq_model,
                temperature=0.1,
                max_tokens=1024,
                max_retries=0,  # we handle retry/fallback ourselves in _invoke_resilient
            )
        elif google_key and google_key not in ("your-gemini-api-key-here", ""):
            logger.info(f"[{self.display_name}] Using Gemini model: {self.model_name}")
            self.llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=google_key,
                temperature=0.1,
                max_output_tokens=1024,
                max_retries=0,
            )
        elif (aimlapi_key := os.getenv("AIMLAPI_KEY")) and "your-" not in aimlapi_key:
            aiml_model = os.getenv("ARGUS_AIMLAPI_MODEL", "gpt-4o")
            logger.info(f"[{self.display_name}] Using AI/ML API model: {aiml_model}")
            self.llm = ChatOpenAI(
                base_url="https://api.aimlapi.com/v1",
                api_key=aimlapi_key,
                model=aiml_model,
                temperature=0.1
            )
        else:
            logger.warning(f"[{self.display_name}] No API key configured. Running with dummy mock model.")
            self.llm = self._make_local_llm()
            self.llm_is_local = True

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
        if self.llm.__class__.__name__ == "ChatGroq":
            prompt = f"{prompt}\n\nCRITICAL: You MUST use standard tool calling. Never output XML tags like <function=...> or </function> to call tools."

        if is_mock_mode():
            # In mock mode, combine custom tools with our mock Band tools
            all_tools = self.custom_tools + self._get_mock_tools()
            self._all_tools = all_tools
            self._agent_prompt = prompt
            self._local_executor = None
            self.agent_executor = self._build_executor(self.llm, all_tools, prompt)

        else:
            # Real mode uses thenvoi LangGraphAdapter wrapper which injects actual tools
            from thenvoi.adapters.langgraph import LangGraphAdapter
            from thenvoi import Agent
            agent_id, api_key = self.load_credentials()
            
            self.adapter = LangGraphAdapter(
                llm=self.llm,
                checkpointer=InMemorySaver(),
                additional_tools=self.custom_tools,
                prompt_template=prompt
            )
            self.real_agent = Agent.create(
                adapter=self.adapter,
                agent_id=agent_id,
                api_key=api_key
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
        """Invoke the agent. If the LLM provider is rate-limited or down, retry
        once for transient errors, then degrade to the local simulation engine
        so the response chain always completes."""
        if self.llm_is_local:
            return await self.agent_executor.ainvoke(inputs, config=config)
        if llm_degraded():
            return await self._get_local_executor().ainvoke(inputs, config=config)

        for attempt in range(2):
            try:
                return await self.agent_executor.ainvoke(inputs, config=config)
            except Exception as e:
                err = str(e)
                err_lower = err.lower()
                fatal = any(marker in err_lower for marker in _FATAL_LLM_ERRORS)
                transient_429 = (
                    "429" in err or "RESOURCE_EXHAUSTED" in err or "rate limit" in err_lower
                )
                if not fatal and transient_429 and attempt == 0:
                    delay = 4 + random.uniform(0, 2)
                    logger.warning(
                        f"[{self.display_name}] Rate limited — one retry in {delay:.1f}s..."
                    )
                    await event_bus.broadcast(self.name, "working", {
                        "current_action": f"Rate limited — retrying in {delay:.0f}s"
                    })
                    await asyncio.sleep(delay)
                    continue
                # Daily quota gone, request too large, provider down, or retry
                # already failed: stop hammering and finish on the local engine.
                degrade_llm(err)
                await event_bus.broadcast(self.name, "working", {
                    "current_action": "LLM provider saturated — continuing on local analysis engine"
                })
                break

        return await self._get_local_executor().ainvoke(inputs, config=config)

    async def handle_mock_message(self, sender: str, message: str):
        """Handles a message arriving in Mock Mode, runs LangGraph executor, and broadcasts updates."""
        # Drop the message if we are already processing one — prevents infinite cascades
        if self._is_busy:
            logger.info(f"[{self.display_name}] Busy — dropping duplicate wakeup from '{sender}'")
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
            if self.name == "executive_decision" and "DECISION" in (report or "").upper():
                memory_graph.set_final_decision(incident_id, (report or "")[:500])

            # Blue Team countermeasures become learned defense recipes, so the
            # team recognizes and counters the same technique faster next time
            if self.name == "blue_team_agent":
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
            logger.info(f"[{self.display_name}] Starting Real WebSocket connection to Band AI platform...")
            await self.real_agent.run()
