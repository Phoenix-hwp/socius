"""
多模型 Provider 实现 — 为每个已注册模型提供 IModelProvider 的具体实现。

工厂函数 ``create_provider()`` 根据模型名自动选择正确的 Provider 类。

设计原则：
    - 所有 Provider 实现同一个 IModelProvider 接口
    - 底层使用 aiohttp 或 httpx 做异步 HTTP 调用
    - 对 Kimi/DeepSeek 自动注入 reasoning_content 修复逻辑
    - 对 DeepSeek 自动过滤 image_url
"""

from __future__ import annotations

import json as _json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.adapter_interfaces import IModelProvider

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 惰性导入：避免框架层强依赖 aiohttp
# ──────────────────────────────────────────────
try:
    import aiohttp  # noqa: F401
    _HAS_ASYNC = True
except ImportError:
    _HAS_ASYNC = False


def _check_async() -> None:
    if not _HAS_ASYNC:
        raise ImportError(
            "aiohttp 未安装。异步 Provider 需要 aiohttp。\n"
            "安装: pip install aiohttp"
        )


# ──────────────────────────────────────────────
# 同步后备：基于 urllib 的同步 Provider
# ──────────────────────────────────────────────
import urllib.request  # noqa: E402
import urllib.error  # noqa: E402
import ssl  # noqa: E402

_SSL_CONTEXT = ssl.create_default_context()


class OpenAICompatibleProvider:
    """通用 OpenAI 兼容 API Provider（同步版本）。

    用于批处理场景（认知管线分类/提炼/合成），不依赖 aiohttp。
    """

    def __init__(
        self,
        api_url: str,
        model_id: str,
        api_key: str | None = None,
        *,
        filter_images: bool = False,
        reasoning_patch: bool = False,
        request_timeout: int = 120,
        max_output_tokens: int = 4096,
    ):
        self.api_url = (api_url or "").rstrip("/")
        self.model_id = model_id
        self.api_key = api_key
        self.filter_images = filter_images
        self.reasoning_patch = reasoning_patch
        self.request_timeout = request_timeout
        self.max_output_tokens = max_output_tokens

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _build_messages(self, prompt: str, system_prompt: str = "") -> list[dict]:
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append({"role": "user", "content": prompt})
        return msgs

    def _patch_reasoning_content(self, messages: list[dict]) -> None:
        """为思考模型注入推理内容占位符——Kimi/DeepSeek 的 reasoning_content 修复。"""
        if not self.reasoning_patch:
            return
        for msg in messages:
            if msg.get("role") != "assistant":
                continue
            tool_calls = msg.get("tool_calls")
            if not isinstance(tool_calls, list) or not tool_calls:
                continue
            if "reasoning_content" not in msg or not msg["reasoning_content"]:
                msg["reasoning_content"] = " "

    def _filter_images(self, messages: list[dict]) -> int:
        """过滤消息中的 image_url。DeepSeek 不支持图片。"""
        if not self.filter_images:
            return 0
        filtered = 0
        for msg in messages:
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
                elif isinstance(part, dict) and part.get("type") == "image_url":
                    filtered += 1
            msg["content"] = "\n".join(text_parts) if text_parts else "[图片内容已过滤]"
        return filtered

    def complete(self, prompt: str, /, *, system_prompt: str = "") -> str:
        """同步单次推理。"""
        messages = self._build_messages(prompt, system_prompt)
        self._patch_reasoning_content(messages)
        self._filter_images(messages)
        return self._call_api(messages)

    def complete_messages(
        self, system_prompt: str, /, *, messages: list[dict]
    ) -> str:
        """多轮消息数组推理——利用 API 提供商的 prompt caching。"""
        full_msgs = []
        if system_prompt:
            full_msgs.append({"role": "system", "content": system_prompt})
        full_msgs.extend(messages)
        self._patch_reasoning_content(full_msgs)
        self._filter_images(full_msgs)
        return self._call_api(full_msgs)

    def _call_api(self, messages: list[dict]) -> str:
        """发送消息数组到 API 并提取回复文本。"""
        body = _json.dumps({
            "model": self.model_id,
            "messages": messages,
            "stream": False,
            "max_tokens": self.max_output_tokens,
        }).encode("utf-8")

        endpoint = f"{self.api_url}/chat/completions"
        req = urllib.request.Request(
            endpoint,
            data=body,
            headers=self._headers(),
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.request_timeout, context=_SSL_CONTEXT) as resp:
                data = _json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"[{self.model_id}] HTTP {e.code}: {body_text}") from e
        except Exception as e:
            raise RuntimeError(f"[{self.model_id}] {type(e).__name__}: {e}") from e

        choices = data.get("choices")
        if not choices:
            raise RuntimeError(f"[{self.model_id}] 无 choices: {data}")

        msg = choices[0]["message"]
        content = msg.get("content", "")
        if not content and "reasoning_content" in msg:
            content = msg["reasoning_content"]
        return content

    def complete_json(self, prompt: str, /, *, schema: dict | None = None) -> dict:
        """同步结构化输出推理。"""
        sp = "Respond ONLY with valid JSON. Do not wrap in markdown code fences."
        if schema:
            sp += f"\nJSON Schema: {_json.dumps(schema, ensure_ascii=False)}"

        full_prompt = f"{sp}\n\n{prompt}"
        text = self.complete(full_prompt)

        # 清理可能的 markdown 代码块包裹
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:]) if len(lines) > 1 else text
        if text.endswith("```"):
            text = text[:-3].strip()

        return _json.loads(text)


