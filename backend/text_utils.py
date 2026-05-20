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


def build_user_prompt(task, mode, user_text):
    task_instruction = {
        "scene_description": "任务侧重：先概括场景可通行性，再指出障碍和人车风险。",
        "navigation_guidance": "任务侧重：优先输出下一步行走、停止、转向、避让等可执行指令。",
        "general_assistance": "任务侧重：兼顾场景理解、风险提醒和下一步建议。",
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
            '- summary: 一句话，说明可通行性和最主要风险。',
            '- guidance: 1 到 4 条短行动建议；高风险时第一条必须是“请先停止”。',
            '- hazards[].type: 使用 obstacle|traffic|pedestrian|step|surface|construction|edge|low_hanging|unknown 等简短英文类型。',
            '- hazards[].severity: 只能是 low、medium、high、unknown。',
            '- riskLevel: 只能是 low、medium、high、unknown，并且不得低于 hazards 中最高 severity。',
            "- confidence: 0 到 1；画面模糊、遮挡或关键区域不可见时不要高于 0.5。",
            "任务类型: {0}".format(task),
            "模式: {0}".format(mode),
            task_instruction,
            mode_instruction,
            "请优先回答用户关心的问题，同时保持安全保守。",
            "用户文字: {0}".format(user_text or "无"),
        ]
    )


_RISK_RANK = {"unknown": 0, "low": 1, "medium": 2, "high": 3}
_VALID_RISKS = set(_RISK_RANK.keys())


def _normalize_risk(value):
    value = str(value or "unknown").strip().lower()
    return value if value in _VALID_RISKS else "unknown"


def _highest_hazard_risk(hazards):
    highest = "unknown"
    for item in hazards:
        if not isinstance(item, dict):
            continue
        severity = _normalize_risk(item.get("severity"))
        if _RISK_RANK[severity] > _RISK_RANK[highest]:
            highest = severity
    return highest


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
    normalized_hazards = hazards if isinstance(hazards, list) else []
    model_risk = _normalize_risk(raw_result.get("riskLevel"))
    hazard_risk = _highest_hazard_risk(normalized_hazards)
    risk_level = model_risk
    if _RISK_RANK[hazard_risk] > _RISK_RANK[risk_level]:
        risk_level = hazard_risk

    normalized = {
        "summary": raw_result.get("summary") or "暂时无法生成稳定描述，请重新采集画面。",
        "guidance": guidance if isinstance(guidance, list) else [],
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
