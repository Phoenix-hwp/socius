"""
多模型配置注册表 — 定义每个模型厂商的端点、API Key 环境变量、特性标记。

设计原则：
    - 配置与代码分离：API Key 从环境变量读取，不写死在代码中
    - 特性标记驱动：filter_images / reasoning_support 等标记让 Provider 自适应
    - 不涉及模型调用逻辑：调用逻辑在 model_providers.py 中
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class ModelConfig:
    """单个模型的配置信息"""

    model_id: str
    """模型标识符（如 deepseek-v4-pro, kimi-k2.6）"""

    display_name: str
    """人类可读名称（如 DeepSeek V4 Pro）"""

    api_url: str
    """API 端点（如 https://api.deepseek.com/v1）"""

    env_key: str | None
    """API Key 环境变量名。None = 不需要认证（如本地 Ollama）"""

    filter_images: bool = False
    """是否需要过滤消息中的 image_url（DeepSeek 不支持图片输入）"""

    reasoning_support: bool = False
    """是否需要修复 reasoning_content 缺失（Kimi/DeepSeek 思考模型需要）"""

    default_system_prompt: str = ""
    """默认 system prompt（可被调用方覆盖）"""

    request_timeout: int = 120
    """请求超时（秒）"""

    max_context_tokens: int = 128_000
    """最大上下文 token 数（估计值，实际以厂商文档为准）"""


# ──────────────────────────────────────────────
# 已注册的模型列表
# ──────────────────────────────────────────────

REGISTERED_MODELS: dict[str, ModelConfig] = {
    "deepseek-v4-pro": ModelConfig(
        model_id="deepseek-v4-pro",
        display_name="DeepSeek V4 Pro",
        api_url="https://api.deepseek.com/v1",
        env_key="DEEPSEEK_API_KEY",
        filter_images=True,          # DeepSeek 不支持 image_url
        reasoning_support=True,      # 思考模型需要 reasoning_content 修复
        max_context_tokens=1_000_000,
    ),
    "kimi-k2.6": ModelConfig(
        model_id="kimi-k2.6",
        display_name="Kimi K2.6",
        api_url="https://api.moonshot.cn/v1",
        env_key="KIMI_API_KEY",
        filter_images=False,         # Kimi 2.6 支持图片
        reasoning_support=True,      # Moonshot API 需要 reasoning_content 修复
        max_context_tokens=256_000,
    ),
    "ollama-local": ModelConfig(
        model_id="ollama-local",
        display_name="Ollama (本地)",
        api_url="http://localhost:11434/api",
        env_key=None,                # 本地不需要 API Key
        max_context_tokens=32_768,
    ),
    "lmstudio-local": ModelConfig(
        model_id="lmstudio-local",
        display_name="LM Studio (本地)",
        api_url="http://localhost:1234/v1",
        env_key=None,                # 本地不需要 API Key
        max_context_tokens=32_768,
    ),
    # ── 通用 OpenAI 兼容端点（自定义 URL） ──
    "custom-openai": ModelConfig(
        model_id="custom-openai",
        display_name="自定义 OpenAI 兼容端点",
        api_url="",                  # 由环境变量 CUSTOM_OPENAI_URL 覆盖
        env_key="CUSTOM_OPENAI_KEY",
        max_context_tokens=128_000,
    ),
}


def get_model_config(model_name: str) -> ModelConfig | None:
    """根据模型名获取配置。

    Args:
        model_name: 模型标识符（如 deepseek-v4-pro）

    Returns:
        ModelConfig 或 None（模型未注册）
    """
    config = REGISTERED_MODELS.get(model_name)
    if config is None:
        return None

    # custom-openai 的 api_url 由环境变量动态覆盖
    if model_name == "custom-openai":
        custom_url = os.environ.get("CUSTOM_OPENAI_URL", "")
        if custom_url:
            config = ModelConfig(
                model_id=config.model_id,
                display_name=config.display_name,
                api_url=custom_url,
                env_key=config.env_key,
                filter_images=config.filter_images,
                reasoning_support=config.reasoning_support,
                max_context_tokens=config.max_context_tokens,
            )

    return config


def list_models() -> list[dict]:
    """列出所有已注册的模型。

    Returns:
        ``[{model_id, display_name, requires_api_key, max_context_tokens}]``
    """
    return [
        {
            "model_id": c.model_id,
            "display_name": c.display_name,
            "requires_api_key": c.env_key is not None,
            "max_context_tokens": c.max_context_tokens,
        }
        for c in REGISTERED_MODELS.values()
    ]


def get_api_key(model_name: str) -> str | None:
    """从环境变量读取模型的 API Key。

    Args:
        model_name: 模型标识符

    Returns:
        API Key 字符串，或 None（模型不需要认证 / 环境变量未设置）
    """
    config = get_model_config(model_name)
    if config is None or config.env_key is None:
        return None
    return os.environ.get(config.env_key, "").strip() or None