# ──────────────────────────────────────────────
# Anthropic Provider — Messages API（非 OpenAI 兼容端点）
# ──────────────────────────────────────────────

class _AnthropicProvider:
    """Anthropic Claude Provider — 使用 Messages API。

    Anthropic API: https://docs.anthropic.com/en/api/messages
    端点: POST /v1/messages
    认证头: x-api-key + anthropic-version
    """

    def __init__(
        self,
        api_url: str,
        model_id: str,
        api_key: str,
        request_timeout: int = 120,
        max_output_tokens: int = 4096,
    ):
        self.api_url = (api_url or "").rstrip("/")
        self.model_id = model_id
        self.api_key = api_key
        self.request_timeout = request_timeout
        self.max_output_tokens = max_output_tokens

    def complete(self, prompt: str, /, *, system_prompt: str = "") -> str:
        body = _json.dumps({
            "model": self.model_id,
            "max_tokens": self.max_output_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")
        return self._call_anthropic(body)

    def complete_messages(
        self, system_prompt: str, /, *, messages: list[dict]
    ) -> str:
        body = _json.dumps({
            "model": self.model_id,
            "max_tokens": self.max_output_tokens,
            "system": system_prompt,
            "messages": messages,
        }).encode("utf-8")
        return self._call_anthropic(body)

    def _call_anthropic(self, body: bytes) -> str:
        endpoint = f"{self.api_url}/messages"
        req = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.request_timeout, context=_SSL_CONTEXT) as resp:
                data = _json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"[Anthropic] HTTP {e.code}: {body_text}") from e
        except Exception as e:
            raise RuntimeError(f"[Anthropic] {type(e).__name__}: {e}") from e

        content = data.get("content", [])
        if not content:
            raise RuntimeError(f"[Anthropic] 无 content: {data}")
        text_parts = [c["text"] for c in content if c.get("type") == "text"]
        return "\n".join(text_parts)

    def complete_json(self, prompt: str, /, *, schema: dict | None = None) -> dict:
        sp = "Respond ONLY with valid JSON. Do not wrap in markdown code fences."
        if schema:
            sp += f"\nJSON Schema: {_json.dumps(schema, ensure_ascii=False)}"
        text = self.complete(prompt, system_prompt=sp)
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:]) if len(lines) > 1 else text
        if text.endswith("```"):
            text = text[:-3].strip()
        return _json.loads(text)


# ──────────────────────────────────────────────
# 工厂函数
# ──────────────────────────────────────────────

