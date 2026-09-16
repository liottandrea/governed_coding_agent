import * as vscode from "vscode";
import { AgentClient } from "./agentClient";
import { AgentTerminalPty } from "./agentTerminal";
import { ChatViewProvider } from "./chatView";

let client: AgentClient;
let currentPty:      AgentTerminalPty | undefined;
let currentTerminal: vscode.Terminal  | undefined;

export function activate(context: vscode.ExtensionContext): void {
  const out = vscode.window.createOutputChannel("Governed Coding Agent");
  client = new AgentClient(out);

  // ── Chat sidebar (WebviewView — primary UI) ─────────────────────────────

  const chatProvider = new ChatViewProvider(context.extensionUri, client, out);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(ChatViewProvider.viewType, chatProvider, {
      webviewOptions: { retainContextWhenHidden: true },
    }),
  );

  // Start subprocess early so panel open is instant
  const cwd = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? process.cwd();
  client.start(cwd);

  // ── Commands ────────────────────────────────────────────────────────────

  context.subscriptions.push(

    vscode.commands.registerCommand("governed-coding-agent.openTerminal", () => {
      ensureTerminal(out).then(([terminal]) => terminal.show(true));
    }),

    vscode.commands.registerCommand("governed-coding-agent.newSession", () => {
      chatProvider.startNewSession();
      vscode.commands.executeCommand("governed-coding-agent.chatView.focus");
    }),

    vscode.commands.registerCommand("governed-coding-agent.refreshSessions", () => {
      if (client.isRunning()) client.send({ type: "sessions" });
    }),

    vscode.commands.registerCommand("governed-coding-agent.resumeSession", (threadId: string) => {
      chatProvider.resumeSession(threadId);
      vscode.commands.executeCommand("governed-coding-agent.chatView.focus");
    }),

    out,
    { dispose: () => client.dispose() },
  );
}

export function deactivate(): void {
  client?.dispose();
}

// ── Terminal lifecycle ──────────────────────────────────────────────────────

/**
 * Returns [terminal, pty]. Re-uses an existing terminal if still alive;
 * otherwise creates a fresh PTY + terminal pair.
 */
async function ensureTerminal(
  out: vscode.OutputChannel,
): Promise<[vscode.Terminal, AgentTerminalPty]> {
  if (currentTerminal && vscode.window.terminals.includes(currentTerminal)) {
    return [currentTerminal, currentPty!];
  }

  const pty      = new AgentTerminalPty(client, out);
  const terminal = vscode.window.createTerminal({ name: "Governed Coding Agent", pty });

  currentPty      = pty;
  currentTerminal = terminal;

  return [terminal, pty];
}
