/**
 * JARVIS 3.0 - Holographic Animated Arc Reactor Engine & Dual Voice STT Controller
 */

// ── 1. HOLOGRAPHIC 3D ARC REACTOR CANVAS ANIMATION ────────────────────────────
const canvas = document.getElementById("arc-reactor-canvas");
const ctx = canvas.getContext("2d");

let width, height;
let particles = [];
let outerRays = [];
let rotationX = 0;
let rotationY = 0;
let rotationZ = 0;
let isEnergyHigh = false;
let pulseEnergy = 1.0;
let audioMicVolume = 0.0;

function resizeCanvas() {
  width = canvas.width = window.innerWidth;
  height = canvas.height = window.innerHeight;
  initParticles();
}

window.addEventListener("resize", resizeCanvas);

function initParticles() {
  particles = [];
  const numParticles = 420;
  const radius = Math.min(width, height) * 0.22;

  for (let i = 0; i < numParticles; i++) {
    const theta = Math.acos(2 * Math.random() - 1);
    const phi = 2 * Math.PI * Math.random();

    particles.push({
      x: radius * Math.sin(theta) * Math.cos(phi),
      y: radius * Math.sin(theta) * Math.sin(phi),
      z: radius * Math.cos(theta),
      size: Math.random() * 2.5 + 1,
      baseRadius: radius,
      color: Math.random() > 0.3 ? "#ffaa00" : (Math.random() > 0.5 ? "#ff5500" : "#ffffff"),
    });
  }

  outerRays = [];
  const numRays = 36;
  for (let i = 0; i < numRays; i++) {
    const angle = (i / numRays) * Math.PI * 2;
    const len = radius * (1.2 + Math.random() * 0.8);
    outerRays.push({
      angle: angle,
      length: len,
      speed: (Math.random() - 0.5) * 0.02,
      thickness: Math.random() * 2 + 1.2,
      color: i % 2 === 0 ? "rgba(255, 170, 0, 0.8)" : "rgba(255, 60, 0, 0.7)",
    });
  }
}

function renderArcReactor() {
  ctx.clearRect(0, 0, width, height);

  const cx = width / 2;
  const cy = height / 2;

  const rotSpeed = isEnergyHigh ? 0.035 : 0.008;
  rotationY += rotSpeed;
  rotationX += rotSpeed * 0.5;
  rotationZ += rotSpeed * 0.3;

  const dynamicBoost = 1.0 + (audioMicVolume * 1.5);
  pulseEnergy = (isEnergyHigh ? 1.4 + Math.sin(Date.now() * 0.015) * 0.25 : 1.0 + Math.sin(Date.now() * 0.004) * 0.08) * dynamicBoost;

  // 1. Radiating Energy Rays
  ctx.save();
  ctx.translate(cx, cy);
  for (const ray of outerRays) {
    ray.angle += ray.speed * (isEnergyHigh ? 3 : 1);
    const endX = Math.cos(ray.angle) * ray.length * pulseEnergy;
    const endY = Math.sin(ray.angle) * ray.length * pulseEnergy;

    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(endX, endY);
    ctx.strokeStyle = isEnergyHigh ? "rgba(0, 240, 255, 0.85)" : ray.color;
    ctx.lineWidth = ray.thickness;
    ctx.shadowBlur = isEnergyHigh ? 25 : 12;
    ctx.shadowColor = isEnergyHigh ? "#00f0ff" : "#ffaa00";
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(endX, endY, 2.5, 0, Math.PI * 2);
    ctx.fillStyle = "#ffffff";
    ctx.fill();
  }
  ctx.restore();

  // 2. 3D Rotating Sphere
  const cosY = Math.cos(rotationY);
  const sinY = Math.sin(rotationY);
  const cosX = Math.cos(rotationX);
  const sinX = Math.sin(rotationX);

  const projected = [];

  for (const p of particles) {
    let x1 = p.x * cosY - p.z * sinY;
    let z1 = p.z * cosY + p.x * sinY;

    let y2 = p.y * cosX - z1 * sinX;
    let z2 = z1 * cosX + p.y * sinX;

    const fov = 450;
    const scale = fov / (fov + z2);
    const px = x1 * scale * pulseEnergy + cx;
    const py = y2 * scale * pulseEnergy + cy;

    projected.push({
      x: px,
      y: py,
      z: z2,
      size: p.size * scale,
      color: isEnergyHigh ? "#00f0ff" : p.color,
      alpha: Math.max(0.2, (z2 + 300) / 600),
    });
  }

  projected.sort((a, b) => b.z - a.z);

  ctx.lineWidth = 0.6;
  for (let i = 0; i < projected.length; i += 4) {
    const p1 = projected[i];
    for (let j = i + 1; j < Math.min(i + 5, projected.length); j++) {
      const p2 = projected[j];
      const dist = Math.hypot(p1.x - p2.x, p1.y - p2.y);
      if (dist < 70) {
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.strokeStyle = isEnergyHigh ? `rgba(0, 240, 255, ${0.35 * (1 - dist / 70)})` : `rgba(255, 170, 0, ${0.35 * (1 - dist / 70)})`;
        ctx.stroke();
      }
    }
  }

  for (const p of projected) {
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
    ctx.fillStyle = p.color;
    ctx.globalAlpha = p.alpha;
    ctx.shadowBlur = isEnergyHigh ? 18 : 8;
    ctx.shadowColor = p.color;
    ctx.fill();
  }
  ctx.globalAlpha = 1.0;

  // 3. Central Core Glowing Star Burst
  const gradient = ctx.createRadialGradient(cx, cy, 5, cx, cy, 90 * pulseEnergy);
  if (isEnergyHigh) {
    gradient.addColorStop(0, "rgba(255, 255, 255, 0.95)");
    gradient.addColorStop(0.3, "rgba(0, 240, 255, 0.7)");
    gradient.addColorStop(0.7, "rgba(0, 100, 255, 0.35)");
  } else {
    gradient.addColorStop(0, "rgba(255, 255, 255, 0.95)");
    gradient.addColorStop(0.3, "rgba(255, 170, 0, 0.7)");
    gradient.addColorStop(0.7, "rgba(255, 60, 0, 0.35)");
  }
  gradient.addColorStop(1, "transparent");

  ctx.beginPath();
  ctx.arc(cx, cy, 90 * pulseEnergy, 0, Math.PI * 2);
  ctx.fillStyle = gradient;
  ctx.fill();

  requestAnimationFrame(renderArcReactor);
}

