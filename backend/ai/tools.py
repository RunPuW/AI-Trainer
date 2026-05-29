"""
backend/ai/tools.py
Agent worktooldefine - place worktoolalluse pydantic defineparameter output Schema
"""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool

from backend.ai.llm_client import get_default_llm


# ============================================================
# 1. knowknow检searchworktool (RAG)
# ============================================================

class KnowledgeInput(BaseModel):
    """knowknow检searchinputparameter"""
    question: str = Field(description="user ask题")
    top_k: int = Field(default=3, description="return text档numamount")


class KnowledgeOutput(BaseModel):
    """knowknow检searchoutput"""
    documents: List[Dict[str, Any]] = Field(description="检searchto text档list")
    answer: str = Field(description="based_on检searchresult 摘need回答")


async def knowledge_retrieval_tool(input_data: KnowledgeInput) -> KnowledgeOutput:
    """
    Search the fitness knowledge base and return relevant documents.

    Example queries:
    - "squat knee valgus what to do?"
    - "deadlift vs squat differences"
    """
    from backend.rag import search_knowledge

    results = search_knowledge(input_data.question, top_k=input_data.top_k)

    if not results:
        return KnowledgeOutput(
            documents=[],
            answer="No relevant knowledge found in the database.",
        )

    # Build a summary from the retrieved documents
    summaries = [doc["content"][:200] for doc in results]
    answer = "Based on the knowledge base: " + " ".join(summaries)

    return KnowledgeOutput(
        documents=results,
        answer=answer,
    )


# ============================================================
# 2. trainingplangenerateworktool
# ============================================================

class UserProfile(BaseModel):
    """userprofile"""
    gender: str = Field(description="ity别: male/female")
    age: int = Field(description="年龄")
    height_cm: float = Field(description="bodyhigh(cm)")
    weight_kg: float = Field(description="bodyre(kg)")
    experience: str = Field(description="经验: beginner/intermediate/advanced")
    injuries: List[str] = Field(default_factory=list, description="injury病history")
    available_equipment: List[str] = Field(description="canuseMachine: barbell, dumbbell, bodyweight etc")
    goal: str = Field(description="target: strength, hypertrophy, fat_loss, endurance")
    sessions_per_week: int = Field(default=3, description="perweektrainingcount")
    duration_weeks: int = Field(default=4, description="training plan duration in weeks")


class TrainingPlanOutput(BaseModel):
    """trainingplanoutput Schema"""
    plan_id: str = Field(description="planID")
    duration_weeks: int = Field(description="periodnum(week)")
    weekly_schedule: List[Dict] = Field(description="perweek安row_arr")
    notes: str = Field(description="note事项")
    
    class Config:
        json_schema_extra = {
            "example": {
                "plan_id": "plan_20250624_001",
                "duration_weeks": 4,
                "weekly_schedule": [
                    {
                        "day": "week ",
                        "focus": "down肢Strength",
                        "exercises": [
                            {"name": "squat", "sets": 4, "reps": "8-10", "rest": "2min"}
                        ]
                    }
                ],
                "notes": "note渐enter负荷..."
            }
        }


async def training_plan_tool(profile: UserProfile) -> TrainingPlanOutput:
    """
    based_onuserprofilegenerateitemityizetrainingplan. 
    
    will考虑: 
    - 经验水flat(Beginner/enter阶/Advanced)
    - canuseMachine
    - injury病限make
    - trainingtarget
    """
    llm = get_default_llm()
    
    # structbuildprovideshow
    prompt = f"""
pleaseas downusergenerate item{profile.duration_weeks}week {profile.goal}trainingplan. 

userprofile: 
- ity别: {profile.gender}
- 年龄: {profile.age}
- bodyhigh/bodyre: {profile.height_cm}cm / {profile.weight_kg}kg
- 经验: {profile.experience}
- canuseMachine: {', '.join(profile.available_equipment)}
- perweektraining: {profile.sessions_per_week}rep
- injury病history: {', '.join(profile.injuries) if profile.injuries else 'none'}

need求: 
1. perweek{profile.sessions_per_week}练, 合reason安row_arrsplitize
2. based_on经验水flatsetting合适 volume intensity
3. 避openinjury病限make movement
4. packagecontains渐enter负荷square案
5. mustoutputascanparse  JSON format

outputformat: 
{{
    "plan_id": "selfactiongenerate",
    "duration_weeks": {profile.duration_weeks},
    "weekly_schedule": [
        {{
            "day": "week ",
            "focus": "trainingrepoint",
            "exercises": [
                {{"name": "movement名", "sets": groupnum, "reps": "countrange", "rest": "restwhenlong"}}
            ]
        }}
    ],
    "notes": "note事项 buildsuggest"
}}
"""
    
    response = await llm.ainvoke(prompt)
    
    # parse JSON
    try:
        content = response.content
        # provideget JSON partial
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content
        
        plan_data = json.loads(json_str)
        return TrainingPlanOutput(**plan_data)
    except Exception as e:
        # parsefailwhenreturn简ize版this
        return TrainingPlanOutput(
            plan_id=f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            duration_weeks=4,
            weekly_schedule=[],
            notes=f"parsefailed: {e}",
        )


