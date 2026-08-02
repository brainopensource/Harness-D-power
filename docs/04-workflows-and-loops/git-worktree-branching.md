---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Worktree Branching & Parallel Isolation**

> [!NOTE]
> **Working Proposal Disclaimer**: Architectural proposal refined iteratively during evaluation.

## **Lifecycle**

1. **Allocate** — `WorktreeManager` creates an ephemeral directory on a dedicated branch off the base ref, returning a `Workspace` handle.
2. **Materialize** — Symlink or copy ignored build artifacts (`node_modules`, `.venv`, `.env`) into the tree.
3. **Isolate** — Sub-agent edits, compiles, and tests within its workspace directory.
4. **Commit & Verify** — Commit per step; verify against a pristine injected test suite.
5. **Select or Land** — Apply merge policy (selection or disjoint landing).
6. **Prune** — Remove directory from disk and prune Git state.

## **Materialization Requirements**

Fresh git worktrees contain only tracked files. Toolchains fail if un-tracked artifacts (`.venv`, `node_modules`, build caches) are omitted. Strategy is ecosystem-dependent: symlink where supported, copy where required, or reference a read-only shared dependency store.

## **Resource Isolation Scope**

Worktrees isolate **tracked file state only**:

| Resource | Isolated? | Consequence & Mitigation |
| :--- | :--- | :--- |
| Tracked files | ✅ | Intended filesystem isolation guarantee. |
| Object database | ❌ | `index.lock` contention & `git gc` races. Serialize Git mutations behind a global lock. |
| Network ports | ❌ | Port collisions (e.g. `:3000`). Allocate ports from a governor pool. |
| Dependency trees | ❌ | Heavy per-tree installs. Share package store where supported. |
| Global caches | ❌ | Concurrent writes (`~/.cargo`, `pip`). Override per-run cache home directories. |
| Databases & services | ❌ | Shared DB migration corruption. Requires dedicated per-branch service instances. |
| Environment & credentials | ❌ | Inherited state. Scrub and re-inject per grant. |

* Full non-file isolation requires containerization (per-branch volumes + network namespaces).

## **Merge Policy: Selection, Not Reconciliation**

### Competing Candidates (System 2)
* Alternative implementations for a single task: select **one winner** and discard remaining candidates. Siblings are never cross-merged.

### Decomposed Parallel Work
* Work is partitioned into **disjoint file sets** using `CodeGraph.impacted_by()`. Sub-tasks with intersecting closures are serialized.

### Landing
* Rebase winner onto latest base ref, execute full test suite in a clean sandbox, and land only on green. Stale base refs trigger re-verification.

## **Checkpoints**

Commit-per-step inside the worktree serves as the unified checkpoint, rollback, and audit primitive.
