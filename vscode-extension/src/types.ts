// JSON-lines protocol types shared between agentClient and chatPanel.

export type DataClass = "public" | "internal" | "restricted";
export type Role = "planner" | "codegen";
export type ModelGroup =
  | "cheap"
  | "mid"
  | "frontier"
  | "local_fast"
  | "local_standard"
  | "local_heavy";

// ── Commands (extension → server, via stdin) ──────────────────────────────

export interface PingCommand {
  type: "ping";
}

export interface StartCommand {
  type: "start";
  thread_id?: string;
  data_class: DataClass;
  role: Role;
  group_overrides?: Partial<Record<string, ModelGroup>>;
  system_prompt?: string;
  include_knowledge: boolean;
  cwd: string;
}

export interface TaskCommand {
  type: "task";
  message: string;
}

export interface DecisionCommand {
  type: "decision";
  decisions: Array<{ type: "approve" } | { type: "reject"; message?: string }>;
}

export interface SessionsCommand {
  type: "sessions";
}

export type ServerCommand =
  | PingCommand
  | StartCommand
  | TaskCommand
  | DecisionCommand
  | SessionsCommand;

// ── Events (server → extension, via stdout) ───────────────────────────────

export interface PongEvent {
  type: "pong";
}

export interface ReadyEvent {
  type: "ready";
  session_id: string;
}

export interface ThinkingEvent {
  type: "thinking";
}

export interface ResponseEvent {
  type: "response";
  content: string;
}

export interface ActionRequest {
  name: string;
  args: Record<string, unknown>;
  description?: string;
}

export interface InterruptEvent {
  type: "interrupt";
  action_requests: ActionRequest[];
}

export interface SessionRow {
  thread_id: string;
  turns: number;
}

export interface SessionsEvent {
  type: "sessions";
  rows: SessionRow[];
}

export interface TraceUrlEvent {
  type: "trace_url";
  url: string;
}

export interface ErrorEvent {
  type: "error";
  message: string;
}

export type AgentEvent =
  | PongEvent
  | ReadyEvent
  | ThinkingEvent
  | ResponseEvent
  | InterruptEvent
  | SessionsEvent
  | TraceUrlEvent
  | ErrorEvent;

// ── Webview ↔ Extension messages ──────────────────────────────────────────

export interface WebviewSettings {
  data_class: DataClass;
  role: Role;
  plannerModel: ModelGroup;
  subagentModel: ModelGroup;
  include_knowledge: boolean;
  system_prompt: string;
}

export type WebviewToExtension =
  | { type: "task"; message: string }
  | { type: "decision"; index: number; approved: boolean; reason?: string }
  | { type: "newSession" }
  | { type: "resumeSession"; thread_id: string }
  | { type: "refreshSessions" }
  | { type: "settingsChanged"; settings: WebviewSettings };

export type ExtensionToWebview =
  | { type: "ready"; session_id: string }
  | { type: "thinking" }
  | { type: "response"; content: string }
  | { type: "interrupt"; action_requests: ActionRequest[] }
  | { type: "sessions"; rows: SessionRow[] }
  | { type: "trace_url"; url: string }
  | { type: "error"; message: string }
  | { type: "settings"; settings: WebviewSettings };
