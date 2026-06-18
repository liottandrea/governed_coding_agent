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
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const agentClient_1 = require("./agentClient");
const chatPanel_1 = require("./chatPanel");
const sessionTree_1 = require("./sessionTree");
function activate(context) {
    const outputChannel = vscode.window.createOutputChannel("UST Agent");
    const client = new agentClient_1.AgentClient(outputChannel);
    const sessionTree = new sessionTree_1.SessionTreeProvider(client);
    // Register session tree view
    const treeView = vscode.window.createTreeView("ust-agent.sessionView", {
        treeDataProvider: sessionTree,
        showCollapseAll: false,
    });
    // Start the subprocess as soon as a workspace is open
    const cwd = vscode.workspace.workspaceFolders?.[0]?.uri?.fsPath ?? process.cwd();
    client.start(cwd);
    client.send({ type: "sessions" }); // initial session list
    // ── Commands ───────────────────────────────────────────────────────────────
    context.subscriptions.push(vscode.commands.registerCommand("ust-agent.openPanel", () => {
        chatPanel_1.ChatPanel.createOrShow(client, context.extensionUri);
    }), vscode.commands.registerCommand("ust-agent.newSession", () => {
        const panel = chatPanel_1.ChatPanel.createOrShow(client, context.extensionUri);
        panel.startNewSession();
    }), vscode.commands.registerCommand("ust-agent.refreshSessions", () => {
        sessionTree.refresh();
    }), vscode.commands.registerCommand("ust-agent.resumeSession", (thread_id) => {
        const panel = chatPanel_1.ChatPanel.createOrShow(client, context.extensionUri);
        panel.resumeSession(thread_id);
    }), treeView, outputChannel, { dispose: () => client.dispose() });
}
function deactivate() { }
//# sourceMappingURL=extension.js.map