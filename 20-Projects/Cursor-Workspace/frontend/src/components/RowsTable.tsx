/**
 * 列表行表格（T10）。
 *
 * - 列：title / 所属库（仅 all 模式 + showDatabaseColumn=true 渲染） / last_edited_time / 操作。
 * - 行内按钮：查看（外链）/ 更新（占位回调）；T10 不实现写入。
 * - 行 state：上层始终保留 **完整 NotionRow**（含 parent / object / url / archived），
 *   `onUpdate(row)` 回调原样透传，便于 T11 / T12 接入写入分型。
 */

import type { NotionRow } from "../types/notion";
import styles from "./RowsTable.module.css";

interface RowsTableProps {
  rows: NotionRow[];
  showDatabaseColumn: boolean;
  /** all 模式下用于把 parent.database_id 映射为级联中的 label。 */
  databaseLabelByID?: Record<string, string>;
  emptyText?: string;
  onView: (row: NotionRow) => void;
  onUpdate: (row: NotionRow) => void;
}

function formatTime(value: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const pad = (n: number) => String(n).padStart(2, "0");
  const yyyy = d.getFullYear();
  const mm = pad(d.getMonth() + 1);
  const dd = pad(d.getDate());
  const hh = pad(d.getHours());
  const mi = pad(d.getMinutes());
  return `${yyyy}-${mm}-${dd} ${hh}:${mi}`;
}

function shortHex(id: string | undefined | null): string {
  if (!id) return "";
  return id.replace(/-/g, "").slice(-8);
}

function describeDatabase(
  row: NotionRow,
  labelByID?: Record<string, string>,
): string {
  const dbid = row.parent?.database_id;
  if (!dbid) return "—";
  const label = labelByID?.[dbid];
  if (label) return label;
  return `db…${shortHex(dbid)}`;
}

export function RowsTable({
  rows,
  showDatabaseColumn,
  databaseLabelByID,
  emptyText,
  onView,
  onUpdate,
}: RowsTableProps) {
  if (rows.length === 0) {
    return (
      <div className={styles.empty}>{emptyText ?? "（无匹配行）"}</div>
    );
  }

  return (
    <div className={styles.wrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>标题</th>
            {showDatabaseColumn ? <th>所属库</th> : null}
            <th>最后编辑</th>
            <th style={{ textAlign: "right" }}>操作</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const empty = !row.title;
            return (
              <tr key={row.id}>
                <td className={styles.titleCell} data-empty={empty} title={row.title || row.id}>
                  {row.title || "(无标题)"}
                </td>
                {showDatabaseColumn ? (
                  <td className={styles.dbCell}>
                    {describeDatabase(row, databaseLabelByID)}
                  </td>
                ) : null}
                <td className={styles.timeCell}>{formatTime(row.last_edited_time)}</td>
                <td>
                  <div className={styles.actionsCell}>
                    <button
                      type="button"
                      className={styles.actionBtn}
                      disabled={!row.url}
                      onClick={() => onView(row)}
                      title={row.url ?? "无可打开 URL"}
                    >
                      查看
                    </button>
                    <button
                      type="button"
                      className={styles.actionBtn}
                      onClick={() => onUpdate(row)}
                      title="更新（T12 接入写入分型）"
                    >
                      更新
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
