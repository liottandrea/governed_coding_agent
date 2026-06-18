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
exports.SessionTreeProvider = exports.SessionItem = void 0;
const vscode = __importStar(require("vscode"));
class SessionItem extends vscode.TreeItem {
    constructor(thread_id, turns) {
        const short = thread_id.slice(0, 8);
        super(`${short}…  (${turns} turns)`, vscode.TreeItemCollapsibleState.None);
        this.thread_id = thread_id;
        this.turns = turns;
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
exports.SessionItem = SessionItem;
class SessionTreeProvider {
    constructor(client) {
        this._onDidChangeTreeData = new vscode.EventEmitter();
        this.onDidChangeTreeData = this._onDidChangeTreeData.event;
        this.rows = [];
        this.client = client;
        client.onEvent((event) => {
            if (event.type === "sessions") {
                this.rows = event.rows;
                this._onDidChangeTreeData.fire();
            }
        });
    }
    refresh() {
        this.client.send({ type: "sessions" });
    }
    getTreeItem(element) {
        return element;
    }
    getChildren() {
        return this.rows.map((r) => new SessionItem(r.thread_id, r.turns));
    }
}
exports.SessionTreeProvider = SessionTreeProvider;
//# sourceMappingURL=sessionTree.js.map