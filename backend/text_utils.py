import json


SYSTEM_PROMPT = """
你是盲人视觉语言导航（VLN）辅助系统的场景理解与行动建议模块。
你的目标不是完整描述画面，而是帮助盲人用户安全、简洁、可执行地理解前方环境。

核心原则：
1. 安全优先：先识别会影响通行的风险，再给行动建议。
2. 只基于可见信息判断；看不清、距离不确定或遮挡时必须说明“不确定”，不能编造。
3. 指令必须短、明确、可执行，适合语音播报；避免长篇解释、视觉修饰和无关细节。
4. 使用以用户前进方向为基准的方位：正前方、左前方、右前方、左侧、右侧、脚下。
5. 对距离只能给粗略估计，例如“近处”“约一到两步”“数米外”；不确定时不要给精确距离。
6. 不要替代导盲杖、导盲犬、地图导航或交通规则判断；遇到车流、台阶、施工、拥挤、低矮障碍时应保守提醒。
7. 如果用户文字中包含目的地或任务，优先围绕该任务给建议；否则默认关注前方可通行性。

重点观察对象：
- 通行区域：人行道、盲道、路口、门、走廊、楼梯、电梯、坡道、斑马线。
- 障碍风险：台阶、坑洼、路缘、柱子、车辆、行人、自行车、电动车、施工围挡、低矮/悬挂障碍、湿滑地面。
- 导航线索：盲道走向、门口、路口边界、墙面边界、扶手、斑马线、交通灯、可通行缺口。

风险等级定义：
- low：通行区域清楚，仅有远处或边缘轻微风险。
- medium：存在需要绕行、减速或保持距离的风险，例如近处障碍、车辆靠近、行人密集、盲道被部分占用。
- high：存在立即碰撞、跌落、误入车道、台阶/坑洞、快速车辆、施工危险等需要立刻停止或改变动作的风险。
- unknown：画面不足、遮挡严重、无法判断通行安全。

一致性规则：
- hazards 中任一项 severity 为 medium，则 riskLevel 至少为 medium。
- hazards 中任一项 severity 为 high，则 riskLevel 必须为 high。
- 无法判断关键通行安全时，riskLevel 使用 unknown，confidence 不得高于 0.5。

输出规则：
- 只输出 JSON 对象，不要使用 Markdown，不要输出额外解释。
- 所有文本使用中文。
- summary 一句话概括当前可通行性和主要风险。
- guidance 给 1 到 4 条短指令，每条尽量不超过 25 个汉字。
- hazards 只列影响安全或通行的风险；没有风险时返回空数组。
- confidence 为 0 到 1 之间的小数，表示对本次判断的把握程度。
""".strip()


GENERAL_ASSISTANCE_SYSTEM_PROMPT = """
你是盲人视觉辅助系统的综合问答与场景理解模块。
你的目标是根据图像直接回答用户的问题，并在必要时补充安全提醒。

核心原则：
1. 用户问什么先答什么；例如形状、颜色、物体、位置、数量、文字、动作等问题，先给出可见答案。
2. 只基于可见信息判断；看不清、遮挡或不确定时必须说明“不确定”，不能编造。
3. 回答要简洁，适合语音播报。
4. 只有画面中存在真实可见、会影响安全或通行的风险时，才输出导航或风险提醒。
5. 不要把普通视觉问答强行改写成行走建议。

输出规则：
- 只输出 JSON 对象，不要使用 Markdown，不要输出额外解释。
- 所有文本使用中文。
- summary 一句话，优先直接回答用户问题。
- guidance 给 0 到 4 条相关建议；没有必要行动时返回空数组。
- hazards 只列真实可见且影响安全或通行的风险；没有风险时返回空数组。
- riskLevel 使用 low、medium、high、unknown。
- confidence 为 0 到 1 之间的小数，表示对本次判断的把握程度。
""".strip()


def build_system_prompt(task):
    if task == "general_assistance":
        return GENERAL_ASSISTANCE_SYSTEM_PROMPT
    return SYSTEM_PROMPT


_RISK_RANK = {"unknown": 0, "low": 1, "medium": 2, "high": 3}
_VALID_RISKS = set(_RISK_RANK.keys())


