"""Context assembly and compaction — see docs/02-architecture/prompt-architecture.md.

Agency-internal. Nothing here is a hexagonal port: `ContextAssembler` owns in-process
prompt state and `ExchangeCompactor` takes domain models on both sides, so neither has a
remote implementation to abstract over (ADR-0023's port-rent rule would demote them on
sight).
"""

from sagiha.agency.context.assembler import AnchoredState, AssembledPrompt, ContextAssembler
from sagiha.agency.context.compactor import (
    SUMMARY_TAG,
    Exchange,
    ExchangeCompactor,
    ModelCompactor,
    TruncatingCompactor,
)
from sagiha.agency.context.tokens import estimate_tokens, message_tokens, messages_tokens

__all__ = [
    "SUMMARY_TAG",
    "AnchoredState",
    "AssembledPrompt",
    "ContextAssembler",
    "Exchange",
    "ExchangeCompactor",
    "ModelCompactor",
    "TruncatingCompactor",
    "estimate_tokens",
    "message_tokens",
    "messages_tokens",
]
