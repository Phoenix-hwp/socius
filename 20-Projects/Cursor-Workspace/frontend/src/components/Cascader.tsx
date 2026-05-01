/**
 * 列式级联组件（T09）。
 *
 * 数据：从父组件传入 `notion_cascader_options.json` 的 `options[]`（已由后端
 * `GET /notion/cascader/options` 同源返回）。组件本身**不发任何请求**。
 *
 * 行为：
 *   - 触发器按钮显示当前路径（"全部" 或 "根 / 子节点 / …"）。
 *   - 弹层为列式：每列即上一列选中节点的 `children`；第 0 列即根节点列表。
 *   - 第 0 列顶部固定一项 **"全部"**（伪根）；选中后 `mode='all'` 并关闭。
 *   - 单击 **叶子**（无 children 或 children 为空）→ 关闭并 `onChange`。
 *   - 单击 **非叶子** → 展开下一列；若当前节点本身可作为目标（page/database），
 *     长按或双击会带来歧义，故仅以 "展开 vs 选中" 单一语义：**有 children 必展开**。
 *     用户选中容器自身的能力，留给 T10 列表层（按需在路径栏点击当前节点）。
 *   - `disabled === true` 节点不可选、不可展开。
 *
 * 边界：组件外部点击关闭弹层（`mousedown` 监听）。
 */

import { useEffect, useMemo, useRef, useState } from "react";
import {
  ALL_SELECTION,
  CascaderNode,
  CascaderSelection,
  deriveModeFromNode,
} from "../types/cascader";
import styles from "./Cascader.module.css";

interface CascaderProps {
  options: CascaderNode[];
  value: CascaderSelection;
  onChange: (selection: CascaderSelection) => void;
  /** 触发器无选中时的占位文案（默认 "全部"）。 */
  placeholder?: string;
}

const ALL_LABEL = "全部";

function hasChildren(node: CascaderNode): boolean {
  return Array.isArray(node.children) && node.children.length > 0;
}

function buildSelection(node: CascaderNode, pathLabels: string[]): CascaderSelection {
  return {
    mode: deriveModeFromNode(node),
    node,
    pathLabels,
  };
}

/**
 * 把外部传入的 `value.pathLabels` 还原成"列式选中链"。
 * 若 pathLabels 与当前 options 对不上（例如配置已刷新），返回空链。
 */
function resolvePathToColumns(
  options: CascaderNode[],
  pathLabels: string[],
): CascaderNode[] {
  const chain: CascaderNode[] = [];
  let pool: CascaderNode[] = options;
  for (const label of pathLabels) {
    const found: CascaderNode | undefined = pool.find(
      (n: CascaderNode) => n.label === label,
    );
    if (!found) return [];
    chain.push(found);
    pool = Array.isArray(found.children) ? found.children : [];
  }
  return chain;
}

export function Cascader({ options, value, onChange, placeholder }: CascaderProps) {
  const [open, setOpen] = useState(false);
  const [hoverChain, setHoverChain] = useState<CascaderNode[]>(() =>
    resolvePathToColumns(options, value.pathLabels),
  );
  const wrapRef = useRef<HTMLDivElement | null>(null);

  // 当外部 value/options 变化时，重置内部 hoverChain，避免列式状态与外部脱节
  useEffect(() => {
    setHoverChain(resolvePathToColumns(options, value.pathLabels));
  }, [options, value.pathLabels]);

  useEffect(() => {
    if (!open) return;
    function onDocMouseDown(ev: MouseEvent) {
      if (!wrapRef.current) return;
      if (!wrapRef.current.contains(ev.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocMouseDown);
    return () => document.removeEventListener("mousedown", onDocMouseDown);
  }, [open]);

  const triggerLabel = useMemo(() => {
    if (value.mode === "all") return placeholder ?? ALL_LABEL;
    if (value.pathLabels.length === 0) return placeholder ?? ALL_LABEL;
    return value.pathLabels.join(" / ");
  }, [value, placeholder]);

  /** 列式渲染：第 0 列 = options；后续每列 = hoverChain[i] 的 children。 */
  const columns: CascaderNode[][] = useMemo(() => {
    const cols: CascaderNode[][] = [options];
    for (const node of hoverChain) {
      const ch = node.children;
      if (Array.isArray(ch) && ch.length > 0) cols.push(ch);
    }
    return cols;
  }, [options, hoverChain]);

  function handleClickAll() {
    onChange(ALL_SELECTION);
    setHoverChain([]);
    setOpen(false);
  }

  function handleClickNode(node: CascaderNode, columnIndex: number) {
    if (node.disabled) return;
    const ancestors = hoverChain.slice(0, columnIndex);
    const nextChain = [...ancestors, node];

    if (hasChildren(node)) {
      // 展开下一列；不立即选中（容器自身选中由 T10 路径栏支持）
      setHoverChain(nextChain);
      return;
    }
    // 叶子：选中并关闭
    const pathLabels = nextChain.map((n) => n.label);
    onChange(buildSelection(node, pathLabels));
    setOpen(false);
  }

  function isNodeActive(node: CascaderNode, columnIndex: number): boolean {
    return hoverChain[columnIndex]?.value === node.value;
  }

  return (
    <div className={styles.wrap} ref={wrapRef}>
      <button
        type="button"
        className={styles.trigger}
        data-open={open}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className={styles.triggerLabel} title={triggerLabel}>
          {triggerLabel}
        </span>
        <span className={styles.caret} aria-hidden="true">
          ▾
        </span>
      </button>
      {open ? (
        <div className={styles.popover} role="dialog" aria-label="所属目录级联">
          {columns.map((col, ci) => (
            <div className={styles.column} key={`col-${ci}`}>
              {ci === 0 ? (
                <div className={styles.allRow}>
                  <button
                    type="button"
                    className={styles.option}
                    data-active={value.mode === "all"}
                    onClick={handleClickAll}
                  >
                    <span className={styles.optionLabel}>{ALL_LABEL}</span>
                    <span className={styles.typeBadge}>聚合</span>
                  </button>
                </div>
              ) : null}
              {col.length === 0 ? (
                <div className={styles.empty}>（无子项）</div>
              ) : (
                col.map((node) => {
                  const showChevron = hasChildren(node);
                  return (
                    <button
                      type="button"
                      key={node.value}
                      className={styles.option}
                      data-active={isNodeActive(node, ci)}
                      disabled={node.disabled}
                      onClick={() => handleClickNode(node, ci)}
                    >
                      <span className={styles.optionLabel} title={node.label}>
                        {node.label}
                      </span>
                      <span
                        className={styles.typeBadge}
                        data-kind={node.notionObjectType}
                      >
                        {node.notionObjectType}
                      </span>
                      {showChevron ? (
                        <span className={styles.chevron} aria-hidden="true">
                          ›
                        </span>
                      ) : null}
                    </button>
                  );
                })
              )}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
