# TradingAgents Web

Web 界面，支持通过浏览器使用 TradingAgents 多 Agent 交易分析功能。

## 启动

```bash
# 开发模式（前后端分离，带 CORS）
tradingagents web --dev --port 8000

# 生产模式（前端已构建，由 FastAPI 直接 serve）
tradingagents web --port 8000
```

## 开发

前端开发服务器（代理 API 到后端）：

```bash
cd web/client
npm run dev
```

后端（另一个终端）：

```bash
tradingagents web --dev --port 8000
```

然后浏览器访问 `http://localhost:5173`。

## 构建前端

```bash
cd web/client
npm install
npm run build
```

构建后的文件输出到 `web/client/dist/`，生产模式由 FastAPI 自动 serve。

## 功能

- **新建分析**：输入股票代码和日期，选择实时流式或后台模式
- **实时进度**：流式模式下查看 Agent 执行链和报告逐步生成
- **历史报告**：查看已完成的分析报告
- **20 并发**：后台自动排队超出并发的任务
- **默认模型**：后台固定使用 Qwen（qwen3.6-plus），前端不暴露模型选择

## 技术栈

- **后端**：FastAPI + uvicorn + sse-starlette
- **前端**：React 18 + TypeScript + Tailwind CSS + Vite
- **并发控制**：`asyncio.Semaphore(20)` 限制同时执行的分析任务