resizeCanvas();
renderArcReactor();


// ── 2. DUAL VOICE STT & CONTINUOUS AUTO-SUBMIT CONTROLLER ─────────────────────
let recognition = null;
let isListening = false;
let autoListenMode = true;
let isProcessing = false;
let audioContext = null;
let audioAnalyser = null;

const micOrbTrigger = document.getElementById("mic-orb-trigger");
const footerMicBtn = document.getElementById("footer-mic-btn");
const commandInput = document.getElementById("command-input");
const footerSendBtn = document.getElementById("footer-send-btn");
const liveTranscriptBanner = document.getElementById("live-transcript-banner");
const coreStateLabel = document.getElementById("core-state-label");
const emergencyStopBtn = document.getElementById("emergency-stop-btn");
const autoListenToggle = document.getElementById("auto-listen-toggle");
const autoListenStatus = document.getElementById("auto-listen-status");

// Auto-Listen Toggle
if (autoListenToggle) {
  autoListenToggle.addEventListener("click", () => {
    autoListenMode = !autoListenMode;
    autoListenToggle.classList.toggle("active", autoListenMode);
    autoListenStatus.textContent = autoListenMode ? "ON" : "OFF";
    if (autoListenMode && !isListening && !isProcessing) {
      startListening();
    }
  });
}

// Request Microphone Permissions & Audio Level Monitor
async function requestMicAccess() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioContext.createMediaStreamSource(stream);
    audioAnalyser = audioContext.createAnalyser();
    audioAnalyser.fftSize = 64;
    source.connect(audioAnalyser);

    const dataArray = new Uint8Array(audioAnalyser.frequencyBinCount);
    function checkAudioLevel() {
      if (audioAnalyser) {
        audioAnalyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
        audioMicVolume = sum / (dataArray.length * 255);
      }
      requestAnimationFrame(checkAudioLevel);
    }
    checkAudioLevel();
  } catch (e) {
    console.warn("Microphone permission prompt result:", e);
  }
}

function initSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn("Browser SpeechRecognition unavailable, using server mic fallback.");
    return;
  }

  recognition = new SpeechRecognition();
  recognition.lang = "en-IN";
  recognition.continuous = false;
  recognition.interimResults = true;

  recognition.onstart = () => {
    isListening = true;
    isEnergyHigh = true;
    micOrbTrigger.classList.add("listening");
    footerMicBtn.classList.add("active");
    coreStateLabel.textContent = "LISTENING (BOLIYE)...";
    liveTranscriptBanner.innerHTML = "<span style='color: #00f0ff;'>🎙️ Sun raha hoon... Boliye...</span>";
  };

  recognition.onresult = (event) => {
    let transcript = "";
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      transcript += event.results[i][0].transcript;
    }
    commandInput.value = transcript;
    liveTranscriptBanner.innerHTML = `<span style='color: #ffaa00;'>Transcribing:</span> "${transcript}"`;

    if (event.results[0].isFinal) {
      liveTranscriptBanner.innerHTML = `<span style='color: #00ffaa;'>⚡ Auto-Executing:</span> "${transcript}"...`;
      executeCommand(transcript);
    }
  };

  recognition.onerror = (event) => {
    console.warn("Speech Recognition Error:", event.error);
    isListening = false;
    isEnergyHigh = false;
    micOrbTrigger.classList.remove("listening");
    footerMicBtn.classList.remove("active");

    // If browser speech recognition failed with network or permission, fallback to server hardware mic!
    if (event.error === "network" || event.error === "not-allowed" || event.error === "service-not-allowed") {
      liveTranscriptBanner.innerHTML = "<span style='color: #ffaa00;'>Falling back to Server Hardware Mic...</span>";
      listenViaServerMic();
      return;
    }

    if (autoListenMode && !isProcessing) {
      setTimeout(startListening, 1500);
    }
  };

  recognition.onend = () => {
    isListening = false;
    if (!isProcessing) {
      isEnergyHigh = false;
      micOrbTrigger.classList.remove("listening");
      footerMicBtn.classList.remove("active");
      coreStateLabel.textContent = "CLICK OR SPEAK";

      if (autoListenMode) {
        setTimeout(startListening, 800);
      }
    }
  };
}

function startListening() {
  if (isProcessing) return;
  if (!recognition) initSpeechRecognition();
  if (recognition && !isListening) {
    try {
      recognition.start();
    } catch (e) {
      // If already started or failed, try server mic
      listenViaServerMic();
    }
  } else if (!recognition) {
    listenViaServerMic();
  }
}

function stopListening() {
  isListening = false;
  isEnergyHigh = false;
  micOrbTrigger.classList.remove("listening");
  footerMicBtn.classList.remove("active");
  coreStateLabel.textContent = "CLICK OR SPEAK";
  if (recognition) {
    try { recognition.stop(); } catch (e) {}
  }
}

// Fallback: Server Physical Microphone Endpoint
async function listenViaServerMic() {
  if (isProcessing) return;
  isListening = true;
  isEnergyHigh = true;
  micOrbTrigger.classList.add("listening");
  footerMicBtn.classList.add("active");
  coreStateLabel.textContent = "SERVER MIC LISTENING...";
  liveTranscriptBanner.innerHTML = "<span style='color: #00f0ff;'>🎙️ Laptop Mic se sun raha hoon... Boliye...</span>";

  try {
    const res = await fetch("/api/voice/listen", { method: "POST" });
    const data = await res.json();
    isListening = false;
    isEnergyHigh = false;
    micOrbTrigger.classList.remove("listening");
    footerMicBtn.classList.remove("active");

    if (data.success && data.transcript) {
      appendChatMessage("user", "Shivam", data.transcript);
      const reply = data.response?.message || "Ji Boss, ho gaya.";
      liveTranscriptBanner.innerHTML = `<span style='color: #00ffaa;'>JARVIS:</span> ${reply}`;
      appendChatMessage("assistant", "JARVIS", reply);
      speakText(reply);
    } else {
      liveTranscriptBanner.textContent = data.message || "Kuch sunayi nahi diya.";
    }
  } catch (err) {
    isListening = false;
    isEnergyHigh = false;
    console.error("Server mic error:", err);
  }

  if (autoListenMode && !isProcessing) {
    setTimeout(startListening, 1000);
  }
}

// Mic Click Triggers
micOrbTrigger.addEventListener("click", () => {
  requestMicAccess();
  if (isListening) stopListening();
  else startListening();
});

footerMicBtn.addEventListener("click", () => {
  requestMicAccess();
  if (isListening) stopListening();
  else startListening();
});


