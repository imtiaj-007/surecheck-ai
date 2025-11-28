"""
Modular LLM Provider with Singleton Pattern
Supports multiple LLM providers with easy extensibility
"""

from functools import lru_cache
from typing import Any, Literal

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

# Commented imports for future use
# from langchain_anthropic import ChatAnthropic
# from langchain_community.chat_models import ChatPerplexity
# from langchain_groq import ChatGroq
# from langchain_community.chat_models import ChatDeepSeek
from src.core.config import settings

LLMProvider = Literal["gemini", "openai", "anthropic", "grok", "perplexity", "deepseek"]


class LLMProviderConfig:
    """Configuration for each LLM provider"""

    @staticmethod
    def get_provider_config() -> dict[str, dict[str, Any]]:
        """
        Returns configuration for all providers.
        Each provider needs: api_key, model, and class.
        """
        return {
            "gemini": {
                "api_key": settings.GEMINI_API_KEY,
                "model": settings.GEMINI_MODEL,
                "class": ChatGoogleGenerativeAI,
                "enabled": bool(settings.GEMINI_API_KEY),
            },
            "openai": {
                "api_key": settings.OPENAI_API_KEY,
                "model": settings.OPENAI_MODEL,
                "class": ChatOpenAI,
                "enabled": bool(settings.OPENAI_API_KEY),
            },
            # Uncomment and configure as needed
            # "anthropic": {
            #     "api_key": settings.ANTHROPIC_API_KEY,
            #     "model": settings.ANTHROPIC_MODEL,  # e.g., "claude-sonnet-4-5-20250929"
            #     "class": ChatAnthropic,
            #     "enabled": bool(settings.ANTHROPIC_API_KEY),
            # },
            # "grok": {
            #     "api_key": settings.GROK_API_KEY,
            #     "model": settings.GROK_MODEL,  # e.g., "grok-beta"
            #     "class": ChatGroq,
            #     "enabled": bool(settings.GROK_API_KEY),
            # },
            # "perplexity": {
            #     "api_key": settings.PERPLEXITY_API_KEY,
            #     "model": settings.PERPLEXITY_MODEL,  # e.g., "llama-3.1-sonar-large-128k-online"
            #     "class": ChatPerplexity,
            #     "enabled": bool(settings.PERPLEXITY_API_KEY),
            # },
            # "deepseek": {
            #     "api_key": settings.DEEPSEEK_API_KEY,
            #     "model": settings.DEEPSEEK_MODEL,  # e.g., "deepseek-chat"
            #     "class": ChatDeepSeek,
            #     "enabled": bool(settings.DEEPSEEK_API_KEY),
            # },
        }


@lru_cache(maxsize=10)
def get_llm(
    provider: LLMProvider = "gemini",
    temperature: float = 0.0,
    max_tokens: int | None = None,
    **kwargs: Any,
) -> BaseChatModel:
    """
    Returns a configured LLM instance with singleton pattern via LRU cache.

    Args:
        provider: The LLM provider to use
        temperature: Model temperature (0.0 = deterministic, 1.0 = creative)
        max_tokens: Maximum tokens in response (optional)
        **kwargs: Additional provider-specific arguments

    Returns:
        Configured LLM instance

    Raises:
        ValueError: If provider is not configured or API key is missing

    Example:
        >>> llm = get_llm("openai", temperature=0.7)
        >>> response = llm.invoke("Hello, world!")
    """
    config = LLMProviderConfig.get_provider_config()

    if provider not in config:
        available = [p for p, c in config.items() if c["enabled"]]
        raise ValueError(
            f"Provider '{provider}' not found. "
            f"Available providers: {', '.join(available) if available else 'None'}"
        )

    provider_config = config[provider]

    if not provider_config["enabled"]:
        raise ValueError(
            f"Provider '{provider}' is not configured. "
            f"Please set {provider.upper()}_API_KEY in settings."
        )

    # Build initialization arguments
    init_args = {
        "model": provider_config["model"],
        "temperature": temperature,
        "api_key": provider_config["api_key"],
        **kwargs,
    }

    # Add max_tokens if provided
    if max_tokens is not None:
        init_args["max_tokens"] = max_tokens

    # Initialize and return the LLM
    llm_class = provider_config["class"]
    return llm_class(**init_args)


def get_default_llm(temperature: float = 0.0, **kwargs: Any) -> BaseChatModel:
    """
    Returns the default/fallback LLM provider.
    Tries providers in order of preference.

    Args:
        temperature: Model temperature
        **kwargs: Additional arguments

    Returns:
        First available configured LLM instance

    Raises:
        ValueError: If no LLM providers are configured
    """
    config = LLMProviderConfig.get_provider_config()
    priority_order = ["gemini", "openai", "anthropic", "grok", "perplexity", "deepseek"]

    for provider in priority_order:
        if provider in config and config[provider]["enabled"]:
            return get_llm(provider, temperature=temperature, **kwargs)

    raise ValueError("No LLM providers configured. Please set at least one API key in settings.")


def list_available_providers() -> list[str]:
    """
    Returns a list of currently configured and available LLM providers.

    Returns:
        List of provider names that have valid API keys
    """
    config = LLMProviderConfig.get_provider_config()
    return [provider for provider, cfg in config.items() if cfg["enabled"]]


def clear_llm_cache() -> None:
    """
    Clears the LLM cache. Useful for testing or if you need to force
    re-initialization of LLM instances.
    """
    get_llm.cache_clear()