# ============================================================
# 3. trainingreportgenerateworktool(core - integrate FSM data)
# ============================================================

class SessionDataInput(BaseModel):
    """singlereptrainingsessiondata - 由 FSM layer产出 """
    session_id: str = Field(description="sessionID")
    movement: str = Field(description="movementtype: squat/deadlift/bench etc")
    total_reps: int = Field(description="totalcount")
    duration_seconds: int = Field(description="trainingwhenlong(秒)")
    
    # amountizerefmark
    reps: List[Dict] = Field(description="perrepredup detaildata")
    
    # 汇totalstatistics
    avg_score: float = Field(description="averagescore")
    best_score: float = Field(description="bestscore")
    worst_score: float = Field(description="worstscore")
    
    # errorstatistics
    error_summary: Dict[str, int] = Field(description="errortype计num")


class TrainingReportOutput(BaseModel):
    """trainingreportoutput Schema"""
    overall_score: float = Field(description="overallscore 0-100")
    highlights: List[str] = Field(description="highlights")
    corrections: List[str] = Field(description="need改enter groundsquare")
    recovery_plan: str = Field(description="recovery_tips")
    next_session_goals: List[str] = Field(description="downreptrainingtarget")
    
    class Config:
        json_schema_extra = {
            "example": {
                "overall_score": 78.5,
                "highlights": ["squatdepth达mark率high", "trunkctrlmakestable"],
                "corrections": ["no3group出现kneevalgus", "bottom停顿time偏short"],
                "recovery_plan": "buildsuggeststretchquad 腘绳肌, 泡沫shaftrelax...",
                "next_session_goals": ["保holddepth", "ctrlmakeeccentricvelocity"]
            }
        }


async def training_report_tool(session_data: SessionDataInput) -> TrainingReportOutput:
    """
    based_on FSM 产出 amountizedatageneratetrainingreport. 
    
    thisYesconnect算法layer  LLM  coreendpoint. 
    """
    llm = get_default_llm()
    
    # structbuilddetail provideshow
    prompt = f"""
你Yes loc专业 Strengthtraining教练. pleasebased_on downamountizedataasusergeneratetrainingreport. 

[movement]: {session_data.movement}
[trainingwhenlong]: {session_data.duration_seconds // 60}split钟
[totalcount]: {session_data.total_reps}
[averagescore]: {session_data.avg_score:.1f}

[perreprep_details]:
{json.dumps(session_data.reps, indent=2, ensure_ascii=False)[:2000]}

[errorstatistics]:
{json.dumps(session_data.error_summary, indent=2, ensure_ascii=False)}

pleasegeneratepackagecontains downinner容 report(mustoutput JSON): 
1. overall_score: Generalscore(based_on算法score error率)
2. highlights: thisreptraining highlights(至few2item)
3. corrections: need改enter groundsquare(mostmany3item, 按优先级)
4. recovery_plan: recovery_tips(stretch, relax, 营养)
5. next_session_goals: downreptrainingtarget(specific, can衡amount)

outputmustYes 效  JSON format. 
"""
    
    response = await llm.ainvoke(prompt)
    
    # parse JSON
    try:
        content = response.content
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content
        
        report_data = json.loads(json_str)
        return TrainingReportOutput(**report_data)
    except Exception as e:
        # 兜basereturn
        return TrainingReportOutput(
            overall_score=session_data.avg_score,
            highlights=["complete training"],
            corrections=["dataparseexception, pleasere试"],
            recovery_plan="trainingbackpleasenotestretch",
            next_session_goals=["continue加油"],
        )


# ============================================================
# 4. movement纠错buildsuggestworktool(realwhenfeedback)
# ============================================================

class RealtimeCorrectionInput(BaseModel):
    """realwhen纠错input - singleframeorshort期窗口data"""
    current_state: str = Field(description="current FSM state")
    knee_angle: float = Field(description="currentknee_angle")
    trunk_tibia_diff: float = Field(description="trunk-tibiaBadvalue")
    errors: List[str] = Field(default=[], description="currentdetectionto error")
    rep_count: int = Field(description="currentredupcount")


