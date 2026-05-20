from flask import Flask, jsonify, request, send_from_directory

from backend.file_tools import append_formal_log, save_debug_artifact
from backend.llm_client import BlindAssistLLMClient
from backend.text_utils import build_tts_payload, normalize_result
from file_utils import (
    ensure_directory,
    get_frontend_dir,
    image_bytes_to_data_url,
    image_input_to_bytes,
    project_path,
)


def create_app(settings):
    app = Flask(
        __name__,
        static_folder=None,
    )

    ensure_directory(project_path(settings["output_dir"]))
    frontend_dir = get_frontend_dir()
    llm_client = BlindAssistLLMClient(settings)

    @app.route("/")
    def index():
        return send_from_directory(frontend_dir, "index.html")

    @app.route("/assets/<path:filename>")
    def assets(filename):
        return send_from_directory(frontend_dir, filename)

    @app.route("/api/health")
    def health():
        return jsonify(
            {
                "ok": True,
                "service": "blind-assist-web-demo",
                "defaultProvider": settings["default_provider"],
                "formalIntervalMs": settings["formal_interval_ms"],
                "providers": ["mock", "openai", "deepseek", "qwen", "zhipu"],
            }
        )

    @app.route("/api/providers")
    def providers():
        return jsonify(
            {
                "defaultProvider": settings["default_provider"],
                "providers": [
                    {
                        "id": "mock",
                        "label": "Mock Demo",
                        "enabled": True,
                    },
                    {
                        "id": "openai",
                        "label": "GPT",
                        "enabled": bool(settings["openai"]["api_key"]),
                    },
                    {
                        "id": "deepseek",
                        "label": "DeepSeek",
                        "enabled": bool(settings["deepseek"]["api_key"]),
                    },
                    {
                        "id": "qwen",
                        "label": "Qwen3.6-Plus",
                        "enabled": bool(settings["qwen"]["api_key"] and settings["qwen"]["base_url"]),
                    },
                    {
                        "id": "zhipu",
                        "label": "GLM",
                        "enabled": bool(settings["zhipu"]["api_key"]),
                    },
                ],
            }
        )

    @app.route("/api/debug/analyze", methods=["POST"])
    def debug_analyze():
        try:
            payload = request.get_json(silent=True) or {}
            provider = request.form.get("provider") or payload.get(
                "provider", settings["default_provider"]
            )
            task = request.form.get("task") or payload.get("task", "scene_description")
            user_text = request.form.get("text") or payload.get("text", "")

            if request.files.get("image"):
                image_file = request.files["image"]
                image_bytes = image_file.read()
                filename = image_file.filename or "upload.jpg"
                mime_type = image_file.mimetype or "image/jpeg"
            else:
                image_base64 = payload.get("imageBase64")
                mime_type = payload.get("mimeType", "image/jpeg")
                filename = payload.get("fileName", "upload.jpg")
                if not image_base64:
                    return jsonify({"ok": False, "message": "调试模式需要上传图片。"}), 400
                image_bytes = image_input_to_bytes(image_base64)

            image_data_url = image_bytes_to_data_url(image_bytes, mime_type)
            llm_result = llm_client.analyze(
                provider=provider,
                task=task,
                mode="debug",
                user_text=user_text,
                image_data_url=image_data_url,
            )
            normalized = normalize_result(llm_result["result"], task=task, user_text=user_text)
            response_payload = {
                "ok": True,
                "mode": "debug",
                "provider": llm_result["provider"],
                "model": llm_result["model"],
                "result": normalized,
                "ttsPayload": build_tts_payload(normalized),
            }

            saved = save_debug_artifact(
                output_dir=project_path(settings["output_dir"]),
                original_name=filename,
                image_bytes=image_bytes,
                response_payload=response_payload,
            )
            response_payload["savedArtifacts"] = saved

            return jsonify(response_payload)
        except Exception as exc:
            return jsonify({"ok": False, "message": str(exc)}), 500

    @app.route("/api/formal/analyze", methods=["POST"])
    def formal_analyze():
        try:
            payload = request.get_json(silent=True) or {}
            image_base64 = payload.get("frameBase64")
            if not image_base64:
                return jsonify({"ok": False, "message": "正式模式需要实时视频帧。"}), 400

            provider = payload.get("provider") or settings["default_provider"]
            task = payload.get("task", "navigation_guidance")
            user_text = payload.get("text", "")
            session_id = payload.get("sessionId", "default-formal-session")
            mime_type = payload.get("mimeType", "image/jpeg")

            image_bytes = image_input_to_bytes(image_base64)
            image_data_url = image_bytes_to_data_url(image_bytes, mime_type)
            llm_result = llm_client.analyze(
                provider=provider,
                task=task,
                mode="formal",
                user_text=user_text,
                image_data_url=image_data_url,
            )
            normalized = normalize_result(llm_result["result"], task=task, user_text=user_text)
            response_payload = {
                "ok": True,
                "mode": "formal",
                "provider": llm_result["provider"],
                "model": llm_result["model"],
                "sessionId": session_id,
                "result": normalized,
                "ttsPayload": build_tts_payload(normalized),
            }

            append_formal_log(
                output_dir=project_path(settings["output_dir"]),
                session_id=session_id,
                payload=response_payload,
            )

            return jsonify(response_payload)
        except Exception as exc:
            return jsonify({"ok": False, "message": str(exc)}), 500

    @app.route("/api/tts/payload", methods=["POST"])
    def tts_payload():
        payload = request.get_json(silent=True) or {}
        if payload.get("result"):
            response = build_tts_payload(payload["result"], language=payload.get("language", "zh-CN"))
        else:
            response = {
                "text": payload.get("text", ""),
                "language": payload.get("language", "zh-CN"),
                "priority": "normal",
                "voiceHints": {"tone": "calm", "pace": "steady"},
            }

        return jsonify({"ok": True, "ttsPayload": response})

    return app
