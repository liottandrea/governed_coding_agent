/**
 * agentTerminal.ts
 *
 * Keyboard reference
 * ──────────────────
 *  Enter          Submit the current buffer as a task
 *  Alt+Enter      Insert a literal newline in the buffer (multi-line tasks)
 *  Backspace      Delete last character
 *  Up / Down      Walk input history (most-recent first)
 *  Ctrl+C         Cancel a running task; clear the buffer if idle
 *  Ctrl+L         Clear screen and redraw the header
 *  /new           Start a fresh session (can also type as a command)
 *  /clear         Alias for Ctrl+L
 *
 * HITL approval prompt
 * ────────────────────
 *  Y  or  Enter   Approve all pending actions
 *  n              Reject all
 *  1,3            Comma-separated indices to reject; the rest are approved
 */

import * as vscode from "vscode";
import { AgentClient } from "./agentClient";
import { AgentEvent, ActionRequest, DataClass, Role, ModelGroup } from "./types";

// ── ANSI helpers ──────────────────────────────────────────────────────────────

const C = {
  reset:     "\x1b[0m",
  bold:      "\x1b[1m",
  dim:       "\x1b[2m",
  green:     "\x1b[32m",
  yellow:    "\x1b[33m",
  red:       "\x1b[31m",
  cyan:      "\x1b[36m",
  gray:      "\x1b[90m",
  crlf:      "\r\n",
  clearLine: "\r\x1b[K",
  cursorUp:  "\x1b[1A",
  clearScr:  "\x1b[2J\x1b[H",
} as const;

const SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏".split("");

// ── Pure renderer ─────────────────────────────────────────────────────────────

class Renderer {
  private w: (s: string) => void;
  private cols = 80;
  private spinTimer: ReturnType<typeof setInterval> | null = null;
  private spinFrame = 0;
  private spinLabel = "";
  private toolBlockActive = false;

  constructor(write: (s: string) => void) {
    this.w = write;
  }

  setDimensions(cols: number, _rows: number): void {
    this.cols = cols;
  }

  private ln(s = ""): void { this.w(s + C.crlf); }

  private rule(): void {
    this.ln(C.gray + "  " + "─".repeat(Math.max(Math.min(this.cols - 6, 60), 10)) + C.reset);
  }

  // ── Screen ────────────────────────────────────────────────────────────────

  clearScreen(): void { this.w(C.clearScr); }

  welcome(): void {
    this.ln();
    this.ln(C.bold + C.cyan + "  Governed Coding Agent" + C.reset);
    this.ln(
      C.gray +
      "  Enter ↵ submit  ·  Alt+Enter newline  ·  ↑↓ history  ·  Ctrl+C cancel" +
      C.reset,
    );
    this.ln();
  }

  sessionHeader(id: string): void {
    this.rule();
    this.ln(C.gray + "  session " + id.slice(0, 8) + C.reset);
    this.rule();
    this.ln();
  }

  // ── Input prompt ──────────────────────────────────────────────────────────

  /** Overwrite the current line with a fresh prompt + buffer. */
  prompt(buf: string): void {
    this.w(C.clearLine + C.bold + C.cyan + "  ❯ " + C.reset + buf);
  }

  /** Called on Enter — move past the typed line without erasing it. */
  endInputLine(): void { this.w(C.crlf); }

  // ── Spinner ───────────────────────────────────────────────────────────────

  startSpinner(label: string): void {
    this.stopSpinner();
    this.spinLabel = label;
    this.spinFrame = 0;
    this.w(C.gray + "  " + SPINNER_FRAMES[0] + "  " + label + "…" + C.reset);
    this.spinTimer = setInterval(() => {
      this.spinFrame = (this.spinFrame + 1) % SPINNER_FRAMES.length;
      this.w(
        C.clearLine +
        C.gray + "  " + SPINNER_FRAMES[this.spinFrame] + "  " + this.spinLabel + "…" + C.reset,
      );
    }, 80);
  }

  stopSpinner(): void {
    const was = this.spinTimer !== null;
    if (this.spinTimer) { clearInterval(this.spinTimer); this.spinTimer = null; }
    if (was) this.w(C.clearLine);
  }

  // ── Tool call blocks ──────────────────────────────────────────────────────

  toolStart(name: string, summary: string): void {
    this.stopSpinner();
    this.ln(
      C.gray + "  ├─ " + C.reset +
      C.cyan + name + C.reset +
      C.dim + "  " + summary + C.reset,
    );
    this.toolBlockActive = true;
    this.startSpinner("running");
  }

