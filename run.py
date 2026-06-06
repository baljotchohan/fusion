# run.py
"""
Entry point for the ARGUS Autonomous Cyber Defense Command Center.
Launches the FastAPI backend and all 9 specialized AI agents concurrently.
"""
import os
import asyncio
import logging
import uvicorn
from dotenv import load_dotenv

# Import all agents
from agents.threat_intel import ThreatIntelAgent
from agents.recon import ReconAgent
from agents.red_team import RedTeamAgent
from agents.attack_path import AttackPathAgent
from agents.detection import DetectionAgent
from agents.malware import MalwareAgent
from agents.blue_team import BlueTeamAgent
from agents.incident_commander import IncidentCommander
from agents.executive_decision import ExecutiveDecisionAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("argus.run")

async def main():
    load_dotenv()
    logger.info("Initializing ARGUS System...")

    # Instantiate all 9 agents
    agents = [
        ThreatIntelAgent(),
        ReconAgent(),
        RedTeamAgent(),
        AttackPathAgent(),
        DetectionAgent(),
        MalwareAgent(),
        BlueTeamAgent(),
        IncidentCommander(),
        ExecutiveDecisionAgent()
    ]

    # Instantiate Uvicorn Config and Server for FastAPI API + WebSockets
    config = uvicorn.Config(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        loop="asyncio"
    )
    server = uvicorn.Server(config)

    # Start FastAPI backend and run all agents concurrently
    logger.info("Starting FastAPI backend and all 9 Band agents concurrently...")
    
    tasks = [server.serve()] + [agent.run() for agent in agents]
    
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("ARGUS tasks cancelled. Shutting down...")
    except Exception as e:
        logger.error(f"ARGUS run encountered an error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("ARGUS stopped by user.")
