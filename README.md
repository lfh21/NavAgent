# blind-assist-web-demo

这是一个 Web Demo 项目，用于展示盲人辅助系统的最小可行实现。它四类模块：

1. 前端交互
2. 后端大模型响应处理
3. 大模型 API 接口
4. 额外功能


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

## 2. 满足大作业要求


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


- `Python 3.10+`


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


## 7. 接口概览

- `GET /`
- `GET /api/health`
- `GET /api/providers`
- `POST /api/debug/analyze`
- `POST /api/formal/analyze`
- `POST /api/tts/payload`