// @ts-nocheck
(function () {
  "use strict";

  const vscode = acquireVsCodeApi();

  // ── DOM refs ──────────────────────────────────────────────────────────────
  const chat = document.getElementById("chat");
  const msgInput = document.getElementById("msgInput");
  const btnSend = document.getElementById("btnSend");
  const btnNew = document.getElementById("btnNew");
  const sessionIdEl = document.getElementById("sessionId");
  const traceLink = document.getElementById("traceLink");

  const ctrlDataClass = document.getElementById("dataClass");
  const ctrlRole = document.getElementById("role");
  const ctrlPlannerModel = document.getElementById("plannerModel");
  const ctrlSubagentModel = document.getElementById("subagentModel");
  const ctrlKnowledge = document.getElementById("knowledge");
  const ctrlSystemPrompt = document.getElementById("systemPrompt");

  // ── State ─────────────────────────────────────────────────────────────────
  let busy = false;
  let pendingCards = []; // approval card DOM nodes for current interrupt
  let pendingDecisions = []; // collected decisions (filled as user clicks)
  let pendingTotal = 0;

  // ── Helpers ───────────────────────────────────────────────────────────────

  function scrollToBottom() {
    chat.scrollTop = chat.scrollHeight;
  }

  function setBusy(val) {
    busy = val;
    btnSend.disabled = val;
    msgInput.disabled = val;
    if (!val) msgInput.focus();
  }

  function getSettings() {
    return {
      data_class: ctrlDataClass.value,
      role: ctrlRole.value,
      plannerModel: ctrlPlannerModel.value,
      subagentModel: ctrlSubagentModel.value,
      include_knowledge: ctrlKnowledge.checked,
      system_prompt: ctrlSystemPrompt.value.trim(),
    };
  }

  // ── Render helpers ────────────────────────────────────────────────────────

  function appendBubble(cls, html) {
    const el = document.createElement("div");
    el.className = `bubble ${cls}`;
    el.innerHTML = html;
    chat.appendChild(el);
    scrollToBottom();
    return el;
  }

  /** Very light markdown → HTML: fenced code blocks and inline code only. */
  function renderMarkdown(text) {
    // fenced code blocks
    text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
      return `<pre><code>${escHtml(code.trim())}</code></pre>`;
    });
    // inline code
    text = text.replace(/`([^`]+)`/g, (_, code) => `<code>${escHtml(code)}</code>`);
    // preserve newlines
    text = text.replace(/\n/g, "<br>");
    return text;
  }

  function escHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function toolIcon(name) {
    const icons = { write_file: "✏️", execute: "⚡", read_file: "📄", glob: "🔍", grep: "🔍" };
    return icons[name] || "🔧";
  }

  // ── Approval card rendering ───────────────────────────────────────────────

  function renderInterrupt(actionRequests) {
    pendingCards = [];
    pendingDecisions = new Array(actionRequests.length).fill(null);
    pendingTotal = actionRequests.length;

    actionRequests.forEach((req, idx) => {
      const card = document.createElement("div");
      card.className = "approval-card";

      const argsText = JSON.stringify(req.args, null, 2);
      let bodyHtml = "";

      if (req.name === "write_file") {
        const filePath = req.args.file_path || "?";
        const lines = (req.args.content || "").split("\n").length;
        bodyHtml = `<div>→ <strong>${escHtml(String(filePath))}</strong> (${lines} lines)</div>`;
      } else if (req.name === "execute") {
        bodyHtml = `<div>→ <code>${escHtml(String(req.args.command || "?"))}</code></div>`;
      }

      card.innerHTML = `
        <div class="card-header">
          <span class="tool-icon">${toolIcon(req.name)}</span>
          <span>${escHtml(req.name)}</span>
        </div>
        <div class="card-body">
          ${bodyHtml}
          <details>
            <summary>Show arguments</summary>
            <pre class="args">${escHtml(argsText)}</pre>
          </details>
        </div>
        <div class="card-actions" id="actions-${idx}">
          <button class="btn-reject" id="reject-${idx}">Reject ✕</button>
          <button class="btn-approve" id="approve-${idx}">Approve ✓</button>
        </div>
      `;

      chat.appendChild(card);
      pendingCards.push(card);

      document.getElementById(`approve-${idx}`).addEventListener("click", () => recordDecision(idx, true));
      document.getElementById(`reject-${idx}`).addEventListener("click", () => recordDecision(idx, false));
    });

    scrollToBottom();
  }

  function recordDecision(idx, approved) {
    pendingDecisions[idx] = approved ? { type: "approve" } : { type: "reject" };

    // Disable buttons on this card and show badge
    const actionsEl = document.getElementById(`actions-${idx}`);
    const badge = document.createElement("span");
    badge.className = `decision-badge ${approved ? "approved" : "rejected"}`;
    badge.textContent = approved ? "✓ Approved" : "✕ Rejected";
    actionsEl.innerHTML = "";
    actionsEl.appendChild(badge);

    // Check if all decisions collected
    if (pendingDecisions.every((d) => d !== null)) {
      vscode.postMessage({ type: "decision", decisions: pendingDecisions });
      pendingCards = [];
      pendingDecisions = [];
      pendingTotal = 0;
      setBusy(true); // back to busy while agent continues
    }
  }

  // ── Send message ──────────────────────────────────────────────────────────

  function sendMessage() {
    const text = msgInput.value.trim();
    if (!text || busy) return;
    msgInput.value = "";

    appendBubble("user", escHtml(text));
    setBusy(true);
    vscode.postMessage({ type: "task", message: text });
  }

  // ── Inbound messages from extension ──────────────────────────────────────

  window.addEventListener("message", (e) => {
    const msg = e.data;
    switch (msg.type) {
      case "ready":
        sessionIdEl.textContent = `Session: ${msg.session_id.slice(0, 8)}…`;
        traceLink.style.display = "none";
        setBusy(false);
        break;

      case "thinking":
        appendBubble("thinking", "⏳ Thinking…");
        setBusy(true);
        break;

      case "response":
        // Remove last "thinking" bubble if present
        const last = chat.querySelector(".bubble.thinking:last-child");
        if (last) last.remove();
        appendBubble("agent", renderMarkdown(msg.content));
        setBusy(false);
        break;

      case "interrupt":
        // Remove "thinking" bubble
        const th = chat.querySelector(".bubble.thinking:last-child");
        if (th) th.remove();
        renderInterrupt(msg.action_requests);
        setBusy(false); // user needs to click approve/reject
        break;

      case "trace_url":
        traceLink.href = msg.url;
        traceLink.style.display = "inline";
        break;

      case "sessions":
        // Sessions are handled by the sidebar tree — nothing to do in webview
        break;

      case "error":
        const ethinking = chat.querySelector(".bubble.thinking:last-child");
        if (ethinking) ethinking.remove();
        appendBubble("error", `⚠ ${escHtml(msg.message)}`);
        setBusy(false);
        break;
    }
  });

  // ── Event wiring ──────────────────────────────────────────────────────────

  btnSend.addEventListener("click", sendMessage);

  msgInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  btnNew.addEventListener("click", () => {
    chat.innerHTML = "";
    traceLink.style.display = "none";
    sessionIdEl.textContent = "Starting new session…";
    vscode.postMessage({ type: "newSession" });
    setBusy(true);
  });

  // Notify extension whenever a control changes
  [ctrlDataClass, ctrlRole, ctrlPlannerModel, ctrlSubagentModel, ctrlKnowledge, ctrlSystemPrompt].forEach((el) => {
    el.addEventListener("change", () => {
      vscode.postMessage({ type: "settingsChanged", settings: getSettings() });
    });
  });

  // ── Init ──────────────────────────────────────────────────────────────────
  // Trigger a new session automatically on first load
  sessionIdEl.textContent = "Starting session…";
  setBusy(true);
  vscode.postMessage({ type: "newSession" });
})();
