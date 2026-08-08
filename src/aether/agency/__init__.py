"""`agency/` — the mutable capability layer (ADR-0018, `spec.md` §3).

Sits below `workflow/` and above `measurement/` in the lattice:

    engine > workflow > agency > measurement > kernel > adapters > ports > domain

`workflow/` holds the TCB execution machinery — the executor, the validator,
the topology schema. `agency/` holds the mutable capabilities that machinery
drives: context sources, the prompt assembler, inference, parsers, roles.
The TCB drives mutable capabilities; that is the direction I7 and I8 require
and the direction `aether-agency-cannot-reach-the-judge` (`.importlinter`)
enforces: `agency/` may not import `workflow/`, `measurement/`, or
`evolution/`. The thing that judges is not reachable from the thing being
judged.
"""

from __future__ import annotations
