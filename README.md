# CyberTrainer 赛博私教

CyberTrainer 是一个基于计算机视觉和大语言模型的 AI 健身私教项目。它的目标是让普通用户只用摄像头就能获得动作识别、训练计数、错误提示、训练报告和 AI 问答服务。

当前 MVP 重点支持深蹲训练：系统会通过摄像头识别人体关键点，判断你处于站立、下蹲、底部、起立等阶段，并根据膝盖、髋部、躯干等角度给出动作反馈。

## 这个项目能做什么

1. 实时姿态识别  
   使用 MediaPipe 检测人体 33 个关键点，例如肩膀、髋部、膝盖、脚踝。

2. 深蹲状态判断  
   通过有限状态机识别深蹲过程：站立、下降、底部、上升、完成一次。

3. 动作质量分析  
   根据膝角、躯干角度、膝盖轨迹等信息判断常见问题，例如膝盖内扣、深度不足、躯干过度前倾。

4. 自动计数和评分  
   只有完成一次完整动作才计数，避免只蹲了一半就误判。

5. Web 训练界面  
   提供登录、训练计划、动作库、AI 助手、训练页面和报告页面。

6. 摄像头选择  
   支持在训练页面选择摄像头，适合默认摄像头不可用或外接摄像头的情况。

7. AI 私教问答  
   后端接入 DeepSeek/OpenAI 兼容接口，可以回答动作技术、训练计划和恢复建议。

8. 训练报告  
   训练结束后生成反馈报告，展示完成次数、动作深度、主要问题和改进建议。

## 给小白的理解方式

可以把这个项目理解成三层：

第一层是“眼睛”：摄像头和 MediaPipe 负责看见你的人体关键点。

第二层是“大脑”：Python 算法根据关键点计算角度，再判断你是不是正在深蹲、有没有动作问题。

第三层是“教练”：Web 页面把结果展示给你，AI 助手负责用更自然的话解释训练建议。

你不需要一开始就理解所有算法。先能跑起来，再看页面上的动作反馈，就能慢慢理解系统如何工作。

## 技术栈

### Python 核心算法

- Python 3.11/3.12：主要后端和算法语言。
- MediaPipe Pose Landmarker：人体姿态检测，输出 33 个关键点。
- OpenCV：摄像头读取、视频画面显示、调试可视化。
- NumPy：角度、距离、比例等数学计算。
- pyttsx3：本地语音反馈。
- pytest：核心算法测试。

### 后端服务

- FastAPI：提供 HTTP API 和 WebSocket 服务。
- Uvicorn：运行 FastAPI 后端。
- SQLAlchemy：数据库 ORM。
- SQLite：本地开发数据库。
- Pydantic：请求和响应数据校验。
- python-jose：JWT 登录认证。
- passlib：密码哈希。
- slowapi：接口限流。

### AI 能力

- DeepSeek/OpenAI 兼容接口：用于 AI 私教问答、训练计划和报告分析。
- LangChain：封装 LLM、工具调用和 Agent 逻辑。
- ChromaDB：向量知识库，用于检索训练知识。

### 前端页面

- Vue 3：前端框架。
- TypeScript：让前端代码更安全。
- Vite：前端开发和构建工具。
- Element Plus：UI 组件库。
- Pinia：前端状态管理。
- Vue Router：页面路由。
- Axios：前端请求后端 API。
- Tailwind CSS：样式工具。

## 项目结构

