import * as vscode from "vscode";
import { AgentClient } from "./agentClient";
import { DataClass, Role, ModelGroup, AgentEvent } from "./types";

export class ChatViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "ust-agent.chatView";

  private view?: vscode.WebviewView;
  private cwd: string;

  constructor(
    private readonly extensionUri: vscode.Uri,
    private readonly client: AgentClient,
    private readonly out: vscode.OutputChannel,
  ) {
    this.cwd = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? process.cwd();
    client.onEvent((ev: AgentEvent) => {
      this.view?.webview.postMessage(ev);
    });
  }

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _ctx: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken,
  ): void {
    this.view = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this.extensionUri, "webview")],
    };
    webviewView.webview.html = this.buildHtml(webviewView.webview);

    webviewView.webview.onDidReceiveMessage((msg) => {
      switch (msg.type) {
        case "ready":
          if (!this.client.isRunning()) this.client.start(this.cwd);
          this.client.send({ type: "sessions" });
          break;
        case "new_session":
          this.sendStart(undefined);
          break;
        case "resume_session":
          this.sendStart(msg.thread_id as string);
          break;
        case "task":
          this.client.send({ type: "task", message: msg.message as string });
          break;
        case "decision":
          this.client.send({ type: "decision", decisions: msg.decisions });
          break;
        case "refresh_sessions":
          if (this.client.isRunning()) this.client.send({ type: "sessions" });
          break;
      }
    });
  }

  startNewSession(): void { this.sendStart(undefined); }
  resumeSession(threadId: string): void { this.sendStart(threadId); }

  private sendStart(threadId: string | undefined): void {
    if (!this.client.isRunning()) this.client.start(this.cwd);
    const cfg = vscode.workspace.getConfiguration("ustAgent");
    const sub = (cfg.get<string>("subagentModel") ?? "cheap") as ModelGroup;
    this.client.send({
      type:              "start",
      thread_id:         threadId,
      data_class:        (cfg.get<string>("dataClass")      ?? "internal") as DataClass,
      role:              (cfg.get<string>("role")            ?? "planner")  as Role,
      include_knowledge: cfg.get<boolean>("includeKnowledge") ?? true,
      group_overrides: {
        planner:             (cfg.get<string>("plannerModel") ?? "mid") as ModelGroup,
        codegen:             sub,
        knowledge_retrieval: sub,
        summary:             sub,
        testing:             sub,
      },
      cwd: this.cwd,
    });
  }

  private buildHtml(webview: vscode.Webview): string {
    const cssUri = webview.asWebviewUri(vscode.Uri.joinPath(this.extensionUri, "webview", "chat.css"));
    const jsUri  = webview.asWebviewUri(vscode.Uri.joinPath(this.extensionUri, "webview", "chat.js"));
    const nonce  = Array.from({ length: 32 }, () =>
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"[Math.floor(Math.random() * 62)]
    ).join("");

    return [
      "<!DOCTYPE html>",
      '<html lang="en">',
      "<head>",
      '  <meta charset="UTF-8">',
      '  <meta name="viewport" content="width=device-width,initial-scale=1.0">',
      `  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">`,
      `  <link rel="stylesheet" href="${cssUri}">`,
      "  <title>UST Agent</title>",
      "</head>",
      "<body>",
      '  <div id="app">',
      '    <header id="header">',
      '      <span class="brand">',
      '        <svg class="brand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">',
      '          <rect x="3" y="7" width="18" height="13" rx="2.5"/>',
      '          <line x1="12" y1="7" x2="12" y2="4"/>',
      '          <circle cx="12" cy="3" r="1.2" fill="currentColor" stroke="none"/>',
      '          <rect x="7" y="10.5" width="3" height="3" rx="0.8" fill="currentColor" stroke="none"/>',
      '          <rect x="14" y="10.5" width="3" height="3" rx="0.8" fill="currentColor" stroke="none"/>',
      '          <line x1="8.5" y1="16" x2="11" y2="16"/>',
      '          <line x1="13" y1="16" x2="15.5" y2="16"/>',
      "        </svg>",
      '        <span class="brand-name">UST Agent</span>',
      "      </span>",
      '      <div class="header-actions">',
      '        <button id="btn-new" class="icon-btn" title="New chat">+</button>',
      '        <button id="btn-history" class="icon-btn" title="Session history">&#x29d6;</button>',
      "      </div>",
      "    </header>",
      '    <div id="sessions-panel" class="hidden">',
      '      <div id="sessions-header">',
      "        <span>Recent sessions</span>",
      '        <button id="btn-close-sessions" class="icon-btn small">&#x2715;</button>',
      "      </div>",
      '      <div id="sessions-list"></div>',
      "    </div>",
      '    <div id="messages" role="log" aria-live="polite">',
      '      <div class="empty-state">',
      "        <p>Start a new chat or resume a past session.</p>",
      '        <button id="btn-start-empty" class="primary-btn">New chat</button>',
      "      </div>",
      "    </div>",
      '    <div id="input-row">',
      '      <textarea id="input" placeholder="Message UST Agent…" rows="1" aria-label="Message"></textarea>',
      '      <button id="btn-send" title="Send">↑</button>',
      "    </div>",
      "  </div>",
      `  <script nonce="${nonce}" src="${jsUri}"></script>`,
      "</body>",
      "</html>",
    ].join("\n");
  }
}