def build_user_prompt(task, mode, user_text):
    task_instruction = {
        "scene_description": "\n".join(
            [
                "任务侧重：先概括画面场景，再指出会影响安全或通行的风险。",
                "如果用户提出具体问题，请在 summary 中先直接回答，再补充必要风险。",
            ]
        ),
        "navigation_guidance": "\n".join(
            [
                "任务侧重：优先输出下一步行走、停止、转向、避让等可执行指令。",
                "只有当用户明确提问具体物体、形状、文字或位置时，才先回答问题再给行动建议。",
            ]
        ),
        "general_assistance": "\n".join(
            [
                "任务侧重：这是综合辅助/视觉问答模式，不要默认只做导航提醒。",
                "如果用户提出具体问题，summary 必须先直接回答这个问题；例如询问形状、颜色、物体、位置、数量、文字时，先给出可见答案。",
                "guidance 只放与用户问题相关的补充建议；如果没有必要行动，返回空数组或很短的确认建议。",
                "hazards 只列真实可见且会影响安全的风险；不要为了导航而泛化出无关风险。",
                "riskLevel 按当前画面真实安全风险判断；普通物体识别问题通常为 low，除非画面中有明显危险。",
            ]
        ),
    }.get(task, "请输出适合盲人辅助场景的结果。")

    mode_instruction = {
        "debug": "当前是调试模式：输入为单张图片，请给出相对完整但仍适合语音播报的分析。",
        "formal": "当前是实时模式：输入为连续视频帧中的一帧，请输出更短、更直接的即时提醒。",
    }.get(mode, "请输出稳定结果。")

    json_template = (
        '{"summary":"","guidance":[""],'
        '"hazards":[{"type":"","severity":"","description":""}],'
        '"riskLevel":"low|medium|high|unknown","confidence":0.0}'
    )

    return "\n".join(
        [
            "请严格输出以下 JSON 结构：",
            json_template,
            "字段约束：",
            '- summary: 一句话；综合辅助模式下必须先回答用户具体问题，再说明必要风险。',
            '- guidance: 0 到 4 条短建议；高风险时第一条必须是“请先停止”。',
            '- hazards[].type: 使用 obstacle|traffic|pedestrian|step|surface|construction|edge|low_hanging|unknown 等简短英文类型。',
            '- hazards[].severity: 只能是 low、medium、high、unknown。',
            '- riskLevel: 只能是 low、medium、high、unknown，并且不得低于 hazards 中最高 severity。',
            '- confidence: 0 到 1；画面模糊、遮挡或关键区域不可见时不要高于 0.5。',
            "任务类型: {0}".format(task),
            "模式: {0}".format(mode),
            task_instruction,
            mode_instruction,
            "请优先回答用户关心的问题；只有与安全或通行相关时才输出导航式提醒。",
            "用户文字: {0}".format(user_text or "无"),
        ]
    )


def _normalize_risk(value):
    value = str(value or "unknown").strip().lower()
    return value if value in _VALID_RISKS else "unknown"


def _normalize_text(value):
    return " ".join(str(value or "").split())


def _normalize_guidance_items(guidance):
    if not isinstance(guidance, list):
        return []

    normalized = []
    for item in guidance:
        text = _normalize_text(item)
        if text:
            normalized.append(text)
    return normalized


def _normalize_hazards(hazards):
    if not isinstance(hazards, list):
        return []

    normalized = []
    for item in hazards:
        if not isinstance(item, dict):
            continue

        normalized.append(
            {
                "type": _normalize_text(item.get("type")).lower() or "unknown",
                "severity": _normalize_risk(item.get("severity")),
                "description": _normalize_text(item.get("description")) or "未提供风险描述",
            }
        )
    return normalized


def _highest_hazard_risk(hazards):
    highest = "unknown"
    for item in hazards:
        if not isinstance(item, dict):
            continue
        severity = _normalize_risk(item.get("severity"))
        if _RISK_RANK[severity] > _RISK_RANK[highest]:
            highest = severity
    return highest


def _dedupe_sentences(items):
    unique = []
    seen = set()
    for item in items:
        text = _normalize_text(item).strip("。；，,. ")
        if not text:
            continue

        key = text.replace(" ", "")
        if key in seen:
            continue

        seen.add(key)
        unique.append(text + "。")

    return "".join(unique)


def _select_next_interval_ms(risk_level, event_type, default_interval_ms):
    try:
        base_interval = int(default_interval_ms)
    except (TypeError, ValueError):
        base_interval = 1500

    base_interval = max(800, min(5000, base_interval))

    if risk_level == "high":
        return 900
    if risk_level in {"medium", "unknown"}:
        return 1200
    if event_type == "change":
        return base_interval
    return min(max(base_interval + 700, 2000), 3200)


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
    normalized_hazards = _normalize_hazards(raw_result.get("hazards"))
    guidance = _normalize_guidance_items(raw_result.get("guidance"))
    model_risk = _normalize_risk(raw_result.get("riskLevel"))
    hazard_risk = _highest_hazard_risk(normalized_hazards)
    risk_level = model_risk
    if _RISK_RANK[hazard_risk] > _RISK_RANK[risk_level]:
        risk_level = hazard_risk

    normalized = {
        "summary": _normalize_text(raw_result.get("summary")) or "暂时无法生成稳定描述，请重新采集画面。",
        "guidance": guidance,
        "hazards": normalized_hazards,
        "riskLevel": risk_level,
        "confidence": raw_result.get("confidence", 0.5),
        "task": task,
        "sourceText": user_text or "",
    }

    try:
        normalized["confidence"] = max(0.0, min(1.0, float(normalized["confidence"])))
    except (TypeError, ValueError):
        normalized["confidence"] = 0.5

    if normalized["riskLevel"] == "unknown":
        normalized["confidence"] = min(normalized["confidence"], 0.5)

    return normalized


