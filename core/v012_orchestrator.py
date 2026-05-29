"""
V012 管线编排器 — 代码化执行层。

替代原 flow-v012-pipeline-execute.mdc 中以下逻辑：
    - 阶段 A/B：数据合并（briefs + Task-Type-Registry）
    - 阶段 C：拆解后 N 判定与分叉
    - 阶段 C-bis：展示顺序强制（先输出再 ask）
    - 阶段 C-ter：写入 Pending-Plan-Tracker

规则文件仅保留 LLM 判断类约束（禁止短路、必须覆盖全量等）。
"""

from __future__ import annotations

import json as _json
import re
from pathlib import Path
from typing import Any


# ── 阶段 1：数据合并（briefs + registry → unified slots）──

# briefs label → registry name 的概念别名映射
# 当 briefs 中某 slot 的 label 和 registry 中某 slot 的 name 指同一概念时使用
_SLOT_CONCEPT_ALIASES: dict[str, str] = {
    "审查范围": "target_files",
    "审查深度": "review_focus",
    "输出格式": "output_action",
}

def resolve_slots(
    briefs_path: Path,
    registry_path: Path,
    task_type: str,
    *,
    project_dir: Path,
) -> list[dict]:
    """合并 briefs 和 Task-Type-Registry 的 slots，briefs 优先。

    Returns:
        [
            {"name": "review_depth", "label_cn": "审查深度", "strategy": "must_ask", "source": "briefs"},
            ...
        ]
    """
    slots: list[dict] = []

    # 1. 读取 briefs（内部按 label_cn 去重，同 label 只取首次出现）
    seen_labels: set[str] = set()
    if briefs_path.exists():
        text = briefs_path.read_text(encoding="utf-8")
        for m in re.finditer(
            r"- \[(must_ask|auto_fill|context_derive)\]\s+(.+?)(?:\n|$)",
            text,
        ):
            strategy = m.group(1)
            raw = m.group(2).strip()
            # 解析 "审查深度（快速扫描 / 逐函数 / 逐行？）" → label_cn
            label_cn = raw.split("：", 1)[0].split("（", 1)[0].strip("*").strip()
            if label_cn in seen_labels:
                continue
            seen_labels.add(label_cn)
            slot_name = _SLOT_CONCEPT_ALIASES.get(label_cn, label_cn)
            slots.append({"label_cn": label_cn, "strategy": strategy, "source": "briefs", "name": slot_name})

    # 2. 读取 Task-Type-Registry 作为兜底
    registry_slots: list[dict] = []
    if registry_path.exists():
        data = _json.loads(registry_path.read_text(encoding="utf-8"))
        task_types = data.get("task_types", data) if isinstance(data, dict) else data
        if isinstance(task_types, list):
            for t in task_types:
                if t.get("type_id") == task_type:
                    for s in t.get("required_slots", []):
                        label = s.get("label_cn", s.get("name", ""))
                        strategy = s.get("strategy", "must_ask")
                        registry_slots.append(
                            {"label_cn": label, "strategy": strategy, "source": "registry", "name": s.get("name", label)}
                        )
                    break

    # 3. 合并：briefs 已覆盖的 label_cn / name / 别名 不再从 registry 追加
    covered_labels = {s["label_cn"] for s in slots}
    covered_names = {s.get("name", "") for s in slots if s.get("name")}
    # name→label_cn 反向别名（registry name 可能指向 briefs 已有的 label）
    _alias_to_label: dict[str, str] = {v: k for k, v in _SLOT_CONCEPT_ALIASES.items()}
    for rs in registry_slots:
        r_label = rs["label_cn"]
        r_name = rs.get("name", "")
        if r_label in covered_labels:
            continue
        if r_name in covered_names:
            continue
        # 别名检测：registry name 的别名对应 briefs 已有的 label
        if r_name in _alias_to_label and _alias_to_label[r_name] in covered_labels:
            continue
        # 反向：registry label 在别名表中，对应 briefs 已有的 name
        if r_label in _SLOT_CONCEPT_ALIASES and _SLOT_CONCEPT_ALIASES[r_label] in covered_names:
            continue
        slots.append(rs)

    return slots


# ── 阶段 2：生成阶段 B 的 LLM prompt（精简） ──

