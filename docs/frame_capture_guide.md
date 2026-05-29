# 错误帧截取功能使用指南

## 功能概述

错误帧截取功能可以在检测到动作不标准时自动截取当前帧，用于训练报告展示。这有助于用户回顾和改进自己的动作技术。

## 功能特性

### 1. 自动截取
- 当检测到错误动作时自动截取帧
- 支持多种错误类型：膝内扣、躯干前倾、脚跟抬起、深度不足等

### 2. 智能冷却
- 相同错误类型有冷却时间（默认3秒），避免重复截取
- 可配置每个错误类型的最大截取数量

### 3. 信息覆盖层
- 截取的帧会自动添加信息覆盖层，包含：
  - 错误类型和描述
  - 当前角度数据
  - 训练状态和次数
  - 时间戳

### 4. 报告集成
- 截取的帧可以嵌入HTML训练报告
- 支持生成错误帧拼图

## 使用方法

### 基本使用

```python
from frame_capture import FrameCaptureManager

# 创建管理器
capture_manager = FrameCaptureManager(
    output_dir="captured_frames",  # 输出目录
    cooldown_seconds=3.0,          # 冷却时间
    max_captures_per_error=5,      # 每类错误最大截取数
    max_total_captures=50,         # 总最大截取数
)

# 在检测到错误时截取帧
captured = capture_manager.capture_frame(
    frame=current_frame,
    error_type="knee_valgus",
    error_description="膝盖内扣 (ratio=0.75)",
    rep_number=3,
    angles={"knee_angle": 95, "hip_angle": 85},
    state="bottom",
)

# 保存所有截取的帧
saved_paths = capture_manager.save_captures()
```

### 与FSM集成

```python
from fsm import SquatFSM
from frame_capture import FrameCaptureManager

# 创建FSM和截取管理器
fsm = SquatFSM("configs/movement_rules.json")
capture_manager = FrameCaptureManager()

# 设置回调
def on_error_with_data(error_type, error_description, angles):
    captured = capture_manager.capture_frame(
        frame=current_frame,
        error_type=error_type,
        error_description=error_description,
        rep_number=fsm.rep_count,
        angles=angles,
        state=fsm.state.value,
    )

fsm.on_error_with_data = on_error_with_data
```

### 生成训练报告

```python
from report_generator import ReportGenerator

# 创建报告生成器
generator = ReportGenerator()

# 生成HTML报告
report_path = generator.generate_html_report(
    session_data=session_data,
    captured_frames=captured_frames,
    include_images=True,
)

# 生成错误帧拼图
mosaic_path = generator.generate_mosaic_image(
    captured_frames=captured_frames,
)
```

## 配置选项

### FrameCaptureManager 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| output_dir | str | "captured_frames" | 截取帧输出目录 |
| cooldown_seconds | float | 3.0 | 相同错误类型的冷却时间（秒） |
| max_captures_per_error | int | 5 | 每类错误的最大截取数量 |
| max_total_captures | int | 50 | 总最大截取数量 |
| image_quality | int | 85 | JPEG压缩质量（0-100） |
| max_width | int | 640 | 截取帧的最大宽度 |

### 错误类型

| 错误类型 | 说明 |
|----------|------|
| trunk_forward_lean | 躯干过度前倾 |
| knee_valgus | 膝盖内扣 |
| hip_dominant | 髋驱动明显 |
| knee_dominant | 膝驱动明显 |
| heel_lift | 脚跟抬起 |
| insufficient_depth | 深度不足 |

## 文件结构

```
captured_frames/
├── 20240101_120000/           # 会话ID
│   ├── a1b2c3d4_knee_valgus.jpg
│   ├── e5f6g7h8_trunk_forward_lean.jpg
│   └── ...
└── 20240101_130000/
    └── ...

reports/
├── report_20240101_120000.html
├── mosaic_20240101_120000.jpg
└── ...
```

## API端点

### 生成训练报告

```
POST /api/report/generate
```

请求体：
```json
{
    "session_data": {
        "summary": {...},
        "captured_frames": [...]
    },
    "include_images": true
}
```

响应：
```json
{
    "success": true,
    "report_path": "reports/report_20240101_120000.html",
    "message": "报告生成成功"
}
```

### 生成错误帧拼图

```
POST /api/report/mosaic
```

请求体：
```json
{
    "session_data": {
        "captured_frames": [...]
    }
}
```

响应：
```json
{
    "success": true,
    "mosaic_path": "reports/mosaic_20240101_120000.jpg",
    "message": "拼图生成成功"
}
```

## 最佳实践

1. **合理设置冷却时间**
   - 太短会导致截取过多相似帧
   - 太长可能错过重要错误
   - 建议2-5秒

2. **限制截取数量**
   - 避免占用过多存储空间
   - 建议每类错误3-5张，总数不超过50张

3. **定期清理**
   - 定期清理旧的截取帧和报告
   - 可以设置自动清理策略

4. **报告生成时机**
   - 建议在训练结束后自动生成报告
   - 可以提供手动触发选项

## 示例代码

完整示例见 `camera.py`，展示了如何将帧截取功能集成到主程序中。
