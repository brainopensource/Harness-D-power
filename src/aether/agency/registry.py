"""`Registry[T]` — the "Protocol + registry + get_x(name)" idiom
(`coding_guidelines.md` §2.1, templated on `workflow/edit_format.py`),
factored once so `capabilities/sources.py`, `capabilities/parsers.py`,
`capabilities/inference.py` and `roles.py` do not each hand-write the same
dict-lookup-and-raise boilerplate.

Each capability keeps its **own** named exception (`UnknownSource`,
`UnknownParser`, ...) rather than sharing one generic error type — an error
naming the kind of thing that went missing is more useful than one naming
"a capability", and `edit_format.py`'s `UnknownEditFormat` is the precedent.
`Registry` takes that exception type as a parameter rather than defining it,
so the specificity survives the factoring.
"""

from __future__ import annotations

from collections.abc import Mapping


class Registry[T]:
    """name -> capability, frozen at construction (I6). No runtime
    registration: build one, keep it, never mutate it. `get()` raises **at
    the call site that resolves a name to an implementation** — for every
    capability in this layer that is composition time, not the moment a
    prompt is first assembled (`UnknownEditFormat`'s precedent: a topology or
    role naming an unimplemented thing fails at load)."""

    def __init__(self, kind: str, items: Mapping[str, T], *, unknown: type[Exception]) -> None:
        self._kind = kind
        self._items = dict(items)
        self._unknown = unknown

    def get(self, name: str) -> T:
        item = self._items.get(name)
        if item is None:
            raise self._unknown(f"unknown {self._kind} {name!r}; registered: {sorted(self._items)}")
        return item

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._items))


__all__ = ["Registry"]
