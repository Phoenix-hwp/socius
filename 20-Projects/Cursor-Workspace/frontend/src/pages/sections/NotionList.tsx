/**
 * 列表区段（T10）。
 *
 * 行为：根据 `selection.mode` 调用三类后端端点；切换 selection 自动重置分页与游标。
 *   - all      → fetchAllDatabasesQuery({ page, pageSize, title })
 *   - database → fetchDatabaseQuery(node.id, { startCursor, pageSize, title })
 *   - page     → fetchPageList(node.id) → 渲染 message + Notion 外链
 *
 * 行内按钮：
 *   - 查看 → window.open(row.url)
 *   - 更新 → console.info + UI 临时回显（T12 接入实际写入）
 */

import { useEffect, useMemo, useRef, useState } from "react";
import {
  fetchAllDatabasesQuery,
  fetchDatabaseQuery,
  fetchPageList,
} from "../../api/client";
import { Pager } from "../../components/Pager";
import { RowsTable } from "../../components/RowsTable";
import type { CascaderSelection } from "../../types/cascader";
import type { NotionRow, PageListResponse } from "../../types/notion";
import styles from "./NotionList.module.css";

const DEFAULT_PAGE_SIZE = 25;
const TITLE_DEBOUNCE_MS = 250;

interface NotionListProps {
  selection: CascaderSelection;
  databaseLabelByID: Record<string, string>;
}

interface AllPaging {
  page: number;
  totalItems: number;
  totalPages: number;
  hasMore: boolean;
  databaseCount: number;
}

interface CursorPaging {
  pageIndex: number;
  startCursor: string | null;
  nextCursor: string | null;
  hasMore: boolean;
}

function shortHex(id: string | undefined | null, take = 8): string {
  if (!id) return "";
  return id.replace(/-/g, "").slice(-take);
}

function describeUpdateTarget(row: NotionRow): string {
  return [
    row.title || "(无标题)",
    `object=${row.object}`,
    `id…${shortHex(row.id)}`,
  ].join(" · ");
}

