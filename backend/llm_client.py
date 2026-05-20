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

        if selected_provider in {"openai", "deepseek", "qwen"}:
            return self._analyze_openai_compatible(
                provider=selected_provider,
                task=task,
                mode=mode,
                user_text=user_text,
                image_data_url=image_data_url,
            )

        if selected_provider == "zhipu":
            return self._analyze_zhipu(
                task=task,
                mode=mode,
                user_text=user_text,
                image_data_url=image_data_url,
            )

        raise ValueError("不支持的 provider: {0}".format(selected_provider))

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
