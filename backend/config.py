import os


def _to_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _to_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_settings():
    return {
        "app_host": os.getenv("APP_HOST", "127.0.0.1"),
        "app_port": _to_int(os.getenv("APP_PORT"), 8000),
        "app_debug": _to_bool(os.getenv("APP_DEBUG"), True),
        "default_provider": os.getenv("DEFAULT_PROVIDER", "mock"),
        "formal_interval_ms": _to_int(os.getenv("FORMAL_INTERVAL_MS"), 1500),
        "output_dir": os.getenv("OUTPUT_DIR", "output"),
        "openai": {
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        },
        "deepseek": {
            "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
            "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        },
        "zhipu": {
            "api_key": os.getenv("ZHIPU_API_KEY", ""),
            "model": os.getenv("ZHIPU_MODEL", "glm-4v-flash"),
        },
    }
