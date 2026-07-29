# ADR-0008: Native Provider SDKs, No Universal Abstraction Layer

**Status**: Accepted
**Date**: 2026-07-28

## Context
A universal layer such as LiteLLM buys 100+ providers for one integration. It pays for them by normalizing to a lowest common denominator, and the three capabilities this harness depends on most are exactly what gets normalized: provider-specific prompt cache control (`cache_control`), extended-thinking blocks whose signatures must round-trip verbatim to continue a tool-use turn, and per-provider tool-use semantics.

## Decision
Native first-party SDKs — `anthropic`, `openai`, `google-genai` — as separate adapters behind one `ModelProvider` port. No LiteLLM dependency. The `openai` SDK with a `base_url` override covers OpenAI-compatible endpoints (Ollama, vLLM, LM Studio, OpenRouter, Together, Groq), which collapses the long-tail argument for a universal layer.

## Consequences
Full fidelity on caching, reasoning continuity, and tool semantics — the first of which is the single largest cost lever in the system. Each tier-1 provider costs a small adapter, which the conformance suite keeps honest. **Model-agnosticism is preserved at the port, not at the SDK**: zero lock-in comes from `ModelProvider` being one narrow interface, not from routing through someone else's abstraction.

## Reversal Conditions
A provider appears that is neither tier-1 nor OpenAI-compatible and matters enough to support, and hand-writing its adapter proves materially more expensive than adopting a universal layer for that one case.
