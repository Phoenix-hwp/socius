/**
 * Notion 行与三类列表响应类型（T10，对齐 Spec §6.1 与 backend `_project_row`）。
 *
 * - `NotionRow.parent` 与 `object` 为后续写入分型（T11/T12）必须，**禁止裁剪**。
 * - `last_edited_time` / `created_time` 由后端按 last_edited_time 降序排序后透传。
 */

export type NotionObject = "page" | "database";

export interface NotionParent {
  type?: "database_id" | "page_id" | "workspace" | string;
  database_id?: string;
  page_id?: string;
  workspace?: boolean;
}

export interface NotionRow {
  id: string;
  object: NotionObject;
  last_edited_time: string | null;
  created_time: string | null;
  parent: NotionParent | null;
  url: string | null;
  archived: boolean;
  title: string;
}

export interface FilterApplied {
  title: string | null;
}

export interface AllQueryResponse {
  mode: "all";
  databaseCount: number;
  items: NotionRow[];
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  hasMore: boolean;
  filterApplied: FilterApplied;
}

export interface DatabaseQueryResponse {
  databaseId: string;
  items: NotionRow[];
  nextCursor: string | null;
  hasMore: boolean;
  pageSize: number;
  filterApplied: FilterApplied;
  rawCount: number;
}

export interface PageListCascaderContext {
  label: string;
  rootLabel: string;
  pathLabels: string[];
}

export interface PageListResponse {
  mode: "page";
  pageId: string;
  notionObjectType: "page";
  isLeaf: boolean;
  listSupported: false;
  items: NotionRow[];
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  hasMore: false;
  message: string;
  cascader: PageListCascaderContext;
}
