(function () {
  const modeTabs = document.querySelectorAll(".mode-tab");
  const panels = document.querySelectorAll("[data-panel]");
  const providerSelect = document.querySelector("#providerSelect");

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

  function setMode(mode) {
    modeTabs.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.mode === mode);
    });
    panels.forEach((panel) => {
      panel.classList.toggle("is-hidden", panel.dataset.panel !== mode);
    });
  }

  function prettyPrintResult(data) {
    if (!data || !data.result) {
      return "暂无结果";
    }

    const result = data.result;
    const guidance = (result.guidance || []).length
      ? result.guidance.map((item) => "- " + item).join("\n")
      : "- 无";
    const hazards = (result.hazards || []).length
      ? result.hazards
          .map((item) => "- [" + (item.severity || "unknown") + "] " + (item.description || ""))
          .join("\n")
      : "- 无";

    return [
      "provider: " + (data.provider || "-"),
      "model: " + (data.model || "-"),
      "summary: " + (result.summary || "-"),
      "riskLevel: " + (result.riskLevel || "-"),
      "confidence: " + (result.confidence || "-"),
      "",
      "guidance:",
      guidance,
      "",
      "hazards:",
      hazards,
      "",
      "tts:",
      (data.ttsPayload && data.ttsPayload.text) || "-",
    ].join("\n");
  }

  async function loadProviders() {
    try {
      const response = await fetch("/api/providers");
      const data = await response.json();
      providerSelect.innerHTML = "";
      (data.providers || []).forEach((provider) => {
        const option = document.createElement("option");
        option.value = provider.id;
        option.textContent = provider.enabled ? provider.label : provider.label + "（未配置）";
        providerSelect.appendChild(option);
      });
      providerSelect.value = data.defaultProvider || "mock";
    } catch (error) {
      providerSelect.value = "mock";
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

    debugResult.textContent = "正在分析...";

    try {
      const response = await fetch("/api/debug/analyze", {
        method: "POST",
        body: form,
      });
      const data = await response.json();
      debugResult.textContent = prettyPrintResult(data);
    } catch (error) {
      debugResult.textContent = "调试分析失败: " + error.message;
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
      formalStatus.textContent = "实时分析中...";
      formalResult.textContent = prettyPrintResult(data);
    } catch (error) {
      formalStatus.textContent = "实时分析失败: " + error.message;
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

  modeTabs.forEach((button) => {
    button.addEventListener("click", function () {
      setMode(button.dataset.mode);
    });
  });

  loadProviders();
})();
