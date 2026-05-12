import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.base import GenericResponse
from app.services.auth_service import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/digital-twin", tags=["Digital Twin"])

# Static ship manifest — would come from actual ship data integration in prod
SHIP_MANIFEST = [
    {
        "ship_id": "INS-VIKRANT-R11",
        "name": "INS Vikrant",
        "class": "Vikrant-class Aircraft Carrier",
        "hull_number": "R11",
        "commissioned": "2022-09-02",
        "displacement_tonnes": 45000,
        "home_port": "Karwar",
        "status": "operational",
    },
    {
        "ship_id": "INS-VISHAKHAPATNAM-D66",
        "name": "INS Vishakhapatnam",
        "class": "Visakhapatnam-class Destroyer",
        "hull_number": "D66",
        "commissioned": "2021-11-21",
        "displacement_tonnes": 7400,
        "home_port": "Mumbai",
        "status": "operational",
    },
    {
        "ship_id": "INS-DRONACHARYA-SHORE",
        "name": "INS Dronacharya",
        "class": "Gunnery School (Shore Establishment)",
        "hull_number": "N/A",
        "commissioned": "1969-01-01",
        "displacement_tonnes": 0,
        "home_port": "Kochi",
        "status": "operational",
    },
]


# Twin state connection manager for WebSocket broadcasts
class TwinConnectionManager:
    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, ship_id: str, ws: WebSocket):
        await ws.accept()
        if ship_id not in self.active:
            self.active[ship_id] = []
        self.active[ship_id].append(ws)

    def disconnect(self, ship_id: str, ws: WebSocket):
        if ship_id in self.active and ws in self.active[ship_id]:
            self.active[ship_id].remove(ws)

    async def broadcast(self, ship_id: str, message: dict):
        for ws in list(self.active.get(ship_id, [])):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(ship_id, ws)


twin_manager = TwinConnectionManager()


def _get_ship_by_id(ship_id: str) -> dict | None:
    return next((s for s in SHIP_MANIFEST if s["ship_id"] == ship_id), None)


def _generate_ship_state(ship: dict) -> dict:
    """Generate a realistic mock digital twin state for a ship."""
    return {
        "ship_id": ship["ship_id"],
        "name": ship["name"],
        "timestamp": datetime.now(UTC).isoformat(),
        "position": {"lat": 15.3173, "lon": 73.9614},
        "heading_deg": 45,
        "speed_knots": 12.5,
        "depth_m": 0,
        "systems": {
            "propulsion": {
                "status": "operational",
                "rpm": 180,
                "fuel_percent": 78.3,
            },
            "navigation": {
                "status": "operational",
                "gps_fix": True,
                "radar_active": True,
            },
            "weapons": {
                "status": "safe",
                "systems_online": ["76mm-gun", "CIWS", "AK-630"],
            },
            "damage_control": {
                "status": "normal",
                "flooding_alerts": [],
                "fire_alerts": [],
            },
            "communications": {
                "status": "operational",
                "hf_link": True,
                "satcom": True,
                "iff_mode": 3,
            },
            "power": {
                "status": "operational",
                "generators_active": 2,
                "bus_voltage_v": 440,
                "load_percent": 62.1,
            },
        },
        "crew_readiness": 0.92,
        "readiness_state": "C1",
    }


def _generate_system_graph(ship: dict) -> dict:
    """Generate a system dependency graph for a ship."""
    return {
        "ship_id": ship["ship_id"],
        "nodes": [
            {"id": "propulsion", "label": "Propulsion", "type": "mechanical"},
            {"id": "power", "label": "Power Generation", "type": "electrical"},
            {"id": "navigation", "label": "Navigation Suite", "type": "electronic"},
            {"id": "damage_control", "label": "Damage Control", "type": "safety"},
            {"id": "weapons", "label": "Weapons Systems", "type": "combat"},
            {"id": "comms", "label": "Communications", "type": "electronic"},
            {"id": "fuel", "label": "Fuel System", "type": "mechanical"},
        ],
        "edges": [
            {"from": "power", "to": "propulsion", "type": "depends_on"},
            {"from": "power", "to": "navigation", "type": "depends_on"},
            {"from": "power", "to": "weapons", "type": "depends_on"},
            {"from": "power", "to": "comms", "type": "depends_on"},
            {"from": "fuel", "to": "propulsion", "type": "depends_on"},
            {"from": "fuel", "to": "power", "type": "depends_on"},
            {"from": "navigation", "to": "weapons", "type": "feeds"},
            {"from": "damage_control", "to": "propulsion", "type": "monitors"},
            {"from": "damage_control", "to": "power", "type": "monitors"},
        ],
    }


