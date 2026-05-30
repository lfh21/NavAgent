(function () {
  const FORMAL_MIN_INTERVAL = 800;
  const FORMAL_MAX_INTERVAL = 5000;

  const modeTabs = document.querySelectorAll(".mode-tab");
  const panels = document.querySelectorAll("[data-panel]");
  const providerSelect = document.querySelector("#providerSelect");
  const speakLatest = document.querySelector("#speakLatest");
  const stopSpeech = document.querySelector("#stopSpeech");

  const debugTask = document.querySelector("#debugTask");
  const debugText = document.querySelector("#debugText");
  const debugImage = document.querySelector("#debugImage");
  const debugPreview = document.querySelector("#debugPreview");
  const debugResult = document.querySelector("#debugResult");
  const debugAnalyze = document.querySelector("#debugAnalyze");

  const formalTask = document.querySelector("#formalTask");
  const formalText = document.querySelector("#formalText");
  const formalInterval = document.querySelector("#formalInterval");
  const formalVideo = document.querySelector("#formalVideo");
  const formalCanvas = document.querySelector("#formalCanvas");
  const formalStatus = document.querySelector("#formalStatus");
  const formalResult = document.querySelector("#formalResult");
  const formalEventBadge = document.querySelector("#formalEventBadge");
  const formalNextIntervalBadge = document.querySelector("#formalNextIntervalBadge");
  const formalSessionBadge = document.querySelector("#formalSessionBadge");
  const formalSpeakLatest = document.querySelector("#formalSpeakLatest");
  const formalStopSpeech = document.querySelector("#formalStopSpeech");
  const formalIntervalDown = document.querySelector("#formalIntervalDown");
  const formalIntervalUp = document.querySelector("#formalIntervalUp");
  const startCamera = document.querySelector("#startCamera");
  const startFormal = document.querySelector("#startFormal");
  const stopFormal = document.querySelector("#stopFormal");

  let currentMode = "formal";
  let currentStream = null;
  let liveTimer = null;
  let liveLoopActive = false;
  let liveLoopPaused = false;
  let inFlight = false;
  let latestTtsPayload = null;
  let lastAutoSpokenText = "";
  let formalSessionId = "";
  let nextFormalDelayMs = sanitizeInterval(formalInterval.value || 1500);
  let formalForceDetailed = false;
  let lastFrameSignature = "";
  let lastFormalState = null;

  function sanitizeInterval(value, fallback) {
    const numericFallback = Number(fallback || 1500);
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      return Math.max(FORMAL_MIN_INTERVAL, Math.min(FORMAL_MAX_INTERVAL, numericFallback));
    }
    return Math.max(FORMAL_MIN_INTERVAL, Math.min(FORMAL_MAX_INTERVAL, Math.round(parsed)));
  }

  function riskLabel(riskLevel) {
    return {
      low: "低风险",
      medium: "中风险",
      high: "高风险",
      unknown: "无法判断",
    }[riskLevel] || "无法判断";
  }

  function eventLabel(eventType) {
    return {
      stable: "环境稳定",
      change: "场景变化",
      warning: "风险提醒",
      danger: "立即避险",
      paused: "已暂停",
      idle: "等待启动",
    }[eventType] || "状态更新";
  }

  function setLatestTtsPayload(payload) {
    latestTtsPayload = payload && payload.text ? payload : null;
    if (speakLatest) {
      speakLatest.disabled = !latestTtsPayload;
    }
    if (formalSpeakLatest) {
      formalSpeakLatest.disabled = !latestTtsPayload;
    }
  }

  function speakPayload(payload, options) {
    const settings = options || {};
    const force = Boolean(settings.force);

    if (!("speechSynthesis" in window)) {
      window.alert("当前浏览器不支持语音播报。");
      return;
    }

    if (!payload || !payload.text) {
      return;
    }

    if (!force && payload.text === lastAutoSpokenText) {
      return;
    }

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(payload.text);
    utterance.lang = payload.language || "zh-CN";
    utterance.rate = payload.voiceHints && payload.voiceHints.pace === "fast" ? 1.15 : 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    window.speechSynthesis.speak(utterance);
    if (!force) {
      lastAutoSpokenText = payload.text;
    }
  }

  function stopSpeechPlayback(options) {
    const settings = options || {};
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }

    if (!settings.silent && currentMode === "formal") {
      setFormalStatus("已停止当前语音播报。", "muted");
    }
  }

  function setMode(mode) {
    currentMode = mode;
    modeTabs.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.mode === mode);
    });
    panels.forEach((panel) => {
      panel.classList.toggle("is-hidden", panel.dataset.panel !== mode);
    });

    if (mode !== "formal" && (liveLoopActive || currentStream)) {
      stopLiveLoop();
    }
  }

  function setFormalStatus(message, tone) {
    formalStatus.textContent = message;
    formalStatus.dataset.tone = tone || "info";
  }

  function clearResult(target) {
    target.classList.add("result-empty");
    target.classList.remove("is-error");
    target.innerHTML = "";
  }

  function setPlainResult(target, message, isError) {
    target.classList.toggle("is-error", Boolean(isError));
    target.classList.add("result-empty");
    target.textContent = message;
  }

  function createList(items, emptyText, renderItem) {
    const list = document.createElement("ul");
    list.className = "result-list";

    if (!items || !items.length) {
      const item = document.createElement("li");
      item.textContent = emptyText;
      list.appendChild(item);
      return list;
    }

    items.forEach((entry) => {
      const item = document.createElement("li");
      item.appendChild(renderItem(entry));
      list.appendChild(item);
    });

    return list;
  }

  function appendSection(container, title, contentNode) {
    const section = document.createElement("section");
    section.className = "result-section";

    const heading = document.createElement("h3");
    heading.textContent = title;
    section.appendChild(heading);
    section.appendChild(contentNode);
    container.appendChild(section);
  }

  function renderResult(target, data) {
    target.innerHTML = "";

    if (data && data.ok === false) {
      setPlainResult(target, "请求失败：" + (data.message || "后端未返回错误详情"), true);
      return;
    }

    if (!data || !data.result) {
      setPlainResult(target, "暂无结果", false);
      return;
    }

    target.classList.remove("result-empty", "is-error");
    const result = data.result;
    const meta = document.createElement("div");
    meta.className = "result-meta";

    const modelBadge = document.createElement("span");
    modelBadge.className = "result-badge";
    modelBadge.textContent = data.model || data.provider || "当前模型";
    meta.appendChild(modelBadge);

    const riskBadge = document.createElement("span");
    riskBadge.className = "result-badge risk-" + (result.riskLevel || "unknown");
    riskBadge.textContent = riskLabel(result.riskLevel);
    meta.appendChild(riskBadge);

    if (data.eventType) {
      const eventBadge = document.createElement("span");
      eventBadge.className = "result-badge event-" + data.eventType;
      eventBadge.textContent = eventLabel(data.eventType);
      meta.appendChild(eventBadge);
    }

    if (typeof data.shouldSpeak === "boolean") {
      const speakBadge = document.createElement("span");
      speakBadge.className = "result-badge";
      speakBadge.textContent = data.shouldSpeak ? "本轮播报" : "本轮静默";
      meta.appendChild(speakBadge);
    }

    if (data.nextIntervalMs) {
      const intervalBadge = document.createElement("span");
      intervalBadge.className = "result-badge";
      intervalBadge.textContent = "下轮 " + data.nextIntervalMs + "ms";
      meta.appendChild(intervalBadge);
    }

    const confidenceBadge = document.createElement("span");
    confidenceBadge.className = "result-badge";
    confidenceBadge.textContent = "置信度 " + (result.confidence ?? "-");
    meta.appendChild(confidenceBadge);
    target.appendChild(meta);

    const summary = document.createElement("p");
    summary.className = "result-summary";
    summary.textContent = result.summary || "暂时无法生成稳定描述，请重新采集画面。";
    appendSection(target, "场景概述", summary);

    appendSection(
      target,
      "导航建议",
      createList(result.guidance, "暂无导航建议", (entry) => document.createTextNode(entry))
    );

    appendSection(
      target,
      "风险提醒",
      createList(result.hazards, "没有发现明显风险", (entry) => {
        const wrapper = document.createElement("span");
        const severity = document.createElement("strong");
        severity.textContent = riskLabel(entry.severity);
        wrapper.appendChild(severity);
        wrapper.appendChild(document.createTextNode("：" + (entry.description || "未提供风险描述")));
        return wrapper;
      })
    );

    const tts = document.createElement("p");
    tts.className = "result-tts";
    tts.textContent = (data.ttsPayload && data.ttsPayload.text) || "暂无可播报内容。";
    appendSection(target, "语音播报内容", tts);
  }

  async function loadProviders() {
    try {
      const response = await fetch("/api/providers");
      const data = await response.json();
      const providers = Array.isArray(data.providers) ? data.providers : [];
      if (!providers.length) {
        return;
      }

      providerSelect.innerHTML = "";
      providers.forEach((provider) => {
        const option = document.createElement("option");
        option.value = provider.id;
        option.dataset.enabled = provider.enabled ? "true" : "false";
        option.textContent = provider.enabled ? provider.label : provider.label + "（未配置）";
        providerSelect.appendChild(option);
      });

      const options = Array.from(providerSelect.options);
      const firstEnabled = options.find((option) => option.dataset.enabled === "true");
      const defaultOption = options.find((option) => option.value === data.defaultProvider);
      providerSelect.value = firstEnabled
        ? firstEnabled.value
        : defaultOption
          ? defaultOption.value
          : providerSelect.options[0].value;
    } catch (error) {
      if (providerSelect.options.length) {
        providerSelect.value = providerSelect.options[0].value;
      }
    }
  }

  function updateFormalControls() {
    startFormal.disabled = liveLoopActive && !liveLoopPaused;
    stopFormal.disabled = !liveLoopActive && !currentStream;
    startCamera.disabled = Boolean(currentStream);
    startFormal.textContent = liveLoopPaused ? "继续实时分析" : "开始实时分析";
  }

  function updateFormalRuntime(eventType) {
    const normalizedDelay = sanitizeInterval(nextFormalDelayMs, formalInterval.value || 1500);
    formalNextIntervalBadge.textContent = "下一轮 " + normalizedDelay + "ms";
    formalSessionBadge.textContent = formalSessionId ? "会话 " + formalSessionId.slice(-8) : "会话未启动";
    formalEventBadge.dataset.event = eventType || (liveLoopPaused ? "paused" : liveLoopActive ? "change" : "idle");
    formalEventBadge.textContent = eventLabel(formalEventBadge.dataset.event);
  }

  function buildSessionId() {
    return "live-" + Date.now().toString(36);
  }

  function clearFormalTimer() {
    if (liveTimer) {
      window.clearTimeout(liveTimer);
      liveTimer = null;
    }
  }

  function scheduleNextFormalTick(delay) {
    clearFormalTimer();
    if (!liveLoopActive || liveLoopPaused) {
      return;
    }

    nextFormalDelayMs = sanitizeInterval(delay, formalInterval.value || 1500);
    updateFormalRuntime(formalEventBadge.dataset.event);
    liveTimer = window.setTimeout(function () {
      sendFormalFrame();
    }, nextFormalDelayMs);
  }

  function queueImmediateRefresh() {
    formalForceDetailed = true;
    if (liveLoopActive && !liveLoopPaused) {
      scheduleNextFormalTick(120);
    }
  }

  function applyFormalIntervalValue(nextValue, sourceLabel) {
    const sanitizedValue = sanitizeInterval(nextValue, formalInterval.value || 1500);
    formalInterval.value = sanitizedValue;
    nextFormalDelayMs = sanitizedValue;
    updateFormalRuntime(formalEventBadge.dataset.event);

    if (currentMode === "formal") {
      setFormalStatus(
        "基础间隔已调整为 " + sanitizedValue + "ms。" + (sourceLabel ? " 来源：" + sourceLabel + "。" : ""),
        "info"
      );
    }

    if (liveLoopActive && !liveLoopPaused && !inFlight) {
      scheduleNextFormalTick(nextFormalDelayMs);
    }

    return sanitizedValue;
  }

  function adjustFormalInterval(delta, sourceLabel) {
    const currentValue = sanitizeInterval(formalInterval.value || nextFormalDelayMs || 1500);
    return applyFormalIntervalValue(currentValue + delta, sourceLabel);
  }

  function frameSignatureDelta(previousSignature, nextSignature) {
    if (!previousSignature || !nextSignature) {
      return Number.POSITIVE_INFINITY;
    }

    const previousValues = previousSignature.split("-").map(Number);
    const nextValues = nextSignature.split("-").map(Number);
    const length = Math.min(previousValues.length, nextValues.length);
    if (!length) {
      return Number.POSITIVE_INFINITY;
    }

    let total = 0;
    for (let index = 0; index < length; index += 1) {
      total += Math.abs(previousValues[index] - nextValues[index]);
    }
    return total / length;
  }

  function computeFrameSignature(context, width, height) {
    const sampleColumns = 8;
    const sampleRows = 6;
    const imageData = context.getImageData(0, 0, width, height).data;
    const values = [];

    for (let row = 0; row < sampleRows; row += 1) {
      for (let column = 0; column < sampleColumns; column += 1) {
        const x = Math.min(width - 1, Math.floor(((column + 0.5) * width) / sampleColumns));
        const y = Math.min(height - 1, Math.floor(((row + 0.5) * height) / sampleRows));
        const offset = (y * width + x) * 4;
        const red = imageData[offset];
        const green = imageData[offset + 1];
        const blue = imageData[offset + 2];
        values.push(Math.round(red * 0.299 + green * 0.587 + blue * 0.114));
      }
    }

    return values.join("-");
  }

  async function waitForVideoReady(timeoutMs) {
    if (formalVideo.videoWidth && formalVideo.videoHeight) {
      return;
    }

    await new Promise((resolve, reject) => {
      let settled = false;
      const cleanup = () => {
        formalVideo.removeEventListener("loadedmetadata", handleReady);
        formalVideo.removeEventListener("canplay", handleReady);
        window.clearTimeout(timer);
      };
      const finish = (callback) => {
        if (settled) {
          return;
        }
        settled = true;
        cleanup();
        callback();
      };
      const handleReady = () => finish(resolve);
      const handleTimeout = () => {
        if (formalVideo.videoWidth && formalVideo.videoHeight) {
          finish(resolve);
          return;
        }
        finish(() => reject(new Error("摄像头已打开，但视频流尚未就绪。")));
      };
      const timer = window.setTimeout(handleTimeout, timeoutMs || 1600);

      formalVideo.addEventListener("loadedmetadata", handleReady, { once: true });
      formalVideo.addEventListener("canplay", handleReady, { once: true });
    });
  }

  async function openCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setFormalStatus("当前浏览器不支持摄像头接口。", "danger");
      return false;
    }

    if (currentStream) {
      return true;
    }

    try {
      currentStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });
      formalVideo.srcObject = currentStream;
      await formalVideo.play().catch(function () {
        return undefined;
      });
      await waitForVideoReady();
      setFormalStatus("摄像头已打开，等待开始实时分析。", "info");
      updateFormalControls();
      return true;
    } catch (error) {
      if (currentStream) {
        currentStream.getTracks().forEach((track) => track.stop());
      }
      currentStream = null;
      formalVideo.srcObject = null;
      setFormalStatus("打开摄像头失败：" + error.message, "danger");
      return false;
    }
  }

  function captureFrameSnapshot() {
    const sourceWidth = formalVideo.videoWidth;
    const sourceHeight = formalVideo.videoHeight;
    if (!sourceWidth || !sourceHeight) {
      throw new Error("当前没有可采集的视频帧");
    }

    const maxWidth = 640;
    const scale = Math.min(1, maxWidth / sourceWidth);
    const width = Math.max(240, Math.round(sourceWidth * scale));
    const height = Math.max(180, Math.round(sourceHeight * scale));

    formalCanvas.width = width;
    formalCanvas.height = height;
    const context = formalCanvas.getContext("2d", { willReadFrequently: true });
    context.drawImage(formalVideo, 0, 0, width, height);

    const signature = computeFrameSignature(context, width, height);
    const dataUrl = formalCanvas.toDataURL("image/jpeg", 0.7);
    return {
      frameBase64: dataUrl.split(",")[1],
      width,
      height,
      signature,
    };
  }

  function buildFormalStatusText(data) {
    const prefix = {
      stable: "环境稳定，继续监测中。",
      change: "场景发生变化，已更新指导。",
      warning: "前方有需要留意的风险。",
      danger: "高风险，请优先停下并处理前方障碍。",
    }[data.eventType] || "实时分析已更新。";

    const suffix = data.nextIntervalMs ? " 下轮约 " + data.nextIntervalMs + "ms。" : "";
    return prefix + suffix;
  }

  function buildFormalTone(eventType) {
    if (eventType === "danger") {
      return "danger";
    }
    if (eventType === "warning") {
      return "warning";
    }
    if (eventType === "stable") {
      return "muted";
    }
    return "info";
  }

  async function sendFormalFrame() {
    if (!liveLoopActive || liveLoopPaused || inFlight) {
      return;
    }

    let snapshot;
    try {
      snapshot = captureFrameSnapshot();
    } catch (error) {
      setFormalStatus(error.message, "warning");
      scheduleNextFormalTick(nextFormalDelayMs);
      return;
    }

    const frameDelta = frameSignatureDelta(lastFrameSignature, snapshot.signature);
    const shouldSkipStableFrame = Boolean(
      lastFormalState &&
        lastFormalState.riskLevel === "low" &&
        !formalForceDetailed &&
        frameDelta < 8
    );

    if (shouldSkipStableFrame) {
      lastFrameSignature = snapshot.signature;
      nextFormalDelayMs = Math.max(sanitizeInterval(formalInterval.value) + 600, 2200);
      setFormalStatus("画面变化很小，暂不重复请求。", "muted");
      updateFormalRuntime("stable");
      scheduleNextFormalTick(nextFormalDelayMs);
      return;
    }

    inFlight = true;
    setFormalStatus("正在分析当前画面...", "info");

    try {
      const response = await fetch("/api/formal/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          provider: providerSelect.value,
          task: formalTask.value,
          text: formalText.value.trim(),
          frameBase64: snapshot.frameBase64,
          mimeType: "image/jpeg",
          sessionId: formalSessionId,
          requestedIntervalMs: sanitizeInterval(formalInterval.value),
          frameMeta: {
            timestamp: new Date().toISOString(),
            width: snapshot.width,
            height: snapshot.height,
          },
          clientState: {
            lastSummary: lastFormalState ? lastFormalState.summary : "",
            guidance: lastFormalState ? lastFormalState.guidance : [],
            lastRiskLevel: lastFormalState ? lastFormalState.riskLevel : "unknown",
            lastSpokenText: lastFormalState ? lastFormalState.lastSpokenText : "",
            forceDetailed: formalForceDetailed,
          },
        }),
      });
      const data = await response.json();

      if (!liveLoopActive) {
        return;
      }

      if (!response.ok || (data && data.ok === false)) {
        throw new Error((data && data.message) || "后端请求失败");
      }

      renderResult(formalResult, data);
      setLatestTtsPayload(data.ttsPayload);
      nextFormalDelayMs = sanitizeInterval(data.nextIntervalMs, formalInterval.value || 1500);
      setFormalStatus(buildFormalStatusText(data), buildFormalTone(data.eventType));
      updateFormalRuntime(data.eventType || "change");

      if (data.result) {
        lastFormalState = {
          summary: data.result.summary || "",
          guidance: Array.isArray(data.result.guidance) ? data.result.guidance : [],
          riskLevel: data.result.riskLevel || "unknown",
          lastSpokenText:
            data.shouldSpeak && data.ttsPayload && data.ttsPayload.text
              ? data.ttsPayload.text
              : lastFormalState && lastFormalState.lastSpokenText
                ? lastFormalState.lastSpokenText
                : "",
        };
      }

      if (data.shouldSpeak) {
        speakPayload(data.ttsPayload);
      }
    } catch (error) {
      setFormalStatus("实时分析失败：" + error.message, "danger");
      setLatestTtsPayload(null);
      nextFormalDelayMs = Math.max(sanitizeInterval(formalInterval.value), 1500);
      updateFormalRuntime("warning");
    } finally {
      lastFrameSignature = snapshot.signature;
      formalForceDetailed = false;
      inFlight = false;
      if (liveLoopActive && !liveLoopPaused) {
        scheduleNextFormalTick(nextFormalDelayMs);
      }
    }
  }

  async function startFormalLoop() {
    setMode("formal");
    const cameraReady = await openCamera();
    if (!cameraReady) {
      return;
    }

    liveLoopActive = true;
    liveLoopPaused = false;
    formalSessionId = formalSessionId || buildSessionId();
    nextFormalDelayMs = sanitizeInterval(formalInterval.value || 1500);
    formalForceDetailed = true;
    updateFormalControls();
    updateFormalRuntime("change");
    await sendFormalFrame();
  }

  function pauseFormalLoop() {
    if (!liveLoopActive || liveLoopPaused) {
      return;
    }

    liveLoopPaused = true;
    clearFormalTimer();
    setFormalStatus("已暂停实时分析。按空格或点击“继续实时分析”恢复。", "info");
    updateFormalRuntime("paused");
    updateFormalControls();
  }

  function stopLiveLoop() {
    liveLoopActive = false;
    liveLoopPaused = false;
    clearFormalTimer();

    if (currentStream) {
      currentStream.getTracks().forEach((track) => track.stop());
      currentStream = null;
    }

    formalVideo.srcObject = null;
    formalSessionId = "";
    lastFrameSignature = "";
    lastFormalState = null;
    lastAutoSpokenText = "";
    setLatestTtsPayload(null);
    nextFormalDelayMs = sanitizeInterval(formalInterval.value || 1500);
    setFormalStatus("实时分析已停止。", "muted");
    updateFormalRuntime("idle");
    updateFormalControls();
  }

  function handleSpacebarToggle(event) {
    const target = event.target;
    const tagName = target && target.tagName ? target.tagName.toLowerCase() : "";
    if (tagName === "input" || tagName === "textarea" || target.isContentEditable) {
      return;
    }

    if (event.code !== "Space" || currentMode !== "formal") {
      return;
    }

    event.preventDefault();
    if (!liveLoopActive) {
      startFormalLoop();
      return;
    }

    if (liveLoopPaused) {
      liveLoopPaused = false;
      formalForceDetailed = true;
      updateFormalControls();
      updateFormalRuntime("change");
      sendFormalFrame();
      return;
    }

    pauseFormalLoop();
  }

  function handleFormalAccessibilityShortcuts(event) {
    if (currentMode !== "formal") {
      return;
    }

    if (event.ctrlKey || event.metaKey || event.altKey) {
      return;
    }

    const target = event.target;
    const tagName = target && target.tagName ? target.tagName.toLowerCase() : "";
    const editing = tagName === "input" || tagName === "textarea" || target.isContentEditable;

    if (event.code === "Space") {
      handleSpacebarToggle(event);
      return;
    }

    if (editing) {
      return;
    }

    if (event.code === "KeyS") {
      event.preventDefault();
      if (latestTtsPayload) {
        speakPayload(latestTtsPayload, { force: true });
        setFormalStatus("正在播报当前结果。", "info");
      } else {
        setFormalStatus("当前还没有可播报的分析结果。", "warning");
      }
      return;
    }

    if (event.code === "KeyX") {
      event.preventDefault();
      stopSpeechPlayback();
      return;
    }

    if (event.code === "Minus") {
      event.preventDefault();
      adjustFormalInterval(-100, "键盘减号");
      return;
    }

    if (event.code === "Equal") {
      event.preventDefault();
      adjustFormalInterval(100, "键盘加号");
    }
  }

  debugImage.addEventListener("change", function () {
    const file = debugImage.files[0];
    if (!file) {
      return;
    }
    const objectUrl = URL.createObjectURL(file);
    debugPreview.src = objectUrl;
  });

  debugAnalyze.addEventListener("click", async function () {
    const file = debugImage.files[0];
    if (!file) {
      debugResult.textContent = "请先上传图片。";
      return;
    }

    const form = new FormData();
    form.append("image", file);
    form.append("provider", providerSelect.value);
    form.append("task", debugTask.value);
    form.append("text", debugText.value.trim());

    setPlainResult(debugResult, "正在分析...", false);

    try {
      const response = await fetch("/api/debug/analyze", {
        method: "POST",
        body: form,
      });
      const data = await response.json();
      renderResult(debugResult, data);
      setLatestTtsPayload(data && data.ok === false ? null : data.ttsPayload);
    } catch (error) {
      setPlainResult(debugResult, "调试分析失败：" + error.message, true);
      setLatestTtsPayload(null);
    }
  });

  startCamera.addEventListener("click", async function () {
    await openCamera();
  });

  startFormal.addEventListener("click", async function () {
    if (!liveLoopActive) {
      await startFormalLoop();
      return;
    }

    if (liveLoopPaused) {
      liveLoopPaused = false;
      formalForceDetailed = true;
      updateFormalControls();
      updateFormalRuntime("change");
      await sendFormalFrame();
    }
  });

  stopFormal.addEventListener("click", function () {
    stopLiveLoop();
  });

  formalText.addEventListener("input", queueImmediateRefresh);
  formalTask.addEventListener("change", queueImmediateRefresh);
  formalInterval.addEventListener("change", function () {
    applyFormalIntervalValue(formalInterval.value || 1500, "输入框");
  });
  providerSelect.addEventListener("change", function () {
    if (currentMode === "formal") {
      queueImmediateRefresh();
    }
  });

  speakLatest.addEventListener("click", function () {
    if (!latestTtsPayload) {
      window.alert("暂无可播报内容");
      return;
    }

    speakPayload(latestTtsPayload, { force: true });
  });

  stopSpeech.addEventListener("click", function () {
    stopSpeechPlayback({ silent: currentMode !== "formal" });
  });

  formalSpeakLatest.addEventListener("click", function () {
    if (!latestTtsPayload) {
      setFormalStatus("当前还没有可播报的分析结果。", "warning");
      return;
    }

    speakPayload(latestTtsPayload, { force: true });
    setFormalStatus("正在播报当前结果。", "info");
  });

  formalStopSpeech.addEventListener("click", function () {
    stopSpeechPlayback();
  });

  formalIntervalDown.addEventListener("click", function () {
    adjustFormalInterval(-100, "页面按钮");
  });

  formalIntervalUp.addEventListener("click", function () {
    adjustFormalInterval(100, "页面按钮");
  });

  modeTabs.forEach((button) => {
    button.addEventListener("click", function () {
      setMode(button.dataset.mode);
    });
  });

  document.addEventListener("keydown", handleFormalAccessibilityShortcuts);

  clearResult(debugResult);
  clearResult(formalResult);
  setMode("formal");
  updateFormalControls();
  updateFormalRuntime("idle");
  loadProviders();
})();
