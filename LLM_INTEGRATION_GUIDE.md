# 赛博私教 - AI Agent 对接完整架构

## 一、当前已完成代码

### 1. 后端 AI 服务 (`backend/`)

```
backend/
├── ai/
│   ├── __init__.py
│   ├── llm_client.py      # LLM 客户端（DeepSeek/OpenAI/Claude）
│   ├── tools.py            # 工具定义（4个核心工具 + Pydantic Schema）
│   ├── prompts.py          # 系统提示词模板
│   └── agent.py            # 单 Agent + 多工具实现
├── api/
│   ├── __init__.py
│   └── routes.py           # FastAPI 路由（HTTP + WebSocket）
├── main.py                 # FastAPI 应用入口
├── requirements.txt        # 依赖
└── ARCHITECTURE.md         # 架构文档
```

### 2. 算法层桥接 (`camera_llm_bridge.py`)

- 演示如何将 `fsm.py` 的数据对接到后端
- 包含数据格式转换
- 支持训练报告提交和实时反馈

### 3. 核心工具

| 工具名 | 用途 | 调用方 |
|--------|------|--------|
| `generate_training_report` | 根据 FSM 数据生成训练报告 | camera.py (训练结束) |
| `realtime_correction` | 实时动作纠错建议 | camera.py (可选) |
| `generate_training_plan` | 用户画像 → 训练计划 | 前端/对话 |
| `knowledge_retrieval` | RAG 知识问答 | 对话 Agent |

---

## 二、对接流程（ camera.py → LLM ）

### 步骤 1：启动后端服务

```bash
cd backend
pip install -r requirements.txt

# 配置 API Key
export DEEPSEEK_API_KEY=your_key_here
# 或
export OPENAI_API_KEY=your_key_here

# 启动服务
python main.py
# 服务运行在 http://localhost:8000
```

### 步骤 2：修改 camera.py 集成 LLM

```python
# camera.py 中新增
from camera_llm_bridge import LLMBridge

class CyberTrainer:
    def __init__(self, ...):
        # ... 原有初始化 ...
        
        # 新增：LLM 桥接
        self.llm_bridge = LLMBridge(
            api_url="http://localhost:8000",
            enabled=True  # 可在配置中关闭
        )
        
        # 扩展回调
        self.fsm.on_rep_complete = self._on_rep_complete
    
    def _on_rep_complete(self, rep):
        """完成重复时的回调"""
        # 原有逻辑...
        
        # 可选：每5次获取一次 AI 鼓励
        if rep.rep_number % 5 == 0:
            asyncio.create_task(self._get_ai_encouragement(rep))
    
    async def _get_ai_encouragement(self, rep):
        """获取 AI 鼓励（异步，不阻塞主循环）"""
        feedback = await self.llm_bridge.get_feedback(
            geo=self.geometry.get_last_valid(),
            state=self.fsm.state.value,
            errors=rep.errors,
            rep_count=rep.rep_number
        )
        if feedback:
            self.overlay.feedback.speak(feedback)
    
    def shutdown(self):
        """关闭时生成报告"""
        summary = self.fsm.get_session_summary()
        
        if summary.get("total_reps", 0) > 0:
            # 同步调用（训练结束，可以等待）
            report = asyncio.run(self.llm_bridge.submit_session(summary))
            
            if report:
                # 显示 AI 报告
                self._display_ai_report(report)
        
        self.llm_bridge.close()
        # ... 原有清理逻辑 ...
    
    def _display_ai_report(self, report: dict):
        """显示 AI 生成的报告"""
        print("\n" + "=" * 50)
        print(f"  综合评分: {report['overall_score']:.1f}/100")
        print("=" * 50)
        print(f"\n亮点:")
        for h in report['highlights']:
            print(f"  ✓ {h}")
        print(f"\n改进建议:")
        for c in report['corrections']:
            print(f"  • {c}")
        print(f"\n恢复方案:")
        print(f"  {report['recovery_plan']}")
        print(f"\n下次目标:")
        for g in report['next_session_goals']:
            print(f"  → {g}")
```

---

## 三、数据流详解

### 训练报告数据流

