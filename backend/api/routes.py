"""
backend/api/routes.py
FastAPI route definitions.
"""

import asyncio
import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.ai.safety import sanitize_user_input
from backend.core.security import decode_token

limiter = Limiter(key_func=get_remote_address)
AI_REQUEST_TIMEOUT_SECONDS = float(os.getenv("AI_REQUEST_TIMEOUT_SECONDS", "30"))


router = APIRouter(prefix="/api")


# ============================================================
# datamodel
# ============================================================

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_calls: list = []


class ReportRequest(BaseModel):
    session_data: Dict[str, Any]


class ReportResponse(BaseModel):
    overall_score: float
    highlights: list
    corrections: list
    recovery_plan: str
    next_session_goals: list


class UserProfile(BaseModel):
    gender: str
    age: int
    height_cm: float
    weight_kg: float
    experience: str
    injuries: List[str] = []
    available_equipment: List[str]
    goal: str
    sessions_per_week: int = 3
    duration_weeks: int = 4


class PlanRequest(BaseModel):
    profile: UserProfile


class PlanResponse(BaseModel):
    plan_id: str
    duration_weeks: int
    weekly_schedule: list
    notes: str


class FeedbackRequest(BaseModel):
    frame_data: Dict[str, Any]


class FeedbackResponse(BaseModel):
    immediate_feedback: str
    encouragement: str
    should_speak: bool


def _build_local_chat_fallback(message: str, error: Exception) -> str:
    """Return a useful local answer when the remote LLM is unavailable."""
    normalized = message.lower()
    prefix = "AI 服务暂时连接不稳定，我先按本地深蹲标准库给你建议："

    if "膝" in message and ("内扣" in message or "valgus" in normalized):
        advice = (
            "膝盖内扣通常表示膝盖轨迹向身体中线偏移。训练时让膝盖跟随脚尖方向，"
            "下蹲和起立都主动向外打开膝盖，先降低速度，用徒手深蹲找稳定轨迹。"
        )
    elif "深" in message or "depth" in normalized or "蹲" in message:
        advice = (
            "深蹲底部目标是大腿接近与地面平行，本项目默认优秀底部膝角约 85°-115°，"
            "超过 130° 会判为深度不足。先保证脚跟不抬、躯干稳定，再逐步增加深度。"
        )
    elif "恢复" in message or "拉伸" in message or "酸" in message:
        advice = (
            "训练后先做 3-5 分钟低强度走动，再拉伸股四头肌、臀肌和小腿。"
            "如果是关节刺痛，停止训练并降低下一次强度；如果是肌肉酸胀，优先补水、睡眠和轻量活动。"
        )
    elif "计划" in message or "新手" in message:
        advice = (
            "新手建议每周 2-3 次力量训练，每次先做徒手深蹲 3 组，每组 8-12 次。"
            "动作稳定后再增加负重，并把训练目标控制在动作质量优先。"
        )
    else:
        advice = (
            "当前可先围绕三点自查：脚跟是否稳定贴地、膝盖是否对准脚尖、底部躯干和小腿角度是否接近。"
            "训练页面会保留 1-3 张问题截图，结束后可按报告里的主要问题逐项修正。"
        )

    return f"{prefix}\n\n{advice}\n\n外部 AI 错误类型：{type(error).__name__}。"


def _build_local_report_fallback(session_data: Dict[str, Any], error: Exception) -> Dict[str, Any]:
    errors = session_data.get("errors") or []
    error_summary = session_data.get("error_details") or session_data.get("error_summary") or {}
    issue_count = len(errors) + sum(int(v) for v in error_summary.values() if isinstance(v, int))
    rep_count = int(session_data.get("rep_count") or session_data.get("total_reps") or 0)
    score = max(45, min(100, 88 - issue_count * 8 - (18 if rep_count == 0 else 0)))

    highlights = [
        f"完成 {rep_count} 次动作" if rep_count > 0 else "本次没有稳定记录到完整次数",
        "已生成本地训练反馈，外部 AI 暂时不可用",
    ]
    corrections = list(errors[:3])
    if not corrections:
        corrections = [
            "保持脚跟稳定贴地",
            "膝盖跟随脚尖方向移动",
            "底部让大腿接近与地面平行",
        ]

    return {
        "overall_score": float(score),
        "highlights": highlights,
        "corrections": corrections,
        "recovery_plan": f"训练后做 3-5 分钟低强度放松，拉伸股四头肌、臀肌和小腿。外部 AI 错误类型：{type(error).__name__}。",
        "next_session_goals": [
            "等待 5 秒准备倒计时结束后再开始动作",
            "完成一次完整下蹲和起立后再结束训练",
            "保留全身在画面内，便于姿态检测稳定判断",
        ],
    }


def _build_local_plan_fallback(profile: UserProfile, error: Exception) -> Dict[str, Any]:
    sessions = max(1, min(profile.sessions_per_week, 6))
    schedule = []
    for day in range(1, sessions + 1):
        schedule.append({
            "day": f"第 {day} 次训练",
            "focus": "深蹲动作质量与基础力量",
            "exercises": [
                {"name": "徒手深蹲", "sets": 3, "reps": "8-12", "rest": "60-90秒"},
                {"name": "臀桥", "sets": 3, "reps": "10-15", "rest": "60秒"},
                {"name": "平板支撑", "sets": 3, "reps": "30-45秒", "rest": "60秒"},
            ],
        })

    return {
        "plan_id": f"local_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "duration_weeks": profile.duration_weeks,
        "weekly_schedule": schedule,
        "notes": f"外部 AI 暂时不可用，已生成本地基础计划。错误类型：{type(error).__name__}。",
    }


