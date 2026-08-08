"""Capability implementations: sources, inference, parsers, edit formats.

Each module here follows the same `Protocol + registry + get_x(name)` idiom
(`coding_guidelines.md` §2.1) built once in `agency/registry.py`.
"""

from __future__ import annotations
