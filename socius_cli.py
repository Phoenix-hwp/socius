"""
Socius CLI — 框架层独立运行入口点。

不依赖 Cursor IDE。通过 ``pip install -e .`` 安装后，在终端直接运行::

    socius run --task-type notion_create --model deepseek-v4-pro

    socius list-models

    socius verify

框架层：
    - 加载规则 → ContextBuilder 组装上下文
    - 选择模型 → IModelProvider 实现（DeepSeek/Kimi/Ollama）
    - 执行 Agent 循环 → read → think → act → observe
    - 工具调用 → IToolProvider 实现

Usage:
    socius run [--task-type TYPE] [--model MODEL] [--prompt TEXT]
    socius list-models
    socius verify

"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# 确保 REPO_ROOT 在 sys.path 中
_REPO_ROOT = Path(__file__).resolve().parent  # socius_cli.py 在仓库根目录
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.model_registry import list_models
from adapters.cursor.adapter import CursorAdapter
from core.context_builder import ContextBuilder

logger = logging.getLogger("socius")


def cmd_list_models():
    """列出所有已注册的模型。"""
    models = list_models()
    print("\n已注册模型:\n")
    print(f"  {'模型ID':<25} {'显示名':<30} {'需要 API Key':<15} {'最大上下文':<15}")
    print(f"  {'-'*25} {'-'*30} {'-'*15} {'-'*15}")
    for m in models:
        key_needed = "是" if m["requires_api_key"] else "否（本地）"
        tokens = f"{m['max_context_tokens']:,}"
        print(f"  {m['model_id']:<25} {m['display_name']:<30} {key_needed:<15} {tokens:<15}")


def cmd_verify():
    """快速自检——验证框架层各组件可用性。"""
    print("Socius 框架层自检\n" + "=" * 60)

    adapter = CursorAdapter(project_dir=str(_REPO_ROOT))
    summary = adapter.summary()

    checks = [
        ("平台", summary["platform"]),
        ("项目目录", summary["project_dir"]),
        ("当前模型", summary["model"]),
        ("已加载规则", str(summary["rules_loaded"])),
        ("已发现技能", str(summary["skills_discovered"])),
        ("钩子事件", str(len(summary["hook_events"])) + " 个"),
        ("可用工具", str(len(summary["tools"])) + " 个"),
    ]

    for label, value in checks:
        print(f"  {label:<12}: {value}")

    # 上下文构建器测试
    builder = ContextBuilder(
        rule_engine=adapter.rule_engine,
        skill_loader=adapter.skill_loader,
        project_dir=str(_REPO_ROOT),
    )
    ctx = builder.build(task_context={"task_type": "notion_create", "domain": "notion"})
    ctx_lines = ctx.count("\n")
    print(f"  上下文长度    : {len(ctx)} 字符, {ctx_lines} 行")
    print(f"  上下文包含 GUARD 前缀: {'<!-- GUARD_MANDATORY_PREFIX -->' in ctx}")

    print("\n✅ 框架层自检通过")


def cmd_run(args: argparse.Namespace):
    """执行 Agent 循环 — 框架层独立运行。

    Agent 循环:
        1. ContextBuilder 组装上下文（规则 + 技能 + 任务标签）
        2. IModelProvider.complete() 调用模型推理
        3. 解析输出 → 提取工具调用 → IToolProvider.execute()
        4. 工具结果反馈 → 下一轮推理 → 直到完成
    """
    task_type = args.task_type or "general"
    model_name = args.model or "deepseek-v4-pro"
    user_prompt = args.prompt

    if not user_prompt:
        print("请输入任务描述（CTRL+D 结束）:")
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except (EOFError, KeyboardInterrupt):
            pass
        user_prompt = "\n".join(lines)

    if not user_prompt.strip():
        print("❌ 任务描述不能为空")
        sys.exit(1)

    print(f"\n🚀 Socius Agent 启动")
    print(f"  任务类型: {task_type}")
    print(f"  模型: {model_name}")
    print(f"  任务: {user_prompt[:80]}{'...' if len(user_prompt) > 80 else ''}")
    print("=" * 60)

    try:
        adapter = CursorAdapter(project_dir=str(_REPO_ROOT), model_name=model_name)
    except RuntimeError as e:
        print(f"\n❌ 模型初始化失败: {e}")
        print(f"\n提示: 设置环境变量 {model_name.upper()}_API_KEY 或使用本地模型（ollama-local / lmstudio-local）")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ {e}")
        sys.exit(1)

    # 1. 构建上下文
    builder = ContextBuilder(
        rule_engine=adapter.rule_engine,
        skill_loader=adapter.skill_loader,
        project_dir=str(_REPO_ROOT),
    )
    context = builder.build(
        task_context={
            "task_type": task_type,
            "domain": args.domain or "general",
            "risk_level": args.risk_level or "low",
        },
    )

    # 2. 组装 system_prompt
    system_prompt = f"""{context}

