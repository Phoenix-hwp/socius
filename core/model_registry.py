"""
多模型配置注册表 — 两层结构：提供商（ProviderConfig）+ 模型（由用户输入）。

设计原则：
    - 提供商决定 api_url / env_key / Provider 类 / 特性标记
    - 模型名由用户在 CLI 交互时输入（带默认建议）
    - 配置与代码分离：API Key 从环境变量读取，不写死在代码中
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class ProviderConfig:
    """提供商标识（api_url、env_key、Provider 类）——不绑定具体模型名。"""

    provider_id: str
    """唯一标识符（如 deepseek, kimi, ollama）"""

    display_name: str
    """人类可读名称（如 DeepSeek）"""

    api_url: str
    """API 端点"""

    env_key: str | None
    """API Key 环境变量名。None = 不需要认证（如本地 Ollama）"""

    default_model: str
    """建议的默认模型名（CLI 显示给用户作为参考）"""

    model_hint: str
    """模型名输入时的提示文本（如 deepseek-chat / deepseek-reasoner）"""

    filter_images: bool = False
    reasoning_support: bool = False
    request_timeout: int = 120
    max_context_tokens: int = 128_000
    max_output_tokens: int = 4096
    """API 请求的 max_tokens 参数。推理模型（DeepSeek v4-pro / Kimi k2.6）需更大（≥8192），
    为 reasoning_content 和 content 各留一半预算。"""


# ──────────────────────────────────────────────
# 已注册的提供商（按 CLI 显示顺序）
# ──────────────────────────────────────────────

REGISTERED_PROVIDERS: dict[str, ProviderConfig] = {
    "ollama": ProviderConfig(
        provider_id="ollama",
        display_name="Ollama",
        api_url="http://localhost:11434/api",
        env_key=None,
        default_model="llama3.2",
        model_hint="如 llama3.2, qwen3:14b, mistral 等（通过 ollama pull 已安装的模型）",
        max_context_tokens=32_768,
        max_output_tokens=2048,
    ),
    "lmstudio": ProviderConfig(
        provider_id="lmstudio",
        display_name="LM Studio",
        api_url="http://localhost:1234/v1",
        env_key=None,
        default_model="local-model",
        model_hint="在 LM Studio 中加载的模型名称",
        max_context_tokens=32_768,
        max_output_tokens=2048,
    ),
    "openai": ProviderConfig(
        provider_id="openai",
        display_name="OpenAI",
        api_url="https://api.openai.com/v1",
        env_key="OPENAI_API_KEY",
        default_model="gpt-5.5",
        model_hint="gpt-5.5 (旗舰) / gpt-5.4 / gpt-4.1 / gpt-4o 等",
        max_context_tokens=128_000,
    ),
    "anthropic": ProviderConfig(
        provider_id="anthropic",
        display_name="Anthropic",
        api_url="https://api.anthropic.com/v1",
        env_key="ANTHROPIC_API_KEY",
        default_model="claude-sonnet-4-6",
        model_hint="claude-sonnet-4-6 (主力) / claude-opus-4-7 / claude-haiku-4-5 等",
        max_context_tokens=200_000,
    ),
    "deepseek": ProviderConfig(
        provider_id="deepseek",
        display_name="DeepSeek",
        api_url="https://api.deepseek.com/v1",
        env_key="DEEPSEEK_API_KEY",
        default_model="deepseek-v4-pro",
        model_hint="deepseek-v4-pro / deepseek-v4-flash（legacy: deepseek-chat 2026-07-24 废弃）",
        filter_images=True,
        reasoning_support=True,
        max_context_tokens=1_000_000,
        max_output_tokens=8192,
    ),
    "kimi": ProviderConfig(
        provider_id="kimi",
        display_name="Kimi (Moonshot)",
        api_url="https://api.moonshot.cn/v1",
        env_key="KIMI_API_KEY",
        default_model="kimi-k2.6",
        model_hint="kimi-k2.6 (主力) / kimi-k2.5 / moonshot-v1-128k 等",
        reasoning_support=True,
        max_context_tokens=256_000,
        max_output_tokens=8192,
    ),
    "custom": ProviderConfig(
        provider_id="custom",
        display_name="自定义 OpenAI 兼容端点",
        api_url="",
        env_key="CUSTOM_OPENAI_KEY",
        default_model="",
        model_hint="请输入模型名称（如 gpt-4o, qwen-max 等）",
        max_context_tokens=128_000,
    ),
}


# ── 向后兼容别名（旧 provider_id 映射到新的） ──
_PROVIDER_ALIASES = {
    "ollama-local": "ollama",
    "lmstudio-local": "lmstudio",
    "deepseek-v4-pro": "deepseek",
    "kimi-k2.6": "kimi",
    "custom-openai": "custom",
}


def get_provider(provider_id: str) -> ProviderConfig | None:
    """根据提供商 ID 获取配置。

    Args:
        provider_id: 如 deepseek, kimi, ollama（也支持旧别名）

    Returns:
        ProviderConfig 或 None
    """
    pid = _PROVIDER_ALIASES.get(provider_id, provider_id)
    return REGISTERED_PROVIDERS.get(pid)


def list_providers() -> list[dict]:
    """列出所有已注册的提供商。

    Returns:
        [{provider_id, display_name, default_model, requires_api_key, max_context_tokens}]
    """
    return [
        {
            "provider_id": p.provider_id,
            "display_name": p.display_name,
            "default_model": p.default_model,
            "model_hint": p.model_hint,
            "requires_api_key": p.env_key is not None,
            "max_context_tokens": p.max_context_tokens,
            "max_output_tokens": p.max_output_tokens,
            "api_url": p.api_url,
        }
        for p in REGISTERED_PROVIDERS.values()
    ]


def get_api_key(provider_id: str) -> str | None:
    """从环境变量读取提供商的 API Key。

    Args:
        provider_id: 提供商标识符

    Returns:
        API Key 字符串，或 None
    """
    provider = get_provider(provider_id)
    if provider is None or provider.env_key is None:
        return None
    return os.environ.get(provider.env_key, "").strip() or None


# ── 向后兼容（旧调用方仍可用，但会输出 deprecated log） ──

def list_models() -> list[dict]:
    """[已废弃] 列出所有提供商（兼容旧接口）。
    新代码请使用 list_providers()。"""
    import logging
    logging.getLogger("socius").debug("list_models() is deprecated, use list_providers()")
    return [
        {
            "model_id": p.provider_id,
            "display_name": p.display_name,
            "requires_api_key": p.env_key is not None,
            "max_context_tokens": p.max_context_tokens,
        }
        for p in REGISTERED_PROVIDERS.values()
    ]
