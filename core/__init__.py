"""Phoenix Framework Core — 认知引擎 + P008 决策框架 + TEP 任务编排。

框架层零 Cursor 依赖。所有平台适配器通过 adapter_interfaces.py 的 Protocol 接口接入。

子包:
    knowledge/ — 认知引擎（分类器、提炼模板、激活引擎、概念树）
    guard/     — P008 决策框架 + 安全闸门
    data/      — JSON/JSONL schema + reader/writer
    skills/    — 技能注册表 + 脚本
"""

from core.adapter_interfaces import (
    IHookBus,
    IModelProvider,
    IRuleEngine,
    ISkillLoader,
    IToolProvider,
    IUserInteraction,
)

__all__ = [
    "IModelProvider",
    "IRuleEngine",
    "IToolProvider",
    "IHookBus",
    "ISkillLoader",
    "IUserInteraction",
]
