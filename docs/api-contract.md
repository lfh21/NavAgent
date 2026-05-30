# API Contract

## `GET /api/health`

返回服务状态、默认 provider 和 formal 模式轮询间隔。

## `GET /api/providers`

返回前端可用的 provider 列表。

## `POST /api/debug/analyze`

### 表单模式

- `image`: 图片文件
- `provider`: `openai|ernie|qwen|gemini|kimi|zhipu`
- `task`: `scene_description|navigation_guidance|general_assistance`
- `text`: 用户输入

### JSON 模式

```json
{
  "provider": "mock",
  "task": "scene_description",
  "text": "请描述前方环境",
  "imageBase64": "......",
  "mimeType": "image/jpeg",
  "fileName": "debug.jpg"
}
```

## `POST /api/formal/analyze`

```json
{
  "provider": "mock",
  "task": "navigation_guidance",
  "text": "持续告诉我前方障碍，并在需要时给我转向提示。",
  "frameBase64": "......",
  "mimeType": "image/jpeg",
  "sessionId": "live-demo-session"
}
```

## `POST /api/tts/payload`

```json
{
  "result": {
    "summary": "前方通道基本可通行。",
    "guidance": ["保持缓慢直行。"],
    "hazards": [],
    "riskLevel": "low"
  },
  "language": "zh-CN"
}
```
