import * as vscode from "vscode";
import { AgentClient } from "./agentClient";
import { SessionRow, WebviewSettings } from "./types";

export class SessionItem extends vscode.TreeItem {
  constructor(
    public readonly thread_id: string,
    public readonly turns: number
  ) {
    const short = thread_id.slice(0, 8);
    super(`${short}…  (${turns} turns)`, vscode.TreeItemCollapsibleState.None);
    this.tooltip = thread_id;
    this.description = `${turns} turn${turns !== 1 ? "s" : ""}`;
    this.iconPath = new vscode.ThemeIcon("comment-discussion");
    this.command = {
      command: "ust-agent.resumeSession",
      title: "Resume Session",
      arguments: [thread_id],
    };
  }
}

export class SessionTreeProvider
  implements vscode.TreeDataProvider<SessionItem>
{
  private _onDidChangeTreeData = new vscode.EventEmitter<
    SessionItem | undefined | null | void
  >();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  private rows: SessionRow[] = [];
  private client: AgentClient;

  constructor(client: AgentClient) {
    this.client = client;
    client.onEvent((event) => {
      if (event.type === "sessions") {
        this.rows = event.rows;
        this._onDidChangeTreeData.fire();
      }
    });
  }

  refresh(): void {
    this.client.send({ type: "sessions" });
  }

  getTreeItem(element: SessionItem): vscode.TreeItem {
    return element;
  }

  getChildren(): SessionItem[] {
    return this.rows.map((r) => new SessionItem(r.thread_id, r.turns));
  }
}
