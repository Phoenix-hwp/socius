import { useEffect, useMemo, useState } from "react";
import { Cascader } from "../components/Cascader";
import { fetchCascaderOptions, fetchHealth } from "../api/client";
import {
  ALL_SELECTION,
  CascaderNode,
  CascaderOptionsPayload,
  CascaderSelection,
} from "../types/cascader";
import styles from "./NotionHomeworkPage.module.css";

function shortId(id: string | undefined | null): string {
  if (!id) return "(无)";
  const tail = id.replace(/-/g, "").slice(-8);
  return tail || id;
}

function describeNode(node: CascaderNode | null, mode: CascaderSelection["mode"]): string {
  if (mode === "all") return "mode=all（聚合所有 database 根/子节点）";
  if (!node) return "mode=" + mode;
  return [
    `mode=${mode}`,
    `notionObjectType=${node.notionObjectType}`,
    `id…${shortId(node.id)}`,
  ].join(" · ");
}

export function NotionHomeworkPage() {
  const [healthText, setHealthText] = useState<string>("正在检测本机 API…");
  const [healthOk, setHealthOk] = useState<boolean | null>(null);
  const [cascaderPayload, setCascaderPayload] = useState<CascaderOptionsPayload | null>(null);
  const [cascaderError, setCascaderError] = useState<string | null>(null);
  const [selection, setSelection] = useState<CascaderSelection>(ALL_SELECTION);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchHealth();
        if (cancelled) return;
        const token = data.tokenPresent ? "已配置" : "未检测到";
        setHealthOk(true);
        setHealthText(`后端在线 · status=${data.status} · Token：${token}（由服务端读取，前端不携带）`);
      } catch {
        if (cancelled) return;
        setHealthOk(false);
        setHealthText(
          "无法连接本机 API。请先启动后端（默认 127.0.0.1:8787）。若本页来自 Vite（:5173），请确认 vite 代理；若本页与 API 同源（:8787），请确认服务已启动。",
        );
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const payload = await fetchCascaderOptions();
        if (cancelled) return;
        setCascaderPayload(payload);
        setCascaderError(null);
      } catch (err) {
        if (cancelled) return;
        const msg = err instanceof Error ? err.message : String(err);
        setCascaderError(`级联选项加载失败：${msg}`);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const options = useMemo<CascaderNode[]>(
    () => cascaderPayload?.options ?? [],
    [cascaderPayload],
  );

  const generatedAt = cascaderPayload?.generatedAt ?? "—";
  const rootCount = options.length;
  const selectionDesc = describeNode(selection.node, selection.mode);

  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>Notion 作业</h1>
      <p className={styles.lead}>
        MVP 壳（T09）：级联组件已接入 <code>/notion/cascader/options</code>。列表与行内操作将在{" "}
        <strong>T10</strong> 接入。
      </p>

      <section
        className={styles.card}
        data-state={healthOk === null ? "pending" : healthOk ? "ok" : "err"}
        aria-live="polite"
      >
        <h2 className={styles.cardTitle}>本机 API</h2>
        <p className={styles.cardBody}>{healthText}</p>
      </section>

      <section
        className={styles.card}
        data-state={cascaderError ? "err" : cascaderPayload ? "ok" : "pending"}
        aria-live="polite"
      >
        <h2 className={styles.cardTitle}>所属目录</h2>
        {cascaderError ? (
          <p className={styles.cardBody}>{cascaderError}</p>
        ) : !cascaderPayload ? (
          <p className={styles.cardBody}>正在加载级联选项…</p>
        ) : (
          <div className={styles.directoryRow}>
            <Cascader options={options} value={selection} onChange={setSelection} />
            <div className={styles.directoryMeta}>
              <div>
                <span className={styles.metaKey}>schemaVersion</span>
                <span>{cascaderPayload.schemaVersion}</span>
              </div>
              <div>
                <span className={styles.metaKey}>generatedAt</span>
                <span>{generatedAt}</span>
              </div>
              <div>
                <span className={styles.metaKey}>roots</span>
                <span>{rootCount}</span>
              </div>
              <div>
                <span className={styles.metaKey}>selection</span>
                <span>{selectionDesc}</span>
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
