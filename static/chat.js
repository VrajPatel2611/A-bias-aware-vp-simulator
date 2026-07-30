// chat.js
// Consultation interface: history chat, examination, investigations.
// Sprint 3: tabbed actions + deterministic exam/lab result cards.

let questionCount = 0;

// ── Helpers ──────────────────────────────────────────────────────────

function scrollToBottom() {
  const box = document.getElementById("chat-box");
  if (box) box.scrollTop = box.scrollHeight;
}

function updateProgress(count) {
  questionCount = count;
  const numEl  = document.getElementById("q-count-num");
  const fillEl = document.getElementById("progress-fill");
  const hintEl = document.getElementById("min-hint");
  if (!numEl) return;

  numEl.textContent = count;
  const min = typeof CASE_MIN_QUESTIONS !== "undefined" ? CASE_MIN_QUESTIONS : 7;
  const pct = Math.min((count / min) * 100, 100);

  if (fillEl) {
    fillEl.style.width = pct + "%";
    fillEl.classList.toggle("complete", count >= min);
  }
  if (hintEl) {
    hintEl.textContent = count >= min ? "Minimum reached ✓" : `Aim for at least ${min}`;
    hintEl.style.color = count >= min ? "var(--green-600)" : "var(--slate-400)";
  }
}

function showTyping() {
  const ind = document.getElementById("typing-indicator");
  if (ind) { ind.classList.add("show"); scrollToBottom(); }
}
function hideTyping() {
  const ind = document.getElementById("typing-indicator");
  if (ind) ind.classList.remove("show");
}

function addMessage(speaker, text, type) {
  const box = document.getElementById("chat-box");
  const div = document.createElement("div");
  div.className = `msg ${type}`;

  const speakerEl = document.createElement("div");
  speakerEl.className = "speaker";
  speakerEl.textContent = speaker;

  const textEl = document.createElement("div");
  textEl.textContent = text;

  div.appendChild(speakerEl);
  div.appendChild(textEl);

  const typing = document.getElementById("typing-indicator");
  if (typing) box.insertBefore(div, typing);
  else box.appendChild(div);
  scrollToBottom();
}

// Clinical result card (examination or investigation)
function addClinicalCard(kind, label, text) {
  const box = document.getElementById("chat-box");
  const div = document.createElement("div");
  div.className = `clinical-card ${kind}`;   // kind: "exam" | "lab"

  const header = document.createElement("div");
  header.className = "cc-header";
  const icon = kind === "exam" ? "🩺" : "🧪";
  const tag  = kind === "exam" ? "Examination" : "Result";
  header.textContent = `${icon}  ${tag} — ${label}`;

  const body = document.createElement("div");
  body.className = "cc-body";
  body.textContent = text;

  div.appendChild(header);
  div.appendChild(body);

  const typing = document.getElementById("typing-indicator");
  if (typing) box.insertBefore(div, typing);
  else box.appendChild(div);
  scrollToBottom();
}


// ── Tabs ──────────────────────────────────────────────────────────────

function switchTab(name) {
  document.querySelectorAll(".action-tab").forEach(t => {
    t.classList.toggle("active", t.dataset.tab === name);
  });
  document.querySelectorAll(".tab-panel").forEach(p => {
    p.classList.toggle("active", p.id === "panel-" + name);
  });
  if (name === "history") {
    const inp = document.getElementById("user-input");
    if (inp) inp.focus();
  }
}


// ── History question ──────────────────────────────────────────────────

async function sendMessage() {
  const input = document.getElementById("user-input");
  const message = input.value.trim();
  if (!message) return;

  addMessage("You", message, "user");
  input.value = "";

  const askBtn = document.getElementById("ask-btn");
  askBtn.disabled = true;
  askBtn.textContent = "…";
  showTyping();

  try {
    const r = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await r.json();
    hideTyping();
    if (data.error) addMessage("System", data.error, "system-msg");
    else {
      addMessage("Patient", data.response, "patient");
      updateProgress(data.question_count);
    }
  } catch (err) {
    hideTyping();
    addMessage("System", "Connection error — is the server running?", "system-msg");
  }

  askBtn.disabled = false;
  askBtn.textContent = "Ask";
  input.focus();
}


// ── Examination ───────────────────────────────────────────────────────

async function performExam(systemKey, btn) {
  if (btn) { btn.disabled = true; btn.classList.add("loading"); }
  try {
    const r = await fetch("/examine", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ system: systemKey }),
    });
    const data = await r.json();
    if (data.error) {
      addMessage("System", data.error, "system-msg");
      if (btn) { btn.disabled = false; btn.classList.remove("loading"); }
      return;
    }
    addClinicalCard("exam", data.label, data.finding);
    if (btn) { btn.classList.remove("loading"); btn.classList.add("done"); btn.textContent = "✓ " + data.label; }
  } catch (err) {
    addMessage("System", "Could not perform examination.", "system-msg");
    if (btn) { btn.disabled = false; btn.classList.remove("loading"); }
  }
}


// ── Investigation ─────────────────────────────────────────────────────

async function orderTest(testKey, btn) {
  if (btn) { btn.disabled = true; btn.classList.add("loading"); }
  try {
    const r = await fetch("/investigate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ test: testKey }),
    });
    const data = await r.json();
    if (data.error) {
      addMessage("System", data.error, "system-msg");
      if (btn) { btn.disabled = false; btn.classList.remove("loading"); }
      return;
    }
    addClinicalCard("lab", data.label, data.result);
    if (btn) { btn.classList.remove("loading"); btn.classList.add("done"); btn.textContent = "✓ " + data.label; }
  } catch (err) {
    addMessage("System", "Could not order investigation.", "system-msg");
    if (btn) { btn.disabled = false; btn.classList.remove("loading"); }
  }
}


// ── Submit diagnosis ──────────────────────────────────────────────────

async function submitDiagnosis() {
  const diagInput = document.getElementById("diagnosis-input");
  const diagnosis = diagInput.value.trim();
  if (!diagnosis) {
    diagInput.focus();
    diagInput.style.borderColor = "var(--amber-600)";
    setTimeout(() => { diagInput.style.borderColor = ""; }, 2000);
    return;
  }

  const min = typeof CASE_MIN_QUESTIONS !== "undefined" ? CASE_MIN_QUESTIONS : 7;
  const warnEl = document.getElementById("min-warning");
  if (questionCount < min && warnEl && !warnEl.classList.contains("show")) {
    warnEl.classList.add("show");
    await new Promise(r => setTimeout(r, 1600));
  }

  const btn = document.getElementById("conclude-btn");
  btn.disabled = true;
  btn.textContent = "Analysing your reasoning…";
  const askBtn = document.getElementById("ask-btn");
  if (askBtn) askBtn.disabled = true;

  try {
    const r = await fetch("/conclude", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ diagnosis }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.error || `Server error ${r.status}`);
    }
    window.location.href = "/feedback";
  } catch (err) {
    btn.disabled = false;
    btn.textContent = "Submit & Get Feedback";
    if (askBtn) askBtn.disabled = false;
    addMessage("System", "Error: " + err.message, "system-msg");
  }
}


// ── Init ──────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", function () {
  const input = document.getElementById("user-input");
  if (input) {
    input.addEventListener("keypress", e => { if (e.key === "Enter") sendMessage(); });
    input.focus();
  }
  const diagInput = document.getElementById("diagnosis-input");
  if (diagInput) {
    diagInput.addEventListener("keypress", e => { if (e.key === "Enter") submitDiagnosis(); });
  }
});
