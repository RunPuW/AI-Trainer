# 赛博私教 - 项目说明

## 项目概述
赛博私教（CyberTrainer）是一个基于计算机视觉的健身动作识别与评估系统。
MVP 阶段聚焦**深蹲**动作的实时识别、错误检测和评分。

## 技术栈
- **Python 3.11/3.12**
- **MediaPipe Pose Landmarker** (33个关键点)
- **OpenCV** (视频捕获与可视化)
- **NumPy** (几何计算)
- **pyttsx3** (语音反馈)

## 项目结构
```
.
├── configs/
│   └── movement_rules.json    # 动作判定规则配置（阈值外置）
├── camera.py                   # 主程序入口
├── geometry.py                 # 几何计算模块
├── fsm.py                      # 有限状态机（深蹲四状态）
├── filters.py                  # EMA滤波器与信号处理
├── overlay.py                  # OpenCV可视化与语音反馈
├── requirements.txt            # Python依赖
└── AGENTS.md                   # 本文件
```

## 核心设计原则
1. **算法先行**：阶段一只做 Python 端核心算法，不引入前端/数据库
2. **阈值外置**：所有判定阈值放在 JSON 中，便于自测调参
3. **文献基准**：初始阈值基于运动科学文献，通过自测修正系统误差
4. **单人调试**：支持仅用自己的身体完成算法闭环验证

## 深蹲状态机
```
STANDING -> DESCENDING -> BOTTOM -> ASCENDING -> STANDING
```

## 关键阈值（来自文献+自测修正）
| 指标 | 文献基准 | 系统初始值 | 说明 |
|------|---------|-----------|------|
| 底部膝角 | 100°-110° | ≤115° | 预留 MediaPipe 系统误差 |
| 躯干-胫骨差值 | ±10° | ±10° | 中立范围 |
| 躯干前倾警戒 | 45° | ≤45° | 过度前倾 |
| 膝内扣比例 | - | <0.82 | 需自测标定 |

## 运行方式
```bash
# 1. 创建虚拟环境
python -m venv venv

# 2. 激活环境（Windows）
venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行
python camera.py
```

## 调参流程
1. 按 FMS 标准执行标准深蹲，记录系统输出
2. 故意做错动作（内扣、前倾、浅蹲），记录边界值
3. 修改 `configs/movement_rules.json` 中的阈值
4. 重复测试，用 Git 记录每次调整

## 按键控制
- `Q` - 退出
- `R` - 重置状态机
- `S` - 保存会话数据
- `D` - 切换调试模式

## 校准记录模板
```json
{
  "date": "2026-05-24",
  "subject": "self",
  "shoes": "flat",
  "camera_position": "side",
  "observed_bottom_knee_angle": 115,
  "literature_reference": 105,
  "adjustment": "+10° system bias",
  "notes": "..."
}
```
