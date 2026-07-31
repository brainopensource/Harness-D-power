"""Tree-sitter AST-bounded chunking for Python source."""

from __future__ import annotations

from dataclasses import dataclass

from tree_sitter import Node
from tree_sitter_language_pack import get_parser

# Rough token estimate: whitespace-split words (good enough for max_chunk_tokens budgets).
_DEF_TYPES = frozenset({"function_definition", "async_function_definition", "class_definition"})


@dataclass(frozen=True, slots=True)
class Chunk:
    path: str
    symbol_path: str
    start_line: int
    end_line: int
    text: str


def _node_name(node: Node, source: bytes) -> str:
    name = node.child_by_field_name("name")
    if name is None:
        return "<anonymous>"
    return source[name.start_byte : name.end_byte].decode("utf-8", errors="replace")


def _signature_line(node: Node, source: bytes) -> str:
    """First line of the definition (signature / class header), body stripped for skeleton use."""
    line = source[node.start_byte : node.end_byte].decode("utf-8", errors="replace").splitlines()
    return line[0] if line else ""


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def _emit_chunk(
    path: str,
    symbol_path: str,
    node: Node,
    source: bytes,
    *,
    max_chunk_tokens: int,
) -> list[Chunk]:
    raw = source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")
    prefix = f"# {path}\n# {symbol_path}\n"
    body = prefix + raw
    start = node.start_point[0] + 1
    end = node.end_point[0] + 1
    if _estimate_tokens(body) <= max_chunk_tokens:
        return [Chunk(path=path, symbol_path=symbol_path, start_line=start, end_line=end, text=body)]

    # Oversized: keep signature prefix + split body on top-level statements inside the block.
    sig = _signature_line(node, source)
    body_node = node.child_by_field_name("body")
    if body_node is None or not body_node.children:
        return [Chunk(path=path, symbol_path=symbol_path, start_line=start, end_line=end, text=body)]

    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_start = start
    header = f"{prefix}{sig}\n"
    for child in body_node.children:
        piece = source[child.start_byte : child.end_byte].decode("utf-8", errors="replace")
        candidate = header + "\n".join([*buf, piece])
        if buf and _estimate_tokens(candidate) > max_chunk_tokens:
            text = header + "\n".join(buf)
            chunks.append(
                Chunk(
                    path=path,
                    symbol_path=symbol_path,
                    start_line=buf_start,
                    end_line=child.start_point[0],
                    text=text,
                )
            )
            buf = [piece]
            buf_start = child.start_point[0] + 1
        else:
            if not buf:
                buf_start = child.start_point[0] + 1
            buf.append(piece)
    if buf:
        chunks.append(
            Chunk(
                path=path,
                symbol_path=symbol_path,
                start_line=buf_start,
                end_line=end,
                text=header + "\n".join(buf),
            )
        )
    return chunks or [Chunk(path=path, symbol_path=symbol_path, start_line=start, end_line=end, text=body)]


def _walk(
    path: str,
    node: Node,
    source: bytes,
    *,
    max_chunk_tokens: int,
    parent_path: str,
    out: list[Chunk],
    symbols: list[tuple[str, str, str, int, str]],
) -> None:
    if node.type in _DEF_TYPES:
        name = _node_name(node, source)
        symbol_path = f"{parent_path}.{name}" if parent_path else name
        if node.type == "class_definition":
            kind = "class"
        elif parent_path:
            kind = "method"
        else:
            kind = "function"
        sig = _signature_line(node, source)
        symbols.append((path, name, kind, node.start_point[0] + 1, sig))
        out.extend(
            _emit_chunk(path, symbol_path, node, source, max_chunk_tokens=max_chunk_tokens)
        )
        # Recurse into class body for methods; do not re-chunk nested functions as top-level
        # duplicates if we already emitted the outer function — still walk classes.
        if node.type == "class_definition":
            body = node.child_by_field_name("body")
            if body is not None:
                for child in body.children:
                    _walk(
                        path,
                        child,
                        source,
                        max_chunk_tokens=max_chunk_tokens,
                        parent_path=symbol_path,
                        out=out,
                        symbols=symbols,
                    )
        return

    for child in node.children:
        _walk(
            path,
            child,
            source,
            max_chunk_tokens=max_chunk_tokens,
            parent_path=parent_path,
            out=out,
            symbols=symbols,
        )


def chunk_python_source(
    path: str,
    source: bytes,
    *,
    max_chunk_tokens: int = 1024,
) -> tuple[list[Chunk], list[tuple[str, str, str, int, str]]]:
    """Return (chunks, symbols) where symbols are (path, name, kind, line, signature)."""
    parser = get_parser("python")
    tree = parser.parse(source)
    chunks: list[Chunk] = []
    symbols: list[tuple[str, str, str, int, str]] = []
    _walk(
        path,
        tree.root_node,
        source,
        max_chunk_tokens=max_chunk_tokens,
        parent_path="",
        out=chunks,
        symbols=symbols,
    )
    return chunks, symbols


def skeleton_from_symbols(signatures: list[str]) -> str:
    return "\n".join(signatures)
