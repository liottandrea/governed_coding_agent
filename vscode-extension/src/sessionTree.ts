import * as vscode from "vscode";
import { SessionRow } from "./types";

export class SessionItem extends vscode.TreeItem {
  constructor(
    public readonly thread_id: string,
    public readonly turns: number,
  ) {
    const short = thread_id.slice(0, 8);
    super(`${short}…  (${turns} turns)`, vscode.TreeItemCollapsibleState.None);
    this.tooltip     = thread_id;
    this.description = `${turns} turn${turns !== 1 ? "s" : ""}`;
    this.iconPath    = new vscode.ThemeIcon("comment-discussion");
    this.command     = {
      command:   "governed-coding-agent.resumeSession",
      title:     "Resume Session",
      arguments: [thread_id],
    };
  }
}

export class SessionTreeProvider implements vscode.TreeDataProvider<SessionItem> {
  private _change = new vscode.EventEmitter<SessionItem | undefined | null | void>();
  readonly onDidChangeTreeData = this._change.event;

  private rows: SessionRow[] = [];

  /** Called by extension.ts whenever a `sessions` event arrives from the agent. */
  update(rows: SessionRow[]): void {
    this.rows = rows;
    this._change.fire();
  }

  getTreeItem(el: SessionItem): vscode.TreeItem { return el; }

  getChildren(): SessionItem[] {
    return this.rows.map((r) => new SessionItem(r.thread_id, r.turns));
  }
}