def build_phase_b_prompt(slots: list[dict], task_id: str, briefs_content: str) -> str:
    """为阶段 B 生成精简系统提示：只问 must_ask 项。"""
    must_ask = [s for s in slots if s["strategy"] == "must_ask"]
    auto_fill = [s for s in slots if s["strategy"] == "auto_fill"]

    lines = [
        f"你是 V012 管线的信息确认阶段。任务 ID: {task_id}。",
        "",
        f"需要确认的信息项（共 {len(must_ask)} 项）：",
    ]
    for i, s in enumerate(must_ask, 1):
        lines.append(f"  {i}. {s['label_cn']}")

    if auto_fill:
        lines.append("\n已自动填充（无需询问）：")
        for s in auto_fill:
            lines.append(f"  - {s['label_cn']}")

    lines.extend(
        [
            "",
            "请逐一向用户确认上述信息（每次 ask 问一项）。",
            "用户回答后，进入下一项。全部确认完毕后，输出 DONE。",
        ]
    )

    return "\n".join(lines)


# ── 阶段 3：生成阶段 C 拆解 prompt ──

def build_decompose_prompt(task_id: str, briefs_content: str, slots: list[dict]) -> str:
    """为阶段 C 生成拆解 prompt。"""
    return f"""你是 V012 管线的任务拆解阶段。任务 ID: {task_id}。

以下是任务描述和已确认的槽位信息，请严格按照它来拆解子任务，不要自己编造任务内容：

{briefs_content}

请将以上任务拆解成可独立完成、可独立验收的子任务。每个子任务第一行必须是编号+简短名称（≤30字）。

然后补充每个子任务需要的方法（method）、预估耗时（estimated_minutes）、产出路径（output_to）。

请输出结构化拆解结果，然后输出 DONE。"""


# ── 阶段 4：生成 C-bis 展示 prompt ──

def build_plan_review_prompt(decomposition_result: str) -> str:
    """为 C-bis 生成排期确认 prompt。强制先展示再问。"""
    return f"""你是 V012 管线的排期确认阶段。请先完整输出拆解结果表（子任务列表 + 方法 + 预估耗时 + 产出 + 依赖关系），然后问用户确认。
拆解结果：
{decomposition_result}

请先输出完整表格，再发起确认。"""


# ── 阶段 5：C-ter 写入 Pending-Plan-Tracker（纯代码，不走 LLM） ──

def _get_tool_count(registry_path: Path, task_type: str) -> int:
    """从 Task-Type-Registry 中读取该 task_type 需要的工具种类数。

    工具数 = len(internal_skills) + len(external_skills)。
    candidates 和 uncovered 不计入（它们是候选/缺口，不是已绑定的工具）。
    """
    if not registry_path.exists() or not task_type:
        return 1
    data = _json.loads(registry_path.read_text(encoding="utf-8"))
    for t in data.get("task_types", []):
        if t.get("type_id") == task_type:
            skills = t.get("skills", {})
            return len(skills.get("internal", [])) + len(skills.get("external", []))
    return 1


def _get_uncovered_skills(registry_path: Path, task_type: str) -> list[str]:
    """从 Task-Type-Registry 中读取该 task_type 的 uncovered（缺失）技能清单。
    
    Returns:
        缺失技能的 readable name 列表，如 ["WebFetch（网页）", "Playwright CLI"]
    """
    if not registry_path.exists() or not task_type:
        return []
    data = _json.loads(registry_path.read_text(encoding="utf-8"))
    for t in data.get("task_types", []):
        if t.get("type_id") == task_type:
            return t.get("skills", {}).get("uncovered", [])
    return []


def format_uncovered_skills_prompt(task_type: str, uncovered: list[str]) -> str:
    """格式化技能缺口提示文本，注入到拆解 prompt 中。"""
    if not uncovered:
        return ""
    skill_list = "\n".join(f"  - {s}" for s in uncovered)
    return f"""

## ⚠ 技能缺口检测
本任务类型 `{task_type}` 标记了以下缺失技能（从 Task-Type-Registry.uncovered 读取）：
{skill_list}

这些技能 **当前未安装**，部分子任务可能无法执行或需要降级方案。
**建议**：在继续拆解前，先安装缺失技能。回复「安装技能」开始安装流程（会自动走完整的安全闸门 + 沙箱试运行 + 确认部署）。
"""


