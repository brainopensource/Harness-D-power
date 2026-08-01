"""AST-bounded Python source chunking via Tree-sitter."""

from __future__ import annotations

from dataclasses import dataclass

from tree_sitter import Node, Tree
from tree_sitter_language_pack import get_parser

from sagiha.adapters.indexer.walk import module_name

_SYMBOL_NODE_TYPES = frozenset({"function_definition", "async_function_definition", "class_definition"})


@dataclass(frozen=True)
class Chunk:
    path: str
    symbol_path: str
    start_line: int
    end_line: int
    #: What gets indexed and what gets shown: the envelope followed by `body`.
    text: str
    #: The raw AST span, unenveloped, for consumers that need clean bytes.
    body: str = ""


def _envelope(path: str, symbol_path: str, signature: str, body: str) -> str:
    """Prefix a chunk with the context needed to read it standalone (M-5).

    BM25 cannot match a query on a file path or a dotted symbol name unless
    those strings are *in* the indexed text — and a goal usually mentions one or
    the other. Without this, a recall miss caused by chunking gets misattributed
    to "lexical retrieval is weak", which is the trigger ADR-0014 uses to justify
    the dense tier. Wrong cause, expensive cure.
    """
    return f"{path}\n{symbol_path}\n{signature}\n---\n{body}"


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
                    text=_envelope(path, symbol_path, sig, text),
                    body=text,
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
                text=_envelope(path, symbol_path, sig, text),
                body=text,
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


def parse_python(source: bytes) -> Tree:
    """Parse Python source once; shared by indexer chunking and code-graph extraction."""
    return get_parser("python").parse(source)


def analyze_python_tree(
    path: str,
    source: bytes,
    tree: Tree,
) -> tuple[list[Chunk], list[tuple[str, str, str, int, str]]]:
    """Chunk an already-parsed Python tree and collect symbol rows for indexing.

    Returns chunks and symbol rows ``(path, name, kind, line, signature)``.
    """
    module = module_name(path)
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


def analyze_python_source(
    path: str, source: bytes
) -> tuple[list[Chunk], list[tuple[str, str, str, int, str]]]:
    """Chunk Python source and collect symbol rows for indexing.

    Returns chunks and symbol rows ``(path, name, kind, line, signature)``.
    """
    tree = parse_python(source)
    return analyze_python_tree(path, source, tree)


def chunk_python_source(path: str, source: bytes) -> list[Chunk]:
    """Chunk Python source at function/class boundaries."""
    chunks, _ = analyze_python_source(path, source)
    return chunks
