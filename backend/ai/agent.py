"""
backend/ai/agent.py
single Agent + worktool架structreal现
"""

import json
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain.memory import ConversationBufferMemory

from backend.ai.llm_client import get_default_llm
from backend.ai.prompts import get_main_prompt, format_system_prompt
from backend.ai.tools import get_tools


class CyberCoachAgent:
    """
    Cyber Trainer Agent - single Agent + manyworktoolmockstyle
    
    core职责: 
    1. handlereasonuserself然lang言chat
    2. routeto合适 worktool
    3. 维护chat记忆
    4. outputendstructizeresult
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or self._generate_session_id()
        self.llm = get_default_llm()
        self.tools = get_tools()
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            input_key="input",
            output_key="output",
            return_messages=True,
        )
        
        # create Agent
        self.agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=get_main_prompt(),
        )
        
        # package装as Executor(selfactionhandlereasonworktoolcall循ring)
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=False,
            max_iterations=10,
            handle_parsing_errors=True,
        )
    
    def _generate_session_id(self) -> str:
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def chat(self, message: str) -> Dict[str, Any]:
        """
        handlereasonuser消息, returnresponse. 
        
        Returns:
            {
                "response": str,  # self然lang言回dup
                "tool_calls": List,  # use worktool
                "session_id": str,
            }
        """
        # 注incurrenttimetosystem统provideshow
        current_time = datetime.now().isoformat()
        
        result = await self.executor.ainvoke(
            {"input": message, "current_time": current_time},
            config=RunnableConfig(session_id=self.session_id),
        )
        
        return {
            "response": result.get("output", ""),
            "tool_calls": result.get("intermediate_steps", []),
            "session_id": self.session_id,
        }
    
    async def chat_stream(self, message: str) -> AsyncGenerator[str, None]:
        """
        流styleresponse(used_for WebSocket). 
        
        Yields:
            JSON char符string, packagecontainstype inner容
        """
        # LangChain Agent  流stylebranchhold 限, this里mock拟real现
        # real际项目 cancanneedmorefine粒度 ctrlmake
        
        result = await self.chat(message)
        
        # mock拟splitblockoutput
        response = result["response"]
        words = response.split()
        
        for i, word in enumerate(words):
            chunk = {
                "type": "content",
                "content": word + " ",
                "is_end": i == len(words) - 1,
            }
            yield json.dumps(chunk, ensure_ascii=False)
    
    def clear_memory(self):
        """清emptychat记忆"""
        self.memory.clear()
    
    def get_memory(self) -> List[Dict]:
        """getgetcurrentchathistory"""
        messages = self.memory.chat_memory.messages
        return [
            {"role": "user" if isinstance(m, HumanMessage) else "assistant",
             "content": m.content}
            for m in messages
        ]


# ============================================================
# worktooldirectconncallendpoint(绕pass Agent pushreason, directconncall)
# ============================================================

async def generate_training_report(session_data: Dict) -> Dict:
    """
    directconngeneratetrainingreport(供 FSM layercall).

    thisYes Python side camera.py → LLM  coreintegratepoint.

    Supports two data formats:
    - FSM format (from camera.py via LLMBridge): has total_reps, reps, avg_score, etc.
    - Frontend format (from WorkoutSession.vue): has rep_count, errors, error_details, etc.
    """
    from backend.ai.tools import training_report_tool, SessionDataInput

    # Normalize frontend format to SessionDataInput format
    normalized = {
        "session_id": session_data.get("session_id", "unknown"),
        "movement": session_data.get("movement", "squat"),
        "total_reps": session_data.get("total_reps") or session_data.get("rep_count", 0),
        "duration_seconds": session_data.get("duration_seconds", 0),
        "reps": session_data.get("reps", []),
        "avg_score": session_data.get("avg_score", 0),
        "best_score": session_data.get("best_score", 0),
        "worst_score": session_data.get("worst_score", 0),
        "error_summary": session_data.get("error_summary", {}),
    }

    # Build error_summary from errors list if not provided
    if not normalized["error_summary"] and session_data.get("errors"):
        from collections import Counter
        error_types = [e.split(":")[0] if ":" in e else e for e in session_data["errors"]]
        normalized["error_summary"] = dict(Counter(error_types))

    # Build error_summary from error_details if available
    if not normalized["error_summary"] and session_data.get("error_details"):
        normalized["error_summary"] = {
            k: v for k, v in session_data["error_details"].items()
        }

    input_data = SessionDataInput(**normalized)
    result = await training_report_tool(input_data)

    return result.model_dump()


async def get_realtime_feedback(frame_data: Dict) -> Dict:
    """
    getgetrealwhen纠错buildsuggest(供 camera.py perframecall). 
    
    lightamount级, 尽amountuse规rule, necessarywhenonly_thencall LLM. 
    """
    from backend.ai.tools import realtime_correction_tool, RealtimeCorrectionInput
    
    input_data = RealtimeCorrectionInput(**frame_data)
    result = await realtime_correction_tool(input_data)
    
    return result.model_dump()


# ============================================================
# Agent instance management with session expiry
# ============================================================

SESSION_TTL_SECONDS = 3600  # 60 minutes

# Maps session_id -> (agent, last_access_timestamp)
_agent_instances: Dict[str, tuple] = {}


def _cleanup_expired_sessions():
    """Remove agent sessions that haven't been accessed in SESSION_TTL_SECONDS."""
    now = datetime.now().timestamp()
    expired = [
        sid for sid, (_, last_access) in _agent_instances.items()
        if now - last_access > SESSION_TTL_SECONDS
    ]
    for sid in expired:
        del _agent_instances[sid]


def get_agent(session_id: Optional[str] = None) -> CyberCoachAgent:
    """
    Get or create an agent instance.

    Runs cleanup on each call to expire stale sessions.
    """
    _cleanup_expired_sessions()

    if session_id is None:
        return CyberCoachAgent()

    if session_id not in _agent_instances:
        _agent_instances[session_id] = (CyberCoachAgent(session_id=session_id), datetime.now().timestamp())
    else:
        # Update last access time
        agent, _ = _agent_instances[session_id]
        _agent_instances[session_id] = (agent, datetime.now().timestamp())

    return _agent_instances[session_id][0]


def clear_agent(session_id: str):
    """Remove a specific agent instance."""
    if session_id in _agent_instances:
        del _agent_instances[session_id]
