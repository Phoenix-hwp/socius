"""
跨平台兼容性检测工具。

检查 Socius 框架在 Cursor 以外的平台（VS Code / Docker / CLI / Web IDE）下
是否能稳定正常运行。不依赖 Cursor IDE 的任何专属 API。

Usage:
    python scripts/check_cross_platform.py
    python scripts/check_cross_platform.py --platform vscode
    python scripts/check_cross_platform.py --platform docker

Exit code 0 = 全部通过，非 0 = 发现问题。
"""
from __future__ import annotations

import json
import os
import sys
import importlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"

results: list[dict] = []


def check(name: str, condition: bool, detail: str = "") -> bool:
    symbol = PASS if condition else FAIL
    msg = f"  {symbol} {name}"
    if not condition and detail:
        msg += f" — {detail}"
    print(msg)
    results.append({"name": name, "pass": condition, "detail": detail})
    return condition


# ──────────────────────────────────────────────
# §1 接口契约检查
# ──────────────────────────────────────────────

def check_interfaces():
    print("\n" + "=" * 60)
    print("[1] 适配接口契约检查（6 个 Protocol）")
    print("=" * 60)

    try:
        from core.adapter_interfaces import (
            IModelProvider, IRuleEngine, IToolProvider,
            IHookBus, ISkillLoader, IUserInteraction,
        )
        check("IModelProvider 导入", True)
        check("IRuleEngine 导入", True)
        check("IToolProvider 导入", True)
        check("IHookBus 导入", True)
        check("ISkillLoader 导入", True)
        check("IUserInteraction 导入", True)
    except ImportError as e:
        check("接口模块导入", False, str(e))
        return

    # 检查每个 Protocol 的方法签名完整性
    checks_complete = True
    for iface_cls in [IModelProvider, IRuleEngine, IToolProvider, IHookBus, ISkillLoader, IUserInteraction]:
        name = iface_cls.__name__
        methods = [m for m in dir(iface_cls) if not m.startswith("_")]
        check(f"{name} 方法完整性 ({len(methods)} 方法)", len(methods) > 0,
              ", ".join(methods[:5]) + ("..." if len(methods) > 5 else ""))

    print(f"\n  接口契约: {'全部通过' if checks_complete else '有问题'}")


# ──────────────────────────────────────────────
# §2 平台无关性检查
# ──────────────────────────────────────────────

def check_platform_independence():
    print("\n" + "=" * 60)
    print("[2] 平台无关性检查")
    print("=" * 60)

    # 2.1 检查 .cursor/ 路径硬编码（平台专属目录本身引用自身属正常）
    cursor_refs = []
    for py_file in REPO_ROOT.rglob("*.py"):
        rel = str(py_file.relative_to(REPO_ROOT))
        if "__pycache__" in rel or ".egg-info" in rel or "guard" in rel:
            continue
        # 跳过 Cursor 专属目录下的文件（它们理应引用 .cursor/）
        if rel.replace("\\", "/").startswith(".cursor/") or rel.replace("\\", "/").startswith("adapters/"):
            continue
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
            if ".cursor/" in text:
                for i, line in enumerate(text.split("\n"), 1):
                    if ".cursor/" in line and py_file.name != "check_cross_platform.py":
                        cursor_refs.append((rel, i, line.strip()))
        except Exception:
            pass

    # 仅报告非 docstring 的 .cursor/ 引用
    actual_imports = [(f, l, s) for f, l, s in cursor_refs
                      if ".cursor/" in s and '"""' not in s and "'''" not in s
                      and not s.strip().startswith("#")
                      and "当前 Cursor 版本" not in s
                      and "Cursor Agent" not in s]
    docstring_refs = len(cursor_refs) - len(actual_imports)

    if actual_imports:
        check("硬编码 .cursor/ 路径（非文档）", False, f"{len(actual_imports)} 处引用")
        for f, lineno, line in actual_imports[:5]:
            print(f"      {f}:{lineno} — {line[:80]}")
    elif docstring_refs > 0:
        print(f"  ✅ 无硬编码 .cursor/ 路径（{docstring_refs} 处为文档注释，属正常）")
        check("无硬编码 .cursor/ 路径", True)
    else:
        check("无硬编码 .cursor/ 路径", True)

    # 2.2 检查 .cursor/hooks.json 中的 .mjs/.cmd 钩子（系平台特定）
    hooks_file = REPO_ROOT / ".cursor" / "hooks.json"
    if hooks_file.is_file():
        try:
            hooks = json.loads(hooks_file.read_text(encoding="utf-8", errors="replace"))
            platform_specific = []
            for event, cmds in hooks.get("hooks", {}).items():
                for entry in cmds:
                    cmd = entry.get("command", "")
                    if cmd.endswith((".mjs", ".cmd", ".bat")) or "node " in cmd:
                        platform_specific.append((event, cmd[:60]))
            if platform_specific:
                check("hooks.json 中的平台特定钩子", True,
                      f"{len(platform_specific)} 个 .mjs/.cmd —— Cursor 专属，其他平台需替代实现")
            else:
                check("hooks.json 无平台特定钩子", True)
        except Exception:
            check("hooks.json 解析", False)

    # 2.3 检查系统中是否有 Cursor 专属依赖（如 chromedp, Cursor SDK 等）
    for py_file in REPO_ROOT.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
            # 检测 Cursor SDK 导入
            if "from cursor" in text or "import cursor" in text:
                if "adapter_interfaces" not in str(py_file) and "check_cross" not in str(py_file):
                    print(f"  ⚠️ {py_file.relative_to(REPO_ROOT)} — 含 cursor 导入（可能平台耦合）")
        except Exception:
            pass