def _build_subtasks_from_briefs(task_id: str, briefs_content: str, min_count: int, llm_descriptions: list[str] | None = None) -> list[dict]:
    """从 briefs 内容构建子任务条目，优先使用 LLM 拆解的子任务描述。"""
    from datetime import date as _date

    subs = []
    title_match = re.search(r"# .+?[：:]\s*(.+)", briefs_content)
    brief_title = title_match.group(1).strip() if title_match else task_id

    output_path = ""
    op_match = re.search(r"\[auto_fill\]\s*产出路径[：:]\s*(.+)", briefs_content)
    if op_match:
        output_path = op_match.group(1).strip().strip("`")
    else:
        output_path = f"Simulation-Sandbox/outputs/{task_id}/"

    def _day_offset(offset: int) -> str:
        return (_date.today() + __import__("datetime").timedelta(days=offset)).isoformat()

    if "代码审查" in briefs_content or "code_review" in briefs_content:
        subs = [
            {"id": f"{task_id}-PT1", "description": "扫描并分析目标文件的代码问题", "method": "扫描", "estimated_minutes": 15,
             "output_to": output_path, "planned_completion": _day_offset(0)},
            {"id": f"{task_id}-PT2", "description": "生成代码审查报告", "method": "撰写", "estimated_minutes": 30,
             "output_to": output_path, "planned_completion": _day_offset(1)},
        ]
    else:
        for i in range(1, min_count + 1):
            desc = f"{brief_title} — 子任务 {i}"
            if llm_descriptions and i <= len(llm_descriptions):
                desc = llm_descriptions[i - 1]
            subs.append({"id": f"{task_id}-PT{i}", "description": desc,
                         "method": "按 briefs 要求执行", "estimated_minutes": 30,
                         "output_to": output_path, "planned_completion": _day_offset(i - 1)})

    # 保证至少 min_count 条
    while len(subs) < min_count:
        i = len(subs) + 1
        subs.append({"id": f"{task_id}-PT{i}", "description": f"{task_id} 子任务 {i}", "method": "按 briefs 要求执行", "estimated_minutes": 30, "output_to": ""})

    # 注入顺序依赖：PT2 依赖 PT1，PT3 依赖 PT2...
    for i, s in enumerate(subs):
        if i > 0:
            prev_id = f"{task_id}-PT{i}"
            s["depends_on"] = [prev_id]
            s["input_from"] = [{"from_task": prev_id, "asset": subs[i - 1].get("output_to", "前序产出物")}]

    return subs[:min_count]