@router.get(
    "/ships",
    response_model=GenericResponse[list[dict]],
    summary="List Ship Manifest",
    description=(
        "Retrieve the complete registry of naval vessels available in the "
        "Aegis fleet management system."
    ),
)
async def list_ships(
    current_user: User = Depends(get_current_user),
):
    """Return the ship manifest."""
    return {
        "success": True,
        "message": "Ship manifest retrieved",
        "data": SHIP_MANIFEST,
    }


@router.get(
    "/{ship_id}",
    response_model=GenericResponse[dict],
    summary="Get Digital Twin State",
    description=(
        "Retrieve real-time telemetry, position, and system health status for "
        "a specific vessel's digital twin."
    ),
)
async def get_ship_twin(
    ship_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get the current digital twin state for a ship."""
    ship = _get_ship_by_id(ship_id)
    if not ship:
        raise HTTPException(status_code=404, detail="Ship not found in manifest")

    state = _generate_ship_state(ship)
    return {
        "success": True,
        "message": "Ship twin state retrieved",
        "data": state,
    }


@router.get(
    "/{ship_id}/systems",
    response_model=GenericResponse[dict],
    summary="Get System Dependency Graph",
    description=(
        "Retrieve a structural mapping of ship systems (Propulsion, Power, Weapons) "
        "and their operational dependencies."
    ),
)
async def get_ship_systems(
    ship_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get the system dependency graph for a ship."""
    ship = _get_ship_by_id(ship_id)
    if not ship:
        raise HTTPException(status_code=404, detail="Ship not found in manifest")

    graph = _generate_system_graph(ship)
    return {
        "success": True,
        "message": "System graph retrieved",
        "data": graph,
    }


@router.post(
    "/{ship_id}/simulate",
    response_model=GenericResponse[dict],
    summary="Simulate System Fault",
    description=(
        "Inject a synthetic failure or degradation into a ship system to test "
        "crew readiness and damage control response."
    ),
)
async def simulate_fault(
    ship_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
):
    """
    Simulate a fault scenario on a ship system.
    Body: {"system": "propulsion", "fault_type": "partial_failure", "severity": 0.7}
    """
    ship = _get_ship_by_id(ship_id)
    if not ship:
        raise HTTPException(status_code=404, detail="Ship not found in manifest")

    system = body.get("system", "propulsion")
    fault_type = body.get("fault_type", "partial_failure")
    severity = float(body.get("severity", 0.5))

    # Generate affected systems based on dependency graph
    dependency_map = {
        "power": ["navigation", "weapons", "comms", "propulsion"],
        "propulsion": ["speed"],
        "navigation": ["weapons"],
        "fuel": ["propulsion", "power"],
    }

    cascade_effects = dependency_map.get(system, [])

    simulation_result = {
        "ship_id": ship_id,
        "simulation_id": str(uuid.uuid4()),
        "fault": {
            "system": system,
            "fault_type": fault_type,
            "severity": severity,
        },
        "affected_systems": cascade_effects,
        "estimated_restoration_minutes": int(20 + severity * 60),
        "damage_control_actions": [
            f"Isolate {system} from main bus",
            f"Activate backup {system} if available",
            f"Dispatch damage control team to {system} compartment",
        ],
        "simulated_at": datetime.now(UTC).isoformat(),
    }

    # Broadcast to connected WebSocket clients
    await twin_manager.broadcast(ship_id, {"type": "fault_simulation", **simulation_result})

    return {
        "success": True,
        "message": "Fault simulation complete",
        "data": simulation_result,
    }


@router.websocket("/ws/digital-twin/{ship_id}")
async def digital_twin_websocket(
    ship_id: str,
    websocket: WebSocket,
):
    """
    WebSocket for live ship telemetry stream.
    Client authenticates with JWT as first message, then receives telemetry ticks.
    """
    await websocket.accept()

    try:
        auth_msg = await websocket.receive_text()
        payload = verify_token(auth_msg)
        if payload is None:
            await websocket.send_json({"type": "error", "detail": "Unauthorized"})
            await websocket.close(code=4001)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    ship = _get_ship_by_id(ship_id)
    if not ship:
        await websocket.send_json({"type": "error", "detail": "Ship not found"})
        await websocket.close(code=4004)
        return

    if ship_id not in twin_manager.active:
        twin_manager.active[ship_id] = []
    twin_manager.active[ship_id].append(websocket)

    await websocket.send_json({"type": "connected", "ship_id": ship_id})

    try:
        while True:
            # Receive keep-alives or commands from client
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                msg = {"raw": data}

            if msg.get("type") == "request_state":
                state = _generate_ship_state(ship)
                await websocket.send_json({"type": "state_update", "data": state})

    except WebSocketDisconnect:
        twin_manager.disconnect(ship_id, websocket)
        logger.info("Digital twin WS disconnect: ship=%s", ship_id)
    except Exception as exc:
        logger.error("Digital twin WS error: ship=%s error=%s", ship_id, exc)
        twin_manager.disconnect(ship_id, websocket)
