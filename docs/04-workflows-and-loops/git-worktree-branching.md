# **Worktree Branching & Parallel Isolation**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Lifecycle**

1. **Allocate** — `WorktreeManager` creates an ephemeral directory on a dedicated branch off the base ref, returning a `Workspace` (not a path).
2. **Materialize** — link or copy ignored-but-required artifacts into the tree.
3. **Isolate** — the sub-agent edits, compiles, and tests within its directory.
4. **Commit & Verify** — commit per step; verify against a pristine injected test suite.
5. **Select or Land** — see merge policy below.
6. **Prune** — remove from disk and prune Git state.

## **Materialization Is Required, Not Optional**

A fresh worktree contains **only tracked files**. `.env`, `node_modules`, `.venv`, `target/`, and every build cache are simply absent, so the first command the agent runs fails. The previous design omitted this step entirely, which would have blocked the very first parallel run.

Materialization links or copies these artifacts, and the strategy is per-ecosystem: symlink where the toolchain tolerates it, copy where it does not, and share a read-only dependency store where the package manager supports one.

## **What Worktrees Do and Do Not Isolate**

Worktrees isolate **tracked file state**. Nothing else. Stating this precisely matters because failures from the rows below present as mysterious model errors:

| Resource | Isolated? | Consequence and mitigation |
| :---- | :---- | :---- |
| Tracked files | ✅ | The intended guarantee |
| Object database | ❌ | `index.lock` contention, `git gc` races. Serialize Git mutations behind one lock |
| Network ports | ❌ | Two agents binding `:3000` collide. Allocate from a governor-held pool |
| Dependency trees | ❌ | Per-tree install: minutes and gigabytes per branch |
| Global caches | ❌ | Concurrent writes to `~/.cargo`, pip, npm. Set per-run cache homes |
| Databases & services | ❌ | Parallel migrations corrupt a shared dev database. Needs per-branch instances |
| Environment & credentials | ❌ | Inherited from the parent. Scrub and re-inject per grant |

Isolating the bottom five requires **containers with per-branch volumes and a network namespace**. This is why containerization moved earlier in the roadmap: it is the only mechanism that makes the isolation claim true, and the previous Day-1 gate of "zero cross-branch state contamination" was therefore unreachable as specified.

## **Merge Policy: Selection, Not Reconciliation**

Rebasing *k* siblings that edited overlapping files makes conflict the expected case, and LLM conflict resolution is a high-variance operation to place on the critical path. Two situations, previously conflated, are handled differently:

### Competing candidates (System 2)
Alternative solutions to **one** task. Exactly one winner is selected; the rest are **discarded**. Siblings are never merged with each other, so conflicts cannot arise by construction. This is the common case, and it needs no conflict resolution at all.

### Decomposed parallel work
Distinct sub-tasks advancing together. The code graph partitions work into **disjoint file sets** before dispatch, using `CodeGraph.impacted_by()` to compute each sub-task's closure. Sub-tasks whose closures intersect are **serialized rather than parallelized**. Prevention at partition time is cheaper and far more reliable than reconciliation at merge time — and it puts the dependency graph the system already maintains to real use.

### Landing
Optimistic: rebase onto the latest base, re-run the full suite in a clean sandbox, land only on green. A stale base means re-verification, never a silent merge.

## **Checkpoints**

Commit-per-step inside the worktree is the checkpoint primitive — unifying checkpoint, rollback, and audit at negligible cost, and giving every intermediate state a diffable identity.
