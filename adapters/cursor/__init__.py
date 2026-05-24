"""CursorAdapter — 将 Cursor IDE Agent 能力映射到 Phoenix 框架接口。

6 个适配器接口均由 CursorAdapter 聚合，各接口可独立使用::

    from adapters.cursor.adapter import CursorAdapter, CursorRuleEngine

    adapter = CursorAdapter()
    rules = adapter.rule_engine.load_rules()
    active = adapter.rule_engine.filter_active(rules)
    adapter.hook_bus.fire("sessionStart")
"""

from adapters.cursor.adapter import (
    CursorAdapter,
    CursorHookBus,
    CursorRuleEngine,
    CursorSkillLoader,
    CursorToolProvider,
    CursorUserInteraction,
)

__all__ = [
    "CursorAdapter",
    "CursorRuleEngine",
    "CursorToolProvider",
    "CursorHookBus",
    "CursorSkillLoader",
    "CursorUserInteraction",
]
