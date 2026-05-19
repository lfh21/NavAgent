import json


SYSTEM_PROMPT = (
    "你是一个盲人辅助系统的视觉理解与寻路助手。"
    "你需要根据用户的文字和视觉输入，输出简洁、可信、可执行的中文结果。"
    "必须优先关注障碍物、台阶、门、地面状态、可通行区域、方向信息和人车风险。"
    "如果信息不足，请明确说不确定，不要编造细节。"
    "只输出 JSON。"
)


def build_user_prompt(task, mode, user_text):
    task_instruction = {
        "scene_description": "请重点输出场景概述和障碍风险。",
        "navigation_guidance": "请重点输出可执行的寻路与避障指令。",
        "general_assistance": "请兼顾场景描述与可执行建议。",
    }.get(task, "请输出适合盲人辅助场景的结果。")

    mode_instruction = {
        "debug": "当前是调试模式，用户上传的是单张图片，请给出稳定的场景分析。",
        "formal": "当前是正式模式，输入来自实时视频帧，请优先输出短句描述或寻路指令。",
    }.get(mode, "请输出稳定结果。")

    json_template = (
        '{"summary":"","guidance":[""],'
        '"hazards":[{"type":"","severity":"","description":""}],'
        '"riskLevel":"low|medium|high|unknown","confidence":0.0}'
    )

    return (
        "输出 JSON，格式如下：\n"
        + json_template
        + "\n任务类型: {task}\n"
        + "模式: {mode}\n"
        + "{task_instruction}\n"
        + "{mode_instruction}\n"
        + "用户文字: {user_text}\n"
    ).format(
        task=task,
        mode=mode,
        task_instruction=task_instruction,
        mode_instruction=mode_instruction,
        user_text=user_text or "无",
    )


def extract_json_object(text):
    if isinstance(text, dict):
        return text

    if not isinstance(text, str):
        raise ValueError("模型响应不是字符串，无法提取 JSON")

    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or start >= end:
        raise ValueError("模型响应中未找到合法 JSON 对象")

    return json.loads(text[start : end + 1])


def normalize_result(raw_result, task, user_text):
    raw_result = raw_result if isinstance(raw_result, dict) else {}
    hazards = raw_result.get("hazards")
    guidance = raw_result.get("guidance")

    normalized = {
        "summary": raw_result.get("summary") or "暂时无法生成稳定描述，请重新采集画面。",
        "guidance": guidance if isinstance(guidance, list) else [],
        "hazards": hazards if isinstance(hazards, list) else [],
        "riskLevel": raw_result.get("riskLevel") or "unknown",
        "confidence": raw_result.get("confidence", 0.5),
        "task": task,
        "sourceText": user_text or "",
    }

    try:
        normalized["confidence"] = max(0.0, min(1.0, float(normalized["confidence"])))
    except (TypeError, ValueError):
        normalized["confidence"] = 0.5

    return normalized


def build_tts_payload(result, language="zh-CN"):
    summary = result.get("summary", "")
    guidance = "".join(result.get("guidance", []))
    hazards = "".join(item.get("description", "") for item in result.get("hazards", []))
    combined_text = "".join(part for part in [summary, hazards, guidance] if part)

    return {
        "text": combined_text or summary or "暂无可播报内容。",
        "language": language,
        "priority": "high" if result.get("riskLevel") == "high" else "normal",
        "voiceHints": {
            "tone": "calm",
            "pace": "steady" if result.get("riskLevel") != "high" else "fast",
        },
    }
