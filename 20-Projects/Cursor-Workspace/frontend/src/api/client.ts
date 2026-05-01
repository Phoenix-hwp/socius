/** 开发态经 Vite proxy 访问本机 FastAPI；生产构建由 FastAPI 同源挂载 dist。 */

import type { CascaderOptionsPayload } from "../types/cascader";
import type {
  AllQueryResponse,
  DatabaseQueryResponse,
  PageListResponse,
} from "../types/notion";

export type HealthResponse = {
  status: string;
  tokenPresent?: boolean;
};

type QueryValue = string | number | boolean | null | undefined;

function buildQuery(params?: Record<string, QueryValue>): string {
  if (!params) return "";
  const search = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === null || v === undefined || v === "") continue;
    search.set(k, String(v));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

async function getJson<T>(
  path: string,
  params?: Record<string, QueryValue>,
): Promise<T> {
  const url = `${path}${buildQuery(params)}`;
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = ` ${JSON.stringify(body)}`;
    } catch {
      // ignore parse failure; HTTP code is enough for users
    }
    throw new Error(`HTTP ${res.status} ${url}${detail}`);
  }
  return (await res.json()) as T;
}

export async function fetchHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/health");
}

export async function fetchCascaderOptions(): Promise<CascaderOptionsPayload> {
  return getJson<CascaderOptionsPayload>("/notion/cascader/options");
}

export interface AllQueryArgs {
  page?: number;
  pageSize?: number;
  title?: string | null;
}

export async function fetchAllDatabasesQuery(
  args: AllQueryArgs = {},
): Promise<AllQueryResponse> {
  return getJson<AllQueryResponse>("/notion/databases/all/query", {
    page: args.page,
    page_size: args.pageSize,
    title: args.title ?? undefined,
  });
}

export interface DatabaseQueryArgs {
  pageSize?: number;
  startCursor?: string | null;
  title?: string | null;
}

export async function fetchDatabaseQuery(
  databaseId: string,
  args: DatabaseQueryArgs = {},
): Promise<DatabaseQueryResponse> {
  const safeId = encodeURIComponent(databaseId);
  return getJson<DatabaseQueryResponse>(`/notion/databases/${safeId}/query`, {
    page_size: args.pageSize,
    start_cursor: args.startCursor ?? undefined,
    title: args.title ?? undefined,
  });
}

export interface PageListArgs {
  page?: number;
  pageSize?: number;
}

export async function fetchPageList(
  pageId: string,
  args: PageListArgs = {},
): Promise<PageListResponse> {
  const safeId = encodeURIComponent(pageId);
  return getJson<PageListResponse>(`/notion/pages/${safeId}/list`, {
    page: args.page,
    page_size: args.pageSize,
  });
}
