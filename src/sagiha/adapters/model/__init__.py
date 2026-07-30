"""ModelProvider adapters — see docs/02-architecture/prompt-architecture.md."""

from sagiha.adapters.model.cassette import CassetteModelProvider
from sagiha.adapters.model.fallback import FallbackModelAdapter
from sagiha.adapters.model.openai import (
    OpenAIAdapterError,
    OpenAIExtraMissingError,
    OpenAIModelAdapter,
    OpenAIModelError,
)

__all__ = [
    "CassetteModelProvider",
    "FallbackModelAdapter",
    "OpenAIAdapterError",
    "OpenAIExtraMissingError",
    "OpenAIModelAdapter",
    "OpenAIModelError",
]
