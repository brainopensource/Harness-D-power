# **Dependencies & Version Policy**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

Every dependency below is a decision, not a suggestion. Sprint 1 should open zero of these questions.

## **Toolchain**

| Concern | Choice | Rationale |
| :--- | :--- | :--- |
| Python | **`>=3.13`** | Target runtime. No upper cap: SAGIHA is an application pinned by `uv.lock`, and caps on applications only create resolver friction |
| Package manager | **uv** | Fast enough to run inside the agent's own inner loop; `uv.lock` committed and authoritative |
| Lint + format | **ruff** | Replaces black, flake8, isort, pyupgrade with one tool and one config |
| Type checking | **pyright strict** (blocking) + **mypy strict** (advisory) | See below |
| Testing | **pytest `>=8.3`** + **pytest-asyncio `>=0.24`** | Conformance suites need parametrized async fixtures |
| Layer enforcement | **import-linter** | Makes the CAR boundary a build failure rather than a convention |

**Why 3.13 specifically.** Beyond current typing ergonomics, 3.13 ships the free-threaded build (PEP 703). That is directly relevant to this architecture: the strongest argument for compiled sidecars was GIL contention during CPU-bound Tree-sitter parsing, and a free-threaded interpreter attacks that problem without leaving Python. It is experimental and not the default, but it is one more reason the [sidecar deferral](../02-architecture/performance-sidecars.md) is likely to hold — and it should be benchmarked before any Rust rewrite is funded.

### Two Type Checkers, One Gate

Both are configured strict, but they occupy **different roles**:

* **pyright is the blocking CI gate.** It is the same engine the agent consumes through `LSPAdapter`, so the harness's self-check and the diagnostics the agent sees while editing can never disagree — a subtle but real property, since a divergence would mean the agent "fixes" errors CI doesn't see, or vice versa.
* **mypy runs as a non-blocking second opinion.** It catches a genuinely different slice of defects, particularly around variance and overloads.

Running *both* as blocking gates is a known failure mode: the two disagree at the edges, and the resolution is invariably a cast written to satisfy a checker rather than to express intent. Advisory-second-opinion keeps the extra coverage without that tax. A recurring mypy-only finding is promoted to blocking case-by-case.

## **Runtime Dependencies**

`pyproject.toml`:

```toml
[project]
requires-python = ">=3.13"
dependencies = [
  "pydantic>=2.10,<3",          # domain models + config validation, all port boundaries
  "anyio>=4.6",                 # structured concurrency, portable task groups
  "httpx>=0.28",                # HTTP for providers and MCP HTTP-SSE
  "typer>=0.15",                # CLI
  "rich>=13.9",                 # TUI rendering, diff display
  "structlog>=24.4",            # structured logging bridged to OTel
  "tree-sitter>=0.23",          # AST parsing
  "tree-sitter-language-pack>=0.7",   # bundled grammars, avoids per-language pins
  "sqlite-vec>=0.1",            # dense retrieval tier, Day 0
  "lsprotocol>=2023.0",         # typed LSP messages
  "mcp>=1.0",                   # official MCP SDK, stdio + HTTP-SSE
  "opentelemetry-sdk>=1.29",
  "opentelemetry-exporter-otlp>=1.29",
]
```

Floors here, exact pins in `uv.lock`. The lock file is committed and authoritative — the agent must never resolve dependencies non-deterministically mid-run.

## **Model Provider SDKs — Native, Behind One Port**

```toml
[project.optional-dependencies]
anthropic = ["anthropic>=0.40"]     # cache_control prompt caching, extended thinking
google    = ["google-genai>=0.1"]   # unified Google SDK
openai    = ["openai>=1.50"]        # GPT-*, plus every OpenAI-compatible endpoint
```

**Decision: native first-party SDKs, no universal abstraction layer.**

The obvious alternative — LiteLLM or similar — buys 100+ providers for one integration, but pays for them by normalizing to a lowest common denominator. The three capabilities this harness depends on most are exactly the ones that get normalized away:

* **Prompt cache control.** Cache breakpoints are provider-specific structures (`cache_control` on Anthropic). A layer that flattens them silently disables the largest cost lever in the system, and the entire [context architecture](../02-architecture/context-and-cache-engineering.md) is built on them.
* **Reasoning block fidelity.** Extended-thinking blocks carry signatures that must round-trip **verbatim** to continue a tool-use turn. Universal layers routinely re-serialize or drop provider-specific fields, breaking continuation and the cache with it.
* **Tool-use semantics.** Parallel tool calls, strict schema adherence, and streaming delta shapes differ per provider in ways that affect correctness, not just ergonomics.

**The `openai` SDK covers the long tail by itself.** Pointing its `base_url` at an OpenAI-compatible endpoint reaches Ollama, vLLM, LM Studio, OpenRouter, Together, Groq, and most local inference servers — through one adapter the harness already maintains. That collapses the main argument for a universal layer, so **LiteLLM is not a dependency**. If a provider appears that is neither tier-1 nor OpenAI-compatible, it gets its own small adapter behind `ModelProvider`, which is a few hundred lines.

**Model-agnosticism is a property of the port, not of the client library.** Zero lock-in comes from `ModelProvider` being one narrow interface with a conformance suite — not from routing everything through someone else's abstraction.

## **LSP Client — A Correction to Earlier Drafts**

Earlier revisions named **`pygls`**. `pygls` is a framework for *building* language servers; the harness needs to *consume* them. The stack is therefore:

* **`lsprotocol`** for typed LSP messages
* **a small in-house async JSON-RPC client** driving server subprocesses over stdio

`multilspy` is a credible alternative that wraps server lifecycle for several languages, but it owns its own process model, which conflicts with `ResourceGovernor` pool bounds. In-house is roughly 300 lines and keeps warm pooling, document overlays, and crash recovery under harness control — all three load-bearing under parallel search.

## **Deliberately Absent**

| Not used | Why |
| :--- | :--- |
| LiteLLM | Native tier-1 SDKs + OpenAI-compatible `base_url` cover the space without flattening cache and reasoning semantics |
| LangChain / LlamaIndex | The orchestrator *is* the product; adopting a framework means inheriting its control flow |
| LangGraph | Optional adapter behind `Orchestrator`, never a core dependency |
| Redis | STM is per-session and small; SQLite-WAL already gives durability and queryability |
| LanceDB (at Day 0) | `sqlite-vec` suffices below ~10⁶ vectors; revisit at S2 if measured |
| Neo4j / FalkorDB | Code graph is SQLite; embedded Kùzu only if traversal outgrows SQL |
| black, flake8, isort | Subsumed by ruff |
| poetry | uv resolves faster and its lock diffs cleanly |

## **Upgrade Policy**

Dependency bumps are ordinary harness mutations: conformance suite, benchmark suite, judged against the A/A noise floor.

**Model version changes invalidate the noise floor** and require re-measurement before any later comparison is believed. A provider changing underneath you is statistically indistinguishable from your harness changing, unless you re-baseline first.
