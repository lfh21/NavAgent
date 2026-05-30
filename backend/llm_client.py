import json
import urllib.error
import urllib.request

from backend.text_utils import SYSTEM_PROMPT, build_user_prompt, extract_json_object


def _mock_result(task, user_text):
    if task == "navigation_guidance":
        return {
            "summary": "前方通道基本可通行，左侧存在静态障碍物。",
            "guidance": ["保持缓慢直行。", "接近左侧障碍时略微向右调整。"],
            "hazards": [
                {
                    "type": "obstacle",
                    "severity": "medium",
                    "description": "左前方约一米处存在静态障碍物。",
                }
            ],
            "riskLevel": "medium",
            "confidence": 0.86,
            "echoText": user_text or "",
        }

    return {
        "summary": "当前环境为室内通道，前方区域基本清晰。",
        "guidance": ["可以先原地确认左右环境，再缓慢向前。"],
        "hazards": [],
        "riskLevel": "low",
        "confidence": 0.89,
        "echoText": user_text or "",
    }


class BlindAssistLLMClient(object):
    def __init__(self, settings):
        self.settings = settings

    def analyze(self, provider, task, mode, user_text, image_data_url):
        selected_provider = provider or self.settings["default_provider"]

        if selected_provider == "mock":
            return {
                "provider": "mock",
                "model": "mock-vision-demo",
                "result": _mock_result(task, user_text),
            }

        if selected_provider in {"openai", "ernie", "qwen", "kimi", "zhipu"}:
            return self._analyze_openai_compatible(
                provider=selected_provider,
                task=task,
                mode=mode,
                user_text=user_text,
                image_data_url=image_data_url,
            )

        if selected_provider == "gemini":
            return self._analyze_gemini(
                task=task,
                mode=mode,
                user_text=user_text,
                image_data_url=image_data_url,
            )

        raise ValueError("不支持的 provider: {0}".format(selected_provider))

    def _split_data_url(self, image_data_url):
        if not image_data_url.startswith("data:") or "," not in image_data_url:
            raise ValueError("图像数据格式不正确，预期为 data URL。")

        header, image_base64 = image_data_url.split(",", 1)
        mime_type = "image/jpeg"
        if header.startswith("data:"):
            mime_type = header[5:].split(";", 1)[0] or mime_type

        return mime_type, image_base64

    def _analyze_openai_compatible(self, provider, task, mode, user_text, image_data_url):
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("未安装 openai SDK，请先安装 requirements.txt 中的依赖。")

        provider_settings = self.settings[provider]
        api_key = provider_settings.get("api_key")
        if not api_key:
            raise RuntimeError("{0} API Key 未配置。".format(provider.upper()))

        client = OpenAI(
            api_key=api_key,
            base_url=provider_settings.get("base_url"),
        )

        response = client.chat.completions.create(
            model=provider_settings.get("model"),
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": build_user_prompt(task=task, mode=mode, user_text=user_text),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": image_data_url},
                        },
                    ],
                },
            ],
        )

        content = response.choices[0].message.content
        return {
            "provider": provider,
            "model": provider_settings.get("model"),
            "result": extract_json_object(content),
        }

    def _analyze_gemini(self, task, mode, user_text, image_data_url):
        provider_settings = self.settings["gemini"]
        api_key = provider_settings.get("api_key")
        if not api_key:
            raise RuntimeError("GEMINI API Key 未配置。")

        mime_type, image_base64 = self._split_data_url(image_data_url)
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": image_base64,
                            }
                        },
                        {
                            "text": build_user_prompt(task=task, mode=mode, user_text=user_text),
                        },
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1000,
            },
        }

        base_url = provider_settings.get("base_url", "").rstrip("/")
        model = provider_settings.get("model")
        url = "{0}/models/{1}:generateContent".format(base_url, model)
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError("Gemini API 请求失败，HTTP {0}: {1}".format(exc.code, detail)) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError("无法连接到 Gemini API: {0}".format(exc)) from exc

        try:
            parts = data["candidates"][0].get("content", {}).get("parts", [])
            content = "".join(part.get("text", "") for part in parts).strip()
        except (KeyError, IndexError, TypeError):
            raise RuntimeError("Gemini API 返回格式不符合预期: {0}".format(json.dumps(data, ensure_ascii=False)))

        if not content:
            raise RuntimeError("Gemini API 没有返回文字内容: {0}".format(json.dumps(data, ensure_ascii=False)))

        return {
            "provider": "gemini",
            "model": model,
            "result": extract_json_object(content),
        }

    def _analyze_zhipu(self, task, mode, user_text, image_data_url):
        try:
            from zhipuai import ZhipuAI
        except ImportError:
            raise RuntimeError("未安装 zhipuai SDK，请先安装 requirements.txt 中的依赖。")

        provider_settings = self.settings["zhipu"]
        api_key = provider_settings.get("api_key")
        if not api_key:
            raise RuntimeError("ZHIPU API Key 未配置。")

        client = ZhipuAI(api_key=api_key)
        response = client.chat.completions.create(
            model=provider_settings.get("model"),
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": build_user_prompt(task=task, mode=mode, user_text=user_text),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": image_data_url},
                        },
                    ],
                },
            ],
        )

        content = response.choices[0].message.content
        return {
            "provider": "zhipu",
            "model": provider_settings.get("model"),
            "result": extract_json_object(content),
        }
