# 智训 Web Frontend

基于 Figma 彩色稿转译的 Web 前端项目，使用 Vue 3 + TypeScript + Vite + Element Plus + Tailwind CSS。

## 技术栈

- Vue 3 `^3.4.0`
- TypeScript `^5.3.3`
- Vite `^5.0.11`
- Element Plus `^2.5.3`
- Pinia `^2.1.7`
- Vue Router `^4.2.5`
- Axios `^1.6.5`
- `@mediapipe/tasks-vision` `^0.10.21`
- ECharts `^5.4.3`

## 路由

- `/`：Landing 品牌首页
- `/login`：登录
- `/register`：注册
- `/dashboard`：主控台，需要登录
- `/questionnaire`：4 步体能问卷，需要登录
- `/movements`：动作库
- `/workout`：实时训练，需要登录

`meta.requiresAuth` 页面会检查 `localStorage.token`，没有 token 时跳转到 `/login`。

## 开发

```bash
npm install
npm run dev
```

Vite 代理：

- `/api` -> `http://localhost:8000`
- `/ws` -> `ws://localhost:8000`

## MediaPipe 配置

默认从官方 CDN 加载 WASM 与 Pose Landmarker Lite 模型。部署时可通过环境变量改成自托管地址：

```bash
VITE_MEDIAPIPE_WASM_BASE=/mediapipe/wasm
VITE_POSE_MODEL_URL=/models/pose_landmarker_lite.task
```
