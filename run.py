# run.py
"""
Entry point for FUSION — AI-Powered Venture Capital Investment Committee.
Launches the FastAPI backend and all 5 specialized VC partner agents concurrently.
"""
import os
import asyncio
import logging
import socket
import uvicorn
from dotenv import load_dotenv

# Import FUSION agents
from agents.managing_partner import ManagingPartner
from agents.financial_partner import FinancialPartner
from agents.legal_partner import LegalPartner
from agents.technical_partner import TechnicalPartner
from agents.market_partner import MarketPartner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fusion.run")

def _check_port(port: int) -> None:
    """Raise a clear error if the port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", port))
        except OSError:
            raise RuntimeError(
                f"\n\n[FUSION] Port {port} is already in use.\n"
                f"  → Kill the old process with:  lsof -ti :{port} | xargs kill -9\n"
                f"  → Or set a different port:    PORT={port + 1} python run.py\n"
            )


async def main():
    load_dotenv(override=True)
    logger.info("⚖️  Initializing FUSION Investment Committee...")

    port = int(os.getenv("PORT", 8000))
    _check_port(port)

    # Instantiate all 5 FUSION partner agents
    agents = [
        ManagingPartner(),      # Orchestrator — chairs the committee
        FinancialPartner(),     # Revenue, burn, unit economics
        LegalPartner(),         # Litigation, IP, regulatory
        TechnicalPartner(),     # Stack, security, scalability
        MarketPartner(),        # TAM, competition, sector timing
    ]

    logger.info(f"  ✓ Managing Partner — managing-partner-room")
    logger.info(f"  ✓ Financial Partner — finance-partner-room")
    logger.info(f"  ✓ Legal Partner — legal-partner-room")
    logger.info(f"  ✓ Technical Partner — tech-partner-room")
    logger.info(f"  ✓ Market Partner — market-partner-room")

    # FastAPI backend + WebSockets
    config = uvicorn.Config(
        "api.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        loop="asyncio"
    )
    server = uvicorn.Server(config)

    async def run_agent_with_delay(agent, delay: float):
        if delay > 0:
            logger.info(f"  → Staggering startup: waiting {delay}s before starting {agent.__class__.__name__}...")
            await asyncio.sleep(delay)
        await agent.run()

    logger.info(f"Starting FUSION backend on port {port} and all 5 partner agents...")

    # 2s minimum gives FastAPI time to register event-bus listeners before agents start
    tasks = [server.serve()] + [run_agent_with_delay(agent, 2.0 + i * 4.0) for i, agent in enumerate(agents)]

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("FUSION tasks cancelled. Shutting down committee...")
    except (SystemExit, OSError) as e:
        logger.error(
            f"[FUSION] Server failed to start — port {port} may be in use.\n"
            f"  Run:  lsof -ti :{port} | xargs kill -9  then retry.\n"
            f"  Original error: {e}"
        )
        raise
    except Exception as e:
        logger.error(f"FUSION encountered an error: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("FUSION stopped. Committee adjourned.")