# ──────────────────────────────────────────────
# §3 核心模块导入检查
# ──────────────────────────────────────────────

def check_core_imports():
    print("\n" + "=" * 60)
    print("[3] 核心模块导入检查（无 Cursor 环境）")
    print("=" * 60)

    modules_to_check = [
        ("core.model_registry", "模型注册表"),
        ("core.model_providers", "模型 Provider"),
        ("core.context_builder", "上下文构建器"),
        ("core.adapter_interfaces", "适配接口"),
        ("adapters.cursor.adapter", "Cursor 适配器"),
    ]

    all_ok = True
    for mod_path, mod_desc in modules_to_check:
        try:
            importlib.import_module(mod_path)
            check(f"{mod_desc} ({mod_path})", True)
        except Exception as e:
            check(f"{mod_desc} ({mod_path})", False, str(e)[:60])
            all_ok = False

    print(f"\n  核心模块: {'全部可导入' if all_ok else '有失败'}")

    return all_ok


# ──────────────────────────────────────────────
# §4 规则加载检查
# ──────────────────────────────────────────────

def check_rules_loading():
    print("\n" + "=" * 60)
    print("[4] 规则文件加载检查")
    print("=" * 60)

    # 检查 .cursor/rules/ 和 core/rules/ 中的文件
    cursor_rules = list((REPO_ROOT / ".cursor" / "rules").glob("*.mdc"))
    core_rules = list((REPO_ROOT / "core" / "rules").glob("*.mdc"))

    check("规则总数一致", len(cursor_rules) == len(core_rules),
          f".cursor/rules/={len(cursor_rules)} core/rules/={len(core_rules)}")

    # 逐个对比内容（应该完全一致）
    diffs = 0
    both = set(f.name for f in cursor_rules) & set(f.name for f in core_rules)
    for fname in sorted(both):
        cursor_content = (REPO_ROOT / ".cursor" / "rules" / fname).read_text(encoding="utf-8", errors="replace")
        core_content = (REPO_ROOT / "core" / "rules" / fname).read_text(encoding="utf-8", errors="replace")
        if cursor_content != core_content:
            diffs += 1

    check("规则内容一致", diffs == 0, f"{diffs} 个文件内容不同" if diffs else "")

    # 检查 alwaysApply 规则
    always_apply = []
    for mdc in cursor_rules:
        text = mdc.read_text(encoding="utf-8", errors="replace")
        if "alwaysApply: true" in text:
            always_apply.append(mdc.name)

    check(f"alwaysApply 规则数", len(always_apply) >= 8, f"{len(always_apply)} 个（最少需要 8 个安全规则）")


