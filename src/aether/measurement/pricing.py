"""Token → `usd_micros` conversion, so the governor's dollar dimension is real.

Until Sprint 3.5 `composition.py` reported prompt/completion tokens into
`Actuals` and **nothing ever wrote `usd_micros`**. A run seeded with
`seed_run_budget(usd_micros=200_000)` would therefore never be denied: the
ledger compared spend against a dimension that was always zero. A budget cap
enforced against a field nobody writes is the same defect class as a contract
that selects no files — it passes green and forbids nothing.

**Prices here are inputs, not measurements.** They come from the provider's
published rate card and are used to *bound* spend, never reported as a result:
`measurement.md` §6 forbids a number we did not measure from appearing in a
claim. Cost-per-resolved-task in a published report must come from the
provider's own reported usage where it exists.

Rounding is deliberately **up**, per call. A cap that rounds down leaks a
fraction of a cent per call and, over a 300-task publication run, a cap that
leaks is not a cap.
"""

from __future__ import annotations

import math

from aether.domain.budget import BudgetDims
from aether.domain.ids import Frozen


class ModelPrice(Frozen):
    """Rate card entry. Integer micro-USD per *million* tokens — the unit
    providers quote, kept integer so budget arithmetic stays integer (I3)."""

    prompt_usd_micros_per_mtok: int
    completion_usd_micros_per_mtok: int


#: Published rates, 2026-08. A model absent here prices at `UNKNOWN_PRICE`,
#: which is deliberately **not** zero — an unpriced model must not look free to
#: a spend cap. Update from the provider's rate card, never from memory.
PRICES: dict[str, ModelPrice] = {
    # OpenRouter
    "deepseek/deepseek-v4-flash": ModelPrice(
        prompt_usd_micros_per_mtok=270_000, completion_usd_micros_per_mtok=1_100_000
    ),
    "qwen/qwen3-coder": ModelPrice(
        prompt_usd_micros_per_mtok=300_000, completion_usd_micros_per_mtok=1_200_000
    ),
    "qwen/qwen-2.5-coder-32b-instruct": ModelPrice(
        prompt_usd_micros_per_mtok=60_000, completion_usd_micros_per_mtok=180_000
    ),
    # Local endpoints cost nothing per token; electricity is not in this ledger.
    "local": ModelPrice(prompt_usd_micros_per_mtok=0, completion_usd_micros_per_mtok=0),
}

#: The price of a model we have no rate for. High on purpose: an unknown model
#: should trip a cap early and loudly rather than spend silently under one.
UNKNOWN_PRICE = ModelPrice(
    prompt_usd_micros_per_mtok=10_000_000, completion_usd_micros_per_mtok=30_000_000
)

#: Endpoints that bill nothing. Matched against the base URL, so a local run
#: does not have to name every model it might serve.
FREE_ENDPOINT_HOSTS = ("localhost", "127.0.0.1", "0.0.0.0", "host.docker.internal")


def is_free_endpoint(base_url: str) -> bool:
    host = base_url.split("//", 1)[-1].split("/", 1)[0].split(":", 1)[0]
    return host in FREE_ENDPOINT_HOSTS


def price_for(model: str, *, base_url: str | None = None) -> ModelPrice:
    if base_url is not None and is_free_endpoint(base_url):
        return PRICES["local"]
    return PRICES.get(model, UNKNOWN_PRICE)


def cost_usd_micros(
    model: str, prompt_tokens: int, completion_tokens: int, *, base_url: str | None = None
) -> int:
    """Micro-USD for one call, rounded **up**. A cap that rounds down leaks."""
    price = price_for(model, base_url=base_url)
    prompt_cost = prompt_tokens * price.prompt_usd_micros_per_mtok / 1_000_000
    completion_cost = completion_tokens * price.completion_usd_micros_per_mtok / 1_000_000
    return math.ceil(prompt_cost + completion_cost)


def priced(
    model: str, dims: BudgetDims, *, base_url: str | None = None
) -> BudgetDims:
    """`dims` with `usd_micros` filled in from its own token counts.

    Never overwrites a `usd_micros` the provider itself reported — a measured
    cost beats a computed one, always.
    """
    if dims.usd_micros:
        return dims
    return dims.model_copy(
        update={
            "usd_micros": cost_usd_micros(
                model, dims.prompt_tokens, dims.completion_tokens, base_url=base_url
            )
        }
    )


__all__ = [
    "FREE_ENDPOINT_HOSTS",
    "PRICES",
    "UNKNOWN_PRICE",
    "ModelPrice",
    "cost_usd_micros",
    "is_free_endpoint",
    "price_for",
    "priced",
]