```
┌─────────────┐
│   camera.py  │
│  ┌─────────┐ │
│  │   FSM   │ │
│  │ (深蹲)  │ │
│  └────┬────┘ │
│       │      │
│       │ session_data
│       │ {
│       │   total_reps: 12,
│       │   avg_score: 75.5,
│       │   reps: [...],
│       │   error_summary: {...}
│       │ }
│       │
│       ▼
│  ┌──────────────┐
│  │  LLMBridge   │
│  │ submit_session│
│  └───────┬───────┘
└──────────│─────────┘
           │ HTTP POST /api/report
           ▼
┌──────────────────────┐
│   FastAPI Backend    │
│  ┌────────────────┐  │
│  │ training_report│  │
│  │     _tool      │  │
│  └───────┬────────┘  │
│          │           │
│          ▼           │
│  ┌────────────────┐  │
│  │ Prompt +       │  │
│  │ Session Data   │  │
│  └───────┬────────┘  │
│          │           │
│          ▼           │
│  ┌────────────────┐  │
│  │     LLM       │  │
│  │ (DeepSeek/    │  │
│  │  OpenAI)      │  │
│  └───────┬────────┘  │
│          │           │
│          │ JSON      │
│          ▼           │
│  ┌────────────────┐  │
│  │  ReportOutput │  │
│  │  {score,       │  │
│  │   highlights, │  │
│  │   corrections}│  │
│  └───────────────┘  │
└──────────────────────┘
           │
           │ HTTP Response
           ▼
    camera.py 显示
```

---

## 四、演进路线

### 阶段一：单 Agent MVP（当前）

- ✅ 完成 4 个核心工具
- ✅ FastAPI 服务
- ✅ camera.py 桥接
- 🔄 接入 ChromaDB RAG
- 🔄 用户画像持久化

### 阶段二：Plan-Execute（如需）

```python
# 当需要处理复杂任务时迁移到 LangGraph

from langgraph.graph import StateGraph

# 示例：生成复杂训练计划
class PlanExecuteState:
    input: str           # 用户需求
    plan: List[str]    # 步骤列表
    current_step: int  # 当前步骤
    results: List      # 中间结果
    output: str        # 最终输出

# Planner → Executor → Replan?
graph = StateGraph(PlanExecuteState)
graph.add_node("planner", planner_node)
graph.add_node("executor", executor_node)
graph.add_node("replan", replan_node)

graph.set_entry_point("planner")
graph.add_edge("planner", "executor")
graph.add_conditional_edges("executor", should_continue)
graph.add_edge("replan", "executor")
```

### 阶段三：多 Agent（如需要）

```
用户输入
   │
   ▼
┌─────────┐
│ 主控 Agent│ ← 路由决策
└────┬────┘
     │
     ├──→ ┌──────────┐ → 返回
     │    │动作专家  │
     │    │(深蹲/硬拉)│
     │    └──────────┘
     │
     ├──→ ┌──────────┐ → 返回
     │    │ 营养 Agent│
     │    └──────────┘
     │
     └──→ ┌──────────┐ → 返回
          │ 康复 Agent│
          └──────────┘
```

---

## 五、关键设计决策

### 1. 为什么单 Agent + 工具？

- **LangChain 官方建议**："Many use cases work well with just a single agent"
- **延迟可控**：单次 LLM 调用 < 2s
- **调试简单**：工具独立测试
- **扩展灵活**：后续可平滑迁移到多 Agent

### 2. 为什么 camera.py 直接调用 API？

- **解耦**：FSM 层保持轻量，AI 逻辑在后端
- **灵活**：可独立升级 LLM 或切换模型
- **安全**：API Key 不暴露在客户端

### 3. 实时反馈的规则优先策略

```python
# 简单错误 → 本地规则（0ms 延迟）
if "膝盖内扣" in errors:
    return "膝盖向外打开"  # 本地

# 复杂分析 → LLM（30ms-2000ms）
if needs_deep_analysis(geo, history):
    return await call_llm(...)  # 后端
```

---

## 六、测试验证

### 1. 启动服务
```bash
cd backend
python main.py
```

### 2. 测试报告接口
```bash
# 准备测试数据
cat > test_session.json << 'EOF'
{
  "session_data": {
    "session_id": "test_001",
    "movement": "squat",
    "total_reps": 10,
    "duration_seconds": 300,
    "reps": [
      {"rep_number": 1, "overall_score": 80, "errors": []},
      {"rep_number": 2, "overall_score": 75, "errors": ["膝盖内扣"]}
    ],
    "avg_score": 77.5,
    "best_score": 85,
    "worst_score": 65,
    "error_summary": {"膝盖内扣": 3, "躯干前倾": 2}
  }
}
EOF

# 调用 API
curl -X POST http://localhost:8000/api/report \
  -H "Content-Type: application/json" \
  -d @test_session.json
```

### 3. 测试对话接口
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "深蹲时膝盖内扣怎么办？"}'
```

---

## 七、下一步行动

1. **立即可做**：
   - 在 `camera.py` 中集成 `LLMBridge`
   - 配置环境变量并测试报告生成
   - 根据返回调整 `movement_rules.json`

2. **本周可做**：
   - 搭建 ChromaDB 并导入知识库
   - 实现 `knowledge_retrieval` 工具
   - 添加 WebSocket 流式对话

3. **后续演进**：
   - 根据用户反馈决定是否升级 Plan-Execute
   - 根据业务复杂度决定是否拆分多 Agent
