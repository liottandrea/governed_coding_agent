"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.ChatPanel = void 0;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const DEFAULT_SETTINGS = {
    data_class: "internal",
    role: "planner",
    plannerModel: "mid",
    subagentModel: "cheap",
    include_knowledge: true,
    system_prompt: "",
};
class ChatPanel {
    constructor(panel, client, extensionUri) {
        this.settings = { ...DEFAULT_SETTINGS };
        // Pending interrupt: collect one decision per action_request
        this.pendingRequests = [];
        this.decisions = [];
        this.panel = panel;
        this.client = client;
        this.extensionUri = extensionUri;
        this.panel.webview.html = this._getHtml();
        // Forward agent events to the webview
        this.client.onEvent((event) => {
            const msg = event;
            this.panel.webview.postMessage(msg);
        });
        // Handle messages from the webview
        this.panel.webview.onDidReceiveMessage((msg) => {
            this._handleWebviewMessage(msg);
        });
        this.panel.onDidDispose(() => {
            ChatPanel.currentPanel = undefined;
        });
    }
    static createOrShow(client, extensionUri) {
        const column = vscode.window.activeTextEditor?.viewColumn
            ? vscode.ViewColumn.Beside
            : vscode.ViewColumn.One;
        if (ChatPanel.currentPanel) {
            ChatPanel.currentPanel.panel.reveal(column);
            return ChatPanel.currentPanel;
        }
        const panel = vscode.window.createWebviewPanel("ustAgentChat", "UST Agent", column, {
            enableScripts: true,
            retainContextWhenHidden: true,
            localResourceRoots: [vscode.Uri.joinPath(extensionUri, "webview")],
        });
        ChatPanel.currentPanel = new ChatPanel(panel, client, extensionUri);
        return ChatPanel.currentPanel;
    }
    _handleWebviewMessage(msg) {
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
                const decision = msg.approved
                    ? { type: "approve" }
                    : { type: "reject", message: msg.reason };
                this.decisions[msg.index] = decision;
                // Once all pending requests have a decision, send them
                if (this.pendingRequests.length > 0 &&
                    this.decisions.filter(Boolean).length === this.pendingRequests.length) {
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
    _startSession(thread_id) {
        const cwd = vscode.workspace.workspaceFolders?.[0]?.uri?.fsPath ?? process.cwd();
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
    startNewSession() {
        this._startSession(undefined);
    }
    resumeSession(thread_id) {
        this._startSession(thread_id);
        this.panel.reveal();
    }
    _getHtml() {
        const webviewDir = path.join(this.extensionUri.fsPath, "webview");
        const htmlPath = path.join(webviewDir, "index.html");
        let html = fs.readFileSync(htmlPath, "utf-8");
        // Replace resource URIs so webview can load local CSS/JS
        const cssUri = this.panel.webview.asWebviewUri(vscode.Uri.joinPath(this.extensionUri, "webview", "chat.css"));
        const jsUri = this.panel.webview.asWebviewUri(vscode.Uri.joinPath(this.extensionUri, "webview", "chat.js"));
        html = html
            .replace("{{CSS_URI}}", cssUri.toString())
            .replace("{{JS_URI}}", jsUri.toString());
        return html;
    }
}
exports.ChatPanel = ChatPanel;
//# sourceMappingURL=chatPanel.js.map