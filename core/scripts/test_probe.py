"""自测探针脚本 — 注入 FLAG 标记 + 收集日志 + 自动扫回「亮灯地图」。

使用方式:
    python core/scripts/test_probe.py --task V012-DRILL-024 [--model deepseek-chat] [--max-rounds 20] [--no-llm]

--no-llm 模式：不调 LLM，仅验证探针框架本身（解析、文件写入、flag 收集）。
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Win GBK -> UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 仓库根
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

FLAG_LOG_PATH = _REPO_ROOT / "Simulation-Sandbox" / "logs" / "probe-flags.jsonl"
MAP_PATH = _REPO_ROOT / "Simulation-Sandbox" / "logs" / "probe-light-map.json"


def write_flag(flag_type: str, **extra):
    """写一条 flag 日志。"""
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "flag": flag_type,
        **extra,
    }
    FLAG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(FLAG_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def collect_light_map():
    """从 flag 日志生成「亮灯地图」。"""
    if not FLAG_LOG_PATH.exists():
        print("❌ 未找到 flag 日志")
        return None

    flags = []
    with open(FLAG_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                flags.append(json.loads(line))

    tally = {}
    for f in flags:
        t = f["flag"]
        tally[t] = tally.get(t, 0) + 1

    lamp_order = [
        ("PROBE_START", "[O] 探针启动", None),
        ("TOOL_OK", "[v] 工具成功", tally.get("TOOL_OK", 0)),
        ("TOOL_FAIL", "[X] 工具失败", tally.get("TOOL_FAIL", 0)),
        ("WRITE_OK", "[W] write 成功", tally.get("WRITE_OK", 0)),
        ("WRITE_FAIL", "[!] write 失败", tally.get("WRITE_FAIL", 0)),
        ("DONE_NO_WRITE", "[!] DONE 但无产出", tally.get("DONE_NO_WRITE", 0)),
        ("DONE_WITH_WRITE", "[~] DONE 有产出", tally.get("DONE_WITH_WRITE", 0)),
        ("DONE_VERIFIED", "[@] 产出验证通过", tally.get("DONE_VERIFIED", 0)),
        ("REPEAT_READ", "[R] 重复读文件", tally.get("REPEAT_READ", 0)),
        ("NO_TOOL_STREAK", "[-] 连续无工具", tally.get("NO_TOOL_STREAK", 0)),
        ("MAX_ROUNDS", "[M] 达到最大轮次", tally.get("MAX_ROUNDS", 0)),
        ("ASK_FLOW", "[F] 流程提问", tally.get("ASK_FLOW", 0)),
        ("ASK_SLOT", "[?] 槽位提问", tally.get("ASK_SLOT", 0)),
        ("PROBE_END", "[#] 探针结束", None),
    ]

    total = len(flags)
    red_count = tally.get("DONE_NO_WRITE", 0) + tally.get("TOOL_FAIL", 0)
    health = max(0, 100 - (red_count / max(total, 1)) * 100)

    result = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "total_flags": total,
        "health_pct": round(health, 1),
        "tally": tally,
        "lamps": [{"flag": t, "label": line, "count": c} for t, line, c in lamp_order],
    }
    with open(MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result


def print_light_map(result: dict):
    print("\n  ---- 亮灯地图 ---- Brain Probe ----")
    print("=" * 50)
    print(f"  flag: {result['total_flags']}  |  health: {result['health_pct']}%")
    print()
    for lamp in result["lamps"]:
        count_str = f" x{lamp['count']}" if lamp["count"] is not None else ""
        print(f"  {lamp['label']}{count_str}")
    print("=" * 50)


# ═══════════════════════════════════════════════════════
# 无 LLM 的模拟测试（仅验证探针框架）
# ═══════════════════════════════════════════════════════
def dry_run():
    FLAG_LOG_PATH.unlink(missing_ok=True)

    write_flag("PROBE_START", task="V012-DRILL-024", mode="dry")
    write_flag("TOOL_OK", tool="read", path=".cursor/rules/flow-v012-drill-bridge.mdc")
    write_flag("TOOL_OK", tool="grep", pattern="V012-DRILL-024")
    write_flag("ASK_SLOT", question="审查深度")
    write_flag("ASK_SLOT", question="输出格式")
    write_flag("TOOL_OK", tool="read", path="Simulation-Sandbox/sandbox/health_check.py")
    write_flag("WRITE_OK", path="Simulation-Sandbox/outputs/V012-DRILL-024/code-review-report.md", size=2048)
    write_flag("DONE_VERIFIED", path="Simulation-Sandbox/outputs/V012-DRILL-024/code-review-report.md")
    write_flag("PROBE_END")

    result = collect_light_map()
    if result:
        print_light_map(result)
        print("\n  ✅ 探针框架自检通过")
    else:
        print("\n  ❌ 探针框架自检失败")


# ═══════════════════════════════════════════════════════
# LLM 驱动的真实探针
# ═══════════════════════════════════════════════════════
def run_llm_probe(task_id: str, model: str, max_rounds: int, api_key: str | None = None):
    try:
        from core.model_registry import get_provider
        from core.model_providers import create_provider
    except ImportError as e:
        print(f"❌ 导入模型模块失败: {e}")
        return

    provider_id = "deepseek" if "deepseek" in model else model
    provider = get_provider(provider_id)
    if not provider:
        print(f"❌ 未注册的提供商: {provider_id}")
        return

    resolved_key = api_key or os.environ.get(provider.env_key or "", "").strip()
    if not resolved_key and provider.env_key:
        print(f"❌ 未设置 {provider.env_key}")
        return

    llm = create_provider(provider_id, model_name=model, api_key=resolved_key)
    print(f"🔌 模型: {model}  |  task: {task_id}  |  max: {max_rounds} 轮")

    clean_context = f"""你是 Socius，运行在 {_REPO_ROOT}。
