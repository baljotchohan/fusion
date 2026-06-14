#!/usr/bin/env python3
"""
test_band_connection.py
─────────────────────────────────────────────────────────────────
Quick smoke-test for your Band AI credential.
Connects ONE real agent to Band, listens for messages, and
echoes them back so you can confirm the WebSocket round-trip.

Usage:
    python3.13 test_band_connection.py

Expected output:
    ✅ Agent created — connecting WebSocket...
    📨 Listening for messages (send one from the Band dashboard)...
    [Ctrl+C to stop]
"""

import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("band_test")

# ── Your credentials ──────────────────────────────────────────
import yaml
with open("agent_config.yaml", "r") as f:
    _config = yaml.safe_load(f) or {}
AGENT_ID = _config.get("managing_partner", {}).get("agent_id", "4695d3aa-4ad8-47ca-9573-c31801a38e6c")
API_KEY  = _config.get("managing_partner", {}).get("api_key", "band_a_1781364822_XCak89KrQLYEBeZRaXJcxeqSwuSRIbFL")
# ─────────────────────────────────────────────────────────────


async def main():
    from thenvoi import Agent
    from thenvoi.core.simple_adapter import SimpleAdapter
    from thenvoi import PlatformMessage

    print("\n🔌 Connecting to Band platform...")

    message_count = 0

    class EchoAdapter(SimpleAdapter):
        """Minimal adapter: logs every incoming message and sends a reply."""

        async def on_message(
            self,
            msg: "PlatformMessage",
            tools,
            history,
            participants_msg,
            contacts_msg,
            *,
            is_session_bootstrap: bool,
            room_id: str,
        ) -> None:
            nonlocal message_count
            message_count += 1
            content = getattr(msg, "content", str(msg))
            sender  = getattr(msg, "sender",  "unknown")
            logger.info(f"📨 Message #{message_count} from '{sender}' in room '{room_id}': {content[:200]}")

            # Extract sender handle for the mandatory @mention in reply
            raw_sender = getattr(msg, "sender_handle", None) or getattr(msg, "sender", None)
            sender_handle = str(raw_sender) if raw_sender else "baljotchohan23"

            # Echo back — send_message requires at least one mention
            reply = f"[ARGUS echo] Got your message: {content[:120]}"
            try:
                await tools.send_message(content=reply, mentions=[sender_handle])
                logger.info(f"✉️  Reply sent → @{sender_handle}")
            except Exception as e:
                logger.warning(f"Could not send reply: {e}")
                # Fallback: try with the known handle directly
                try:
                    await tools.send_message(content=reply, mentions=["baljotchohan23"])
                    logger.info("✉️  Reply sent via fallback mention")
                except Exception as e2:
                    logger.warning(f"Fallback also failed: {e2}")

    adapter = EchoAdapter()

    agent = Agent.create(
        adapter=adapter,
        agent_id=AGENT_ID,
        api_key=API_KEY,
    )

    print(f"✅ Agent created — connecting WebSocket...")
    print(f"   Agent ID : {AGENT_ID}")
    print(f"   Handle   : @baljotchohan23/demo")
    print()
    print("📨 Listening for messages.")
    print("   → Go to app.thenvoi.com (Band dashboard)")
    print("   → Open any room and @mention your demo agent")
    print("   → You should see the message printed here + an echo reply in Band")
    print("   Press Ctrl+C to stop.\n")

    try:
        await agent.run()
    except KeyboardInterrupt:
        print(f"\n🛑 Stopped. Received {message_count} message(s) during the test.")


if __name__ == "__main__":
    asyncio.run(main())
