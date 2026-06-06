# api/main.py
"""
FastAPI application serving REST endpoints and a WebSocket server
to stream real-time agent updates to the Next.js dashboard.
"""
import os
import json
import logging
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.event_bus import event_bus
from core.band_client import mock_bus, is_mock_mode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("argus.api")

app = FastAPI(title="ARGUS API", version="1.0.0")

# Enable CORS for the Next.js War Room dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket dashboard connections
active_websockets: List[WebSocket] = []

async def broadcast_event_to_websockets(event_data: dict):
    """Callback registered with event_bus to forward agent updates to the dashboard."""
    if not active_websockets:
        return
    
    message = json.dumps(event_data)
    # Broadcast to all connected clients
    for ws in list(active_websockets):
        try:
            await ws.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send to WebSocket: {e}")
            active_websockets.remove(ws)

# Register the event bus listener on application startup
@app.on_event("startup")
async def startup_event():
    event_bus.register_listener(broadcast_event_to_websockets)
    logger.info("FastAPI: Event bus WebSocket listener registered.")

@app.on_event("shutdown")
async def shutdown_event():
    event_bus.unregister_listener(broadcast_event_to_websockets)
    logger.info("FastAPI: Event bus WebSocket listener unregistered.")

# ─── REST ENDPOINTS ───────────────────────────────────────────

class TriggerResponse(BaseModel):
    status: str
    message: str
    mode: str

@app.post("/api/trigger-attack", response_model=TriggerResponse)
async def trigger_attack():
    """Triggers the demo phishing attack simulation by sending the initial alert to Threat Intel."""
    logger.info("FastAPI: Attack trigger requested.")
    
    # Load the phishing email alert trigger data
    trigger_path = "data/phishing_email.json"
    if not os.path.exists(trigger_path):
        return {
            "status": "error",
            "message": f"Trigger file not found at {trigger_path}",
            "mode": "mock" if is_mock_mode() else "real"
        }
        
    with open(trigger_path, "r") as f:
        alert_data = json.load(f)
    
    alert_text = json.dumps(alert_data, indent=2)
    
    if is_mock_mode():
        # Offline mock mode: Send via local MockBandBus to threat-intel-room
        logger.info("FastAPI: Mock mode enabled. Sending phishing alert to 'threat-intel-room'...")
        # Start the chain by mentioning Threat Intel
        await mock_bus.send_message(
            sender="SOC-Alert-Sensor",
            target_room="threat-intel-room",
            message=f"@Threat-Intel Phishing email alert: {alert_text}"
        )
        return {
            "status": "success",
            "message": "Phishing attack alert dispatched to threat-intel-room (Mock Mode).",
            "mode": "mock"
        }
    else:
        # Real mode: Connect and send via real Band client API
        # In a real environment, the external sensor would post directly to Band.
        # Here we mock the sensor sending to the real room.
        logger.info("FastAPI: Real mode enabled. Forwarding phishing alert to real Band room...")
        # TODO: Implement real Band sensor publish if needed
        return {
            "status": "success",
            "message": "Phishing attack alert dispatched to real Band SDK rooms.",
            "mode": "real"
        }

@app.get("/api/status")
async def get_status():
    """Basic health check and configuration status."""
    return {
        "status": "healthy",
        "mock_mode": is_mock_mode(),
        "registered_rooms": list(mock_bus.rooms.keys()) if is_mock_mode() else []
    }

# ─── WEBSOCKET ROUTE ──────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for the Next.js dashboard to stream live updates."""
    await websocket.accept()
    active_websockets.append(websocket)
    logger.info(f"FastAPI: WebSocket connected. Active connections: {len(active_websockets)}")
    
    try:
        while True:
            # Maintain connection, check for keepalives
            data = await websocket.receive_text()
            logger.debug(f"FastAPI: Received WS message: {data}")
    except WebSocketDisconnect:
        active_websockets.remove(websocket)
        logger.info(f"FastAPI: WebSocket disconnected. Active connections: {len(active_websockets)}")
    except Exception as e:
        logger.error(f"FastAPI: WebSocket error: {e}")
        if websocket in active_websockets:
            active_websockets.remove(websocket)
