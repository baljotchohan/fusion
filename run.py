# run.py
"""
Entry point for the ARGUS Autonomous Cyber Defense Command Center.
Launches the FastAPI backend and all 9 specialized AI agents concurrently.
"""
import os
import asyncio
import logging
import socket
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

def _check_port(port: int) -> None:
    """Raise a clear error if the port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", port))
        except OSError:
            raise RuntimeError(
                f"\n\n[ARGUS] Port {port} is already in use.\n"
                f"  → Kill the old process with:  lsof -ti :{port} | xargs kill -9\n"
                f"  → Or set a different port:    PORT={port + 1} python run.py\n"
            )


async def main():
    load_dotenv()
    logger.info("Initializing ARGUS System...")

    port = int(os.getenv("PORT", 8000))

    # Pre-flight port check — fail fast with a helpful message
    _check_port(port)

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
        port=port,
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
    except (SystemExit, OSError) as e:
        logger.error(
            f"[ARGUS] Server failed to start — port {port} may be in use.\n"
            f"  Run:  lsof -ti :{port} | xargs kill -9  then retry.\n"
            f"  Original error: {e}"
        )
        raise
    except Exception as e:
        logger.error(f"ARGUS run encountered an error: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("ARGUS stopped by user.")
