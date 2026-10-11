// ---- Config ----
const API_BASE = "http://localhost:8000"; // change if backend runs elsewhere

// ---- State ----
function newSessionId() {
  return "sess_" + Math.random().toString(36).slice(2, 10);
}
let sessionId = newSessionId();

// ---- Elements ----
const consoleEl = document.querySelector(".console");
const stage = document.getElementById("stage");
const transcript = document.getElementById("transcript");
const composer = document.getElementById("composer");
const messageInput = document.getElementById("message");
const logContextWrap = document.getElementById("log-context-wrap");
const logContextInput = document.getElementById("log-context");
const toggleLogBtn = document.getElementById("toggle-log");
const sendBtn = document.getElementById("send-btn");
const newChatBtn = document.getElementById("new-chat");
const connDot = document.getElementById("conn-dot");
const connStatus = document.getElementById("conn-status");
const sessionDisplay = document.getElementById("session-id-display");
const navTrigger = document.getElementById("nav-trigger");
const navPanel = document.getElementById("nav-panel");

sessionDisplay.textContent = sessionId;

function enterConversation() {
  consoleEl.classList.add("started");
}

function scrollToEnd() {
  stage.scrollTop = stage.scrollHeight;
}

// ---- Helpers ----
function timeNow() {
  return new Date().toLocaleTimeString("en-GB", { hour12: false });
}

// Greetings, thanks, and "who are you" style messages have nothing to look up in the
// knowledge base, so a low confidence warning on their replies is misleading.
// Only a message that is entirely small talk matches. A real question never does.
const SMALL_TALK = [
  /^(hi+|hello+|hey+|heya|hiya|yo|namaste|good (morning|afternoon|evening|night))( there| assistant| bot| everyone)?$/,
  /^(how are you|how are you doing|how r u|how are u|how are you doing today|how do you do|how is it going|how's it going|what's up|whats up|sup)( today)?$/,
  /^(who are you|what are you|what is your name|what's your name|whats your name|who made you|who built you|who created you|introduce yourself|tell me about yourself)$/,
  /^(what can you do|what do you do|how can you help( me)?|can you help me|what can you help( me)? with|help|help me)$/,
  /^(thanks|thank you|thx|ok|okay|cool|great|nice|got it|bye|goodbye|see you)( so much| a lot| very much)?$/
];

function isSmallTalk(message, logContext) {
  if (logContext) return false;
  const clean = message.toLowerCase().replace(/[^a-z0-9'\s]/g, " ").replace(/\s+/g, " ").trim();
  if (!clean) return false;
  if (SMALL_TALK.some(re => re.test(clean))) return true;
  // "hi how are you", "hello who are you": a greeting followed by small talk
  const rest = clean.replace(/^(hi+|hello+|hey+|heya|hiya|yo|good (morning|afternoon|evening)) /, "");
  return rest !== clean && SMALL_TALK.some(re => re.test(rest));
}

function addEntry({ role, text, citations = [], flagged = false, flagReason = "", grounded = true, logAttachment = "", warnLowConfidence = true }) {
  const entry = document.createElement("div");
  entry.className = `entry ${role}`;

  const tagLabel = role === "analyst" ? "Analyst" : role === "assistant" ? "Assistant" : "System";

  entry.innerHTML = `
    <div class="entry-meta">
      <span class="tag">${tagLabel}</span>
      <span class="time">${timeNow()}</span>
    </div>
    <div class="entry-body"></div>
  `;
  entry.querySelector(".entry-body").textContent = text;

  if (logAttachment) {
    const logEl = document.createElement("div");
    logEl.className = "log-line";
    logEl.textContent = logAttachment;
    entry.appendChild(logEl);
  }

  if (flagged) {
    const badge = document.createElement("span");
    badge.className = "entry-flag";
    badge.textContent = `Flagged: ${flagReason || "needs review"}`;
    entry.appendChild(badge);
  }

  // Warn when the backend says the answer was not grounded in the knowledge base.
  // Whether a message counts as grounded is decided by the backend (app/validation.py).
  const ungrounded = role === "assistant" && grounded === false;
  if (ungrounded && warnLowConfidence) {
    const badge = document.createElement("span");
    badge.className = "entry-ungrounded";
    badge.textContent = "Low confidence: limited supporting context found";
    badge.title = "The knowledge base had little to support this answer. Check it before acting on it.";
    entry.appendChild(badge);
  }

  // Only show sources when the answer was actually grounded in them.
  const sources = Array.isArray(citations) ? citations : [];
  if (sources.length && !ungrounded) {
    const wrap = document.createElement("div");
    wrap.className = "citations";
    sources.forEach(c => {
      const chip = document.createElement("span");
      chip.className = "citation";
      chip.title = c.snippet || "";
      chip.textContent = `[${c.source}]`;
      wrap.appendChild(chip);
    });
    entry.appendChild(wrap);
  }

  transcript.appendChild(entry);
  scrollToEnd();
}

function addThinking() {
  const el = document.createElement("div");
  el.className = "entry assistant thinking";
  el.setAttribute("role", "status");
  el.innerHTML = `
    <div class="entry-meta"><span class="tag">Assistant</span></div>
    <div class="thinking-row">
      <span class="bars" aria-hidden="true"><i></i><i></i><i></i></span>
      <span class="shimmer">Analyzing</span>
    </div>
  `;
  transcript.appendChild(el);
  scrollToEnd();
  const label = el.querySelector(".shimmer");
  setTimeout(() => { label.textContent = "Still working"; }, 8000);
  return el;
}

async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) {
      connDot.classList.add("online");
      connStatus.textContent = "backend online";
    } else {
      throw new Error("bad status");
    }
  } catch {
    connDot.classList.add("offline");
    connStatus.textContent = "backend unreachable";
  }
}