你是一个 Socius 框架的 Agent（工作搭档）。你有以下工具可用：
- read(path, offset=0, limit=None): 读取文件
- write(path, contents): 写入文件
- shell(command, working_directory=None, block_until_ms=30000): 执行命令
- grep(pattern, path=None): 搜索文本
- glob(glob_pattern, target_directory=None): 匹配文件列表
- delete(path): 删除文件

输出格式：
1. 思考过程（以 "THINK:" 开头，1-3 句）
2. 工具调用（以 "TOOL: tool_name" 开头，然后是 tool_name(params) 格式）
3. 完成时输出 "DONE" 并说明结果

用户任务: {user_prompt}
"""

    # 3. Agent 循环（最多 10 轮）
    max_rounds = 10
    conversation = [{"role": "system", "content": system_prompt}]

    for round_num in range(1, max_rounds + 1):
        print(f"\n--- 第 {round_num} 轮 ---")

        # 调用模型
        try:
            messages = "\n".join(
                f"[{m['role']}]: {m['content'][:200]}" for m in conversation[-3:]
            )
            response = adapter.model_provider.complete(
                f"对话历史:\n{messages}\n\n请输出你的思考过程和下一步行动。",
                system_prompt=system_prompt,
            )
        except RuntimeError as e:
            print(f"❌ 模型调用失败: {e}")
            break

        response = response.strip()
        print(f"模型输出:\n{response[:500]}")

        # 检查是否完成
        if "DONE" in response:
            print("\n✅ Agent 任务完成")
            break

        # 解析工具调用
        tool = _parse_tool_call(response)
        if tool:
            tool_name = tool["name"]
            tool_params = tool["params"]
            print(f"\n🔧 工具调用: {tool_name}({tool_params})")

            result = adapter.tool_provider.execute(tool_name, **tool_params)
            if result["success"]:
                output = result["output"][:500]
                print(f"✅ 结果 ({len(result['output'])} 字符):\n{output}")
            else:
                print(f"❌ 失败: {result['error']}")

            conversation.append({"role": "assistant", "content": response})
            conversation.append({
                "role": "user",
                "content": f"工具 {tool_name} 返回: {result['output'][:1000]}",
            })
        else:
            print("⚠ 未检测到工具调用，结束循环")
            break
    else:
        print(f"\n⚠ 达到最大轮次 ({max_rounds})，结束")


def _parse_tool_call(text: str) -> dict | None:
    """从模型输出中解析工具调用。

    支持格式:
        TOOL: read
        read(path="file.md")
        read(path="file.md", offset=0, limit=10)
    """
    import re

    # 模式 1: TOOL: tool_name
    tool_match = re.search(r"TOOL:\s*(\w+)", text)
    # 模式 2: tool_name(params)
    param_match = re.search(r"(\w+)\((.+?)\)", text)

    if not tool_match and not param_match:
        return None

    tool_name = (tool_match.group(1) if tool_match else param_match.group(1)).lower()

    params = {}
    if param_match:
        raw_params = param_match.group(2)
        # 解析 key="value" 格式的参数
        for match in re.finditer(r'(\w+)\s*=\s*"([^"]*)"', raw_params):
            key = match.group(1)
            value = match.group(2)
            # 尝试转换为数字
            try:
                value = int(value)  # type: ignore[assignment]
            except ValueError:
                pass
            params[key] = value

    # 特殊处理: 如果 text 以 "read" 开头且包含文件路径
    if not params and tool_name == "read":
        path_match = re.search(r'"([^"]+)"', text)
        if path_match:
            params["path"] = path_match.group(1)

    return {"name": tool_name, "params": params}


def main():
    parser = argparse.ArgumentParser(
        description="Socius Framework CLI — 框架层独立运行入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  socius list-models                     # 列出所有已注册模型
  socius verify                          # 框架层自检
  socius run --task-type notion_create   # 执行 Agent 任务
  socius run --model ollama-local --prompt "读取 README.md"
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # list-models
    subparsers.add_parser("list-models", help="列出所有已注册的模型")

    # verify
    subparsers.add_parser("verify", help="框架层自检")

    # run
    run_parser = subparsers.add_parser("run", help="执行 Agent 任务")
    run_parser.add_argument("--task-type", type=str, help="任务类型（如 notion_create, knowledge_digestion）")
    run_parser.add_argument("--domain", type=str, help="知识域（如 notion, git）")
    run_parser.add_argument("--risk-level", type=str, choices=["low", "medium", "high"], default="low")
    run_parser.add_argument("--model", type=str, help="模型标识符（如 deepseek-v4-pro, kimi-k2.6, ollama-local）")
    run_parser.add_argument("--prompt", type=str, help="任务描述（不提供则从 stdin 读取）")

    args = parser.parse_args()

    if args.command == "list-models":
        cmd_list_models()
    elif args.command == "verify":
        cmd_verify()
    elif args.command == "run":
        cmd_run(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