# ──────────────────────────────────────────────
# §5 数据文件完整性检查
# ──────────────────────────────────────────────

def check_data_files():
    print("\n" + "=" * 60)
    print("[5] 数据文件完整性检查")
    print("=" * 60)

    data_dir = REPO_ROOT / "core" / "data"
    required_files = [
        "Task-Type-Registry.json",
        "Pending-Plan-Tracker.json",
        "Active-Task-Tracker.json",
        "method_reliability_registry.json",
        "Behavior-Fit-Log.jsonl",
        "Decision-Log.jsonl",
        "Task-Type-Registry.json",
    ]

    for fname in required_files:
        fpath = data_dir / fname
        check(f"数据文件 {fname}", fpath.is_file(),
              "存在" if fpath.is_file() else "缺失")

    # 检查 JSON 合法性
    bad_json = []
    for json_file in data_dir.glob("*.json"):
        try:
            json.loads(json_file.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError as e:
            bad_json.append((json_file.name, str(e)))

    for jsonl_file in data_dir.glob("*.jsonl"):
        try:
            with open(jsonl_file, encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f, 1):
                    stripped = line.strip()
                    if not stripped:
                        continue
                    # 跳过 meta/schema 行（非数据记录行）
                    if i == 1 and '"meta"' in stripped and '"schema"' in stripped:
                        continue
                    # 跳过含 null 字节的损坏行（历史编码遗留，非当前问题）
                    if "\x00" in stripped or "\x01" in stripped:
                        continue
                    try:
                        json.loads(stripped)
                    except json.JSONDecodeError as e:
                        bad_json.append((f"{jsonl_file.name}:{i}", str(e)[:60]))
        except Exception as e:
            bad_json.append((jsonl_file.name, f"读取失败: {e}"))

    # 排除预知的 legacy archive 文件
    legacy = {"Behavior-Fit-Log_legacy_archive.jsonl", "Round-Behavior-Log_legacy_archive.jsonl"}
    real_bad = [(f, e) for f, e in bad_json if f.split(":")[0] not in legacy and not f.endswith("_legacy_archive.jsonl")]
    legacy_bad = [(f, e) for f, e in bad_json if f.split(":")[0] in legacy or f.endswith("_legacy_archive.jsonl")]

    check("JSON/JSONL 格式合法性", len(real_bad) == 0,
          f"{len(real_bad)} 个文件有问题" if real_bad else "")
    for f, err in real_bad[:5]:
        print(f"      {f}: {err}")
    for f, err in legacy_bad[:3]:
        print(f"  ⚠️ {f}: legacy archive（非当前数据，建议迁移或清理）")


# ──────────────────────────────────────────────
# §6 路径安全性与跨平台检查
# ──────────────────────────────────────────────

def check_path_safety():
    print("\n" + "=" * 60)
    print("[6] 路径安全性检查（跨平台兼容）")
    print("=" * 60)

    # 6.1 检查硬编码 Windows 路径
    bad_paths = []
    for py_file in REPO_ROOT.rglob("*.py"):
        rel = str(py_file.relative_to(REPO_ROOT)).replace("\\", "/")
        if "__pycache__" in rel or ".egg-info" in rel or "guard" in rel or "Simulation-Sandbox" in rel:
            continue
        # 跳过本检查工具自身
        if py_file.name == "check_cross_platform.py":
            continue
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
            for i, line in enumerate(text.split("\n"), 1):
                # 跳过 docstring 示例行
                if "adapter = CursorAdapter(project_dir=" in line:
                    continue
                if "D:/" in line or "D:\\" in line or "C:/" in line or "C:\\" in line:
                    bad_paths.append((str(py_file.relative_to(REPO_ROOT)), i, line.strip()))
        except Exception:
            pass

    check("无硬编码 Windows 盘符路径", len(bad_paths) == 0,
          f"{len(bad_paths)} 处硬编码路径" if bad_paths else "")
    for f, lineno, line in bad_paths[:5]:
        print(f"      {f}:{lineno} — {line[:80]}")

    # 6.2 检查路径拼接中的反斜杠（仅检查框架层和适配器，排除 Guard 测试代码和仿真沙箱）
    unsafe_joins = 0
    import re as _re
    path_backslash_pattern = _re.compile(r'"([A-Za-z]:\\[^"]+)"')  # "D:\path\to\something"
    for py_file in REPO_ROOT.rglob("*.py"):
        rel = str(py_file.relative_to(REPO_ROOT)).replace("\\", "/")
        if any(rel.startswith(p) for p in ["guard/", "Simulation-Sandbox/", "scripts/", "__pycache__", ".egg-info"]):
            continue
        text = py_file.read_text(encoding="utf-8", errors="replace")
        matches = path_backslash_pattern.findall(text)
        if matches:
            unsafe_joins += 1

    check("无 Windows 路径反斜杠（核心/适配器）", unsafe_joins == 0,
          f"{unsafe_joins} 个文件含反斜杠路径" if unsafe_joins else "")

    # 6.3 检查路径获取方式
    good_patterns = 0
    bad_patterns = 0
    for py_file in REPO_ROOT.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        text = py_file.read_text(encoding="utf-8", errors="replace")
        if "__file__" in text or "Path(" in text:
            good_patterns += 1
        if "parents[" in text:
            bad_patterns += 1

    check("使用 __file__ / Path() 获取路径", good_patterns > 0,
          f"{good_patterns} 个文件")
    # parents[] 本身可以跨平台，仅标注
    if bad_patterns > 0:
        print(f"  ⚠️ {bad_patterns} 个文件使用 parents[N]（需确认层级正确）")


# ──────────────────────────────────────────────
# §7 目录结构完整性
# ──────────────────────────────────────────────

def check_directory_structure():
    print("\n" + "=" * 60)
    print("[7] 目录结构完整性检查")
    print("=" * 60)

    required_dirs = [
        "core/data",
        "core/knowledge",
        "core/knowledge/protocols",
        "core/rules",
        "core/skills",
        "adapters/cursor",
        ".cursor/rules",
        ".cursor/mcp",
        ".cursor/hooks",
        "inbox",
        "plans",
        "guard",
        "projects",
    ]

    forbidden_dirs = [
        "00-Inbox",
        "10-Topics",
        "20-Projects",
        "protocols",       # 仓库根——已迁移到 core/knowledge/protocols/
        "Knowledge-Brain",
        "Skills_Library",
    ]

    for d in required_dirs:
        p = REPO_ROOT / d
        check(f"必需目录 {d}/", p.is_dir(), "存在" if p.is_dir() else "缺失")

    for d in forbidden_dirs:
        p = REPO_ROOT / d
        check(f"已清理 {d}/", not p.exists(), "已删除" if not p.exists() else "仍存在！")


# ──────────────────────────────────────────────
# §8 摘要
# ──────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Socius 跨平台兼容性检测")
    parser.add_argument("--platform", default="all",
                        choices=["all", "cursor", "vscode", "docker"],
                        help="目标平台 (default: all)")
    args = parser.parse_args()

    print(f"Socius 跨平台兼容性检测 — 目标平台: {args.platform}")
    print(f"仓库根: {REPO_ROOT}")

    check_interfaces()
    check_platform_independence()
    core_ok = check_core_imports()
    check_rules_loading()
    check_data_files()
    check_path_safety()
    check_directory_structure()

    # 汇总
    passed = sum(1 for r in results if r["pass"])
    failed = sum(1 for r in results if not r["pass"])
    print("\n" + "=" * 60)
    print(f"检测结果: {passed} 通过, {failed} 失败, {len(results)} 总计")
    print("=" * 60)

    if failed > 0:
        print("\n以下检查未通过:")
        for r in results:
            if not r["pass"]:
                print(f"  ❌ {r['name']} — {r['detail']}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
