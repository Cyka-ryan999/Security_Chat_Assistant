// ---- Config ----
const API_BASE = "http://localhost:8000"; // change if backend runs elsewhere

// ---- State ----
const sessionId = "sess_" + Math.random().toString(36).slice(2, 10);
document.getElementById("session-id-display").textContent = sessionId;

// ---- Elements ----
const consoleEl = document.querySelector(".console");
const transcript = document.getElementById("transcript");
const composer = document.getElementById("composer");
const messageInput = document.getElementById("message");
const logContextWrap = document.getElementById("log-context-wrap");
const logContextInput = document.getElementById("log-context");
const toggleLogBtn = document.getElementById("toggle-log");
const sendBtn = document.getElementById("send-btn");
const connDot = document.getElementById("conn-dot");
const connStatus = document.getElementById("conn-status");
const sampleCard = document.getElementById("sample-card");

function enterConversation() {
  consoleEl.classList.add("started");
}

// ---- Helpers ----
function timeNow() {
  return new Date().toLocaleTimeString("en-GB", { hour12: false });
}

function addEntry({ role, text, citations = [], flagged = false, flagReason = "", grounded = true, logAttachment = "" }) {
  const entry = document.createElement("div");
  entry.className = `entry ${role}`;

  const tagLabel = role === "analyst" ? "ANALYST" : role === "assistant" ? "ASSISTANT" : "SYSTEM";

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

  if (role === "assistant" && !grounded) {
    const badge = document.createElement("span");
    badge.className = "entry-ungrounded";
    badge.textContent = "⚠ low-confidence: limited supporting context found";
    entry.appendChild(badge);
  }

  if (flagged) {
    const badge = document.createElement("span");
    badge.className = "entry-flag";
    badge.textContent = `⚑ flagged: ${flagReason || "review"}`;
    entry.appendChild(badge);
  }

  if (citations.length) {
    const wrap = document.createElement("div");
    wrap.className = "citations";
    citations.forEach(c => {
      const chip = document.createElement("span");
      chip.className = "citation";
      chip.title = c.snippet;
      chip.textContent = `[${c.source}]`;
      wrap.appendChild(chip);
    });
    entry.appendChild(wrap);
  }

  transcript.appendChild(entry);
  transcript.scrollTop = transcript.scrollHeight;
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
  sendBtn.textContent = "…";

  addEntry({ role: "analyst", text: message, logAttachment: logContext });

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
    addEntry({
      role: "assistant",
      text: data.answer,
      citations: data.citations,
      flagged: data.flagged,
      flagReason: data.flag_reason,
      grounded: data.grounded,
    });
  } catch (err) {
    addEntry({
      role: "system",
      text: `Request failed: ${err.message}. Is the backend running at ${API_BASE}?`,
    });
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = "Send";
  }
}

// ---- Event wiring ----
toggleLogBtn.addEventListener("click", () => {
  const hidden = logContextWrap.hidden;
  logContextWrap.hidden = !hidden;
  toggleLogBtn.textContent = hidden ? "− hide log/alert field" : "+ attach log/alert";
  if (hidden) logContextInput.focus();
});

document.querySelectorAll(".chip").forEach(chip => {
  chip.addEventListener("click", () => {
    messageInput.value = chip.dataset.q;
    messageInput.focus();
  });
});

sampleCard.addEventListener("click", () => {
  messageInput.value = sampleCard.dataset.q;
  messageInput.focus();
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
  const message = messageInput.value.trim();
  if (!message) return;
  const logContext = logContextInput.value.trim();

  enterConversation();
  sendMessage(message, logContext);

  messageInput.value = "";
  messageInput.style.height = "auto";
  logContextInput.value = "";
});

// ---- Init ----
checkHealth();
