/**
 * 级联选项类型（T09，与 `.cursor/mcp/notion_cascader_options.json` 对齐）。
 *
 * 后端 `GET /notion/cascader/options` 同源返回 `CascaderOptionsPayload` 原样字段；
 * UI 选中态以 `CascaderSelection` 对外暴露，供 T10 列表层按 `mode` 分支：
 *   - `mode === "all"`         → 调用 `/notion/databases/all/query`
 *   - `mode === "database"`    → 调用 `/notion/databases/{id}/query`
 *   - `mode === "page"`        → 调用 `/notion/pages/{id}/list`（占位）
 */

export type NotionObjectType = "page" | "database";
export type CascaderNodeType = "root" | "page" | "database";

export interface CascaderNode {
  label: string;
  value: string;
  nodeType: CascaderNodeType;
  notionObjectType: NotionObjectType;
  id: string;
  url?: string;
  disabled?: boolean;
  loadChildren?: boolean;
  children?: CascaderNode[];
}

export interface CascaderFieldGuide {
  [key: string]: string;
}

export interface CascaderOptionsPayload {
  schemaVersion: string;
  generatedAt: string;
  description?: string;
  fieldGuide?: CascaderFieldGuide;
  options: CascaderNode[];
}

export type CascaderMode = "all" | "database" | "page";

export interface CascaderSelection {
  mode: CascaderMode;
  node: CascaderNode | null;
  pathLabels: string[];
}

export const ALL_SELECTION: CascaderSelection = {
  mode: "all",
  node: null,
  pathLabels: [],
};

export function deriveModeFromNode(node: CascaderNode): CascaderMode {
  return node.notionObjectType === "database" ? "database" : "page";
}
