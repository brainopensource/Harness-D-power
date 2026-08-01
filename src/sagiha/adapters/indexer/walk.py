"""Shared indexing vocabulary — one definition each, imported everywhere.

Four modules (`indexer/fts5.py`, `indexer/service.py`, `code_graph/treesitter.py`,
`outer_loop/init/generate.py`) each carried their own byte-identical `SKIP_DIRS`,
and two carried *divergent* `_module_name` implementations that put the same
symbol in two different namespaces (audit m-3 and M-3). Both are collapsed here.
"""

from __future__ import annotations

from typing import Final

#: Directories never walked for indexing, graphing, or layout discovery.
SKIP_DIRS: Final = frozenset({".git", ".venv", "venv", "node_modules", "__pycache__", ".sagiha"})

#: Non-Python file extensions that carry indexable prose.
TEXT_EXTENSIONS: Final = frozenset({".md", ".mdx"})

#: Fixed chunk-size policy. Was a config knob that the chunker accepted and
#: discarded (`del max_chunk_tokens`) while `fts5.py` hardcoded its own copy.
#: One constant until an ablation justifies tuning — see ADR-0027.
MAX_CHUNK_TOKENS: Final = 1024


def module_name(path: str) -> str:
    """Map a repo-relative source path to its dotted module name.

    `pkg/util.py` → `pkg.util` — the **full dotted path**, matching the code
    graph's `defines` edges.

    The indexer previously took only the last segment (`pkg/util.py` → `util`),
    so the same function was `util.greet` in an FTS `symbol_path` and
    `pkg.util.greet` in a graph node. Cross-referencing a retrieval hit to a
    graph node silently failed, and impact analysis disagreed with call
    resolution (M-3). This is the single surviving definition.
    """
    stem = path[:-3] if path.endswith(".py") else path
    return stem.replace("/", ".")
