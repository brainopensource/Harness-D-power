"""AST-bounded Python source chunking via Tree-sitter."""

from __future__ import annotations

from dataclasses import dataclass

from tree_sitter import Node
from tree_sitter_language_pack import get_parser

_SYMBOL_NODE_TYPES = frozenset(
    {"function_definition", "async_function_definition", "class_definition"}
)


@dataclass(frozen=True)
class Chunk:
    path: str
    symbol_path: str
    start_line: int
    end_line: int
    text: str


def _module_name(path: str) -> str:
    stem = path.rsplit("/", 1)[-1]
    if stem.endswith(".py"):
        stem = stem[:-3]
    return stem.replace("/", ".")


def _node_text(source: bytes, node: Node) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8")


def _first_line(text: str) -> str:
    return text.splitlines()[0] if text else ""


def _walk_symbols(
    node: Node,
    source: bytes,
    *,
    module: str,
    class_name: str | None,
    chunks: list[Chunk],
    signatures: list[tuple[str, str, str, int, str]],
    path: str,
) -> None:
    if node.type in _SYMBOL_NODE_TYPES:
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return
        name = _node_text(source, name_node)
        text = _node_text(source, node)
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1

        if node.type == "class_definition":
            symbol_path = f"{module}.{name}" if class_name is None else f"{module}.{class_name}.{name}"
            kind = "class"
            sig = _first_line(text)
            chunks.append(
                Chunk(
                    path=path,
                    symbol_path=symbol_path,
                    start_line=start_line,
                    end_line=end_line,
                    text=text,
                )
            )
            signatures.append((path, name, kind, start_line, sig))
            body = node.child_by_field_name("body")
            if body is not None:
                for child in body.children:
                    _walk_symbols(
                        child,
                        source,
                        module=module,
                        class_name=name,
                        chunks=chunks,
                        signatures=signatures,
                        path=path,
                    )
            return

        symbol_path = f"{module}.{name}" if class_name is None else f"{module}.{class_name}.{name}"
        kind = "method" if class_name else "function"
        sig = _first_line(text)
        chunks.append(
            Chunk(
                path=path,
                symbol_path=symbol_path,
                start_line=start_line,
                end_line=end_line,
                text=text,
            )
        )
        signatures.append((path, name, kind, start_line, sig))
        return

    for child in node.children:
        _walk_symbols(
            child,
            source,
            module=module,
            class_name=class_name,
            chunks=chunks,
            signatures=signatures,
            path=path,
        )


def analyze_python_source(
    path: str, source: bytes, *, max_chunk_tokens: int
) -> tuple[list[Chunk], list[tuple[str, str, str, int, str]]]:
    """Chunk Python source and collect symbol rows for indexing.

    Returns chunks and symbol rows ``(path, name, kind, line, signature)``.
    """
    del max_chunk_tokens  # reserved for oversized-chunk splitting
    parser = get_parser("python")
    tree = parser.parse(source)
    module = _module_name(path)
    chunks: list[Chunk] = []
    signatures: list[tuple[str, str, str, int, str]] = []
    _walk_symbols(
        tree.root_node,
        source,
        module=module,
        class_name=None,
        chunks=chunks,
        signatures=signatures,
        path=path,
    )
    return chunks, signatures


def chunk_python_source(path: str, source: bytes, *, max_chunk_tokens: int) -> list[Chunk]:
    """Chunk Python source at function/class boundaries."""
    chunks, _ = analyze_python_source(path, source, max_chunk_tokens=max_chunk_tokens)
    return chunks
