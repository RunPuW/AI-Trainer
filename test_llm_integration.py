"""
test_llm_integration.py
LLM integratetestfootthis

testinner容: 
1. backside API health康check
2. trainingreportgenerateendpoint
3. chatendpoint
4. camera.py data流mock拟

runmethod: 
    python test_llm_integration.py

front置item件: 
    1. backsideservicetaskStarted: cd backend && python main.py
    2. ring境changeamountalreadyconfig: DEEPSEEK_API_KEY
"""

import asyncio
import json
import sys
from datetime import datetime

import httpx


# backsideservicetaskground址
BASE_URL = "http://localhost:8000"


class LLMIntegrationTester:
    """LLM 集成tester"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results = []
    
    async def run_all_tests(self):
        """runplace test"""
        print("=" * 60)
        print("  cyber_trainer LLM 集成test")
        print("=" * 60)
        print(f"testtime: {datetime.now().isoformat()}")
        print(f"backsideground址: {BASE_URL}\n")
        
        tests = [
            ("health康check", self.test_health),
            ("chatendpoint", self.test_chat),
            ("trainingreportgenerate", self.test_report),
            ("realwhenfeedback", self.test_feedback),
        ]
        
        passed = 0
        failed = 0
        
        for name, test_func in tests:
            try:
                await test_func()
                print(f"✓ {name}: via")
                passed += 1
            except Exception as e:
                print(f"✗ {name}: failed - {e}")
                failed += 1
        
        print("\n" + "=" * 60)
        print(f"testresult: {passed} via, {failed} failed")
        print("=" * 60)
        
        return failed == 0
    
    async def test_health(self):
        """testhealth康checkendpoint"""
        response = await self.client.get(f"{BASE_URL}/api/health")
        response.raise_for_status()
        data = response.json()
        assert data.get("status") == "ok", "health康checkreturnexception"
    
    async def test_chat(self):
        """testchatendpoint"""
        request_data = {
            "message": "squatwhenkneevalgushow办? ",
            "session_id": None
        }
        
        response = await self.client.post(
            f"{BASE_URL}/api/chat",
            json=request_data
        )
        response.raise_for_status()
        data = response.json()
        
        assert "response" in data, "chatresponsemissing response charsegment"
        assert "session_id" in data, "chatresponsemissing session_id charsegment"
        assert len(data["response"]) > 0, "chatresponseasempty"
        
        print(f"  response预览: {data['response'][:50]}...")
    
    async def test_report(self):
        """testtrainingreportgenerateendpoint"""
        # struct造mock拟  FSM sessiondata
        session_data = {
            "session_id": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "movement": "squat",
            "total_reps": 10,
            "duration_seconds": 300,
            "reps": [
                {
                    "rep_number": i + 1,
                    "duration_ms": 4500,
                    "bottom_knee_angle": 105.0 + i * 2,
                    "bottom_trunk_tibia_diff": 5.0 + i * 0.5,
                    "bottom_trunk_forward": 25.0 + i,
                    "errors": [] if i < 5 else ["kneevalgus"],
                    "warnings": [],
                    "depth_score": 80.0 - i * 2,
                    "form_score": 85.0 - i * 3,
                    "overall_score": 82.5 - i * 2.5,
                }
                for i in range(10)
            ],
            "avg_score": 70.0,
            "best_score": 82.5,
            "worst_score": 50.0,
            "error_summary": {"kneevalgus": 5, "trunkexcessiveforward_lean": 2},
        }
        
        request_data = {"session_data": session_data}
        
        print(f"  provide交data: {json.dumps(session_data, indent=2)[:200]}...")
        
        response = await self.client.post(
            f"{BASE_URL}/api/report",
            json=request_data
        )
        response.raise_for_status()
        data = response.json()
        
        assert "overall_score" in data, "reportmissing overall_score"
        assert "highlights" in data, "reportmissing highlights"
        assert "corrections" in data, "reportmissing corrections"
        assert "recovery_plan" in data, "reportmissing recovery_plan"
        assert "next_session_goals" in data, "reportmissing next_session_goals"
        
        print(f"  generate report:")
        print(f"    overallscore: {data['overall_score']:.1f}")
        print(f"    highlights: {data['highlights'][:2]}")
        print(f"    improvements: {data['corrections'][:2]}")
    
    async def test_feedback(self):
        """testrealwhenfeedbackendpoint"""
        frame_data = {
            "current_state": "bottom",
            "knee_angle": 115.0,
            "trunk_tibia_diff": 8.0,
            "errors": ["kneevalgus"],
            "rep_count": 5
        }
        
        request_data = {"frame_data": frame_data}
        
        response = await self.client.post(
            f"{BASE_URL}/api/feedback",
            json=request_data
        )
        response.raise_for_status()
        data = response.json()
        
        assert "immediate_feedback" in data, "feedbackmissing immediate_feedback"
        assert "encouragement" in data, "feedbackmissing encouragement"
        assert "should_speak" in data, "feedbackmissing should_speak"
        
        print(f"  feedback: {data['immediate_feedback']}")
        print(f"  鼓励: {data['encouragement']}")
    
    async def close(self):
        """close客户side"""
        await self.client.aclose()


async def main():
    """mainin口"""
    tester = LLMIntegrationTester()
    
    try:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)
    finally:
        await tester.close()


if __name__ == "__main__":
    # check依赖
    try:
        import httpx
    except ImportError:
        print("please先安装 httpx: pip install httpx")
        sys.exit(1)
    
    asyncio.run(main())
