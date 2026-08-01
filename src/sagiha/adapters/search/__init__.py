"""CandidateSearch adapters — Best-of-N with sequential repair.

`SequentialCandidateSearch` was deleted here (audit M-8): its `propose()` minted
`candidate-<uuid>` ids for worktrees that never existed, `evaluate()` returned
`None`, and `select()` returned `branch_ids[0]`. Under the v2-S1 H3 doctrine
those are false-success payloads, not dead code.

The sequential case is already covered by `BestOfNSearch` with `n_candidates=1`
(`best_of_n.py::_propose_sequential`), so even a `NotImplementedError` shell
would only point at code that exists. Import `BestOfNSearch` directly.
"""
