---
status: normative
updated: 2026-07-29
---
# ADR-0008: Native Provider SDKs, No Universal Abstraction Layer

**Status**: Accepted  
**Date**: 2026-07-28

## Context
Universal abstraction layers (e.g., LiteLLM) strip provider-specific features like prompt cache controls (`cache_control`), extended-thinking blocks, and custom tool semantics.

## Decision
- Use native SDKs (`anthropic`, `openai`, `google-genai`) behind a single `ModelProvider` port.
- No LiteLLM dependency.
- Use `openai` SDK with `base_url` overrides for OpenAI-compatible endpoints (Ollama, vLLM, OpenRouter, Groq).

## Consequences
- Retains provider features (caching, reasoning continuity, tool schemas).
- Model agnosticism is preserved at the port level, supported by contract testing.

## Reversal Conditions
- Non-tier-1 / non-OpenAI-compatible provider becomes critical and writing a dedicated adapter is prohibitively expensive.