```text
.
├── algorithms/                 # 动作校验算法
├── backend/                    # FastAPI 后端、AI、数据库、API
│   ├── ai/                     # LLM 客户端、Agent、工具、提示词
│   ├── api/                    # HTTP API 和 WebSocket 路由
│   ├── data/                   # 动作库和知识库种子数据
│   ├── db/                     # 数据库连接
│   ├── models/                 # 数据库模型
│   ├── rag/                    # 知识库检索
│   └── main.py                 # 后端入口
├── configs/                    # 动作判定阈值和标准库
├── docs/                       # 项目文档
├── frontend/                   # Vue 前端项目
│   ├── src/
│   │   ├── api/                # 前端 API 封装
│   │   ├── components/         # 通用组件
│   │   ├── composables/        # 姿态检测等复用逻辑
│   │   ├── router/             # 路由配置
│   │   ├── stores/             # Pinia 状态
│   │   └── views/              # 页面
├── scripts/                    # 初始化、启动、校准脚本
├── tests/                      # 自动化测试
├── camera.py                   # Python 摄像头训练入口
├── fsm.py                      # 深蹲有限状态机
├── geometry.py                 # 几何计算
├── filters.py                  # 信号滤波
├── overlay.py                  # OpenCV 可视化和语音反馈
├── requirements.txt            # Python 依赖
└── pyproject.toml              # Python 项目配置
```

## 核心算法说明

### 1. 关键点检测

MediaPipe 会从摄像头画面中识别人体关键点。项目主要使用这些点：

- 肩膀：判断躯干方向。
- 髋部：判断身体中心和下蹲深度。
- 膝盖：计算膝角、判断膝盖内扣。
- 脚踝：判断腿部方向和站姿稳定性。

### 2. 角度计算

`geometry.py` 负责把关键点转换成角度和比例。例如：

- 膝角越小，通常说明蹲得越深。
- 躯干角度过大，可能说明身体前倾过多。
- 左右膝盖相对脚踝的位置异常，可能说明膝盖内扣。

### 3. 状态机

`fsm.py` 用有限状态机识别动作阶段：

```text
STANDING -> DESCENDING -> BOTTOM -> ASCENDING -> STANDING
```

意思是：

- STANDING：站立准备。
- DESCENDING：正在下蹲。
- BOTTOM：到达底部。
- ASCENDING：正在起立。
- 回到 STANDING：完成一次动作。

这样做的好处是系统不会只看某一帧，而是看完整动作过程，所以计数更稳定。

### 4. 阈值外置

动作判定标准放在 `configs/movement_rules.json` 和 `configs/movement_standards.json` 里。你可以根据自己的摄像头角度和身体情况调整阈值，不需要改算法代码。

## 后端接口简介

常用接口：

- `GET /api/health`：检查后端是否正常。
- `POST /api/chat`：AI 助手问答。
- `POST /api/plan`：生成训练计划。
- `POST /api/report`：生成训练报告。
- `WS /ws/pose/{session_id}`：训练页面实时发送姿态关键点，后端返回动作状态和反馈。

启动后可以访问：

```text
http://localhost:8000/docs
```

这里是 FastAPI 自动生成的接口文档。

## 环境准备

推荐环境：

- Windows 10/11
- Python 3.11 或 3.12
- Node.js 18 以上
- 摄像头一个，推荐外接摄像头

## 安装后端依赖

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 配置环境变量

复制 `.env.example` 为 `.env`：

```bash
copy .env.example .env
```

然后填写自己的配置：

```env
DEEPSEEK_API_KEY=你的 DeepSeek API Key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-v4-pro
JWT_SECRET_KEY=请换成一个足够长的随机字符串
```

注意：`.env` 里有真实密钥，不要上传到 GitHub。

## 安装前端依赖

```bash
cd frontend
npm install
```

## 运行方式一：Web 全栈

先构建前端：

```bash
cd frontend
npm run build
```

回到项目根目录，启动后端：

```bash
cd ..
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

然后打开：

```text
http://localhost:8000
```

如果你在 Windows 上遇到 Vite dev server 的 `spawn EPERM` 问题，可以使用项目里的脚本：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start_web.ps1
```

这个脚本会启动 FastAPI，并从 `frontend/dist` 提供 Web 页面。

## 运行方式二：纯 Python 摄像头入口

如果只想测试核心算法，不想打开 Web 页面，可以运行：

```bash
python camera.py
```

常用按键：

- `Q`：退出。
- `R`：重置状态机。
- `S`：保存会话数据。
- `D`：切换调试模式。

