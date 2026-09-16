import * as vscode from "vscode";
import * as cp from "child_process";
import * as readline from "readline";
import { AgentEvent, ServerCommand } from "./types";

/**
 * Manages the governed-coding-agent --server subprocess and the JSON-lines protocol.
 * Emits typed AgentEvents via the onEvent callback.
 */
export class AgentClient {
  private process: cp.ChildProcess | null = null;
  private rl: readline.Interface | null = null;
  private eventHandlers: Array<(event: AgentEvent) => void> = [];
  private outputChannel: vscode.OutputChannel;

  constructor(outputChannel: vscode.OutputChannel) {
    this.outputChannel = outputChannel;
  }

  onEvent(handler: (event: AgentEvent) => void): vscode.Disposable {
    this.eventHandlers.push(handler);
    return new vscode.Disposable(() => {
      const i = this.eventHandlers.indexOf(handler);
      if (i >= 0) this.eventHandlers.splice(i, 1);
    });
  }

  private emit(event: AgentEvent): void {
    for (const h of this.eventHandlers) {
      h(event);
    }
  }

  isRunning(): boolean {
    return this.process !== null && !this.process.killed;
  }

  start(cwd: string): void {
    if (this.isRunning()) {
      return;
    }

    const config = vscode.workspace.getConfiguration("governedCodingAgent");
    const binary: string = config.get("binaryPath") || "governed-coding-agent";
    const agentHome: string = config.get("agentHome") || "";

    const env: NodeJS.ProcessEnv = { ...process.env };
    if (agentHome) {
      env["GOVERNED_AGENT_HOME"] = agentHome;
    }

    this.outputChannel.appendLine(`[AgentClient] spawning: ${binary} --server`);

    this.process = cp.spawn(binary, ["--server"], {
      cwd,
      env,
      stdio: ["pipe", "pipe", "pipe"],
    });

    this.process.stderr?.on("data", (data: Buffer) => {
      this.outputChannel.appendLine(`[server stderr] ${data.toString().trim()}`);
    });

    this.process.on("error", (err) => {
      this.outputChannel.appendLine(`[AgentClient] spawn error: ${err.message}`);
      this.emit({ type: "error", message: `Could not start governed-coding-agent: ${err.message}` });
    });

    this.process.on("exit", (code) => {
      this.outputChannel.appendLine(`[AgentClient] process exited (code=${code})`);
      this.process = null;
      this.rl = null;
    });

    this.rl = readline.createInterface({ input: this.process.stdout! });
    this.rl.on("line", (line) => {
      const trimmed = line.trim();
      if (!trimmed) return;
      this.outputChannel.appendLine(`[server →] ${trimmed}`);
      try {
        const event = JSON.parse(trimmed) as AgentEvent;
        this.emit(event);
      } catch (e) {
        this.outputChannel.appendLine(`[AgentClient] parse error: ${e}`);
      }
    });
  }

  send(cmd: ServerCommand): void {
    if (!this.isRunning() || !this.process?.stdin) {
      this.emit({ type: "error", message: "Agent process is not running." });
      return;
    }
    const line = JSON.stringify(cmd) + "\n";
    this.outputChannel.appendLine(`[→ server] ${line.trim()}`);
    this.process.stdin.write(line);
  }

  stop(): void {
    if (this.process) {
      this.process.kill();
      this.process = null;
      this.rl = null;
    }
  }

  dispose(): void {
    this.stop();
  }
}
