/**
 * 受控分页器（T10）。
 *
 * - mode='page'：0-based 页码（all 模式）。前后翻页通过 onChangePage(nextPage)。
 * - mode='cursor'：单库 Notion 游标分页。仅支持「下一页（带 nextCursor）」与「回到首页」；
 *   反向不支持（Notion API 限制）。
 * - 顶层语义保持显示：当前位置/总数（page 模式）/ 当前游标尾段（cursor 模式）。
 */

import styles from "./Pager.module.css";

interface PageModeProps {
  mode: "page";
  page: number;
  totalPages: number;
  totalItems: number;
  hasMore: boolean;
  loading: boolean;
  onChangePage: (next: number) => void;
}

interface CursorModeProps {
  mode: "cursor";
  /** 当前已加载到第几页（0-based，仅展示用，由父组件递增）。 */
  pageIndex: number;
  /** 后端返回的 nextCursor；为空则没有下一页。 */
  nextCursor: string | null;
  hasMore: boolean;
  loading: boolean;
  onAdvance: (nextCursor: string) => void;
  onReset: () => void;
}

type PagerProps = PageModeProps | CursorModeProps;

function shortHex(s: string | null | undefined, take = 6): string {
  if (!s) return "";
  return s.replace(/-/g, "").slice(-take);
}

export function Pager(props: PagerProps) {
  if (props.mode === "page") {
    const { page, totalPages, totalItems, hasMore, loading, onChangePage } = props;
    const prevDisabled = loading || page <= 0;
    const nextDisabled = loading || (!hasMore && page + 1 >= totalPages);
    return (
      <div className={styles.wrap} role="navigation" aria-label="列表分页">
        <button
          type="button"
          className={styles.btn}
          disabled={prevDisabled}
          onClick={() => onChangePage(Math.max(0, page - 1))}
        >
          上一页
        </button>
        <button
          type="button"
          className={styles.btn}
          disabled={nextDisabled}
          onClick={() => onChangePage(page + 1)}
        >
          下一页
        </button>
        <span className={styles.spacer} />
        <span className={styles.info}>
          第 {page + 1} / {Math.max(1, totalPages)} 页 · 共 {totalItems} 条
        </span>
      </div>
    );
  }

  const { pageIndex, nextCursor, hasMore, loading, onAdvance, onReset } = props;
  const advanceDisabled = loading || !hasMore || !nextCursor;
  return (
    <div className={styles.wrap} role="navigation" aria-label="列表分页（游标）">
      <button
        type="button"
        className={styles.btn}
        disabled={loading || pageIndex === 0}
        onClick={onReset}
      >
        回到首页
      </button>
      <button
        type="button"
        className={styles.btn}
        disabled={advanceDisabled}
        onClick={() => nextCursor && onAdvance(nextCursor)}
      >
        下一页
      </button>
      <span className={styles.spacer} />
      <span className={styles.info}>
        第 {pageIndex + 1} 页 · cursor…{shortHex(nextCursor) || "(末页)"}
      </span>
    </div>
  );
}
