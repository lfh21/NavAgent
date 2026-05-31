# API Contract

所有接口均返回 JSON，除 `GET /` 和 `/assets/<filename>` 外。

## `GET /api/health`

返回服务状态、默认 provider 和正式模式基础轮询间隔。

示例：

```json
{
  "ok": true,
  "service": "blind-assist-web-demo",
  "defaultProvider": "qwen",
  "formalIntervalMs": 1500,
  "providers": ["qwen", "openai", "gemini", "ernie", "kimi", "zhipu"]
}
```

## `GET /api/providers`

返回前端可选 provider 列表，以及每个 provider 是否已经配置。

示例：

```json
{
  "defaultProvider": "qwen",
  "providers": [
    {
      "id": "qwen",
      "label": "Qwen3.6-Plus",
      "enabled": true
    }
  ]
}
```

## `POST /api/debug/analyze`

用于图片导航模式。

### multipart/form-data

- `image`：图片文件，必填
- `provider`：`openai|ernie|qwen|gemini|kimi|zhipu|mock`
- `task`：`scene_description|navigation_guidance|general_assistance`
- `text`：用户输入，可选

### application/json

```json
{
  "provider": "qwen",
  "task": "scene_description",
  "text": "请描述前方环境",
  "imageBase64": "......",
  "mimeType": "image/jpeg",
  "fileName": "debug.jpg"
}
```

### 响应

```json
{
  "ok": true,
  "mode": "debug",
  "provider": "qwen",
  "model": "Qwen3.6-Plus",
  "result": {
    "summary": "前方两米内基本可通行，左侧有椅子。",
    "guidance": [],
    "hazards": [],
    "riskLevel": "low",
    "confidence": 0.88,
    "task": "scene_description",
    "sourceText": "请描述前方环境"
  },
  "ttsPayload": {
    "text": "前方两米内基本可通行，左侧有椅子。",
    "language": "zh-CN",
    "priority": "normal",
    "voiceHints": {
      "tone": "calm",
      "pace": "steady"
    }
  },
  "savedArtifacts": {
    "imagePath": "output/debug/...",
    "jsonPath": "output/debug/..."
  }
}
```

## `POST /api/formal/analyze`

用于视频导航模式。前端把当前摄像头画面截成 JPEG，再提交 base64 图片帧。

### 请求

```json
{
  "provider": "qwen",
  "task": "navigation_guidance",
  "text": "持续告诉我前方障碍，并在需要时给我转向提示。",
  "frameBase64": "......",
  "mimeType": "image/jpeg",
  "sessionId": "live-demo-session",
  "requestedIntervalMs": 1500,
  "frameMeta": {
    "timestamp": "2026-05-31T12:00:00.000Z",
    "width": 640,
    "height": 360
  },
  "clientState": {
    "lastSummary": "前方基本可通行。",
    "guidance": ["保持缓慢直行。"],
    "lastRiskLevel": "low",
    "lastSpokenText": "前方基本可通行。保持缓慢直行。",
    "forceDetailed": false
  }
}
```

必填字段：

- `frameBase64`

常用字段：

- `provider`：未传时使用默认 provider。
- `task`：默认 `navigation_guidance`。
- `sessionId`：用于服务端保存轻量会话状态和 JSONL 日志。
- `requestedIntervalMs`：前端请求的基础间隔，后端会结合风险返回 `nextIntervalMs`。
- `clientState.forceDetailed`：要求本轮尽量生成详细反馈并允许播报。

### 响应

```json
{
  "ok": true,
  "mode": "formal",
  "provider": "qwen",
  "model": "Qwen3.6-Plus",
  "sessionId": "live-demo-session",
  "frameMeta": {
    "timestamp": "2026-05-31T12:00:00.000Z",
    "width": 640,
    "height": 360
  },
  "result": {
    "summary": "前方基本可通行，左前方有障碍。",
    "guidance": ["保持缓慢直行。", "略微向右调整。"],
    "hazards": [
      {
        "type": "obstacle",
        "severity": "medium",
        "description": "左前方约一米处存在静态障碍物。"
      }
    ],
    "riskLevel": "medium",
    "confidence": 0.86,
    "task": "navigation_guidance",
    "sourceText": "持续告诉我前方障碍，并在需要时给我转向提示。"
  },
  "ttsPayload": {
    "text": "有风险。保持缓慢直行。",
    "language": "zh-CN",
    "priority": "high",
    "voiceHints": {
      "tone": "calm",
      "pace": "steady"
    }
  },
  "shouldSpeak": true,
  "eventType": "warning",
  "nextIntervalMs": 1200
}
```

`eventType` 取值：

- `stable`：场景稳定，本轮一般静默。
- `change`：场景或指令发生变化。
- `warning`：中风险或无法判断。
- `danger`：高风险，需要优先播报。

## `POST /api/tts/payload`

把结构化结果整理成 TTS 载荷，也可直接包装纯文本。

### 输入结构化结果

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

### 输入纯文本

```json
{
  "text": "前方通道基本可通行。",
  "language": "zh-CN"
}
```

### 响应

```json
{
  "ok": true,
  "ttsPayload": {
    "text": "前方通道基本可通行。保持缓慢直行。",
    "language": "zh-CN",
    "priority": "normal",
    "voiceHints": {
      "tone": "calm",
      "pace": "steady"
    }
  }
}
```
