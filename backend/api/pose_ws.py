"""
backend/api/pose_ws.py
WebSocket endpoint for real-time pose landmark processing.

Receives landmarks from the frontend MediaPipe detector,
runs geometry analysis + FSM state machine, returns status updates.
"""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.security import decode_token

# Import algorithm modules from project root
_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)
from geometry import SquatGeometry
from fsm import SquatFSM
from view_classifier import ViewClassifier, get_enabled_metrics

_RULES_PATH = os.path.join(_root, "configs", "movement_rules.json")

router = APIRouter()


def _landmark_to_obj(lm_dict: dict):
    """Convert a landmark dict {x, y, z, visibility} to an object with .x, .y, .visibility attrs."""
    return SimpleNamespace(
        x=lm_dict["x"],
        y=lm_dict["y"],
        visibility=lm_dict.get("visibility", 0.5),
    )


def _to_serializable(obj):
    """Ensure all values in a dict are JSON-serializable."""
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_serializable(v) for v in obj]
    if isinstance(obj, float):
        if obj != obj:  # NaN
            return None
        return obj
    return obj


@router.websocket("/ws/pose/{session_id}")
async def pose_ws_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time pose processing.

    Client sends:
        {"type": "landmarks", "landmarks": [{x, y, z, visibility}, ...], "timestamp": number}

    Server returns:
        {"type": "status", "state": "...", "rep_count": N, "knee_angle": N,
         "hip_angle": N, "errors": [...], "warnings": [...], "knee_velocity": N}
    """
    # Authenticate
    token = websocket.query_params.get("token")
    # Skip auth for demo tokens (dev mode)
    if token in ("test_token", "demo-token"):
        payload = {"sub": "demo_user", "demo": True}
    else:
        if not token:
            await websocket.close(code=4001, reason="Missing authentication token")
            return
        payload = decode_token(token)
        if payload is None:
            await websocket.close(code=4003, reason="Invalid or expired token")
            return

    # Per-session algorithm instances
    geometry = SquatGeometry()
    fsm = SquatFSM(rules_path=_RULES_PATH)
    view_classifier = ViewClassifier(fsm.view_classifier_config)

    await websocket.accept()
    print(f"[PoseWS] session {session_id} connected")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") != "landmarks":
                continue

            raw_landmarks = message.get("landmarks", [])
            if not raw_landmarks:
                continue

            # Convert dict landmarks to objects with .x, .y attributes
            landmarks = [_landmark_to_obj(lm) for lm in raw_landmarks]

            # Geometry analysis
            geo = geometry.analyze(landmarks)

            if geo is None:
                await websocket.send_text(json.dumps({
                    "type": "status",
                    "state": "no_person",
                    "rep_count": fsm.rep_count,
                    "knee_angle": 180,
                    "hip_angle": 180,
                    "errors": [],
                    "warnings": [],
                    "knee_velocity": 0,
                }))
                continue

            # View classification
            view_info = view_classifier.classify(landmarks)
            view_mode = view_info["view_mode"]

            # Client can request a specific view mode; use detected mode but warn on mismatch
            requested_view = message.get("view_mode_requested")
            view_warnings = list(view_info.get("warnings", []))
            if requested_view and requested_view != view_mode and view_mode != "unknown":
                label_map = {"front": "正面", "side_left": "左侧", "side_right": "右侧", "oblique": "斜角"}
                view_warnings.append(
                    f"Requested {requested_view} but detected {label_map.get(view_mode, view_mode)}"
                )

            # Get enabled metrics for this view mode
            enabled_metrics, disabled_metrics = get_enabled_metrics(
                view_mode, fsm.camera_views_config
            )

            # FSM update (view-aware)
            status = fsm.update(geo, view_mode, enabled_metrics)

            # Build response with both current frame and accumulated errors
            current_rep = status.get("current_rep", {})
            session_errors = current_rep.get("errors", []) if current_rep else []
            session_warnings = current_rep.get("warnings", []) if current_rep else []

            # Generate correction and safety messages based on current state and errors
            correction = ""
            safety = ""

            # Extract error types from error_details (reliable type keys)
            error_detail_types = [d["type"] for d in status.get("error_details", [])]

            # Generate correction based on errors
            if "trunk_forward_lean" in error_detail_types:
                correction = "保持背部挺直，核心收紧，避免过度前倾"
            elif "knee_valgus" in error_detail_types:
                correction = "膝盖对准脚尖方向，不要内扣，感受臀部发力"
            elif "insufficient_depth" in error_detail_types:
                correction = "尝试蹲得更低，大腿至少与地面平行"
            elif status["errors"]:
                correction = "注意动作质量，保持正确姿势"
            elif status["warnings"]:
                warning_types = [w.split(":")[0] if ":" in w else w for w in status["warnings"]]
                if "hip_dominant" in warning_types:
                    correction = "臀部往后坐多一些，增加膝盖弯曲"
                elif "knee_dominant" in warning_types:
                    correction = "臀部向后推送，让躯干更直立"
                elif "heel_lift" in warning_types:
                    correction = "重心放在脚后跟，保持稳定"

            # Generate safety warning for dangerous situations
            if fsm.state.value in ["descending", "bottom"]:
                knee_angle = status.get("knee_angle", 180)
                if knee_angle < 60:
                    safety = "注意：膝盖弯曲过大，小心关节压力"
                elif "knee_valgus" in error_detail_types:
                    safety = "膝盖内扣可能增加受伤风险，请注意纠正"

            # Send filtered status to frontend
            response = _to_serializable({
                "type": "status",
                "state": status["state"],
                "rep_count": status["rep_count"],
                "knee_angle": status["knee_angle"],
                "hip_angle": status["hip_angle"],
                "errors": status["errors"],
                "warnings": status["warnings"],
                "session_errors": session_errors,
                "session_warnings": session_warnings,
                "knee_velocity": status["knee_velocity"],
                # Real-time feedback
                "correction": correction,
                "safety": safety,
                # View-aware fields
                "view_mode": view_mode,
                "view_confidence": view_info["confidence"],
                "view_warnings": view_warnings,
                "valid_metrics": enabled_metrics,
                "disabled_metrics": disabled_metrics,
            })
            await websocket.send_text(json.dumps(response))

    except WebSocketDisconnect:
        print(f"[PoseWS] session {session_id} disconnected")
    except Exception as e:
        print(f"[PoseWS] session {session_id} error: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e),
            }))
        except Exception:
            pass
