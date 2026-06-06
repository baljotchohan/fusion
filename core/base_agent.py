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
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
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
        self._setup_llm()
        self.agent_executor = None

    def _setup_llm(self):
        """Set up the primary Gemini LLM or fallback Featherless LLM."""
        google_key = os.getenv("GOOGLE_API_KEY")
        featherless_key = os.getenv("FEATHERLESS_API_KEY")
        
        # Determine if we should use Featherless (for specific agents or fallback)
        use_featherless = "llama" in self.model_name.lower() or "qwen" in self.model_name.lower() or "mistral" in self.model_name.lower()
        
        if use_featherless and featherless_key:
            logger.info(f"[{self.display_name}] Using Featherless OS model: {self.model_name}")
            self.llm = ChatOpenAI(
                base_url="https://api.featherless.ai/v1",
                api_key=featherless_key,
                model=self.model_name,
                temperature=0.1
            )
        elif google_key and google_key != "your-gemini-api-key-here":
            logger.info(f"[{self.display_name}] Using Gemini model: {self.model_name}")
            self.llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=google_key,
                temperature=0.1
            )
        else:
            # Local fallback or dummy config for offline execution testing
            logger.warning(f"[{self.display_name}] No API key configured. Running with dummy mock model.")
            self.llm = ChatOpenAI(
                base_url="http://localhost:8000/mock-llm",  # Fake endpoint
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

    def _get_mock_tools(self) -> List[Any]:
        """Creates mock versions of Band SDK platform tools for offline testing."""
        
        @tool
        def mock_thenvoi_send_message(room: str, message: str) -> str:
            """Send a message to another agent room on the Band platform.
            Use this to @mention and collaborate with other agents."""
            asyncio.create_task(mock_bus.send_message(self.display_name, room, message))
            return f"Message sent successfully to room {room}."

        @tool
        def mock_thenvoi_send_event(event: str, data: Optional[Dict[str, Any]] = None) -> str:
            """Broadcast an operational status update or thought to the war room dashboard.
            Use this to report progress, findings, or completed steps."""
            # Capture if it's a progress event or outcome
            logger.info(f"[{self.display_name}] Operation Event: {event}")
            asyncio.create_task(event_bus.broadcast(self.name, "working", {"event": event, "data": data or {}}))
            return "Event reported successfully."

        @tool
        def mock_thenvoi_lookup_peers() -> List[str]:
            """Retrieve the list of active agent rooms available on the platform."""
            return list(mock_bus.rooms.keys())

        @tool
        def mock_thenvoi_add_participant(room: str, agent: str) -> str:
            """Add/recruit a specialist agent to the active chat room dynamically."""
            logger.info(f"[{self.display_name}] Recruited agent {agent} into room {room}")
            return f"Successfully added agent {agent} to room {room}."

        return [mock_thenvoi_send_message, mock_thenvoi_send_event, mock_thenvoi_lookup_peers, mock_thenvoi_add_participant]

    def compile_agent(self):
        """Compiles the LangGraph agent executor."""
        if is_mock_mode():
            # In mock mode, combine custom tools with our mock Band tools
            all_tools = self.custom_tools + self._get_mock_tools()
            self.agent_executor = create_react_agent(
                model=self.llm,
                tools=all_tools,
                state_modifier=self.system_prompt
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
                state_modifier=self.system_prompt
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
        
        try:
            # Invoke compiled React agent
            inputs = {"messages": [("user", f"Message from {sender}: {message}")]}
            
            # Run the agent graph asynchronously
            # We wrap it in a thread-safe executor or direct async call if it's runnable
            config = {"configurable": {"thread_id": self.name}}
            
            response = await self.agent_executor.ainvoke(inputs, config=config)
            
            final_thought = response["messages"][-1].content
            logger.info(f"[{self.display_name}] Completed task. Final Thought: {final_thought[:100]}...")
            
            # Broadcast "done" state with final report
            await event_bus.broadcast(self.name, "done", {"report": final_thought})
            
        except Exception as e:
            logger.error(f"[{self.display_name}] Error running agent: {e}")
            await event_bus.broadcast(self.name, "alert", {"error": str(e)})

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
