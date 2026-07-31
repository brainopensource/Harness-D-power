"""Token estimation — one function, so a real tokenizer swaps in behind it later.

Everything in `agency/context/` that needs a token count calls `estimate_tokens`. It is
deliberately the *only* place a `len(text) // 4` heuristic appears: the compactor's keep
budget and the assembler's headroom check must agree on what a token is, and they can only
agree if they ask the same function.

The estimator is intentionally crude and intentionally *not* provider-specific. Compaction
triggers on headroom, and headroom is a safety margin — an estimate that is within ~20% of
the truth reclaims the window at approximately the right moment, which is all the trigger
needs. A per-provider tokenizer would make the compaction boundary provider-dependent, and
therefore make replay of a recorded run non-deterministic across providers. That is a worse
trade than an imprecise count.
"""

from __future__ import annotations

from sagiha.domain.content import (
    ContentBlock,
    DiagnosticBlock,
    ImageBlock,
    Message,
    ReasoningBlock,
    ResourceBlock,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)

#: Characters per token. ~4 is the standard rough figure for English + code on BPE
#: vocabularies. See the module docstring for why precision is not the goal.
CHARS_PER_TOKEN: int = 4

#: Flat cost attributed to a block that carries no countable text (an image, a resource
#: referenced by URI). Not zero: such a block still occupies real budget, and a zero here
#: would let a history of images report as an empty tail and never compact.
_OPAQUE_BLOCK_TOKENS: int = 256


def estimate_tokens(text: str) -> int:
    """Estimated token count of `text`. Never negative; empty text costs 0."""
    if not text:
        return 0
    return max(1, len(text) // CHARS_PER_TOKEN)


def block_tokens(block: ContentBlock) -> int:
    """Estimated token count of one content block, including its structural overhead."""
    if isinstance(block, TextBlock):
        return estimate_tokens(block.text)
    if isinstance(block, ReasoningBlock):
        # The opaque payload is what is actually transported back to the provider, so it
        # is what costs — the human-readable summary is the cheap part.
        return estimate_tokens(str(block.opaque)) + estimate_tokens(block.summary)
    if isinstance(block, ToolUseBlock):
        return estimate_tokens(block.tool_name) + estimate_tokens(str(block.arguments))
    if isinstance(block, ToolResultBlock):
        return sum(block_tokens(inner) for inner in block.content)
    if isinstance(block, DiagnosticBlock):
        return sum(estimate_tokens(str(d)) for d in block.diagnostics)
    if isinstance(block, ResourceBlock):
        return estimate_tokens(block.text or "") or _OPAQUE_BLOCK_TOKENS
    if isinstance(block, ImageBlock):
        return _OPAQUE_BLOCK_TOKENS
    return _OPAQUE_BLOCK_TOKENS  # pragma: no cover — exhaustive over the union today


def message_tokens(message: Message) -> int:
    return sum(block_tokens(b) for b in message.content)


def messages_tokens(messages: tuple[Message, ...] | list[Message]) -> int:
    return sum(message_tokens(m) for m in messages)
