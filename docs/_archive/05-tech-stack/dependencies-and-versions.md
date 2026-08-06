---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Dependencies & Version Policy**

> [!NOTE]
> **Working Proposal Disclaimer**: Architectural proposal refined iteratively during evaluation.

## **Toolchain**

| Concern | Choice | Rationale |
| :--- | :--- | :--- |
| Python | **`>=3.13`** | Target runtime; leverages PEP 703 free-threading to avoid GIL bottlenecking during Tree-sitter AST parsing ([sidecar deferral](../02-architecture/performance-sidecars.md)). |
| Package manager | **uv** | Fast execution; authoritative `uv.lock` committed to repository. |
| Lint & Format | **ruff** | Unified replacement for black, flake8, isort, and pyupgrade. |
| Type checking | **pyright strict** (blocking) + **mypy strict** (advisory) | Dual-checker strategy: pyright aligns with LSP diagnostics in CI; mypy provides a non-blocking second opinion. |
| Testing | **pytest `>=8.3`**, **pytest-asyncio `>=0.24`** | Supports parametrized async fixtures in conformance suites. |
| Layering | **import-linter** | Enforces CAR boundary contracts in CI. |

## **Runtime & Dev Dependencies**

From `pyproject.toml`:

```toml
[project]
requires-python = ">=3.13"
dependencies = [
  "pydantic>=2.10,<3",                 # Domain models and config validation
  "anyio>=4.6",                        # Structured concurrency and task groups
  "httpx>=0.28",                       # HTTP client for providers and MCP
  "typer>=0.15",                       # CLI parsing
  "rich>=13.9",                        # TUI rendering and diff displays
  "structlog>=24.4",                   # Structured logging bridged to OTel
  "tree-sitter>=0.23",                 # AST parsing
  "tree-sitter-language-pack>=0.7",    # Grammars
  "watchfiles>=0.24",                  # Incremental re-indexing (see Indexing & Retrieval)
  "lsprotocol>=2023.0",                # LSP protocol schemas
  "mcp>=1.0",                          # Official Model Context Protocol SDK
  "opentelemetry-sdk>=1.29",
  "opentelemetry-exporter-otlp>=1.29",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3",
  "pytest-asyncio>=0.24",
  "pytest-cov>=5.0",                 # Backs coverage_not_decreased gate
  "ruff>=0.8.0",
  "pyright>=1.1.380",
  "mypy>=1.13",
  "import-linter>=2.0",
  "detect-secrets>=1.5.0",
]
```

* **No Container SDK**: Containers are invoked directly via Podman CLI inside the `Workspace` adapter to avoid requiring root daemon sockets ([ADR-0016](../08-decisions/0016-container-runtime-podman.md)).

## **Model Provider SDKs**

```toml
[project.optional-dependencies]
anthropic = ["anthropic>=0.40"]     # Prompt cache control & extended thinking
google    = ["google-genai>=0.1"]   # Unified Google SDK
openai    = ["openai>=1.50"]        # OpenAI & OpenAI-compatible endpoints
```

* **Native SDK Strategy**: Native SDKs preserve provider-specific prompt cache control (`cache_control`), reasoning block signatures, and tool-call semantics ([context architecture](../02-architecture/context-and-cache-engineering.md)).
* Universal abstractions (e.g. LiteLLM) are excluded; `openai` SDK covers OpenAI-compatible endpoints (Ollama, vLLM, OpenRouter).

## **LSP Client Architecture**

Combines `lsprotocol` with an in-house async JSON-RPC stdio client. Rejects `pygls` (server-side only) and `multilspy` (conflicts with `ResourceGovernor` process pooling).

## **Deliberately Absent Dependencies**

| Excluded | Rationale |
| :--- | :--- |
| **LiteLLM** | Replaced by native tier-1 SDKs + OpenAI-compatible base URLs to retain prompt caching. |
| **LangChain / LlamaIndex** | Custom orchestrator manages control flow directly. |
| **LangGraph** | Kept optional behind `Orchestrator` adapter; non-core. |
| **Redis** | SQLite-WAL handles session state and trajectory logging. |
| **Vector DBs** (`sqlite-vec`, LanceDB) | Dense retrieval deferred behind measured recall@10 trigger ([ADR-0014](../08-decisions/0014-defer-dense-retrieval.md)); v1 uses BM25/FTS5 + code graph. |
| **Graph DBs** (Neo4j, FalkorDB) | SQLite handles code graphs; Kùzu deferred unless SQL traversal limits are reached. |
| **Container SDKs** | Uses CLI sub-processes per [ADR-0016](../08-decisions/0016-container-runtime-podman.md). |

## **Upgrade Policy**

* Dependency updates are evaluated via test suites against A/A noise floors.
* Provider model updates invalidate baseline noise floors and require mandatory re-baselining.
