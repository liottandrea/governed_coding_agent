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
exports.AgentClient = void 0;
const vscode = __importStar(require("vscode"));
const cp = __importStar(require("child_process"));
const readline = __importStar(require("readline"));
/**
 * Manages the ust-agent --server subprocess and the JSON-lines protocol.
 * Emits typed AgentEvents via the onEvent callback.
 */
class AgentClient {
    constructor(outputChannel) {
        this.process = null;
        this.rl = null;
        this.eventHandlers = [];
        this.outputChannel = outputChannel;
    }
    onEvent(handler) {
        this.eventHandlers.push(handler);
    }
    emit(event) {
        for (const h of this.eventHandlers) {
            h(event);
        }
    }
    isRunning() {
        return this.process !== null && !this.process.killed;
    }
    start(cwd) {
        if (this.isRunning()) {
            return;
        }
        const config = vscode.workspace.getConfiguration("ustAgent");
        const binary = config.get("binaryPath") || "ust-agent";
        const agentHome = config.get("agentHome") || "";
        const env = { ...process.env };
        if (agentHome) {
            env["UST_AGENT_HOME"] = agentHome;
        }
        this.outputChannel.appendLine(`[AgentClient] spawning: ${binary} --server`);
        this.process = cp.spawn(binary, ["--server"], {
            cwd,
            env,
            stdio: ["pipe", "pipe", "pipe"],
        });
        this.process.stderr?.on("data", (data) => {
            this.outputChannel.appendLine(`[server stderr] ${data.toString().trim()}`);
        });
        this.process.on("error", (err) => {
            this.outputChannel.appendLine(`[AgentClient] spawn error: ${err.message}`);
            this.emit({ type: "error", message: `Could not start ust-agent: ${err.message}` });
        });
        this.process.on("exit", (code) => {
            this.outputChannel.appendLine(`[AgentClient] process exited (code=${code})`);
            this.process = null;
            this.rl = null;
        });
        this.rl = readline.createInterface({ input: this.process.stdout });
        this.rl.on("line", (line) => {
            const trimmed = line.trim();
            if (!trimmed)
                return;
            this.outputChannel.appendLine(`[server →] ${trimmed}`);
            try {
                const event = JSON.parse(trimmed);
                this.emit(event);
            }
            catch (e) {
                this.outputChannel.appendLine(`[AgentClient] parse error: ${e}`);
            }
        });
    }
    send(cmd) {
        if (!this.isRunning() || !this.process?.stdin) {
            this.emit({ type: "error", message: "Agent process is not running." });
            return;
        }
        const line = JSON.stringify(cmd) + "\n";
        this.outputChannel.appendLine(`[→ server] ${line.trim()}`);
        this.process.stdin.write(line);
    }
    stop() {
        if (this.process) {
            this.process.kill();
            this.process = null;
            this.rl = null;
        }
    }
    dispose() {
        this.stop();
    }
}
exports.AgentClient = AgentClient;
//# sourceMappingURL=agentClient.js.map