你有能力：read / write / shell / grep / glob / delete / ask。

任务识别：收到 V012-DRILL-* -> read .cursor/rules/flow-v012-pipeline-execute.mdc

输出格式：
1. THINK: 简述
2. TOOL: <name>
   Arguments: {{"key": "val"}}
3. 完成时输出 DONE。输出 DONE 前必须 write 所有产出物并用 read 验证。
4. 需要向用户提问时用 TOOL: ask，禁止纯文本提问，禁止 A/B/C 选择格式。
5. 禁止询问执行流程问题。
6. 读到关键信息后立即切换动作，不要反复读同一文件。

>>> ⚡ INSTRUMENT（仅测试——不影响正常行为）
每执行完一个工具后，在 THINK 之前附加一行 FLAG: <flag_type> <detail>
其中 flag_type 是: TOOL_OK | TOOL_FAIL | WRITE_OK | WRITE_FAIL | ASK_SLOT
例如: FLAG: TOOL_OK read .cursor/rules/flow-v012-pipeline-execute.mdc
DONE 时附加 FLAG: DONE 并说明产出物路径。
禁止向用户展示 FLAG 行。"""
    system_prompt = clean_context

    FLAG_LOG_PATH.unlink(missing_ok=True)
    write_flag("PROBE_START", task=task_id, model=model, max_rounds=max_rounds)

    task_messages = [{"role": "system", "content": system_prompt}]
    recent_tools = []

    for rnd in range(1, max_rounds + 1):
        history = "\n".join(f"[{m['role'][:4]}]: {m['content'][:300]}" for m in task_messages[-15:])
        prompt = f"对话:\n{history}\n\n请输出思考与下一步行动。"

        try:
            response = llm.complete(prompt, system_prompt=system_prompt)
        except RuntimeError as e:
            print(f"\n❌ 模型调用失败 (轮 {rnd}): {e}")
            write_flag("TOOL_FAIL", tool="llm", error=str(e)[:200])
            break

        response = response.strip()
        print(f"\n{'─'*50}\n[轮 {rnd}/{max_rounds}]\n{response[:500]}")

        # 提取 FLAG 行
        flag_lines = [line.strip() for line in response.split("\n") if line.strip().startswith("FLAG:")]
        for fl in flag_lines:
            parts = fl.replace("FLAG:", "").strip().split(maxsplit=1)
            flag_type = parts[0] if parts else "UNKNOWN"
            flag_detail = parts[1] if len(parts) > 1 else ""
            write_flag(flag_type, detail=flag_detail, round=rnd)

        # DONE 检测
        _done_re = re.compile(r'(?:^|\n)DONE(?:\s|$)', re.MULTILINE)
        if _done_re.search(response):
            print(f"\n✅ 检测到 DONE (轮 {rnd})")
            _check_outputs(task_id)
            write_flag("PROBE_END")
            result = collect_light_map()
            if result:
                print_light_map(result)
            return

        # 解析工具调用
        tool = _simple_parse(response)
        if not tool:
            write_flag("NO_TOOL_STREAK", round=rnd, context=response[:120])
            task_messages.append({"role": "assistant", "content": response})
            task_messages.append({"role": "user", "content": "未检测到工具调用。请用 TOOL: ask 提问或执行 TOOL: <name>。"})
            recent_no_tool = sum(1 for m in task_messages[-4:] if m["role"] == "user" and "未检测到" in m["content"])
            if recent_no_tool >= 2:
                print("\n❌ 连续无工具调用，终止")
                write_flag("NO_TOOL_STREAK", status="terminated")
                break
            continue

        # 重复检测
        tool_sig = f"{tool['name']}:{json.dumps(tool['params'], sort_keys=True)}"
        recent_tools.append(tool_sig)
        if len(recent_tools) > 6:
            recent_tools.pop(0)
        if recent_tools.count(tool_sig) >= 3:
            print(f"\n🔶 重复检测: {tool['name']} 连续 {recent_tools.count(tool_sig)} 次")
            write_flag("REPEAT_READ", tool=tool["name"], params=json.dumps(tool["params"]))

        tool_result = _simulate_tool(tool["name"], tool["params"], task_id)

        task_messages.append({"role": "assistant", "content": response})
        task_messages.append({"role": "user", "content": f"工具 {tool['name']} 返回: {tool_result[:800]}"})

    print(f"\n⚠ 达到最大轮次 ({max_rounds})")
    write_flag("MAX_ROUNDS", max_rounds=max_rounds)
    _check_outputs(task_id)
    write_flag("PROBE_END")
    result = collect_light_map()
    if result:
        print_light_map(result)


def _simple_parse(text: str) -> dict | None:
    m = re.search(r"TOOL:\s*(\w+)", text)
    if not m:
        return None
    name = m.group(1).strip().lower()
    args_m = re.search(r"Arguments:\s*(\{.*?\})", text, re.DOTALL)
    params = {}
    if args_m:
        try:
            params = json.loads(args_m.group(1))
        except json.JSONDecodeError:
            pass
    return {"name": name, "params": params}


def _simulate_tool(name: str, params: dict, task_id: str) -> str:
    path = params.get("path", "")

    if name == "read":
        full = _REPO_ROOT / path if not Path(path).is_absolute() else Path(path)
        if full.exists():
            content = full.read_text(encoding="utf-8")[:600]
            write_flag("TOOL_OK", tool="read", path=str(path), size=len(content))
            return f"文件存在 ({full.stat().st_size} bytes):\n{content[:400]}"
        else:
            write_flag("TOOL_FAIL", tool="read", path=str(path), error="文件不存在")
            return f"文件不存在: {path}"

    if name == "write":
        full = _REPO_ROOT / path if not Path(path).is_absolute() else Path(path)
        contents = params.get("contents", "")
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(contents, encoding="utf-8")
        write_flag("WRITE_OK", path=str(path), size=len(contents))
        return f"已写入: {path} ({len(contents)} 字符)"

    if name == "ask":
        write_flag("ASK_SLOT", question=params.get("message", "")[:80])
        return "模拟用户回答: 确认"

    if name == "grep":
        return "grep 结果: (模拟，找到 2 条匹配)"

    if name == "glob":
        return "glob 结果: (模拟)\ntask-pool.json\nbriefs/V012-DRILL-024.md"

    if name == "shell":
        return "shell 模拟: 命令已执行"

    return f"工具 {name} 执行完成"


def _check_outputs(task_id: str):
    output_dir = _REPO_ROOT / "Simulation-Sandbox" / "outputs" / task_id
    if output_dir.exists():
        files = list(output_dir.rglob("*"))
        if files:
            for f in files:
                size = f.stat().st_size if f.is_file() else 0
                write_flag("DONE_VERIFIED", path=str(f.relative_to(_REPO_ROOT)), size=size)
            return
    write_flag("DONE_NO_WRITE", task=task_id)


def main():
    parser = argparse.ArgumentParser(description="Brain Probe — Socius 自测探针")
    parser.add_argument("--task", type=str, default="V012-DRILL-024", help="任务 ID")
    parser.add_argument("--model", type=str, default="deepseek-chat", help="模型名")
    parser.add_argument("--max-rounds", type=int, default=20, help="最大轮次")
    parser.add_argument("--no-llm", action="store_true", help="无 LLM 模拟测试")
    args = parser.parse_args()

    if args.no_llm:
        dry_run()
    else:
        run_llm_probe(args.task, args.model, args.max_rounds)


if __name__ == "__main__":
    main()