class RealtimeCorrectionOutput(BaseModel):
    """realwhen纠错output"""
    immediate_feedback: str = Field(description="即whenfeedback(简short)")
    encouragement: str = Field(description="鼓励lang句")
    should_speak: bool = Field(description="YesNoneedlangaudio播报")


async def realtime_correction_tool(data: RealtimeCorrectionInput) -> RealtimeCorrectionOutput:
    """
    based_oncurrentstategeneraterealwhenfeedback. 
    
    used_fortrainingpass程  即whenref导, thancompletereportmorelightamount. 
    """
    # 简single规rule优先, complexfield景再call LLM
    immediate = ""
    encouragement = ""
    should_speak = False
    
    if "trunk_forward_lean" in data.errors:
        immediate = "注意，背部稍微挺直一些"
        should_speak = True
    elif "knee_valgus" in data.errors:
        immediate = "膝盖向外打开，对准脚尖方向"
        should_speak = True
    elif data.current_state == "bottom" and data.knee_angle > 130:
        immediate = "再往down point, biglegflatrowground面"
        should_speak = True
    
    # per5repredupgive rep鼓励
    if data.rep_count > 0 and data.rep_count % 5 == 0:
        encouragement = f"alreadycomplete {data.rep_count} rep, 保holdsection奏! "
        should_speak = True
    
    return RealtimeCorrectionOutput(
        immediate_feedback=immediate,
        encouragement=encouragement,
        should_speak=should_speak,
    )


# ============================================================
# worktool注册table
# ============================================================

async def _knowledge_retrieval_coroutine(question: str, top_k: int = 3) -> str:
    result = await knowledge_retrieval_tool(KnowledgeInput(question=question, top_k=top_k))
    return json.dumps(result.model_dump(), ensure_ascii=False)


async def _training_plan_coroutine(
    gender: str,
    age: int,
    height_cm: float,
    weight_kg: float,
    experience: str,
    available_equipment: List[str],
    goal: str,
    injuries: Optional[List[str]] = None,
    sessions_per_week: int = 3,
    duration_weeks: int = 4,
) -> str:
    profile = UserProfile(
        gender=gender,
        age=age,
        height_cm=height_cm,
        weight_kg=weight_kg,
        experience=experience,
        injuries=injuries or [],
        available_equipment=available_equipment,
        goal=goal,
        sessions_per_week=sessions_per_week,
        duration_weeks=duration_weeks,
    )
    result = await training_plan_tool(profile)
    return json.dumps(result.model_dump(), ensure_ascii=False)


async def _training_report_coroutine(
    session_id: str,
    movement: str,
    total_reps: int,
    duration_seconds: int,
    reps: List[Dict],
    avg_score: float,
    best_score: float,
    worst_score: float,
    error_summary: Dict[str, int],
) -> str:
    session_data = SessionDataInput(
        session_id=session_id,
        movement=movement,
        total_reps=total_reps,
        duration_seconds=duration_seconds,
        reps=reps,
        avg_score=avg_score,
        best_score=best_score,
        worst_score=worst_score,
        error_summary=error_summary,
    )
    result = await training_report_tool(session_data)
    return json.dumps(result.model_dump(), ensure_ascii=False)


async def _realtime_correction_coroutine(
    current_state: str,
    knee_angle: float,
    trunk_tibia_diff: float,
    rep_count: int,
    errors: Optional[List[str]] = None,
) -> str:
    frame_data = RealtimeCorrectionInput(
        current_state=current_state,
        knee_angle=knee_angle,
        trunk_tibia_diff=trunk_tibia_diff,
        errors=errors or [],
        rep_count=rep_count,
    )
    result = await realtime_correction_tool(frame_data)
    return json.dumps(result.model_dump(), ensure_ascii=False)


TOOLS = [
    StructuredTool.from_function(
        name="knowledge_retrieval",
        description="Search the local fitness knowledge base and answer exercise science questions.",
        coroutine=_knowledge_retrieval_coroutine,
        args_schema=KnowledgeInput,
    ),
    StructuredTool.from_function(
        name="generate_training_plan",
        description="Generate a personalized training plan from a user profile.",
        coroutine=_training_plan_coroutine,
        args_schema=UserProfile,
    ),
    StructuredTool.from_function(
        name="generate_training_report",
        description="Generate a detailed training report from FSM session data.",
        coroutine=_training_report_coroutine,
        args_schema=SessionDataInput,
    ),
    StructuredTool.from_function(
        name="realtime_correction",
        description="Generate short real-time movement correction feedback.",
        coroutine=_realtime_correction_coroutine,
        args_schema=RealtimeCorrectionInput,
    ),
]


def get_tools() -> List[StructuredTool]:
    """getgetplace canuseworktool"""
    return TOOLS