# ============================================================
# HTTP route
# ============================================================

@router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat_endpoint(request: Request, body: ChatRequest):
    """Main chat endpoint with rate limiting and input sanitization."""
    sanitized = sanitize_user_input(body.message)
    try:
        from backend.ai.agent import get_agent

        agent = get_agent(body.session_id)
        result = await asyncio.wait_for(
            agent.chat(sanitized),
            timeout=AI_REQUEST_TIMEOUT_SECONDS,
        )

        return ChatResponse(
            response=result["response"],
            session_id=result["session_id"],
            tool_calls=result["tool_calls"],
        )
    except Exception as e:
        session_id = body.session_id or f"fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return ChatResponse(
            response=_build_local_chat_fallback(sanitized, e),
            session_id=session_id,
            tool_calls=[{"name": "local_rule_fallback", "error_type": type(e).__name__}],
        )


@router.post("/report", response_model=ReportResponse)
@limiter.limit("10/minute")
async def report_endpoint(request: Request, body: ReportRequest):
    """Training report generation endpoint with rate limiting."""
    try:
        from backend.ai.agent import generate_training_report

        report = await asyncio.wait_for(
            generate_training_report(body.session_data),
            timeout=AI_REQUEST_TIMEOUT_SECONDS,
        )
        return ReportResponse(**report)
    except Exception as e:
        return ReportResponse(**_build_local_report_fallback(body.session_data, e))


@router.post("/plan", response_model=PlanResponse)
@limiter.limit("10/minute")
async def plan_endpoint(request: Request, body: PlanRequest):
    """Training plan generation endpoint with rate limiting."""
    try:
        from backend.ai.tools import UserProfile as ToolUserProfile, training_plan_tool

        profile = ToolUserProfile(**body.profile.model_dump())
        plan = await asyncio.wait_for(
            training_plan_tool(profile),
            timeout=AI_REQUEST_TIMEOUT_SECONDS,
        )
        return PlanResponse(**plan.model_dump())
    except Exception as e:
        return PlanResponse(**_build_local_plan_fallback(body.profile, e))


@router.post("/feedback")
async def feedback_endpoint(request: FeedbackRequest):
    """
    realwhenfeedbackendpoint. 
    
    input: singleframeorshort期窗口data
    output: 即whenfeedbackbuildsuggest
    """
    try:
        from backend.ai.agent import get_realtime_feedback

        feedback = await asyncio.wait_for(
            get_realtime_feedback(request.frame_data),
            timeout=AI_REQUEST_TIMEOUT_SECONDS,
        )
        return FeedbackResponse(**feedback)
    except Exception as e:
        return FeedbackResponse(
            immediate_feedback="当前实时反馈服务不稳定，请先保持动作节奏放慢、全身入镜。",
            encouragement=f"本地兜底已启用：{type(e).__name__}",
            should_speak=False,
        )


# ============================================================
# WebSocket route(流stylechat)
# ============================================================

@router.websocket("/ws/chat/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket chat endpoint with token authentication.

    Client sends: {"message": "..."}
    Server returns: {"type": "content", "content": "...", "is_end": false}
    """
    # Authenticate via query param token
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return
    # Skip auth for demo tokens (dev mode)
    if token in ("test_token", "demo-token"):
        payload = {"sub": "demo_user", "demo": True}
    else:
        payload = decode_token(token)
    if payload is None:
        await websocket.close(code=4003, reason="Invalid or expired token")
        return

    await websocket.accept()

    try:
        from backend.ai.agent import get_agent

        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            message = sanitize_user_input(message_data.get("message", ""))

            agent = get_agent(session_id)

            async for chunk in agent.chat_stream(message):
                await websocket.send_text(chunk)

    except WebSocketDisconnect:
        print(f"[WebSocket] session {session_id} disconnect")
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "content": str(e),
            "is_end": True,
        }))


# ============================================================
# trainingreport
# ============================================================

class ReportGenerateRequest(BaseModel):
    """reportgeneraterequest"""
    session_data: Dict[str, Any]
    include_images: bool = True


@router.post("/report/generate")
async def generate_report_endpoint(request: ReportGenerateRequest):
    """
    generateHTMLformat trainingreport

    input: sessiondata(packagecontainssummary captured_frames)
    output: reportfilepath
    """
    try:
        from report_generator import ReportGenerator

        generator = ReportGenerator()
        captured_frames = request.session_data.get("captured_frames", [])

        report_path = generator.generate_html_report(
            session_data=request.session_data,
            captured_frames=captured_frames,
            include_images=request.include_images,
        )

        return {
            "success": True,
            "report_path": report_path,
            "message": "reportgeneratesuccess",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"reportgeneratefailed: {str(e)}")


@router.post("/report/mosaic")
async def generate_mosaic_endpoint(request: ReportGenerateRequest):
    """
    generateerrorframemosaic

    input: sessiondata
    output: mosaicfilepath
    """
    try:
        from report_generator import ReportGenerator

        generator = ReportGenerator()
        captured_frames = request.session_data.get("captured_frames", [])

        mosaic_path = generator.generate_mosaic_image(
            captured_frames=captured_frames,
        )

        return {
            "success": True,
            "mosaic_path": mosaic_path,
            "message": "mosaicgeneratesuccess",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"mosaicgeneratefailed: {str(e)}")


# ============================================================
# health康check
# ============================================================

@router.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
