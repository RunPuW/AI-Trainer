"""
backend/ai/llm_client.py
LLM 客户side封装, branchhold DeepSeek / OpenAI / Claude etcmany种backside
use backend.config   config
"""

import os
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

from backend.config import get_settings


def get_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> "BaseChatModel":
    """
    getget LLM instance. 优先use backend.config   config. 
    
    Args:
        provider: "deepseek", "openai", "claude", Noneruleusering境changeamountorconfig
        model: modelname, None ruleusedefaultvalue
        temperature: 创造ity程度
        max_tokens: maxoutputlength
    
    Returns:
        BaseChatModel instance
    """
    settings = get_settings()
    
    # 优先use传inparameter, 其repuse config config
    provider = provider or os.getenv("LLM_PROVIDER", "deepseek")
    
    provider_configs = {
        "deepseek": {
            "model": model or settings.DEEPSEEK_MODEL,
            "base_url": settings.DEEPSEEK_BASE_URL,
            "api_key": settings.DEEPSEEK_API_KEY,
        },
        "openai": {
            "model": model or "gpt-4o",
            "base_url": None,
            "api_key": os.getenv("OPENAI_API_KEY"),
        },
        "claude": {
            "model": model or "claude-3-5-sonnet-20241022",
            "base_url": "https://api.anthropic.com/v1",
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
        },
    }
    
    if provider not in provider_configs:
        raise ValueError(f" branchhold  provider: {provider}")
    
    config = provider_configs[provider]
    api_key = config["api_key"]
    
    if not api_key:
        raise ValueError(f"pleasesetting {provider.upper()} API Key")
    
    # Import lazily so health checks and rule-based feedback do not load the
    # full LangChain/OpenAI HTTP stack or leave background workers alive.
    import httpx
    from langchain_openai import ChatOpenAI

    extra_kwargs = {}
    if provider == "deepseek":
        # DeepSeek V4 thinking mode requires reasoning_content to be replayed
        # after tool calls. LangChain's OpenAI-compatible tool loop does not
        # preserve that field today, so disable thinking mode for app stability.
        extra_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
        # The desktop environment can define HTTP(S)_PROXY to a closed local
        # port. DeepSeek must ignore ambient proxy env vars or every AI call
        # fails with APIConnectionError / WinError 10061.
        timeout = httpx.Timeout(30.0, connect=10.0)
        extra_kwargs["http_client"] = httpx.Client(trust_env=False, timeout=timeout)
        extra_kwargs["http_async_client"] = httpx.AsyncClient(trust_env=False, timeout=timeout)

    return ChatOpenAI(
        model=config["model"],
        base_url=config["base_url"],
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        **extra_kwargs,
    )


# default LLM instance(single例mockstyle)
_default_llm: Optional["BaseChatModel"] = None


def get_default_llm() -> "BaseChatModel":
    """getgetdefault LLM instance(延迟init). """
    global _default_llm
    if _default_llm is None:
        provider = os.getenv("LLM_PROVIDER", "deepseek")
        _default_llm = get_llm(provider=provider)
    return _default_llm


def reset_default_llm():
    """resetdefault LLM(切换configbackcall). """
    global _default_llm
    _default_llm = None
