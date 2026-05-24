"""Phoenix Framework Core — 认知引擎 + P008 决策框架 + TEP 任务编排。

框架层零 Cursor 依赖。所有平台适配器通过 adapter_interfaces.py 的 Protocol 接口接入。

子包:
    knowledge/         — 认知引擎（分类器、提炼模板、激活引擎、概念树）
    guard/             — P008 决策框架 + 安全闸门
    data/              — JSON/JSONL schema + reader/writer
    skills/            — 技能注册表 + 脚本
    model_registry.py  — 多模型配置注册表（DeepSeek/Kimi/Ollama/LM Studio）
    model_providers.py — IModelProvider 具体实现（OpenAI 兼容 + Ollama）
    context_builder.py — 上下文构建器（替代 Cursor alwaysApply 规则注入）
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
