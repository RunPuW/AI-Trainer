# 赛博私教 AI 层 - 对接 LLM 架构设计

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                      前端层 (React/Vue)                      │
│         ┌──────────────┐    ┌──────────────┐                │
│         │  训练界面     │    │  对话界面     │                │
│         └──────┬───────┘    └──────┬───────┘                │
│                │                   │                        │
│                └─────────┬─────────┘                        │
│                          │ HTTP/WebSocket                   │
└──────────────────────────┼──────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────┐
│                     FastAPI 后端服务                         │
│  ┌───────────────────────┐ │ ┌──────────────────────────────┐ │
│  │   /api/report         │ │ │   /api/chat (Agent)          │ │
│  │   /api/feedback       │─┼─│   /api/plan                  │ │
│  │   (FSM 数据对接)       │ │ │   /ws/chat (流式)            │ │
│  └───────────┬───────────┘ │ └──────────────┬───────────────┘ │
│              │             │                │                 │
│              └─────────────┼────────────────┘                 │
│                            │                                  │
│  ┌─────────────────────────▼─────────────────────────────┐     │
│  │              CyberCoachAgent (单 Agent)              │     │
│  │  ┌─────────────┐ ┌─────────────┐ ┌────────────────┐ │     │
│  │  │ 知识检索     │ │ 计划生成     │ │ 训练报告生成    │ │     │
│  │  └─────────────┘ └─────────────┘ └────────────────┘ │     │
│  └─────────────────────────────────────────────────────┘     │
│                            │                                  │
│  ┌─────────────────────────▼─────────────────────────────┐     │
│  │                     LLM 客户端                        │     │
│  │         (DeepSeek / OpenAI / Claude)                  │     │
│  └─────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────┐
│                     Python 算法层                             │
│  ┌───────────────────────┐ │ ┌──────────────────────────────┐ │
│  │   camera.py           │ │ │   FSM 状态机                  │ │
│  │   - MediaPipe 检测    │─┼─│   - 几何分析                  │ │
│  │   - 实时采集          │ │ │   - 错误检测                  │ │
│  │   - 调用 /api/report  │ │ │   - session_data 生成         │ │
│  └───────────────────────┘ │ └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 核心设计决策

### 1. 单 Agent + 多工具模式（阶段一）

**选择理由**：
- LangChain 官方建议："许多任务使用单 Agent + 精心设计的工具即可完成"
- 复杂度可控，调试简单
- 响应延迟可预测

**核心工具**：
| 工具 | 输入 | 输出 | 调用方 |
|------|------|------|--------|
| `knowledge_retrieval` | 问题文本 | 文档列表+摘要 | Agent |
| `generate_training_plan` | UserProfile | 结构化计划 | Agent |
| `generate_training_report` | SessionData | 结构化报告 | camera.py |
| `realtime_correction` | FrameData | 即时反馈 | camera.py |

### 2. 数据流设计

**训练报告流**（核心）：
```
camera.py (FSM) ──session_data──→ /api/report ──→ LLM ──→ 结构化报告
                                      │
                                      ▼
                         {
                           "overall_score": 78.5,
                           "highlights": [...],
                           "corrections": [...],
                           "recovery_plan": "...",
                           "next_session_goals": [...]
                         }
```

**实时反馈流**：
```
camera.py ──frame_data──→ /api/feedback ──→ 规则优先 ──→ 反馈
                              │
                              └── 复杂情况才调用 LLM
```

### 3. 与 FSM 层的对接点

在 `camera.py` 中新增以下调用：

```python
# 1. 训练结束后生成报告
async def on_session_end(fsm_summary):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/report",
            json={"session_data": fsm_summary}
        )
        report = response.json()
        # 语音播报 highlights[0]
        # 显示 corrections 列表

# 2. 实时反馈（每5帧或错误发生时）
async def get_feedback(current_geo, current_state):
    if should_call_llm(geo, errors):  # 只在必要时
        response = await client.post(
            "http://localhost:8000/api/feedback",
            json={"frame_data": {...}}
        )
        return response.json()
```

### 3. 多 Agent 演进路线（未来）

```
阶段二：Plan-Execute 模式（LangGraph）

用户输入复杂任务
       │
       ▼
┌─────────────┐
│  Planner    │ ← LLM 分解任务为步骤列表
│  (计划节点)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Executor   │ ← 逐步执行工具
│  (执行节点)  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  RePlanner  │ ← 检查是否需要更多步骤
│  (重计划)    │
└─────────────┘

阶段三：多 Agent 协作（如需要）

┌──────────┐
│ 主控 Agent │ ← 路由和整合
└────┬─────┘
     │
     ├──→ ┌──────────┐ ← 动作专家 Agent
     │    │ 深蹲/硬拉  │
     │    └──────────┘
     │
     ├──→ ┌──────────┐ ← 营养 Agent
     │    │ 饮食建议  │
     │    └──────────┘
     │
     └──→ ┌──────────┐ ← 康复 Agent
          │ 伤病咨询  │
          └──────────┘
```

## 实施优先级

### P0 - 立即实施（单 Agent MVP）

1. **backend/ai/** 模块
   - [x] `llm_client.py` - LLM 封装（DeepSeek/OpenAI/Claude）
   - [x] `tools.py` - 工具定义（Pydantic Schema）
   - [x] `prompts.py` - 系统提示词
   - [x] `agent.py` - Agent 组装

2. **backend/api/** 模块
   - [x] `routes.py` - FastAPI 路由
   - [x] WebSocket 流式接口

3. **对接 camera.py**
   - [ ] 新增 `SessionDataExporter` 类
   - [ ] 训练结束调用 `/api/report`
   - [ ] 实时反馈调用 `/api/feedback`

### P1 - 近期实施

4. **知识库接入**
   - ChromaDB 向量库搭建
   - 文献/标准动作视频入库
   - `knowledge_retrieval` 工具实现

5. **用户画像**
   - 数据库设计（SQLite/PostgreSQL）
   - UserProfile 持久化
   - 训练计划关联用户

### P2 - 中期演进

6. **Plan-Execute 模式**
   - LangGraph 迁移
   - 复杂任务拆解

7. **多 Agent（如需要）**
   - 动作专家拆分
   - Agent 间通信机制

## 环境变量

```bash
# .env
LLM_PROVIDER=deepseek  # 或 openai, claude
DEEPSEEK_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# 可选
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4096
```

## 运行方式

```bash
# 1. 安装依赖
cd backend
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key

# 3. 启动服务
python main.py

# 4. 测试
curl -X POST http://localhost:8000/api/report \
  -H "Content-Type: application/json" \
  -d @test_session_data.json
```

## camera.py 集成示例

```python
# camera.py 中新增
import httpx

class LLMBridge:
    def __init__(self, api_url="http://localhost:8000"):
        self.api_url = api_url
        self.client = httpx.AsyncClient()
    
    async def submit_session(self, fsm_summary):
        """训练结束后提交数据获取报告"""
        response = await self.client.post(
            f"{self.api_url}/api/report",
            json={"session_data": fsm_summary}
        )
        return response.json()
    
    async def get_feedback(self, geo, state, errors):
        """获取实时反馈"""
        if not self._should_call_llm(errors):
            return None  # 简单规则处理
        response = await self.client.post(
            f"{self.api_url}/api/feedback",
            json={"frame_data": {...}}
        )
        return response.json()

# 使用
llm_bridge = LLMBridge()

# 训练结束
report = await llm_bridge.submit_session(fsm.get_session_summary())
overlay.speak(report["highlights"][0])
```
