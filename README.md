# blind-assist-web-demo

这是一个网页端盲人视觉辅助系统 Demo，用于展示“前端交互 + 后端大模型响应处理 + 多模态大模型 API + 语音/日志等扩展能力”的最小可演示实现。

系统提供两种使用模式：

- `图片导航模式`：上传单张图片，适合调试模型、prompt 和图片输入质量。
- `视频导航模式`：调用浏览器摄像头，前端定时截取视频帧并通过 HTTP 发给后端分析；寻路任务可持续轮询，场景描述和综合辅助默认单次分析。

## 1. 项目结构

```text
NavAgent/
├── backend/
│   ├── __init__.py
│   ├── api_interface.py
│   ├── config.py
│   ├── file_tools.py
│   ├── llm_client.py
│   └── text_utils.py
├── docs/
│   └── api-contract.md
├── frontend/
│   ├── app.js
│   ├── index.html
│   └── styles.css
├── cli.py
├── file_utils.py
├── main.py
├── output/
├── pyproject.toml
├── requirements.txt
├── README.md
├── 使用方法.md
└── 盲人辅助系统架构计划.md
```

## 2. 功能概览

### 前端交互

- 图片导航模式上传图片并展示结构化分析结果。
- 视频导航模式调用摄像头、截帧、压缩为 JPEG 后提交分析。
- 支持任务切换：`scene_description`、`navigation_guidance`、`general_assistance`。
- 支持 provider 切换，并在页面标记未配置的 provider。
- 支持浏览器 `speechSynthesis` 播报结果。
- 支持浏览器语音输入，将语音识别内容写入问题文本框。
- 视频导航模式支持盲操作快捷键：空格、`S`、`X`、`-`、`+`。

### 后端处理

- 接收 multipart 图片或 JSON base64 图片帧。
- 按任务构造盲人辅助场景 prompt。
- 调用视觉大模型并提取 JSON。
- 规范化 `summary`、`guidance`、`hazards`、`riskLevel`、`confidence`。
- 为语音播报生成 `ttsPayload`。
- 视频导航模式根据风险、变化和上一轮状态返回 `shouldSpeak`、`eventType`、`nextIntervalMs`。
- 保存调试图片、结果 JSON 和正式模式 JSONL 日志。

### 模型接口

`backend/llm_client.py` 当前支持：

- `openai`：OpenAI SDK
- `ernie`：OpenAI 兼容接口
- `qwen`：OpenAI 兼容接口
- `kimi`：OpenAI 兼容接口
- `zhipu`：OpenAI 兼容接口
- `gemini`：Gemini REST API
- `mock`：后端模拟结果，主要用于接口调试

注意：前端 provider 下拉框默认展示真实 provider；`mock` 可通过 API 或代码配置测试后端链路。

## 3. 环境要求

- Python `3.11+`，与 `pyproject.toml` 保持一致。
- 依赖见 `requirements.txt`。

安装依赖：

```bash
pip install -r requirements.txt
```

## 4. 配置

项目启动时会先加载 `.env.example`，再加载 `.env`。后加载的 `.env` 会覆盖默认值，所以本地密钥应写在 `.env` 中。

可从 `.env.example` 复制一份：

```bash
cp .env.example .env
```

Windows PowerShell 可使用：

```powershell
Copy-Item .env.example .env
```

关键配置项：

```env
APP_HOST=127.0.0.1
APP_PORT=8000
APP_DEBUG=true
DEFAULT_PROVIDER=qwen
FORMAL_INTERVAL_MS=1500
OUTPUT_DIR=output

QWEN_API_KEY=
QWEN_BASE_URL=
QWEN_MODEL=Qwen3.6-Plus
```

完整 provider 配置请看 `.env.example` 或 [使用方法.md](使用方法.md)。

## 5. 启动

直接启动：

```bash
python main.py
```

或使用 CLI：

```bash
python cli.py runserver
```

指定地址：

```bash
python cli.py runserver --host 127.0.0.1 --port 8000
```

查看配置：

```bash
python cli.py show-config
```

默认页面地址：

- `http://127.0.0.1:8000/`

## 6. 接口概览

- `GET /`
- `GET /assets/<filename>`
- `GET /api/health`
- `GET /api/providers`
- `POST /api/debug/analyze`
- `POST /api/formal/analyze`
- `POST /api/tts/payload`

详细请求和响应字段见 [docs/api-contract.md](docs/api-contract.md)。

## 7. 输出文件

- `output/debug/`：保存图片导航模式上传的图片和响应 JSON。
- `output/formal/`：按 `sessionId` 保存视频导航模式 JSONL 日志。

## 8. 当前边界

- 当前不是 WebSocket 视频流，而是“浏览器截帧 + HTTP 请求”。
- 尚未接入独立 TTS 合成服务，网页端使用浏览器原生播报。
- 视频导航依赖浏览器摄像头权限。
- 长时间运行时仅维护轻量会话状态，没有复杂的多轮记忆压缩。