export function NotionList({ selection, databaseLabelByID }: NotionListProps) {
  const [titleInput, setTitleInput] = useState("");
  const [debouncedTitle, setDebouncedTitle] = useState("");
  const [rows, setRows] = useState<NotionRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pageMessage, setPageMessage] = useState<PageListResponse | null>(null);

  const [allPaging, setAllPaging] = useState<AllPaging>({
    page: 0,
    totalItems: 0,
    totalPages: 0,
    hasMore: false,
    databaseCount: 0,
  });
  const [cursorPaging, setCursorPaging] = useState<CursorPaging>({
    pageIndex: 0,
    startCursor: null,
    nextCursor: null,
    hasMore: false,
  });
  const [allPage, setAllPage] = useState(0);

  const [lastUpdateTarget, setLastUpdateTarget] = useState<NotionRow | null>(null);

  const reqIdRef = useRef(0);

  // selection 变化时清空 + 重置分页
  useEffect(() => {
    setRows([]);
    setError(null);
    setPageMessage(null);
    setAllPage(0);
    setCursorPaging({ pageIndex: 0, startCursor: null, nextCursor: null, hasMore: false });
    setLastUpdateTarget(null);
  }, [selection.mode, selection.node?.id]);

  // 标题防抖
  useEffect(() => {
    const handle = window.setTimeout(() => {
      setDebouncedTitle(titleInput.trim());
    }, TITLE_DEBOUNCE_MS);
    return () => window.clearTimeout(handle);
  }, [titleInput]);

  // 标题变化时重置 page/cursor
  useEffect(() => {
    setAllPage(0);
    setCursorPaging({ pageIndex: 0, startCursor: null, nextCursor: null, hasMore: false });
  }, [debouncedTitle]);

  // 主拉取副作用
  useEffect(() => {
    const reqId = ++reqIdRef.current;
    let cancelled = false;
    setError(null);

    async function run() {
      if (selection.mode === "all") {
        setLoading(true);
        setPageMessage(null);
        try {
          const res = await fetchAllDatabasesQuery({
            page: allPage,
            pageSize: DEFAULT_PAGE_SIZE,
            title: debouncedTitle || undefined,
          });
          if (cancelled || reqId !== reqIdRef.current) return;
          setRows(res.items);
          setAllPaging({
            page: res.page,
            totalItems: res.totalItems,
            totalPages: res.totalPages,
            hasMore: res.hasMore,
            databaseCount: res.databaseCount,
          });
        } catch (err) {
          if (cancelled || reqId !== reqIdRef.current) return;
          setError(err instanceof Error ? err.message : String(err));
          setRows([]);
        } finally {
          if (!cancelled && reqId === reqIdRef.current) setLoading(false);
        }
        return;
      }

      if (selection.mode === "database" && selection.node) {
        setLoading(true);
        setPageMessage(null);
        try {
          const res = await fetchDatabaseQuery(selection.node.id, {
            pageSize: DEFAULT_PAGE_SIZE,
            startCursor: cursorPaging.startCursor,
            title: debouncedTitle || undefined,
          });
          if (cancelled || reqId !== reqIdRef.current) return;
          setRows(res.items);
          setCursorPaging((prev) => ({
            ...prev,
            nextCursor: res.nextCursor,
            hasMore: res.hasMore,
          }));
        } catch (err) {
          if (cancelled || reqId !== reqIdRef.current) return;
          setError(err instanceof Error ? err.message : String(err));
          setRows([]);
        } finally {
          if (!cancelled && reqId === reqIdRef.current) setLoading(false);
        }
        return;
      }

      if (selection.mode === "page" && selection.node) {
        setLoading(true);
        setRows([]);
        try {
          const res = await fetchPageList(selection.node.id, {
            page: 0,
            pageSize: DEFAULT_PAGE_SIZE,
          });
          if (cancelled || reqId !== reqIdRef.current) return;
          setPageMessage(res);
        } catch (err) {
          if (cancelled || reqId !== reqIdRef.current) return;
          setError(err instanceof Error ? err.message : String(err));
          setPageMessage(null);
        } finally {
          if (!cancelled && reqId === reqIdRef.current) setLoading(false);
        }
        return;
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [
    selection.mode,
    selection.node?.id,
    debouncedTitle,
    allPage,
    cursorPaging.startCursor,
  ]);

  const showDatabaseColumn = selection.mode === "all";

  const metaText = useMemo(() => {
    if (selection.mode === "all") {
      return `mode=all · 聚合 ${allPaging.databaseCount} 个 database`;
    }
    if (selection.mode === "database" && selection.node) {
      return `mode=database · id…${shortHex(selection.node.id)}`;
    }
    if (selection.mode === "page" && selection.node) {
      return `mode=page · id…${shortHex(selection.node.id)}`;
    }
    return "";
  }, [selection, allPaging.databaseCount]);

  const handleView = (row: NotionRow) => {
    if (!row.url) return;
    window.open(row.url, "_blank", "noopener,noreferrer");
  };

  const handleUpdate = (row: NotionRow) => {
    // T10：仅占位回调；T12 将在此分发到更新页（database 行 → properties；page → blocks）
    // eslint-disable-next-line no-console
    console.info("[T10] update target row:", row);
    setLastUpdateTarget(row);
  };

  return (
    <div className={styles.section}>
      <div className={styles.toolbar}>
        <input
          className={styles.titleInput}
          type="search"
          placeholder="按标题过滤（合并去重后内存匹配）"
          value={titleInput}
          onChange={(e) => setTitleInput(e.target.value)}
          aria-label="标题过滤"
          disabled={selection.mode === "page"}
        />
        <span className={styles.meta}>{metaText}</span>
        {loading ? <span className={styles.meta}>加载中…</span> : null}
      </div>

      {lastUpdateTarget ? (
        <div className={styles.banner}>
          <span className={styles.bannerKey}>已捕获</span>
          {describeUpdateTarget(lastUpdateTarget)}（T12 接入写入）
        </div>
      ) : null}

      {error ? (
        <div className={styles.banner} data-kind="error">
          <span className={styles.bannerKey}>错误</span>
          {error}
        </div>
      ) : null}

      {selection.mode === "page" ? (
        <div className={styles.pageHint}>
          <div>{pageMessage?.message ?? "MVP：普通 Notion 页面无数据库式行列表。"}</div>
          {selection.node?.url ? (
            <a
              className={styles.openInNotion}
              href={selection.node.url}
              target="_blank"
              rel="noreferrer noopener"
            >
              在 Notion 中打开此页
            </a>
          ) : null}
        </div>
      ) : (
        <RowsTable
          rows={rows}
          showDatabaseColumn={showDatabaseColumn}
          databaseLabelByID={databaseLabelByID}
          emptyText={
            loading
              ? "加载中…"
              : debouncedTitle
                ? "（无匹配项；可清除过滤词后再试）"
                : "（暂无数据）"
          }
          onView={handleView}
          onUpdate={handleUpdate}
        />
      )}

      {selection.mode === "all" ? (
        <Pager
          mode="page"
          page={allPaging.page}
          totalPages={allPaging.totalPages}
          totalItems={allPaging.totalItems}
          hasMore={allPaging.hasMore}
          loading={loading}
          onChangePage={(next) => setAllPage(next)}
        />
      ) : null}

      {selection.mode === "database" ? (
        <Pager
          mode="cursor"
          pageIndex={cursorPaging.pageIndex}
          nextCursor={cursorPaging.nextCursor}
          hasMore={cursorPaging.hasMore}
          loading={loading}
          onAdvance={(nextCursor) =>
            setCursorPaging((prev) => ({
              ...prev,
              pageIndex: prev.pageIndex + 1,
              startCursor: nextCursor,
              nextCursor: null,
            }))
          }
          onReset={() =>
            setCursorPaging({
              pageIndex: 0,
              startCursor: null,
              nextCursor: null,
              hasMore: false,
            })
          }
        />
      ) : null}
    </div>
  );
}