  /**
   * Collapse the active tool block (2 lines: label + spinner) into a
   * single-line badge using ANSI line-erase codes.
   */
  toolEnd(name: string, ok: boolean, summary: string): void {
    const was = this.spinTimer !== null;
    if (this.spinTimer) { clearInterval(this.spinTimer); this.spinTimer = null; }
    if (was) this.w(C.clearLine);                    // clear spinner line
    if (this.toolBlockActive) {
      this.w(C.cursorUp + C.clearLine);              // move up + clear tool label
      this.toolBlockActive = false;
    }
    const ico = ok ? C.green + "  ✓" : C.red + "  ✗";
    this.ln(ico + C.reset + C.dim + "  " + name + (summary ? "  " + summary : "") + C.reset);
  }

  // ── Response ──────────────────────────────────────────────────────────────

  response(text: string): void {
    let code = false;
    for (const raw of text.split("\n")) {
      if (raw.startsWith("```")) {
        code = !code;
        const lang = raw.slice(3).trim();
        this.ln(C.gray + (code ? "  ┌─" + (lang ? " " + lang : "") : "  └─") + C.reset);
        continue;
      }
      if (code) { this.ln(C.gray + "  │ " + C.reset + raw); continue; }
      const fmt = raw
        .replace(/\*\*([^*\n]+)\*\*/g, C.bold + "$1" + C.reset)
        .replace(/`([^`\n]+)`/g,        C.cyan + "$1" + C.reset);
      this.ln("  " + fmt);
    }
    this.ln();
  }

  // ── HITL ──────────────────────────────────────────────────────────────────

  hitlPrompt(requests: ActionRequest[]): void {
    this.ln();
    this.rule();
    this.ln(
      C.yellow + C.bold + "  Approval required" + C.reset +
      C.gray + "  (" + requests.length + " action" + (requests.length !== 1 ? "s" : "") + ")" + C.reset,
    );
    this.ln();
    requests.forEach((r, i) => {
      let detail: string;
      if (r.name === "write_file") {
        const fp    = String(r.args.file_path ?? "?");
        const lines = String(r.args.content ?? "").split("\n").length;
        detail = fp + C.dim + "  (" + lines + " lines)" + C.reset;
      } else if (r.name === "execute") {
        detail = String(r.args.command ?? "?").slice(0, 72);
      } else {
        detail = JSON.stringify(r.args).slice(0, 72);
      }
      this.ln(
        C.cyan + `  [${i + 1}] ` + C.reset +
        C.bold + r.name + C.reset +
        C.gray + "  " + detail + C.reset,
      );
    });
    this.ln();
    this.w(C.gray + "  Approve all [Y/↵]  ·  reject all [n]  ·  reject specific [1,2…]:  " + C.reset);
  }

  hitlResult(approved: boolean, rejected?: number[]): void {
    this.w(C.crlf);
    if (approved) {
      this.ln(C.green + "  ✓ Approved" + C.reset);
    } else if (rejected?.length) {
      this.ln(C.yellow + "  ✗ Rejected [" + rejected.join(", ") + "]" + C.reset);
    } else {
      this.ln(C.red + "  ✗ Rejected all" + C.reset);
    }
    this.ln();
  }

  // ── Misc ──────────────────────────────────────────────────────────────────

  error(msg: string): void {
    // Show only the first meaningful line; Postgres errors are extremely verbose
    const first = msg.split("\n").map((l) => l.trim()).find((l) => l.length > 0) ?? msg;
    const display = first.length > 110 ? first.slice(0, 107) + "…" : first;
    this.ln();
    this.ln(C.red + "  ✗  " + display + C.reset);
    if (/Connection refused|ECONNREFUSED|15432|postgres/i.test(msg)) {
      this.ln(C.gray + "  ↳ Start Docker:  docker compose up -d" + C.reset);
    }
    this.ln();
  }

  cancel(): void {
    this.w(C.clearLine);
    this.ln(C.yellow + "  ↩ Cancelled" + C.reset);
    this.ln();
  }

  traceUrl(url: string): void {
    this.ln(C.dim + C.gray + "  ↗ " + url + C.reset);
  }

  dispose(): void {
    if (this.spinTimer) { clearInterval(this.spinTimer); this.spinTimer = null; }
  }
}

// ── Pseudoterminal ────────────────────────────────────────────────────────────

type PtyState = "idle" | "prompt" | "busy" | "hitl";

export class AgentTerminalPty implements vscode.Pseudoterminal {
  private readonly _write      = new vscode.EventEmitter<string>();
  private readonly _close      = new vscode.EventEmitter<void | number>();
  private readonly _nameChange = new vscode.EventEmitter<string>();

  readonly onDidWrite      = this._write.event;
  readonly onDidClose      = this._close.event;
  readonly onDidChangeName = this._nameChange.event;

  private readonly r: Renderer;
  private state: PtyState = "idle";
  private buf        = "";
  private hitlBuf    = "";
  private history: string[] = [];
  private histIdx    = -1;
  private pendingHitl: ActionRequest[] = [];
  private sessionId  = "";
  private evtSub: vscode.Disposable | undefined;

  constructor(
    private readonly client: AgentClient,
    private readonly outputChannel: vscode.OutputChannel,
  ) {
    this.r = new Renderer((s) => this._write.fire(s));
  }

  // ── PTY lifecycle ─────────────────────────────────────────────────────────

  open(dims: vscode.TerminalDimensions | undefined): void {
    if (dims) this.r.setDimensions(dims.columns, dims.rows);
    this.r.welcome();

    // Subscribe to agent events (disposable so close() can unsubscribe)
    this.evtSub = this.client.onEvent((ev) => this.onAgentEvent(ev));

    const cwd = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? process.cwd();
    if (!this.client.isRunning()) this.client.start(cwd);

    // Don't auto-start a session here — startNewSession() or resumeSession() handle that.
    // openTerminal just shows the prompt; newSession command calls startNewSession() explicitly.
    this.toPrompt();
  }

  close(): void {
    this.evtSub?.dispose();
    this.r.dispose();
  }

  setDimensions(dims: vscode.TerminalDimensions): void {
    this.r.setDimensions(dims.columns, dims.rows);
  }

  // ── Agent event → terminal output ─────────────────────────────────────────

  private onAgentEvent(ev: AgentEvent): void {
    switch (ev.type) {
      case "pong": break;

      case "ready":
        this.sessionId = ev.session_id;
        this.r.stopSpinner();
        this.r.sessionHeader(ev.session_id);
        this._nameChange.fire("Governed Coding Agent · " + ev.session_id.slice(0, 8));
        this.toPrompt();
        break;

      case "thinking":
        this.state = "busy";
        this.r.startSpinner("Thinking");
        break;

      case "response":
        this.r.stopSpinner();
        this.r.response(ev.content);
        this.client.send({ type: "sessions" }); // refresh sidebar after each turn
        this.toPrompt();
        break;

      case "interrupt":
        this.r.stopSpinner();
        this.pendingHitl = ev.action_requests;
        this.hitlBuf = "";
        this.state = "hitl";
        this.r.hitlPrompt(ev.action_requests);
        break;

      case "trace_url":
        this.r.traceUrl(ev.url);
        this.outputChannel.appendLine("[trace] " + ev.url);
        break;

      case "error":
        this.r.stopSpinner();
        this.r.error(ev.message);
        this.toPrompt();
        break;

      case "sessions":
        break; // forwarded to sidebar by extension.ts
    }
  }

  // ── Input handling ────────────────────────────────────────────────────────

  handleInput(data: string): void {
    if (data === "\x03") { this.ctrlC(); return; }     // Ctrl+C
    if (data === "\x0c") { this.ctrlL(); return; }     // Ctrl+L

    if (this.state === "busy") return;
    if (this.state === "hitl") { this.handleHitlKey(data); return; }

    // Prompt mode
    if (data === "\r")     { this.submit(); return; }
    if (data === "\x1b\r") { this.insertNewline(); return; }  // Alt+Enter
    if (data === "\x7f")   { this.backspace(); return; }
    if (data === "\x1b[A") { this.histUp(); return; }
    if (data === "\x1b[B") { this.histDown(); return; }
    if (data.startsWith("\x1b")) return;               // other escape seqs — ignore

    // Printable characters (handles pastes too)
    const printable = [...data].filter((c) => c.charCodeAt(0) >= 0x20).join("");
    if (printable) {
      this.buf += printable;
      this._write.fire(printable);
    }
  }

  private submit(): void {
    const text = this.buf.trim();
    this.buf = "";
    if (!text) return;

    // Built-in slash commands
    if (text === "/clear" || text === "/cls") { this.ctrlL(); return; }
    if (text === "/new") { this.startNewSession(); return; }

    this.history.unshift(text);
    this.histIdx = -1;
    this.r.endInputLine();
    this.state = "busy";
    this.r.startSpinner("Thinking");
    this.client.send({ type: "task", message: text });
  }

  private insertNewline(): void {
    this.buf += "\n";
    this._write.fire("\r\n  ");
  }

  private backspace(): void {
    if (!this.buf.length) return;
    this.buf = this.buf.slice(0, -1);
    this.r.prompt(this.buf);
  }

  private ctrlC(): void {
    if (this.state === "busy") this.r.cancel();
    this.buf = "";
    this.state = "prompt";
    this.r.prompt("");
  }

  private ctrlL(): void {
    this.r.clearScreen();
    this.r.welcome();
    if (this.state === "prompt") this.r.prompt(this.buf);
  }

  private histUp(): void {
    if (!this.history.length) return;
    this.histIdx = Math.min(this.histIdx + 1, this.history.length - 1);
    this.buf = this.history[this.histIdx];
    this.r.prompt(this.buf);
  }

  private histDown(): void {
    if (this.histIdx <= 0) { this.histIdx = -1; this.buf = ""; this.r.prompt(""); return; }
    this.histIdx--;
    this.buf = this.history[this.histIdx];
    this.r.prompt(this.buf);
  }

  private toPrompt(): void {
    this.state = "prompt";
    this.buf = "";
    this.r.prompt("");
  }

  // ── HITL ──────────────────────────────────────────────────────────────────

  private handleHitlKey(data: string): void {
    if (data === "\r") { this.resolveHitl(); return; }
    if (data === "\x7f") { this.hitlBuf = this.hitlBuf.slice(0, -1); this._write.fire("\b \b"); return; }
    const ch = data.length === 1 && data.charCodeAt(0) >= 0x20 ? data : "";
    if (ch) { this.hitlBuf += ch; this._write.fire(ch); }
  }

  private resolveHitl(): void {
    const raw = this.hitlBuf.trim().toLowerCase();
    const n   = this.pendingHitl.length;

    let decisions: Array<{ type: "approve" } | { type: "reject" }>;

    if (raw === "" || raw === "y") {
      decisions = this.pendingHitl.map(() => ({ type: "approve" as const }));
      this.r.hitlResult(true);
    } else if (raw === "n") {
      decisions = this.pendingHitl.map(() => ({ type: "reject" as const }));
      this.r.hitlResult(false);
    } else {
      const rej = raw.split(/[,\s]+/).map(Number).filter((x) => x >= 1 && x <= n);
      decisions = this.pendingHitl.map((_, i) =>
        rej.includes(i + 1) ? { type: "reject" as const } : { type: "approve" as const },
      );
      this.r.hitlResult(false, rej);
    }

    this.state = "busy";
    this.pendingHitl = [];
    this.hitlBuf = "";
    this.r.startSpinner("Continuing");
    this.client.send({ type: "decision", decisions });
  }

  // ── Public API ────────────────────────────────────────────────────────────

  startNewSession(): void {
    const cwd = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? process.cwd();
    if (!this.client.isRunning()) this.client.start(cwd);
    this.state = "busy";
    this.buf = "";
    this.r.startSpinner("Starting");
    this.sendStart(undefined, cwd);
  }

  resumeSession(threadId: string): void {
    const cwd = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? process.cwd();
    if (!this.client.isRunning()) this.client.start(cwd);
    this.state = "busy";
    this.buf = "";
    this.r.startSpinner("Resuming");
    this.sendStart(threadId, cwd);
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  private sendStart(threadId: string | undefined, cwd: string): void {
    const s = this.settings();
    this.client.send({
      type:             "start",
      thread_id:        threadId,
      data_class:       s.dataClass,
      role:             s.role,
      include_knowledge: s.includeKnowledge,
      group_overrides:  {
        planner:             s.plannerModel,
        codegen:             s.subagentModel,
        knowledge_retrieval: s.subagentModel,
        summary:             s.subagentModel,
        testing:             s.subagentModel,
      },
      cwd,
    });
  }

  private settings() {
    const cfg = vscode.workspace.getConfiguration("governedCodingAgent");
    return {
      dataClass:        (cfg.get<string>("dataClass")      ?? "internal") as DataClass,
      role:             (cfg.get<string>("role")           ?? "planner")  as Role,
      plannerModel:     (cfg.get<string>("plannerModel")   ?? "mid")      as ModelGroup,
      subagentModel:    (cfg.get<string>("subagentModel")  ?? "cheap")    as ModelGroup,
      includeKnowledge: cfg.get<boolean>("includeKnowledge") ?? true,
    };
  }
}