// ── 3. COMMAND EXECUTION & VOICE SYNTHESIS ────────────────────────────────────
async function executeCommand(commandText) {
  const text = (commandText || commandInput.value).trim();
  if (!text) return;

  isProcessing = true;
  commandInput.value = "";
  stopListening();

  isEnergyHigh = true;
  coreStateLabel.textContent = "EXECUTING...";
  liveTranscriptBanner.innerHTML = `<span style='color: #00f0ff;'>⚡ JARVIS Executing:</span> "${text}"...`;

  appendChatMessage("user", "Shivam", text);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, speak_output: false }),
    });

    const data = await res.json();
    isProcessing = false;
    isEnergyHigh = false;
    coreStateLabel.textContent = "CLICK OR SPEAK";

    const reply = data.message || "Ji Boss, complete kar diya.";
    liveTranscriptBanner.innerHTML = `<span style='color: #00ffaa;'>JARVIS:</span> ${reply}`;
    appendChatMessage("assistant", "JARVIS", reply);

    // Speak aloud using browser SpeechSynthesis
    speakText(reply);

  } catch (err) {
    isProcessing = false;
    isEnergyHigh = false;
    coreStateLabel.textContent = "CLICK OR SPEAK";
    const errMsg = `System error: ${err.message}`;
    liveTranscriptBanner.textContent = errMsg;
    appendChatMessage("assistant", "JARVIS", errMsg);
  }

  // Resume auto listening after speech finishes
  if (autoListenMode) {
    setTimeout(startListening, 2000);
  }
}

function speakText(text) {
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "hi-IN";
    utterance.rate = 1.05;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
  }
}

footerSendBtn.addEventListener("click", () => executeCommand());
commandInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") executeCommand();
});

// Quick Protocol Buttons (Home screen)
document.querySelectorAll(".protocol-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const cmd = btn.dataset.cmd;
    executeCommand(cmd);
  });
});

// Emergency Stop
emergencyStopBtn.addEventListener("click", async () => {
  try {
    const resp = await fetch("/api/stop", { method: "POST" });
    const data = await resp.json();
    liveTranscriptBanner.textContent = "🛑 EMERGENCY STOP: All tasks cancelled.";
    appendChatMessage("assistant", "JARVIS", "🛑 Tasks cancelled & resource locks released.");
    speakText("Ruk gaya Boss. Sabhi tasks cancel kar diye hain.");
  } catch (e) {
    console.error(e);
  }
});


// ── 4. CHAT TAB & MESSAGES STREAM ─────────────────────────────────────────────
const chatMessages = document.getElementById("chat-messages");

function appendChatMessage(role, sender, text) {
  const div = document.createElement("div");
  div.className = `terminal-msg ${role}`;
  div.innerHTML = `<span class="msg-tag">[${sender.toUpperCase()}]</span> <span class="msg-txt">${text}</span>`;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}


// ── 5. NAVIGATION & APPS / DIAGNOSTICS DASHBOARD ──────────────────────────────
let allApps = [];
let currentCategory = "All";

document.querySelectorAll(".hud-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".hud-tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".hud-pane").forEach((p) => p.classList.remove("active"));

    tab.classList.add("active");
    const target = document.getElementById(tab.dataset.tab);
    if (target) target.classList.add("active");

    if (tab.dataset.tab === "dashboard-tab") loadApplications();
    if (tab.dataset.tab === "diagnostics-tab") loadDiagnostics();
  });
});

async function loadApplications() {
  try {
    const res = await fetch("/api/apps");
    const data = await res.json();
    allApps = data.apps || [];

    const cntElem = document.getElementById("apps-count-val");
    if (cntElem) cntElem.textContent = `${data.total_apps} DISCOVERED`;
    const dashElem = document.getElementById("dash-total-apps");
    if (dashElem) dashElem.textContent = `${data.total_apps} APPS`;

    renderCategoryPills(data.breakdown || {});
    renderAppsGrid(allApps);
  } catch (e) {
    console.error("Error loading apps:", e);
  }
}

function renderCategoryPills(breakdown) {
  const container = document.getElementById("category-pills");
  if (!container) return;
  container.innerHTML = `<button class="cat-pill ${currentCategory === 'All' ? 'active' : ''}" onclick="filterCategory('All')">All (${allApps.length})</button>`;

  for (const [cat, count] of Object.entries(breakdown)) {
    if (count > 0) {
      container.innerHTML += `<button class="cat-pill ${currentCategory === cat ? 'active' : ''}" onclick="filterCategory('${cat}')">${cat} (${count})</button>`;
    }
  }
}

