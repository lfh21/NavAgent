(function () {
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
  const startCamera = document.querySelector("#startCamera");
  const startFormal = document.querySelector("#startFormal");
  const stopFormal = document.querySelector("#stopFormal");

  let currentStream = null;
  let liveTimer = null;
  let inFlight = false;
  let latestTtsPayload = null;

  function setLatestTtsPayload(payload) {
    latestTtsPayload = payload && payload.text ? payload : null;
    if (speakLatest) {
      speakLatest.disabled = !latestTtsPayload;
    }
  }

  function getSpeechStatusText(text) {
    return latestTtsPayload ? text : "暂无可播报内容";
  }

  function speakPayload(payload) {
    if (!("speechSynthesis" in window)) {
      window.alert("当前浏览器不支持语音播报。");
      return;
    }

    if (!payload || !payload.text) {
      return;
    }

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(payload.text);
    utterance.lang = payload.language || "zh-CN";
    utterance.rate = payload.voiceHints && payload.voiceHints.pace === "fast" ? 1.15 : 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    window.speechSynthesis.speak(utterance);
  }

  function setMode(mode) {
    modeTabs.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.mode === mode);
    });
    panels.forEach((panel) => {
      panel.classList.toggle("is-hidden", panel.dataset.panel !== mode);
    });
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

  function riskLabel(riskLevel) {
    return {
      low: "低风险",
      medium: "中风险",
      high: "高风险",
      unknown: "无法判断",
    }[riskLevel] || "无法判断";
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
      providerSelect.innerHTML = "";
      (data.providers || []).forEach((provider) => {
        const option = document.createElement("option");
        option.value = provider.id;
        option.dataset.enabled = provider.enabled ? "true" : "false";
        option.textContent = provider.enabled ? provider.label : provider.label + "（未配置）";
        providerSelect.appendChild(option);
      });
      const firstEnabled = providerSelect.querySelector('[data-enabled="true"]');
      const defaultProvider = data.defaultProvider || "";
      const defaultOption = providerSelect.querySelector('[value="' + defaultProvider + '"]');
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

  async function openCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      formalStatus.textContent = "当前浏览器不支持摄像头接口。";
      return;
    }

    if (currentStream) {
      return;
    }

    try {
      currentStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      });
      formalVideo.srcObject = currentStream;
      formalStatus.textContent = "摄像头已打开。";
    } catch (error) {
      formalStatus.textContent = "打开摄像头失败: " + error.message;
    }
  }

  function stopLiveLoop() {
    if (liveTimer) {
      window.clearInterval(liveTimer);
      liveTimer = null;
    }

    if (currentStream) {
      currentStream.getTracks().forEach((track) => track.stop());
      currentStream = null;
    }

    formalStatus.textContent = "实时分析已停止。";
  }

  function captureFrameBase64() {
    const width = formalVideo.videoWidth;
    const height = formalVideo.videoHeight;
    if (!width || !height) {
      throw new Error("当前没有可采集的视频帧");
    }

    formalCanvas.width = width;
    formalCanvas.height = height;
    const context = formalCanvas.getContext("2d");
    context.drawImage(formalVideo, 0, 0, width, height);
    const dataUrl = formalCanvas.toDataURL("image/jpeg", 0.85);
    return dataUrl.split(",")[1];
  }

  async function sendFormalFrame() {
    if (inFlight) {
      return;
    }

    inFlight = true;
    formalStatus.textContent = "正在发送实时视频帧...";

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
          frameBase64: captureFrameBase64(),
          mimeType: "image/jpeg",
          sessionId: "live-demo-session",
        }),
      });
      const data = await response.json();
      formalStatus.textContent = data && data.ok === false ? "实时分析失败" : "实时分析中...";
      renderResult(formalResult, data);
      setLatestTtsPayload(data && data.ok === false ? null : data.ttsPayload);
    } catch (error) {
      formalStatus.textContent = "实时分析失败: " + error.message;
      setLatestTtsPayload(null);
    } finally {
      inFlight = false;
    }
  }

  startCamera.addEventListener("click", openCamera);

  startFormal.addEventListener("click", async function () {
    await openCamera();
    if (liveTimer) {
      window.clearInterval(liveTimer);
    }

    const interval = Math.max(800, Number(formalInterval.value || 1500));
    formalStatus.textContent = "准备开始实时分析...";
    await sendFormalFrame();
    liveTimer = window.setInterval(sendFormalFrame, interval);
  });

  stopFormal.addEventListener("click", stopLiveLoop);

  speakLatest.addEventListener("click", function () {
    if (!latestTtsPayload) {
      window.alert(getSpeechStatusText(""));
      return;
    }

    speakPayload(latestTtsPayload);
  });

  stopSpeech.addEventListener("click", function () {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  });

  modeTabs.forEach((button) => {
    button.addEventListener("click", function () {
      setMode(button.dataset.mode);
    });
  });

  loadProviders();
})();