async function sendMessage(message, logContext) {
  sendBtn.disabled = true;
  sendBtn.textContent = "Sending";

  addEntry({ role: "analyst", text: message, logAttachment: logContext });
  const loader = addThinking();

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        message,
        log_context: logContext || null,
      }),
    });

    if (!res.ok) {
      const errText = await res.text();
      throw new Error(errText || `HTTP ${res.status}`);
    }

    const data = await res.json();
    loader.remove();
    addEntry({
      role: "assistant",
      text: data.answer,
      citations: data.citations,
      flagged: data.flagged,
      flagReason: data.flag_reason,
      grounded: data.grounded,
      warnLowConfidence: !isSmallTalk(message, logContext),
    });
  } catch (err) {
    loader.remove();
    addEntry({
      role: "system",
      text: `Request failed: ${err.message}. Is the backend running at ${API_BASE}?`,
    });
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = "Send";
  }
}

function newChat() {
  if (sendBtn.disabled) return; // wait for the current answer
  transcript.innerHTML = "";
  consoleEl.classList.remove("started");
  sessionId = newSessionId();
  sessionDisplay.textContent = sessionId;
  messageInput.value = "";
  messageInput.style.height = "auto";
  logContextInput.value = "";
  logContextWrap.hidden = true;
  toggleLogBtn.textContent = "Attach log";
  stage.scrollTop = 0;
}

// ---- Navigation menu ----
function setPanel(open) {
  navPanel.hidden = !open;
  navTrigger.setAttribute("aria-expanded", String(open));
}

navTrigger.addEventListener("click", (e) => {
  e.stopPropagation();
  setPanel(navPanel.hidden);
});

document.addEventListener("click", (e) => {
  if (!navPanel.hidden && !navPanel.contains(e.target) && !navTrigger.contains(e.target)) {
    setPanel(false);
  }
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !navPanel.hidden) {
    setPanel(false);
    navTrigger.focus();
  }
});

// ---- Event wiring ----
newChatBtn.addEventListener("click", newChat);

toggleLogBtn.addEventListener("click", () => {
  const hidden = logContextWrap.hidden;
  logContextWrap.hidden = !hidden;
  toggleLogBtn.textContent = hidden ? "Hide log" : "Attach log";
  if (hidden) logContextInput.focus();
});

document.querySelectorAll(".chip").forEach(chip => {
  chip.addEventListener("click", () => {
    messageInput.value = chip.dataset.q;
    messageInput.focus();
  });
});

messageInput.addEventListener("input", () => {
  messageInput.style.height = "auto";
  messageInput.style.height = Math.min(messageInput.scrollHeight, 140) + "px";
});

messageInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    composer.requestSubmit();
  }
});

composer.addEventListener("submit", (e) => {
  e.preventDefault();
  if (sendBtn.disabled) return;
  const message = messageInput.value.trim();
  if (!message) return;
  const logContext = logContextInput.value.trim();

  enterConversation();
  sendMessage(message, logContext);

  messageInput.value = "";
  messageInput.style.height = "auto";
  logContextInput.value = "";
});

// ---- Globe (decorative dotted sphere) ----
(function globe() {
  const canvas = document.getElementById("globe");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const N = 950;
  const pts = [];
  for (let i = 0; i < N; i++) {
    const y = 1 - ((i + 0.5) / N) * 2;
    const r = Math.sqrt(1 - y * y);
    const th = i * 2.399963;
    pts.push([Math.cos(th) * r, y, Math.sin(th) * r]);
  }
  const tilt = 0.4, ct = Math.cos(tilt), st = Math.sin(tilt);
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let angle = 0;

  function draw() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (w > 0 && h > 0) {
      const d = window.devicePixelRatio || 1;
      if (canvas.width !== Math.round(w * d) || canvas.height !== Math.round(h * d)) {
        canvas.width = Math.round(w * d);
        canvas.height = Math.round(h * d);
      }
      ctx.setTransform(d, 0, 0, d, 0, 0);
      ctx.clearRect(0, 0, w, h);
      const R = Math.min(w, h) * 0.42, cx = w / 2, cy = h / 2;

      const glow = ctx.createRadialGradient(cx, cy, R * 0.55, cx, cy, R * 1.3);
      glow.addColorStop(0, "rgba(47,124,255,0.20)");
      glow.addColorStop(1, "rgba(47,124,255,0)");
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, w, h);

      const ca = Math.cos(angle), sa = Math.sin(angle);
      for (const p of pts) {
        const x = p[0] * ca + p[2] * sa;
        const z = -p[0] * sa + p[2] * ca;
        const y2 = p[1] * ct - z * st;
        const z2 = p[1] * st + z * ct;
        const depth = (z2 + 1) / 2;
        const a = z2 > 0 ? 0.25 + 0.75 * depth : 0.06;
        ctx.fillStyle = `rgba(165,205,255,${a.toFixed(3)})`;
        const s = z2 > 0 ? 1.6 : 1;
        ctx.fillRect(cx + x * R - s / 2, cy + y2 * R - s / 2, s, s);
      }
    }
    if (!reduce) {
      angle += 0.0028;
      requestAnimationFrame(draw);
    }
  }
  draw();
  if (reduce) window.addEventListener("resize", draw);
})();

// ---- Init ----
checkHealth();
