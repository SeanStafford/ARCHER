"""
LLM provider abstraction and response parsing utilities.

Provides a provider-agnostic interface for LLM API calls with automatic retries
and utilities for parsing structured JSON responses.
"""

import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import partial
from typing import Callable, TypeVar

from dotenv import load_dotenv

load_dotenv()

# Retry configuration
MAX_RETRIES = 5
BASE_DELAY = 1.0

T = TypeVar("T")


def _retry_with_backoff(
    operation: Callable[[], T],
    retryable_exception: type[Exception],
    error_message: str,
) -> T:
    """
    Execute operation with exponential backoff retry on specific exception.

    Args:
        operation: Callable that performs the API request and returns result
        retryable_exception: Exception type that triggers retry
        error_message: Message prefix for retry logging (e.g., "API overloaded")
    """
    for attempt in range(MAX_RETRIES):
        try:
            return operation()
        except retryable_exception:
            if attempt == MAX_RETRIES - 1:
                raise
            delay = BASE_DELAY * (2**attempt)
            print(
                f"  {error_message}, retrying in {delay:.1f}s... "
                f"(attempt {attempt + 1}/{MAX_RETRIES})"
            )
            time.sleep(delay)


# --- LLM Provider Classes ---


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    model: str
    input_tokens: int
    output_tokens: int


class LLMProvider(ABC):
    """
    Abstract base for LLM providers.

    Subclasses must:
    - Set _provider_prefix class attribute (e.g., "anthropic", "openai")
    - Set self._retryable_exception to the exception type that triggers retry
    - Set self._retry_message for logging during retries
    - Implement _call_api() for the actual API call
    - Call update_model(model) in __init__ to set model and name
    """

    _provider_prefix: str
    _retryable_exception: type[Exception]
    _retry_message: str

    name: str
    model: str

    def update_model(self, model: str):
        """Update the model and refresh the provider name."""
        self.model = model
        self.name = f"{self._provider_prefix}/{model}"

    @abstractmethod
    def _call_api(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Make a single API call (no retries). Implemented by subclasses."""
        pass

    def generate(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Generate a response from the LLM with automatic retry on transient errors."""
        return _retry_with_backoff(
            partial(self._call_api, system_prompt, user_prompt),
            self._retryable_exception,
            self._retry_message,
        )


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider with exponential backoff retry."""

    _provider_prefix = "anthropic"
    _retry_message = "API overloaded"

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        # Lazy import - anthropic SDK is heavy, only load if this provider is used
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package required. Install with: pip install anthropic")

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self.client = anthropic.Anthropic(api_key=api_key)
        self._retryable_exception = anthropic.OverloadedError
        self.update_model(model)

    def _call_api(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return LLMResponse(
            content=response.content[0].text,
            model=self.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider with exponential backoff retry."""

    _provider_prefix = "openai"
    _retry_message = "Rate limit hit"

    def __init__(self, model: str = "gpt-4o"):
        # Lazy import - openai SDK is heavy, only load if this provider is used
        try:
            import openai
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = openai.OpenAI(api_key=api_key)
        self._retryable_exception = openai.RateLimitError
        self.update_model(model)

    def _call_api(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return LLMResponse(
            content=response.choices[0].message.content,
            model=self.model,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )


# --- Provider Factory ---


def get_provider(provider_name: str = None, model: str = None) -> LLMProvider:
    """
    Get an LLM provider instance.

    Args:
        provider_name: "anthropic" or "openai" (default: from LLM_PROVIDER env var)
        model: Model name (default: provider-specific default)

    Returns:
        LLMProvider instance
    """
    if provider_name is None:
        provider_name = os.getenv("LLM_PROVIDER", "openai").lower()

    if provider_name == "anthropic":
        return AnthropicProvider(model=model) if model else AnthropicProvider()
    elif provider_name == "openai":
        return OpenAIProvider(model=model) if model else OpenAIProvider()
    else:
        raise ValueError(f"Unknown provider: {provider_name}. Use 'anthropic' or 'openai'")


# --- Response Parsing Utilities ---


def parse_array_response(text: str, fallback_count: int = 4) -> list[str]:
    """
    Parse JSON array from LLM response with robust fallback parsing.

    Args:
        text: LLM response text
        fallback_count: Number of items to return if JSON parsing fails

    Returns:
        List of strings
    """
    text = text.strip()

    # Try direct JSON parse
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return [str(item) for item in result]
    except json.JSONDecodeError:
        pass

    # Try to find JSON array in the text
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            result = json.loads(text[start : end + 1])
            if isinstance(result, list):
                return [str(item) for item in result]
        except json.JSONDecodeError:
            pass

    # Fallback: split by newlines and clean
    lines = []
    for line in text.split("\n"):
        line = line.strip().lstrip("-•*").strip().strip('"').strip(",")
        if line and not line.startswith("[") and not line.startswith("]"):
            lines.append(line)

    return lines[:fallback_count] if lines else []


def parse_dict_response(
    text: str, fallback_dict: dict[str, list[str]] = None
) -> dict[str, list[str]]:
    """
    Parse JSON dict from LLM response with robust fallback parsing.

    Args:
        text: LLM response text
        fallback_dict: Dict to return if parsing fails (default: empty dict)

    Returns:
        Dict mapping strings to lists of strings
    """
    text = text.strip()

    # Try direct JSON parse
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return {
                k: [str(i) for i in v] if isinstance(v, list) else [] for k, v in result.items()
            }
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in the text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            result = json.loads(text[start : end + 1])
            if isinstance(result, dict):
                return {
                    k: [str(i) for i in v] if isinstance(v, list) else [] for k, v in result.items()
                }
        except json.JSONDecodeError:
            pass

    # Fallback: return provided fallback or empty dict
    return fallback_dict if fallback_dict is not None else {}
