"""
camera_llm_bridge.py
camera.py   LLM servicetask bridgemodule
演show如何将 FSM dataintegratetobackside AI servicetask
"""

import json
import asyncio
from typing import Dict, Optional
from dataclasses import asdict

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False


class LLMBridge:
    """
    camera.py  backside LLM servicetask bridgeer. 
    
    职责: 
    1. trainingendbeambackprovide交 session_data getgetcompletereport
    2. realwhengetgetlightamount级feedback(can选)
    3. thisground缓storeavoidredupcall
    """
    
    def __init__(self, api_url: str = "http://localhost:8000", enabled: bool = True):
        self.api_url = api_url
        self.enabled = enabled and _HTTPX_AVAILABLE
        self._client: Optional[httpx.AsyncClient] = None
        self._feedback_cooldown: Dict[str, float] = {}
        
    async def _get_client(self) -> httpx.AsyncClient:
        """延迟init HTTP 客户side"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    def _transform_fsm_to_session_data(self, fsm_summary: Dict) -> Dict:
        """
        将 FSM   session_summary convertasbackside期望  SessionDataInput format. 
        
        fsm_summary format(comeself fsm.py): 
        {
            "total_reps": 12,
            "avg_score": 75.5,
            "best_score": 85.0,
            "worst_score": 60.0,
            "avg_duration_ms": 4500,
            "error_summary": {"kneevalgus": 3, "trunkexcessiveforward_lean": 2},
            "reps": [...]
        }
        """
        return {
            "session_id": f"session_{fsm_summary.get('total_reps', 0)}",
            "movement": "squat",
            "total_reps": fsm_summary.get("total_reps", 0),
            "duration_seconds": int(fsm_summary.get("avg_duration_ms", 0) * fsm_summary.get("total_reps", 0) / 1000),
            "reps": fsm_summary.get("reps", []),
            "avg_score": fsm_summary.get("avg_score", 0),
            "best_score": fsm_summary.get("best_score", 0),
            "worst_score": fsm_summary.get("worst_score", 0),
            "error_summary": fsm_summary.get("error_summary", {}),
        }
    
    async def submit_session(self, fsm_summary: Dict) -> Optional[Dict]:
        """
        trainingendbeambackcall, getgetcompletetrainingreport. 
        
        Returns:
            {
                "overall_score": float,
                "highlights": [str],
                "corrections": [str],
                "recovery_plan": str,
                "next_session_goals": [str]
            }
            or None(if禁useorfail)
        """
        if not self.enabled:
            return None
        
        try:
            session_data = self._transform_fsm_to_session_data(fsm_summary)
            client = await self._get_client()
            
            response = await client.post(
                f"{self.api_url}/api/report",
                json={"session_data": session_data}
            )
            response.raise_for_status()
            
            report = response.json()
            print(f"[LLM] reportalreadygenerate: score={report.get('overall_score', 0):.1f}")
            return report
            
        except Exception as e:
            print(f"[LLM] reportgeneratefailed: {e}")
            return None
    
    async def get_feedback(self, geo: Dict, state: str, errors: list, rep_count: int) -> Optional[str]:
        """
        getgetrealwhenfeedback(lightamount级, 带cooldown). 
        
        目front优先usethisground规rule, only complexfield景call LLM. 
        
        Args:
            geo: currentframegeometrydata
            state: FSM state
            errors: currenterrorlist
            rep_count: currentredupcount
            
        Returns:
            feedbacktextthis or None
        """
        if not self.enabled:
            return None
        
        # 规rule优先: 简singleerrordirectconnthisgroundfeedback
        if "trunk_forward_lean" in errors:
            return "注意，背部稍微挺直一些"
        elif "knee_valgus" in errors:
            return "膝盖向外打开，对准脚尖方向"
        elif state == "bottom" and geo.get("knee_angle", 180) > 130:
            return "再往down point, biglegflatrowground面"
        
        # complexfield景only_thencall LLM(暂 real现, avoid延迟)
        return None
    
    async def close(self):
        """closeconnect"""
        if self._client:
            await self._client.aclose()
            self._client = None


# ============================================================
# 演show: 如何集成to camera.py
# ============================================================

async def demo_integration():
    """
    演show如何将 LLMBridge 集成to camera.py
    """
    from fsm import SquatFSM
    
    # 1. initbridgeer
    bridge = LLMBridge(api_url="http://localhost:8000", enabled=True)
    
    # 2. FSM callbackshow例
    async def on_rep_complete_with_llm(rep):
        """completeredup callback(扩expand版)"""
        print(f"[FSM] completeno {rep.rep_number} rep")
        # 原 逻辑...
    
    async def on_session_end_with_llm(fsm: SquatFSM):
        """sessionendbeamcallback(扩expand版)"""
        summary = fsm.get_session_summary()
        
        # call LLM generatereport
        report = await bridge.submit_session(summary)
        
        if report:
            print("\n" + "=" * 50)
            print("  AI trainingreport")
            print("=" * 50)
            print(f"overallscore: {report['overall_score']:.1f}")
            print(f"highlights: {', '.join(report['highlights'])}")
            print(f"require改enter: {', '.join(report['corrections'])}")
            print(f"recovery_tips: {report['recovery_plan'][:100]}...")
            print("=" * 50)
            
            # langaudio播报no itemhighlights
            # overlay.speak(report["highlights"][0])
    
    # 3. useshow例
    fsm = SquatFSM()
    fsm.on_rep_complete = on_rep_complete_with_llm
    
    # mock拟 些redup...
    # trainingendbeamwhen
    await on_session_end_with_llm(fsm)
    
    await bridge.close()


if __name__ == "__main__":
    # run演show
    asyncio.run(demo_integration())
