import os


def _project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _strip_env_quotes(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _load_env_file(path, override=False):
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            if not key:
                continue
            if key in os.environ and not override:
                continue

            os.environ[key] = _strip_env_quotes(value.strip())


def load_env_files():
    root_dir = _project_root()
    _load_env_file(os.path.join(root_dir, ".env.example"), override=True)
    _load_env_file(os.path.join(root_dir, ".env"), override=True)


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
    load_env_files()

    return {
        "app_host": os.getenv("APP_HOST", "127.0.0.1"),
        "app_port": _to_int(os.getenv("APP_PORT"), 8000),
        "app_debug": _to_bool(os.getenv("APP_DEBUG"), True),
        "default_provider": os.getenv("DEFAULT_PROVIDER", "qwen"),
        "formal_interval_ms": _to_int(os.getenv("FORMAL_INTERVAL_MS"), 1500),
        "output_dir": os.getenv("OUTPUT_DIR", "output"),
        "openai": {
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        },
        "gemini": {
            "api_key": os.getenv("GEMINI_API_KEY", ""),
            "base_url": os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"),
            "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        },
        "qwen": {
            "api_key": os.getenv("QWEN_API_KEY", ""),
            "base_url": os.getenv("QWEN_BASE_URL", ""),
            "model": os.getenv("QWEN_MODEL", "Qwen3.6-Plus"),
        },
        "kimi": {
            "api_key": os.getenv("KIMI_API_KEY", ""),
            "base_url": os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
            "model": os.getenv("KIMI_MODEL", "kimi-k2.6"),
        },
        "zhipu": {
            "api_key": os.getenv("ZHIPU_API_KEY", ""),
            "base_url": os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
            "model": os.getenv("ZHIPU_MODEL", "glm-4v-flash"),
        },
    }
