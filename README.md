# blind-assist-web-demo

这是一个按课程示例要求整理过的 Web Demo 项目，用于展示盲人辅助系统的最小可行实现。它满足截图里要求的四类模块：

1. 前端交互
2. 后端大模型响应处理
3. 大模型 API 接口
4. 额外功能

当前主题不是“本地文件问答”，而是“盲人辅助系统”。但目录结构、模块分层和多厂商 API 预留方式都按示例作业的要求组织，并且额外加入了：

- Debug 模式
  - 上传单张图片，返回场景分析
- Formal 模式
  - 实时摄像头视频帧 + 用户文字，持续输出描述或寻路指令
- 本地输出归档
  - 自动把 Debug 图片和分析结果保存到 `output/`

## 1. 项目结构

```text
agent-demo-api/
├── backend/
│   ├── __init__.py
│   ├── api_interface.py
│   ├── config.py
│   ├── file_tools.py
│   ├── llm_client.py
│   └── text_utils.py
├── frontend/
│   ├── app.js
│   ├── index.html
│   └── styles.css
├── cli.py
├── file_utils.py
├── main.py
├── output/
├── README.md
└── requirements.txt
```

截图里的 `backend/`、`cli.py`、`file_utils.py`、`main.py`、`output/`、`README.md`、`requirements.txt` 都已经补齐。相比示例，我额外加入了 `frontend/`，用于承载网页版交互。

## 2. 对照截图要求

### 2.1 最小可行化方案

- 本项目已经具备前端页面、后端接口、多厂商大模型适配和本地输出归档。
- 演示效果上，至少已经比“纯本地文件智能体助手”的示例多出实时视频分析模式。

### 2.2 作业应包含的模块

#### 前端交互

- `frontend/index.html`
- `frontend/app.js`
- `frontend/styles.css`

功能：

- Debug 模式上传图片
- Formal 模式打开摄像头
- 实时输入文本
- 切换 provider
- 返回场景分析或寻路结果

#### 后端大模型响应处理

- `backend/api_interface.py`
- `backend/text_utils.py`
- `backend/file_tools.py`

功能：

- 接收前端图片或视频帧
- 统一 prompt
- 规范化 JSON 响应
- 生成 TTS 载荷
- 保存调试结果到本地

#### 大模型 API 接口

- `backend/llm_client.py`
- `backend/config.py`

支持：

- OpenAI SDK
- DeepSeek 兼容 OpenAI 接口
- ZhipuAI SDK
- Mock provider

#### 其他功能

- `output/` 本地归档
- `POST /api/tts/payload` TTS 载荷接口
- Formal 模式实时轮询分析

## 3. 技术准备与环境搭建

截图里提到的准备项，本项目对应如下：

### 大模型 API 文档

- OpenAI SDK
- DeepSeek API / OpenAI-Compatible 接口
- ZhipuAI SDK

### API Key

需要自行准备。当前 Demo 预留了三家 provider：

- `openai`
- `deepseek`
- `zhipu`

### 开发语言与环境

课程截图写的是 `Python 3.6+`。但考虑到当前 OpenAI / ZhipuAI SDK 的版本现实，建议直接使用：

- `Python 3.10+`

这样更稳，不容易卡在 SDK 兼容性上。

## 4. 环境变量

建议通过 shell 环境变量配置：

```bash
export APP_HOST=127.0.0.1
export APP_PORT=8000
export APP_DEBUG=true
export DEFAULT_PROVIDER=mock

export OPENAI_API_KEY=...
export OPENAI_BASE_URL=https://api.openai.com/v1
export OPENAI_MODEL=gpt-4o-mini

export DEEPSEEK_API_KEY=...
export DEEPSEEK_BASE_URL=https://api.deepseek.com
export DEEPSEEK_MODEL=deepseek-chat

export ZHIPU_API_KEY=...
export ZHIPU_MODEL=glm-4v-flash
```

## 5. 启动方式

安装依赖：

```bash
pip install -r requirements.txt
```

启动服务：

```bash
python main.py
```

或者：

```bash
python cli.py runserver
```

默认页面地址：

- `http://127.0.0.1:8000/`

## 6. Web 页面模式

### Debug 模式

- 上传一张图片
- 输入用户文字
- 返回稳定的场景分析
- 自动保存调试图片和结果到 `output/debug/`

### Formal 模式

- 调用浏览器摄像头
- 周期性截取当前视频帧
- 搭配实时文字输入
- 持续输出描述或寻路指令

这是一个“准实时轮询”方案，不是 WebSocket 流式方案，但已经满足课程作业里的最小演示要求。

## 7. 接口概览

- `GET /`
- `GET /api/health`
- `GET /api/providers`
- `POST /api/debug/analyze`
- `POST /api/formal/analyze`
- `POST /api/tts/payload`

## 8. 说明

由于当前本地环境禁止运行 Python，我这次完成的是：

- 完整的 Python Web Demo 脚手架
- 简洁前端
- 多 provider 适配层
- README 和目录结构整理

我没有在本地实际启动 `python main.py` 做联调验证。如果你下一步要我继续，我可以在不运行本地 Python 的前提下，继续帮你把接口字段、前端文案和输出格式再细化一轮。