如果默认摄像头不可用，可以尝试：

```bash
python camera.py --camera 1
```

## MediaPipe 模型说明

Web 前端默认可以从远程地址加载 MediaPipe 模型。

如果你要离线运行，建议把模型文件放到静态资源目录，并配置：

```env
VITE_MEDIAPIPE_WASM_BASE=/assets/mediapipe/wasm
VITE_POSE_MODEL_URL=/assets/mediapipe/pose_landmarker_full.task
```

Python 端 `camera.py` 如果需要本地模型，请下载 `pose_landmarker_full.task` 并放在项目根目录。模型文件通常不提交到 GitHub，因为它属于可下载的运行资源。

## 测试

运行核心算法测试：

```bash
python -m pytest -q -p no:cacheprovider
```

运行前端类型检查：

```bash
cd frontend
npm run type-check
```

当前项目测试结果：

```text
54 passed
vue-tsc --noEmit passed
```

## 常见问题

### 1. AI 助手显示网络错误

检查 `.env`：

- `DEEPSEEK_API_KEY` 是否填写。
- `DEEPSEEK_BASE_URL` 是否为 `https://api.deepseek.com/v1`。
- `DEEPSEEK_MODEL` 是否为可用模型，例如 `deepseek-v4-pro`。

还要注意本机代理。如果系统环境变量里有失效代理，可能导致 AI 请求失败。

### 2. 训练页面点击开始训练后卡住

常见原因：

- 摄像头被其他软件占用。
- 浏览器没有摄像头权限。
- 默认摄像头不可用，需要在页面下拉框切换摄像头。
- MediaPipe 模型加载失败。

处理建议：

- 关闭其他占用摄像头的软件。
- 在浏览器地址栏左侧允许摄像头权限。
- 刷新摄像头列表并选择外接摄像头。
- 强制刷新页面，避免旧脚本缓存。

### 3. 动作报告不准

动作识别依赖摄像头角度和身体是否完整入镜。建议：

- 摄像头放在正前方或侧前方。
- 全身进入画面，脚踝、膝盖、髋部、肩膀都要可见。
- 开始训练后先站稳，等待准备倒计时结束再下蹲。
- 每次只做一个完整动作，避免半蹲或快速晃动。

### 4. `.pytest_cache` 权限警告

项目测试命令使用：

```bash
python -m pytest -q -p no:cacheprovider
```

这样不会依赖 pytest 缓存，也不会被损坏的 `.pytest_cache` 干扰。

## 项目当前状态

已完成：

- 深蹲核心状态机。
- 深蹲错误检测。
- 摄像头选择。
- Web 训练界面。
- 训练计划和动作库页面。
- AI 助手接口。
- 训练报告基础能力。
- 核心算法测试。

仍可继续改进：

- 增加更多动作的高精度识别，例如俯卧撑、平板支撑、弓步蹲。
- 增加更完整的训练报告截图管理。
- 增加用户长期训练趋势图。
- 增加更细的个人标定流程。
- 把模型资源整理成更完整的离线部署包。

## 适合谁学习

这个项目适合想学习这些方向的人：

- 计算机视觉入门。
- 人体姿态识别。
- FastAPI 后端开发。
- Vue 前端开发。
- AI Agent 和大语言模型应用。
- 健身动作分析算法。

如果你是小白，可以按这个顺序学习：

1. 先运行 `camera.py`，理解摄像头和姿态识别。
2. 再看 `geometry.py`，理解角度怎么算。
3. 再看 `fsm.py`，理解一次深蹲怎么被识别。
4. 再看 `backend/api/pose_ws.py`，理解前后端如何实时通信。
5. 最后看 `frontend/src/views/WorkoutSession.vue`，理解页面如何展示训练结果。

## 免责声明

CyberTrainer 是训练辅助工具，不是医疗诊断工具。任何疼痛、受伤、眩晕、麻木或不适，都应该停止训练并咨询医生、康复师或专业教练。
