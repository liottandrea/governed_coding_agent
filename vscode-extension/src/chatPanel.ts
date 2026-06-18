import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";
import { AgentClient } from "./agentClient";
import {
  WebviewSettings,
  WebviewToExtension,
  ExtensionToWebview,
  ActionRequest,
} from "./types";

const DEFAULT_SETTINGS: WebviewSettings = {
  data_class: "internal",
  role: "planner",
  plannerModel: "mid",
  subagentModel: "cheap",
  include_knowledge: true,
  system_prompt: "",
};

export class ChatPanel {
  public static currentPanel: ChatPanel | undefined;
  private readonly panel: vscode.WebviewPanel;
  private readonly client: AgentClient;
  private readonly extensionUri: vscode.Uri;
  private settings: WebviewSettings = { ...DEFAULT_SETTINGS };
  // Pending interrupt: collect one decision per action_request
  private pendingRequests: ActionRequest[] = [];
  private decisions: Array<{ type: "approve" } | { type: "reject"; message?: string }> = [];

  private constructor(
    panel: vscode.WebviewPanel,
    client: AgentClient,
    extensionUri: vscode.Uri
  ) {
    this.panel = panel;
    this.client = client;
    this.extensionUri = extensionUri;

    this.panel.webview.html = this._getHtml();

    // Forward agent events to the webview
    this.client.onEvent((event) => {
      const msg: ExtensionToWebview = event as ExtensionToWebview;
      this.panel.webview.postMessage(msg);
    });

    // Handle messages from the webview
    this.panel.webview.onDidReceiveMessage((msg: WebviewToExtension) => {
      this._handleWebviewMessage(msg);
    });

    this.panel.onDidDispose(() => {
      ChatPanel.currentPanel = undefined;
    });
  }

  static createOrShow(client: AgentClient, extensionUri: vscode.Uri): ChatPanel {
    const column = vscode.window.activeTextEditor?.viewColumn
      ? vscode.ViewColumn.Beside
      : vscode.ViewColumn.One;

    if (ChatPanel.currentPanel) {
      ChatPanel.currentPanel.panel.reveal(column);
      return ChatPanel.currentPanel;
    }

    const panel = vscode.window.createWebviewPanel(
      "ustAgentChat",
      "UST Agent",
      column,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [vscode.Uri.joinPath(extensionUri, "webview")],
      }
    );

    ChatPanel.currentPanel = new ChatPanel(panel, client, extensionUri);
    return ChatPanel.currentPanel;
  }

  private _handleWebviewMessage(msg: WebviewToExtension): void {
    switch (msg.type) {
      case "settingsChanged":
        this.settings = msg.settings;
        break;

      case "newSession":
        this._startSession(undefined);
        break;

      case "resumeSession":
        this._startSession(msg.thread_id);
        break;

      case "task":
        this.client.send({ type: "task", message: msg.message });
        break;

      case "decision": {
        const decision =
          msg.approved
            ? { type: "approve" as const }
            : { type: "reject" as const, message: msg.reason };
        this.decisions[msg.index] = decision;

        // Once all pending requests have a decision, send them
        if (
          this.pendingRequests.length > 0 &&
          this.decisions.filter(Boolean).length === this.pendingRequests.length
        ) {
          this.client.send({ type: "decision", decisions: this.decisions });
          this.pendingRequests = [];
          this.decisions = [];
        }
        break;
      }

      case "refreshSessions":
        this.client.send({ type: "sessions" });
        break;
    }
  }

  private _startSession(thread_id?: string): void {
    const cwd =
      vscode.workspace.workspaceFolders?.[0]?.uri?.fsPath ?? process.cwd();

    if (!this.client.isRunning()) {
      this.client.start(cwd);
    }

    this.client.send({
      type: "start",
      thread_id,
      data_class: this.settings.data_class,
      role: this.settings.role,
      group_overrides: {
        planner: this.settings.plannerModel,
        codegen: this.settings.subagentModel,
        knowledge_retrieval: this.settings.subagentModel,
        summary: this.settings.subagentModel,
        testing: this.settings.subagentModel,
      },
      system_prompt: this.settings.system_prompt || undefined,
      include_knowledge: this.settings.include_knowledge,
      cwd,
    });

    // Also refresh sessions list
    this.client.send({ type: "sessions" });
  }

  startNewSession(): void {
    this._startSession(undefined);
  }

  resumeSession(thread_id: string): void {
    this._startSession(thread_id);
    this.panel.reveal();
  }

  private _getHtml(): string {
    const webviewDir = path.join(this.extensionUri.fsPath, "webview");
    const htmlPath = path.join(webviewDir, "index.html");

    let html = fs.readFileSync(htmlPath, "utf-8");

    // Replace resource URIs so webview can load local CSS/JS
    const cssUri = this.panel.webview.asWebviewUri(
      vscode.Uri.joinPath(this.extensionUri, "webview", "chat.css")
    );
    const jsUri = this.panel.webview.asWebviewUri(
      vscode.Uri.joinPath(this.extensionUri, "webview", "chat.js")
    );
    html = html
      .replace("{{CSS_URI}}", cssUri.toString())
      .replace("{{JS_URI}}", jsUri.toString());

    return html;
  }
}
