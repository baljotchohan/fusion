# core/base_agent.py
"""
Base agent class that handles credentials loading, LLM setup,
LangGraph compilation, and tool mapping for both real Band SDK
and offline mock modes.
"""
import os
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

logger = logging.getLogger("argus.base_agent")

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
        self.system_prompt = system_prompt
        self.custom_tools = tools or []
        self.model_name = model_name
        
        load_dotenv()
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = None
        self._setup_llm()
        self.agent_executor = None

    def _setup_llm(self):
        """Set up LLM with priority: Featherless (OSS) → Groq (free/fast) → Gemini (fallback)."""
        google_key = os.getenv("GOOGLE_API_KEY")
        featherless_key = os.getenv("FEATHERLESS_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")

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
            self.llm = ChatGroq(
                api_key=groq_key,
                model=groq_model,
                temperature=0.1
            )
        elif google_key and google_key not in ("your-gemini-api-key-here", ""):
            logger.info(f"[{self.display_name}] Using Gemini model: {self.model_name}")
            self.llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=google_key,
                temperature=0.1
            )
        else:
            logger.warning(f"[{self.display_name}] No API key configured. Running with dummy mock model.")
            self.llm = ChatOpenAI(
                base_url="http://localhost:8000/mock-llm",
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
                config = yaml.safe_load(f)
            agent_conf = config.get(self.name, {})
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
            try:
                self.agent_executor = create_react_agent(
                    model=self.llm,
                    tools=all_tools,
                    prompt=prompt
                )
            except TypeError:
                self.agent_executor = create_react_agent(
                    model=self.llm,
                    tools=all_tools,
                    state_modifier=prompt
                )

        else:
            # Real mode uses thenvoi LangGraphAdapter wrapper which injects actual tools
            from thenvoi.adapters import LangGraphAdapter
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

    async def handle_mock_message(self, sender: str, message: str):
        """Handles a message arriving in Mock Mode, runs LangGraph executor, and broadcasts updates."""
        logger.info(f"[{self.display_name}] Wakeup! Message from '{sender}': {message[:80]}...")
        
        # Broadcast "working" state to event bus/dashboard
        await event_bus.broadcast(self.name, "working", {"current_action": f"Analyzing input from {sender}"})
        
        max_retries = 10

        for attempt in range(max_retries):
            try:
                # Invoke compiled React agent
                inputs = {"messages": [("user", f"Message from {sender}: {message}")]}
                config = {"configurable": {"thread_id": self.name}}
                
                response = await self.agent_executor.ainvoke(inputs, config=config)
                
                final_thought = response["messages"][-1].content
                logger.info(f"[{self.display_name}] Completed task. Final Thought: {final_thought[:100]}...")
                
                # Broadcast "done" state with final report
                await event_bus.broadcast(self.name, "done", {"report": final_thought})
                return

            except Exception as e:
                err_str = str(e)
                is_rate_limit = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower()

                if is_rate_limit and attempt < max_retries - 1:
                    # Short linear backoff delay for faster retries since rate limits are milder on the new model
                    delay = 5 + attempt * 2 + random.uniform(0, 3)
                    logger.warning(
                        f"[{self.display_name}] Rate limited (429). "
                        f"Retry {attempt + 1}/{max_retries - 1} in {delay:.1f}s..."
                    )
                    await event_bus.broadcast(self.name, "working", {
                        "current_action": f"Rate limited — retrying in {delay:.0f}s (attempt {attempt + 1})"
                    })
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[{self.display_name}] Error running agent: {e}")
                    await event_bus.broadcast(self.name, "alert", {"error": str(e)})
                    return

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
