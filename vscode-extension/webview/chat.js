// @ts-nocheck
(function () {
  "use strict";

  const vscode = acquireVsCodeApi();

  // ── DOM refs ──────────────────────────────────────────────────────────────
  const messagesEl      = document.getElementById("messages");
  const inputEl         = document.getElementById("input");
  const btnSend         = document.getElementById("btn-send");
  const btnNew          = document.getElementById("btn-new");
  const btnHistory      = document.getElementById("btn-history");
  const btnCloseSession = document.getElementById("btn-close-sessions");
  const sessionsPanel   = document.getElementById("sessions-panel");
  const sessionsList    = document.getElementById("sessions-list");
  const btnStartEmpty   = document.getElementById("btn-start-empty");

  // ── State ─────────────────────────────────────────────────────────────────
  let busy              = false;
  let thinkingEl        = null;
  let streamingMsgEl    = null;
  let streamingBubble   = null;
  let pendingDecisions  = [];
  let pendingTotal      = 0;
  let decidedCount      = 0;
  let activeToolList    = null;  // current tool-list container
  let activeTool        = null;  // { chipEl, spinEl, nameEl } for current tool

  // ── Helpers ───────────────────────────────────────────────────────────────

  function esc(s) {
    return String(s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function scrollBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function setBusy(val) {
    busy = val;
    btnSend.disabled  = val;
    inputEl.disabled  = val;
    if (!val) inputEl.focus();
  }

  function clearEmpty() {
    const empty = messagesEl.querySelector(".empty-state");
    if (empty) empty.remove();
  }

  function autoResize() {
    inputEl.style.height = "auto";
    inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + "px";
  }

  // ── Markdown renderer (lightweight) ───────────────────────────────────────

  function renderMd(text) {
    // Code blocks
    text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, _lang, code) =>
      `<pre><code>${esc(code.trim())}</code></pre>`
    );
    // Inline code
    text = text.replace(/`([^`\n]+)`/g, (_, c) => `<code>${esc(c)}</code>`);
    // Bold / italic
    text = text.replace(/\*\*([^*\n]+)\*\*/g, (_, t) => `<strong>${t}</strong>`);
    text = text.replace(/\*([^*\n]+)\*/g,   (_, t) => `<em>${t}</em>`);
    // Paragraphs
    text = text.split(/\n\n+/).map(p => `<p>${p.replace(/\n/g, "<br>")}</p>`).join("");
    return text;
  }

  // ── Message builders ──────────────────────────────────────────────────────

  function removeThinking() {
    if (thinkingEl) { thinkingEl.remove(); thinkingEl = null; }
  }

  function finaliseStreaming() {
    if (streamingMsgEl && streamingBubble) {
      streamingBubble.innerHTML = renderMd(streamingBubble.dataset.raw || "");
      streamingMsgEl = null;
      streamingBubble = null;
    }
    activeToolList = null;
    activeTool = null;
  }

  function addUserMsg(text) {
    clearEmpty();
    finaliseStreaming();
    removeThinking();
    const row    = document.createElement("div");
    row.className = "msg user";
    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.textContent = text;
    row.appendChild(bubble);
    messagesEl.appendChild(row);
    scrollBottom();
  }

  function startAgentMsg() {
    clearEmpty();
    removeThinking();
    finaliseStreaming();
    activeToolList = null;
    const row    = document.createElement("div");
    row.className = "msg agent";
    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.dataset.raw = "";
    row.appendChild(bubble);
    messagesEl.appendChild(row);
    streamingMsgEl  = row;
    streamingBubble = bubble;
    scrollBottom();
    return bubble;
  }

  function appendToken(token) {
    if (!streamingBubble) startAgentMsg();
    streamingBubble.dataset.raw += token;
    // Render incrementally as plain text while streaming (no md flicker)
    streamingBubble.textContent = streamingBubble.dataset.raw;
    scrollBottom();
  }

  function addSys(text) {
    const row    = document.createElement("div");
    row.className = "msg sys";
    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.textContent = text;
    row.appendChild(bubble);
    messagesEl.appendChild(row);
    scrollBottom();
  }

  function addError(text) {
    clearEmpty();
    removeThinking();
    const row    = document.createElement("div");
    row.className = "msg err";
    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.textContent = text;
    row.appendChild(bubble);
    messagesEl.appendChild(row);
    scrollBottom();
  }

  function showThinking() {
    removeThinking();
    const row  = document.createElement("div");
    row.className = "thinking-row";
    row.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    messagesEl.appendChild(row);
    thinkingEl = row;
    scrollBottom();
  }

  // ── Tool call chips ───────────────────────────────────────────────────────

  const TOOL_SVG_SPIN = `<svg class="tool-chip-icon spin" viewBox="0 0 16 16" fill="currentColor"><path d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2v1z"/><path d="M8 4.466V.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 0 1 8 4.466z"/></svg>`;
  const TOOL_SVG_OK   = `<svg class="tool-chip-icon ok" viewBox="0 0 16 16" fill="currentColor"><path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/></svg>`;
  const TOOL_SVG_FAIL = `<svg class="tool-chip-icon fail" viewBox="0 0 16 16" fill="currentColor"><path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/></svg>`;

  function ensureToolList() {
    if (!activeToolList || activeToolList.parentNode !== messagesEl) {
      finaliseStreaming();
      removeThinking();
      activeToolList = document.createElement("div");
      activeToolList.className = "tool-list";
      messagesEl.appendChild(activeToolList);
    }
  }

  function toolStart(name, summary) {
    ensureToolList();
    const chip = document.createElement("div");
    chip.className = "tool-chip";
    chip.innerHTML = TOOL_SVG_SPIN +
      `<span class="tool-chip-name">${esc(name)}</span>` +
      (summary ? `<span class="tool-chip-summary">${esc(summary)}</span>` : "");
    activeToolList.appendChild(chip);
    activeTool = chip;
    scrollBottom();
  }

  function toolEnd(name, ok, summary) {
    if (activeTool) {
      activeTool.innerHTML = (ok ? TOOL_SVG_OK : TOOL_SVG_FAIL) +
        `<span class="tool-chip-name">${esc(name)}</span>` +
        (summary ? `<span class="tool-chip-summary">${esc(summary)}</span>` : "");
      activeTool = null;
    }
  }

  // ── HITL ──────────────────────────────────────────────────────────────────

  const TOOL_ICONS = { write_file: "✏", execute: "⚡", read_file: "◎", default: "⟐" };

  function renderInterrupt(requests) {
    clearEmpty();
    finaliseStreaming();
    removeThinking();
    activeToolList = null;

    pendingTotal     = requests.length;
    decidedCount     = 0;
    pendingDecisions = new Array(requests.length).fill(null);

    const section = document.createElement("div");
    section.className = "hitl-section";

    const hdr = document.createElement("div");
    hdr.className = "hitl-header";
    hdr.textContent = `⚠ Approval required — ${requests.length} action${requests.length !== 1 ? "s" : ""}`;
    section.appendChild(hdr);

    requests.forEach((req, idx) => {
      let summary = "";
      if (req.name === "write_file") {
        const fp    = req.args.file_path || "?";
        const lines = String(req.args.content || "").split("\n").length;
        summary = `<code>${esc(String(fp))}</code> <span style="opacity:0.55">(${lines} lines)</span>`;
      } else if (req.name === "execute") {
        summary = `<code>${esc(String(req.args.command || "?").slice(0, 80))}</code>`;
      } else {
        summary = `<code>${esc(JSON.stringify(req.args).slice(0, 80))}</code>`;
      }

      const card = document.createElement("div");
      card.className = "approval-card";
      card.innerHTML = `
        <div class="card-top">
          <span>${TOOL_ICONS[req.name] || TOOL_ICONS.default}</span>
          <span class="card-tool-name">${esc(req.name)}</span>
        </div>
        <div class="card-body">
          <div>${summary}</div>
          <details>
            <summary>Show arguments</summary>
            <pre>${esc(JSON.stringify(req.args, null, 2))}</pre>
          </details>
        </div>
        <div class="card-actions" id="ca-${idx}">
          <button class="btn-reject" id="rej-${idx}">Reject</button>
          <button class="btn-approve" id="app-${idx}">Approve</button>
        </div>`;
      section.appendChild(card);

      card.querySelector(`#app-${idx}`).addEventListener("click", () => decide(idx, true));
      card.querySelector(`#rej-${idx}`).addEventListener("click", () => decide(idx, false));
    });

    messagesEl.appendChild(section);
    scrollBottom();
    setBusy(false);
  }

  function decide(idx, approved) {
    const actionsEl = document.getElementById(`ca-${idx}`);
    if (!actionsEl) return;
    pendingDecisions[idx] = approved ? { type: "approve" } : { type: "reject" };
    decidedCount++;

    const badge = document.createElement("span");
    badge.className = `decided-badge ${approved ? "approved" : "rejected"}`;
    badge.textContent = approved ? "✓ Approved" : "✕ Rejected";
    actionsEl.innerHTML = "";
    actionsEl.appendChild(badge);

    if (decidedCount >= pendingTotal) {
      vscode.postMessage({ type: "decision", decisions: pendingDecisions });
      pendingTotal = 0; decidedCount = 0; pendingDecisions = [];
      setBusy(true);
      showThinking();
    }
  }

  // ── Sessions panel ────────────────────────────────────────────────────────

  function renderSessions(rows) {
    sessionsList.innerHTML = "";
    if (!rows || rows.length === 0) {
      const empty = document.createElement("div");
      empty.style.cssText = "padding:10px 14px;font-size:11px;opacity:0.5;";
      empty.textContent = "No past sessions";
      sessionsList.appendChild(empty);
      return;
    }
    rows.forEach(row => {
      const btn = document.createElement("button");
      btn.className = "session-item";
      btn.innerHTML = `<span class="session-id">${esc(row.thread_id.slice(0, 8))}…</span>
        <span class="session-turns">${row.turns} turn${row.turns !== 1 ? "s" : ""}</span>`;
      btn.addEventListener("click", () => {
        sessionsPanel.classList.add("hidden");
        messagesEl.innerHTML = "";
        setBusy(true);
        showThinking();
        vscode.postMessage({ type: "resume_session", thread_id: row.thread_id });
      });
      sessionsList.appendChild(btn);
    });
  }

  // ── Send ──────────────────────────────────────────────────────────────────

  function send() {
    const text = inputEl.value.trim();
    if (!text || busy) return;
    inputEl.value = "";
    inputEl.style.height = "";
    addUserMsg(text);
    setBusy(true);
    showThinking();
    vscode.postMessage({ type: "task", message: text });
  }

  // ── New session ───────────────────────────────────────────────────────────

  function newSession() {
    messagesEl.innerHTML = "";
    thinkingEl = null; streamingMsgEl = null; streamingBubble = null;
    activeToolList = null; activeTool = null;
    setBusy(true);
    showThinking();
    vscode.postMessage({ type: "new_session" });
  }

  // ── Inbound messages ──────────────────────────────────────────────────────

  window.addEventListener("message", (e) => {
    const msg = e.data;
    switch (msg.type) {

      case "ready":
        removeThinking();
        finaliseStreaming();
        const divider = document.createElement("div");
        divider.className = "session-divider";
        divider.textContent = "session " + msg.session_id.slice(0, 8);
        messagesEl.appendChild(divider);
        setBusy(false);
        break;

      case "thinking":
        if (!thinkingEl) showThinking();
        setBusy(true);
        break;

      case "token":
        removeThinking();
        appendToken(msg.content);
        setBusy(true);
        break;

      case "tool_start":
        removeThinking();
        toolStart(msg.name, msg.summary || "");
        break;

      case "tool_end":
        toolEnd(msg.name, msg.ok !== false, msg.summary || "");
        break;

      case "response":
        removeThinking();
        finaliseStreaming();
        if (!streamingBubble) {
          // Full response without streaming
          const bubble = startAgentMsg();
          bubble.dataset.raw = msg.content;
        }
        finaliseStreaming();
        setBusy(false);
        break;

      case "interrupt":
        renderInterrupt(msg.action_requests);
        break;

      case "trace_url":
        const traceA = document.createElement("a");
        traceA.className = "trace-link";
        traceA.href = msg.url;
        traceA.textContent = "↗ View trace";
        messagesEl.appendChild(traceA);
        scrollBottom();
        break;

      case "error":
        removeThinking();
        finaliseStreaming();
        addError(msg.message.split("\n")[0].trim().slice(0, 140));
        if (/15432|postgres|ECONNREFUSED/i.test(msg.message)) {
          addSys("docker compose up -d");
        }
        setBusy(false);
        break;

      case "sessions":
        renderSessions(msg.rows);
        break;

      case "pong":
        break;
    }
  });

  // ── Event wiring ──────────────────────────────────────────────────────────

  btnSend.addEventListener("click", send);

  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  });

  inputEl.addEventListener("input", autoResize);

  btnNew.addEventListener("click", newSession);

  btnStartEmpty && btnStartEmpty.addEventListener("click", newSession);

  btnHistory.addEventListener("click", () => {
    sessionsPanel.classList.toggle("hidden");
    if (!sessionsPanel.classList.contains("hidden")) {
      vscode.postMessage({ type: "refresh_sessions" });
    }
  });

  btnCloseSession.addEventListener("click", () => {
    sessionsPanel.classList.add("hidden");
  });

  // ── Init ──────────────────────────────────────────────────────────────────
  vscode.postMessage({ type: "ready" });

})();