window.filterCategory = function (cat) {
  currentCategory = cat;
  document.querySelectorAll(".cat-pill").forEach((p) => p.classList.remove("active"));
  if (cat === "All") {
    renderAppsGrid(allApps);
  } else {
    renderAppsGrid(allApps.filter((a) => a.category === cat));
  }
};

function renderAppsGrid(apps) {
  const grid = document.getElementById("apps-hud-grid");
  if (!grid) return;
  if (!apps || apps.length === 0) {
    grid.innerHTML = "<p style='color: var(--text-dim);'>No applications found.</p>";
    return;
  }

  grid.innerHTML = apps.map((a) => `
    <div class="hud-app-card">
      <div>
        <div class="app-card-title">${a.name}</div>
        <div class="app-card-sub">${a.category} // ${a.adapter_name}</div>
      </div>
      <div class="app-card-actions">
        <button class="app-action-btn" onclick="executeCommand('${a.name} open karo')">▶ Launch</button>
        <button class="app-action-btn" onclick="showAppCapabilities('${a.id}')">⚙ Manifest</button>
      </div>
    </div>
  `).join("");
}

// App Capability Modal
const capModal = document.getElementById("capability-modal");
const modalAppName = document.getElementById("modal-app-name");
const modalAppBody = document.getElementById("modal-app-body");
const modalCloseBtn = document.getElementById("modal-close-btn");
if (modalCloseBtn) {
  modalCloseBtn.addEventListener("click", () => {
    capModal.style.display = "none";
  });
}

window.showAppCapabilities = async function (appId) {
  try {
    const res = await fetch(`/api/apps/${appId}/capabilities`);
    const data = await res.json();

    modalAppName.textContent = `${data.app_name} Capabilities`;
    const listHtml = data.capabilities.map((c) => `
      <div style="background: rgba(255, 170, 0, 0.06); border: 1px solid rgba(255, 170, 0, 0.2); padding: 10px; border-radius: 6px; margin-bottom: 8px;">
        <div style="display: flex; justify-content: space-between; font-weight: bold; color: var(--gold-primary);">
          <span>${c.name}</span>
          <span style="font-size: 0.75rem; color: var(--green-status);">[${c.status}]</span>
        </div>
        <div style="font-size: 0.85rem; color: #fff; margin-top: 4px;">${c.description}</div>
      </div>
    `).join("");

    modalAppBody.innerHTML = `
      <p style="color: var(--text-dim); margin-bottom: 12px;">Adapter: <strong style="color: #fff;">${data.adapter}</strong></p>
      ${listHtml}
    `;

    capModal.style.display = "flex";
  } catch (e) {
    alert("Could not load capabilities: " + e);
  }
};

// Diagnostics & Health
async function loadDiagnostics() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    const grid = document.getElementById("diag-grid");
    if (!grid) return;

    grid.innerHTML = Object.entries(data.subsystems || {}).map(([name, h]) => `
      <div class="diag-card">
        <div style="display: flex; justify-content: space-between; font-weight: bold; color: var(--gold-primary); margin-bottom: 6px;">
          <span>${name.toUpperCase()}</span>
          <span style="color: ${h.status === 'HEALTHY' ? 'var(--green-status)' : 'var(--red-alert)'};">[${h.status}]</span>
        </div>
        <div style="font-size: 0.85rem; color: var(--text-dim);">Success Rate: ${h.successful_calls}/${h.total_calls} (${h.total_calls > 0 ? Math.round((h.successful_calls/h.total_calls)*100) : 100}%)</div>
      </div>
    `).join("");
  } catch (e) {
    console.error("Error loading diagnostics:", e);
  }
}

const rescanHealthBtn = document.getElementById("rescan-health-btn");
if (rescanHealthBtn) {
  rescanHealthBtn.addEventListener("click", loadDiagnostics);
}

// Live Clock
setInterval(() => {
  const clock = document.getElementById("hud-clock");
  if (clock) {
    const now = new Date();
    clock.textContent = now.toTimeString().split(" ")[0];
  }
}, 1000);

// Init on Load
document.addEventListener("DOMContentLoaded", () => {
  initSpeechRecognition();
  loadApplications();
  // Auto-start listening after 1 second
  setTimeout(startListening, 1000);
});
