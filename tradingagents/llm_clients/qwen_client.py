import os
from typing import Any, Optional

from langchain_openai import ChatOpenAI

from .base_client import BaseLLMClient, normalize_content
from .validators import validate_model

# Qwen base URL and API key env var
_QWEN_BASE_URL = "https://coding.dashscope.aliyuncs.com/v1"
_QWEN_API_KEY_ENV = "DASHSCOPE_API_KEY"

# Qwen's thinking mode conflicts with tool_choice required by structured output.
# Disabling it ensures with_structured_output works for Portfolio Manager, Trader, etc.
_QWEN_EXTRA_BODY = {"enable_thinking": False}

_PASSTHROUGH_KWARGS = (
    "timeout", "max_retries", "reasoning_effort",
    "api_key", "callbacks", "http_client", "http_async_client",
)


class _QwenChatOpenAI(ChatOpenAI):
    """ChatOpenAI subclass for Qwen with thinking mode disabled.

    Qwen's thinking mode is incompatible with the tool_choice parameter
    that with_structured_output relies on. Disabling thinking ensures all
    agent calls that use structured output succeed.
    """

    def invoke(self, input, config=None, **kwargs):
        return normalize_content(super().invoke(input, config, **kwargs))

    def with_structured_output(self, schema, *, method=None, **kwargs):
        """Wrap with structured output using function calling.

        Explicitly uses function_calling method to avoid the json_schema
        path which sets tool_choice to values Qwen rejects in thinking mode.
        """
        if method is None:
            method = "function_calling"
        return super().with_structured_output(schema, method=method, **kwargs)


class QwenClient(BaseLLMClient):
    """LLM client for Alibaba Qwen (DashScope) via OpenAI-compatible API.

    Thinking mode is disabled by default so that with_structured_output
    (used by Portfolio Manager, Trader, Research Manager) works correctly.
    """

    provider = "qwen"

    def get_llm(self) -> Any:
        self.warn_if_unknown_model()

        api_key = os.environ.get(_QWEN_API_KEY_ENV)
        llm_kwargs: dict[str, Any] = {
            "model": self.model,
            "base_url": self.base_url or _QWEN_BASE_URL,
            "extra_body": _QWEN_EXTRA_BODY,
        }
        if api_key:
            llm_kwargs["api_key"] = api_key

        for key in _PASSTHROUGH_KWARGS:
            if key in self.kwargs:
                llm_kwargs[key] = self.kwargs[key]

        return _QwenChatOpenAI(**llm_kwargs)

    def validate_model(self) -> bool:
        return validate_model(self.provider, self.model)