def write_to_pending_tracker(
    subtasks: list[dict],
    source_task: str,
    *,
    project_dir: Path,
) -> int:
    """将子任务写入 Pending-Plan-Tracker.json，同时标记父任务为 completed。返回写入的条目数。"""
    from datetime import date

    tracker_path = project_dir / "core" / "data" / "Pending-Plan-Tracker.json"
    if not tracker_path.exists():
        data = {"meta": {"pending_fields": ["id", "description", "source_task", "status", "estimated_minutes", "output_to", "planned_completion"]}, "pending": []}
    else:
        data = _json.loads(tracker_path.read_text(encoding="utf-8"))

    pending: list = data.setdefault("pending", [])

    # 幂等：先删除同 source_task 的旧子任务，避免重复追加
    pending[:] = [item for item in pending if item.get("source_task") != source_task or item.get("id") == source_task]

    # 标记父任务为 in_progress（拆解后进入执行阶段，全子任务完成后才 completed）
    for item in pending:
        if item.get("id") == source_task:
            item["status"] = "in_progress"
            break

    count = 0
    today = date.today().isoformat()
    for i, st in enumerate(subtasks, 1):
        pending.append(
            {
                "id": st.get("id", f"{source_task}-PT{i}"),
                "description": st.get("description", st.get("method", "")),
                "source_task": source_task,
                "status": "pending",
                "estimated_minutes": st.get("estimated_minutes", 30),
                "output_to": st.get("output_to", ""),
                "planned_completion": st.get("planned_completion", today),
                "method": st.get("method", ""),
                "depends_on": st.get("depends_on", []),
                "input_from": st.get("input_from", []),
            }
        )
        count += 1

    tracker_path.write_text(_json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return count


# ── 阶段 6：统一入口（供 socius_cli 调用） ──

def v012_orchestrate(
    task_id: str,
    *,
    project_dir: Path,
    adapter: Any,  # CursorAdapter
    debug: bool = False,
) -> dict:
    """V012 管线代码化编排主函数。

    Returns:
        {"phase": "C-ter" | "N=1_skip", "subtasks": [...], "pending_count": int}
    """
    sandbox = project_dir / "Simulation-Sandbox"

    # ── 阶段 A：数据合并 ──
    task_pool_path = sandbox / "task-pool.json"
    briefs_path = sandbox / "briefs" / f"{task_id}.md"
    registry_path = project_dir / "core" / "data" / "Task-Type-Registry.json"

    # 读取 task-pool 条目获取 task_type
    task_type = ""
    if task_pool_path.exists():
        pool = _json.loads(task_pool_path.read_text(encoding="utf-8"))
        for t in pool.get("tasks", []):
            if t.get("id") == task_id:
                task_type = t.get("task_type", "")
                # composite 类型没有直接对应的 registry 条目，用 task_type_registry 回溯
                if task_type == "composite":
                    task_type = t.get("task_type_registry", task_type)
                break

    # 合并 slots
    slots = resolve_slots(briefs_path, registry_path, task_type, project_dir=project_dir)
    must_ask = [s for s in slots if s["strategy"] == "must_ask"]

    # N 判定：基于 Task-Type-Registry 中该 task_type 需要的工具种类数
    # 工具数 = internal_skills + external_skills（不含 candidates/uncovered）
    tool_count = _get_tool_count(registry_path, task_type)
    # 1 个工具及以下 → 简单任务；≥2 个工具 → 复杂任务
    N = 1 if tool_count <= 1 else max(2, tool_count)

    if debug:
        print(f"[V012 Orchestrator] {task_id} task_type={task_type}, tools={tool_count}, N={N}, must_ask={len(must_ask)}/{len(slots)}")

    # ── 阶段 B：逐项确认（如果还有 must_ask） ──
    briefs_content = briefs_path.read_text(encoding="utf-8") if briefs_path.exists() else ""

    if must_ask:
        print(f"\n    请补全以下信息（共 {len(must_ask)} 项）：\n")

        # 从 briefs 原文中提取每个 must_ask 的完整描述（含括号提示）
        briefs_raw_items = {}
        for m in re.finditer(r"- \[must_ask\]\s+(.+)", briefs_content):
            briefs_raw_items[m.group(1).split("（", 1)[0].strip("*").strip()] = m.group(1).strip()

        for i, s in enumerate(must_ask, 1):
            label = s["label_cn"]
            # 尝试从 briefs 原文取完整描述（含括号提示），fallback 到 label_cn
            prompt_text = briefs_raw_items.get(label, label)
            try:
                print(f"    ({i}/{len(must_ask)}) {prompt_text}")
                answer = input("    > ").strip()
            except (EOFError, KeyboardInterrupt):
                answer = ""
            # 空输入时尝试从 briefs 提示中提取默认值
            if not answer:
                raw_text = briefs_raw_items.get(label, "")
                m_default = re.search(r"默认(.+?)[）)]", raw_text)
                if m_default:
                    answer = m_default.group(1).strip()
            # 将回答追加到 briefs_content，供后续拆解阶段参考
            briefs_content += f"\n> [user_answered] {label}：{answer}"
            display_val = answer or "(跳过)"
            print(f"    ✅ 已记录：{label} → {display_val}\n")

        # 槽位值落盘：追加写入 briefs 文件，供断点续跑时恢复
        if briefs_path.exists():
            briefs_path.write_text(briefs_content, encoding="utf-8")
    else:
        if debug:
            print("[V012 Orchestrator] 阶段 B: 无需确认，跳过")

    # ── 阶段 C：拆解（LLM 输出拆解方案）──
    print("    ⚙ 正在分析任务结构并拆解为子任务...")
    # 技能缺口检测：检查 Task-Type-Registry 中该 task_type 的 uncovered 条目
    _uncovered = _get_uncovered_skills(registry_path, task_type)
    _uncovered_hint = format_uncovered_skills_prompt(task_type, _uncovered) if _uncovered else ""
    if _uncovered:
        print(f"    ⚠ 检测到 {len(_uncovered)} 个缺失技能: {_uncovered}")
        print("    💡 建议先安装缺失技能——回复「安装技能」开始安装流程")
    decompose_prompt = build_decompose_prompt(task_id, briefs_content, slots) + _uncovered_hint
    decompose_result = adapter.model_provider.complete(
        decompose_prompt,
        system_prompt="你是任务拆解专家。分析任务后给出拆解方案（至少 " + str(N) + " 个子任务），然后 DONE。",
    )
    if debug:
        print(f"[V012 Orchestrator] 阶段 C 拆解: {decompose_result[:300]}")

    # N 判定：基于工具数（已在 stage A 计算）
    if debug:
        print(f"[V012 Orchestrator] N = {N} (from tool count)")

    # ── N=1 分叉 → 直接走 P008 ──
    if N <= 1:
        return {"phase": "N=1_skip", "subtasks": [], "pending_count": 0}

    # ── N≥2：C-bis + C-ter ──
    # 尝试从 LLM 拆解结果中提取子任务描述，失败则回退到模板
    # 多策略提取：主正则 → 宽松正则 → method 行 → 放弃
    llm_subtask_descs: list[str] | None = None
    if decompose_result:
        # 每次拆解写文件（带时间戳），方便事后排查
        from datetime import datetime as _dt
        _dump_path = project_dir / "Simulation-Sandbox" / "logs" / f"decompose-{task_id}-{_dt.now().strftime('%Y%m%d-%H%M%S')}.txt"
        _dump_path.parent.mkdir(parents=True, exist_ok=True)
        _dump_path.write_text(decompose_result, encoding="utf-8")

        descs: list[str] = []

        # 策略 1：严格编号行（编号后紧跟描述，同行）
        _raw1 = re.findall(r'(?:^|\n)\s*\*{0,2}\d+\s*[.、)）]\s*(.+?)(?:\n|$)', decompose_result, re.MULTILINE)
        if _raw1:
            descs.extend(_raw1)

        # 策略 2：宽松编号行（允许描述跨行，取编号后到下一个编号前的第一行）
        if not descs:
            _blocks = re.split(r'(?:^|\n)\s*\*{0,2}\d+\s*[.、)）]', decompose_result)
            for b in _blocks[1:]:  # 跳过第一个空块
                _first_line = b.strip().split("\n")[0].strip()
                if _first_line and len(_first_line) > 3:
                    descs.append(_first_line)

        # 策略 3：从 method: 行提取
        if not descs:
            _method_lines = re.findall(r'^[Mm]ethod[：:]\s*(.+?)$', decompose_result, re.MULTILINE)
            if _method_lines:
                descs = _method_lines

        if descs:
            # 清洗：去首尾星号，截断到 60 字
            valid = [d.strip().strip("*").strip()[:60] for d in descs if len(d.strip().strip("*")) > 3]
            if valid:
                llm_subtask_descs = valid

        print(f"[V012 Orchestrator] LLM 子任务描述提取 ({len(descs)} raw → "
              f"{len(llm_subtask_descs) if llm_subtask_descs else 0} valid): {llm_subtask_descs}")
    subs = _build_subtasks_from_briefs(task_id, briefs_content, N, llm_descriptions=llm_subtask_descs)
    if not subs:
        # 兜底：基于 N 构造最简子任务
        subs = []
        for i in range(1, N + 1):
            subs.append({
                "id": f"{task_id}-PT{i}",
                "description": f"{task_id} 子任务 {i}",
                "method": "按 briefs 要求执行",
                "estimated_minutes": 30,
                "output_to": "",
            })

    # ── C-bis：展示拆解结果 + 确认 + 用户选择 ──
    from datetime import date as _date_c
    _today_c = _date_c.today()

    _max_adjust = len(subs)
    _adjust_count = 0

    def _show_panel(subtasks: list[dict], show_adjust_hint: bool = True) -> None:
        print(f"\n    当前任务预计分为 {len(subtasks)} 个阶段进行：\n")
        print("    ┌──────┬──────────────────────────────────────┬────────┬──────────────┐")
        print("    │  #   │ 阶段                                  │ 预估   │ 计划日期      │")
        print("    ├──────┼──────────────────────────────────────┼────────┼──────────────┤")
        for i, s in enumerate(subtasks, 1):
            desc_short = s["description"][:36]
            mins = s.get("estimated_minutes", "?")
            date_str = s.get("planned_completion", "-")
            deps = s.get("depends_on", [])
            if deps:
                dep_labels = [re.sub(r".*PT(\d+)$", r"阶段\1", d) for d in deps]
                dep_note = f" (需先完成 {', '.join(dep_labels)})"
            else:
                dep_note = ""
            print(f"    │  {i:<3} │ {desc_short:<36} │ {str(mins)+'min':<6} │ {date_str:<12} │")
            if dep_note:
                print(f"    │      │ {'↳ ' + dep_note.strip():<49} │        │              │")
        print("    └──────┴──────────────────────────────────────┴────────┴──────────────┘")
        print("\n    以上拆解是否合理？")
        print("      1) 写入任务，稍后手动执行")
        print("      2) 写入任务 + 立即开始执行第一阶段")
        if show_adjust_hint:
            print("      如需调整排期，直接输入调整内容（如「阶段2调整到5月26日」）。")
        print()

    _show_panel(subs)

    execute_first = False
    while True:
        try:
            confirm = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            confirm = ""

        # ── 选项识别（宽松匹配）──
        if confirm in ("2",) or any(k in confirm for k in ("立即", "第一", "执行第一", "开始执行第")):
            execute_first = True
            break
        if confirm in ("1",) or any(k in confirm for k in ("稍后", "手动")):
            break
        if confirm.lower() in ("确认", "y", "yes", "ok", "好", "可以", "行", "是", "继续", ""):
            break

        # ── 排期调整：阶段N调整到M月D日 ──
        adj_match = re.search(r"阶段\s*(\d+).*?(\d{1,2})\s*月\s*(\d{1,2})\s*日?", confirm)
        if adj_match:
            stage_idx = int(adj_match.group(1)) - 1
            new_m, new_d = int(adj_match.group(2)), int(adj_match.group(3))
            try:
                new_date = _date_c(2026, new_m, new_d)
            except ValueError:
                print(f"    ⚠ 无效日期：{new_m}月{new_d}日，请重新输入")
                continue
            if new_date < _today_c:
                print(f"    ⚠ 不能早于今天（{_today_c}），请重新输入")
                continue
            if stage_idx < 0 or stage_idx >= len(subs):
                print(f"    ⚠ 阶段 {stage_idx + 1} 不存在（共 {len(subs)} 个阶段），请重新输入")
                continue
            # 更新日期
            subs[stage_idx]["planned_completion"] = new_date.isoformat()
            _adjust_count += 1
            print(f"    ✅ 已更新：阶段{stage_idx + 1} → {new_date.isoformat()}" +
                  (f"（调整 {_adjust_count}/{_max_adjust}）" if _adjust_count < _max_adjust else "（已达调整上限）"))
            _show_panel(subs, show_adjust_hint=(_adjust_count < _max_adjust))
            # 检查顺序一致性（仅警告，不阻塞）
            for i in range(1, len(subs)):
                prev_d = subs[i - 1].get("planned_completion", "")
                curr_d = subs[i].get("planned_completion", "")
                if prev_d and curr_d and prev_d > curr_d:
                    print(f"    ⚠ 注意：阶段{i} 在阶段{i+1} 之后（{prev_d} > {curr_d}），可能不合理的顺序")
                    break
            continue

        # ── 未识别 ──
        print("    未识别输入。请回复「确认」/ 1 / 2 / 或「阶段N调整到M月D日」。")

    # ── 日负载检查（确认后、写入前）──
    load_warnings: list[str] = []
    try:
        # LoadCalculator 已移入 core/，可直接导入
        from core.load_calculator import LoadCalculator
        from datetime import date as _date2
        _lc = LoadCalculator(
            tracker_path=project_dir / "core" / "data" / "Pending-Plan-Tracker.json",
        )
        _report = _lc.calculate()
        _today = _date2.today().isoformat()
        for s in subs:
            _pd = s.get("planned_completion", _today)
            _mins = s.get("estimated_minutes", 30)
            _can, _msg = _lc.can_schedule(_pd, _mins)
            if not _can:
                load_warnings.append(f"🔴 {_pd}：{_msg}")
            elif "⚠" in _msg:
                load_warnings.append(f"🟡 {_pd}：{_msg}")
    except Exception:
        load_warnings = ["⚠ 负载计算不可用，已跳过日负载检查"]

    if load_warnings:
        print("\n    📊 日负载提醒：")
        for w in load_warnings:
            print(f"       {w}")
        print()

    if debug:
        print(f"[V012 Orchestrator] C-ter: 写入 {len(subs)} 条到 Pending-Plan-Tracker")

    # C-ter：写入 Pending-Plan-Tracker（纯代码）
    pending_count = write_to_pending_tracker(subs, task_id, project_dir=project_dir)

    first_subtask_id = subs[0]["id"] if subs else ""
    # 提取阶段 B 收集到的槽位值，供子任务执行时注入上下文
    collected_slot_lines = [
        line for line in briefs_content.split("\n")
        if line.strip().startswith("> [user_answered]")
    ]
    return {
        "phase": "C-ter",
        "subtasks": subs,
        "pending_count": pending_count,
        "load_warnings": load_warnings,
        "execute_first": execute_first,
        "first_subtask_id": first_subtask_id,
        "collected_slots": "\n".join(collected_slot_lines),
    }
