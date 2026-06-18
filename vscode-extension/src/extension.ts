import * as vscode from "vscode";
import { AgentClient } from "./agentClient";
import { ChatPanel } from "./chatPanel";
import { SessionTreeProvider } from "./sessionTree";

export function activate(context: vscode.ExtensionContext): void {
  const outputChannel = vscode.window.createOutputChannel("UST Agent");
  const client = new AgentClient(outputChannel);
  const sessionTree = new SessionTreeProvider(client);

  // Register session tree view
  const treeView = vscode.window.createTreeView("ust-agent.sessionView", {
    treeDataProvider: sessionTree,
    showCollapseAll: false,
  });

  // Start the subprocess as soon as a workspace is open
  const cwd =
    vscode.workspace.workspaceFolders?.[0]?.uri?.fsPath ?? process.cwd();
  client.start(cwd);
  client.send({ type: "sessions" }); // initial session list

  // ── Commands ───────────────────────────────────────────────────────────────

  context.subscriptions.push(
    vscode.commands.registerCommand("ust-agent.openPanel", () => {
      ChatPanel.createOrShow(client, context.extensionUri);
    }),

    vscode.commands.registerCommand("ust-agent.newSession", () => {
      const panel = ChatPanel.createOrShow(client, context.extensionUri);
      panel.startNewSession();
    }),

    vscode.commands.registerCommand("ust-agent.refreshSessions", () => {
      sessionTree.refresh();
    }),

    vscode.commands.registerCommand(
      "ust-agent.resumeSession",
      (thread_id: string) => {
        const panel = ChatPanel.createOrShow(client, context.extensionUri);
        panel.resumeSession(thread_id);
      }
    ),

    treeView,
    outputChannel,
    { dispose: () => client.dispose() }
  );
}

export function deactivate(): void {}