def create_provider(provider_id: str, /, *, model_name: str = "", api_key: str | None = None, api_url: str | None = None) -> IModelProvider:
    """根据提供商 + 模型名创建 IModelProvider 实例。

    Args:
        provider_id: 提供商标识符（如 deepseek, kimi, ollama, anthropic）
        model_name: 用户输入的模型名。空字符串时使用提供商的默认模型。
        api_key: API Key。None 时自动从环境变量读取。
        api_url: 自定义 API 端点。None 时使用注册表中对应提供商的默认 api_url。

    Returns:
        IModelProvider 实例

    Raises:
        ValueError: 提供商未注册
        RuntimeError: API Key 缺失
    """
    from core.model_registry import get_provider, get_api_key, REGISTERED_PROVIDERS

    provider = get_provider(provider_id)
    if provider is None:
        raise ValueError(
            f"未注册的提供商: {provider_id}。"
            f"可用: {list(REGISTERED_PROVIDERS)}"
        )

    resolved_key = api_key
    if resolved_key is None:
        resolved_key = get_api_key(provider_id)

    if provider.env_key is not None and not resolved_key:
        raise RuntimeError(
            f"提供商 {provider.display_name} 需要 API Key。"
            f"请设置环境变量 {provider.env_key}，或显式传入 api_key 参数。"
        )

    resolved_model = model_name or provider.default_model
    resolved_api_url = api_url or provider.api_url
    # URL 合法性校验：防止输入流污染（如交互菜单 index 误入 url 字段）
    from urllib.parse import urlparse as _up
    if resolved_api_url and not _up(resolved_api_url).scheme:
        from warnings import warn as _warn
        _warn(f"api_url 非法值 '{resolved_api_url}'，已自动恢复为 {provider.display_name} 默认端点")
        resolved_api_url = provider.api_url

    # Ollama — 原生 API（/api/generate）
    if provider_id in ("ollama", "ollama-local"):
        return _OllamaProvider(resolved_api_url, resolved_model, provider.request_timeout)

    # Anthropic — Messages API（非 OpenAI 兼容端点）
    if provider_id == "anthropic":
        return _AnthropicProvider(
            api_url=resolved_api_url,
            model_id=resolved_model,
            api_key=resolved_key,
            request_timeout=provider.request_timeout,
            max_output_tokens=provider.max_output_tokens,
        )

    # 其余所有模型走 OpenAI 兼容端点
    return OpenAICompatibleProvider(
        api_url=resolved_api_url,
        model_id=resolved_model,
        api_key=resolved_key,
        filter_images=provider.filter_images,
        reasoning_patch=provider.reasoning_support,
        request_timeout=provider.request_timeout,
        max_output_tokens=provider.max_output_tokens,
    )


# ──────────────────────────────────────────────
# Ollama 专用 Provider（非 OpenAI 兼容的 /api/generate 端点）
# ──────────────────────────────────────────────

class _OllamaProvider:
    """Ollama 本地模型 Provider。

    Ollama 有两个端点：
        - /api/generate   — 单次完成（非 OpenAI 兼容）
        - /v1/chat/completions — OpenAI 兼容（Ollama 0.5+ 才支持）

    默认使用 /api/generate（更广泛兼容）。
    """

    def __init__(self, api_url: str, model_id: str, request_timeout: int = 120):
        self.api_url = api_url.rstrip("/")
        self.model_id = model_id
        self.request_timeout = request_timeout

    def _call_ollama(self, prompt: str, system_prompt: str = "", *, raw: bool = False) -> dict:
        import urllib.request
        import urllib.error

        body = _json.dumps({
            "model": self.model_id,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "raw": raw,
        }).encode("utf-8")

        endpoint = f"{self.api_url}/generate"
        req = urllib.request.Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
                return _json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"[Ollama] HTTP {e.code}: {body_text}") from e
        except Exception as e:
            raise RuntimeError(f"[Ollama] {type(e).__name__}: {e}") from e

    def complete(self, prompt: str, /, *, system_prompt: str = "") -> str:
        data = self._call_ollama(prompt, system_prompt)
        return data.get("response", "")

    def complete_messages(
        self, system_prompt: str, /, *, messages: list[dict]
    ) -> str:
        # Ollama /api/generate 不支持消息数组——回退到拼接
        prompt = "\n".join(
            f"[{m['role']}]: {m['content']}" for m in messages[-20:]
        )
        return self.complete(prompt, system_prompt=system_prompt)

    def complete_json(self, prompt: str, /, *, schema: dict | None = None) -> dict:
        sp = "Respond ONLY with valid JSON. Do not wrap in markdown code fences."
        if schema:
            sp += f"\nJSON Schema: {_json.dumps(schema, ensure_ascii=False)}"
        full_prompt = f"{sp}\n\n{prompt}"

        # Ollama 的 format=json 模式
        data = self._call_ollama(full_prompt, "", raw=True)
        text = data.get("response", "").strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:]) if len(lines) > 1 else text
        if text.endswith("```"):
            text = text[:-3].strip()
        return _json.loads(text)
