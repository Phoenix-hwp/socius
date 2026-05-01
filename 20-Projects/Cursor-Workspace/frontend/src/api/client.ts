/** 开发态经 Vite proxy 访问本机 FastAPI；生产构建由 FastAPI 同源挂载 dist。 */

import type { CascaderOptionsPayload } from "../types/cascader";

export type HealthResponse = {
  status: string;
  tokenPresent?: boolean;
};

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: { Accept: "application/json" } });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} ${path}`);
  }
  return (await res.json()) as T;
}

export async function fetchHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/health");
}

export async function fetchCascaderOptions(): Promise<CascaderOptionsPayload> {
  return getJson<CascaderOptionsPayload>("/notion/cascader/options");
}