def build_tts_payload(result, language="zh-CN", mode="debug", event_type=None):
    result = result if isinstance(result, dict) else {}
    summary = _normalize_text(result.get("summary"))
    guidance = _normalize_guidance_items(result.get("guidance"))
    hazards = []
    for item in result.get("hazards", []):
        if isinstance(item, dict):
            description = _normalize_text(item.get("description"))
            if description:
                hazards.append(description)
    risk_level = _normalize_risk(result.get("riskLevel"))

    if mode == "formal":
        segments = []
        primary_hazard = hazards[0] if hazards else ""

        if risk_level == "high":
            if guidance:
                segments.append(guidance[0])
                segments.extend(guidance[1:2])
            else:
                segments.append("请先停止")
            if primary_hazard:
                segments.append(primary_hazard)
            if summary:
                segments.append(summary)
        elif event_type in {"warning", "change"}:
            if summary:
                segments.append(summary)
            if primary_hazard:
                segments.append(primary_hazard)
            segments.extend(guidance[:2])
        else:
            if summary:
                segments.append(summary)
            segments.extend(guidance[:1])

        combined_text = _dedupe_sentences(segments[:3])
    else:
        combined_text = _dedupe_sentences([summary] + hazards[:1] + guidance[:2])

    priority = "high" if risk_level in {"high", "unknown"} or event_type in {"warning", "danger"} else "normal"
    pace = "fast" if risk_level == "high" else "steady"

    return {
        "text": combined_text or summary or "暂无可播报内容。",
        "language": language,
        "priority": priority,
        "voiceHints": {
            "tone": "calm",
            "pace": pace,
        },
    }


def build_formal_feedback(result, previous_state, default_interval_ms, force_detailed=False, language="zh-CN"):
    previous_state = previous_state if isinstance(previous_state, dict) else {}
    summary = _normalize_text(result.get("summary"))
    guidance = _normalize_guidance_items(result.get("guidance"))
    risk_level = _normalize_risk(result.get("riskLevel"))

    previous_summary = _normalize_text(previous_state.get("summary"))
    previous_guidance = _normalize_guidance_items(previous_state.get("guidance"))
    previous_risk = _normalize_risk(previous_state.get("riskLevel"))
    last_spoken_text = _normalize_text(previous_state.get("lastSpokenText"))

    summary_changed = summary != previous_summary
    guidance_changed = guidance[:2] != previous_guidance[:2]
    risk_changed = risk_level != previous_risk
    first_result = not previous_summary and not previous_guidance and previous_risk == "unknown"

    if risk_level == "high":
        event_type = "danger"
    elif risk_level in {"medium", "unknown"}:
        event_type = "warning"
    elif force_detailed or first_result or summary_changed or guidance_changed or risk_changed:
        event_type = "change"
    else:
        event_type = "stable"

    should_speak = False
    if risk_level == "high":
        should_speak = True
    elif first_result or force_detailed or risk_changed or guidance_changed:
        should_speak = True
    elif risk_level in {"medium", "unknown"} and summary_changed:
        should_speak = True
    elif event_type == "change" and summary_changed:
        should_speak = True

    next_interval_ms = _select_next_interval_ms(risk_level, event_type, default_interval_ms)
    tts_payload = build_tts_payload(
        result=result,
        language=language,
        mode="formal",
        event_type=event_type,
    )
    normalized_tts_text = _normalize_text(tts_payload.get("text"))

    if (
        should_speak
        and normalized_tts_text
        and normalized_tts_text == last_spoken_text
        and risk_level != "high"
        and not force_detailed
    ):
        should_speak = False

    next_spoken_text = normalized_tts_text if should_speak else last_spoken_text
    session_state = {
        "summary": summary,
        "guidance": guidance,
        "riskLevel": risk_level,
        "lastSpokenText": next_spoken_text,
        "eventType": event_type,
    }

    return {
        "eventType": event_type,
        "shouldSpeak": should_speak,
        "nextIntervalMs": next_interval_ms,
        "ttsPayload": tts_payload,
        "sessionState": session_state,
    }
