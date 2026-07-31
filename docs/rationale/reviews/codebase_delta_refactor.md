---
status: historical
retrieval: excluded
---
# CODEBASE DELTA & REFACTOR PLAN — `src/sagiha` → SAGIHA v2

**Baseline audited:** HEAD `66ce774`, ~5.7k LOC src (84 files), 127/127 tests passing (verified in this audit: `PYTHONPATH=src python -m pytest tests/ -q` → `127 passed in 1.30s`, with `openai` + `respx` installed; note the environment ran Python 3.12 against the `requires-python >= 3.13` pin — CI presumably uses 3.13, but the pin is not what made anything pass).
**Reference:** `NEXT_GEN_HARNESS_ARCHITECTURE_SPEC.md` (v2 Spec) + `further_improvements.md` amendments.
**Method:** every claim below was verified against the file at the stated path, not inferred from docs. Where the code contradicts STATUS.md or the tool catalog, the code is quoted.

---

## 0. Executive Findings — What the Line-Level Read Changed

The Spec's plan assumed the docs' description of the code was accurate. Four code-verified findings materially reprioritize the refactor; they are labeled **H** (honesty defects — code that reports success it did not earn) and referenced throughout:

| ID | Finding | Evidence | Severity |
| :- | :--- | :--- | :--- |
| **H1** | **Three of four coding gates are hardcoded constants.** `GateEvaluator.evaluate()` returns `no_new_suppressions=True, tests_unmodified=True, coverage_not_decreased=True, diff_within_bounds=True` unconditionally. `tests_unmodified` — the gate the entire evaluation-capture threat model (T3) rests on, the one `validate_security_invariants` refuses to let config disable — **is a constant**. `GateReport.admitted` is therefore `acceptance_met` wearing four fake medals. Every "gated" claim in STATUS.md inherits this. | `outer_loop/evaluator/gate_evaluator.py:70-79` | **Critical** |
| **H2** | **Budget enforcement is dead code.** `ResourceGovernor.record_spend()` is called nowhere in `src/` (grep-verified). `remaining_budget()` therefore always returns the full budget; `RunLoop`'s budget-exhaustion break is unreachable. `RunLoop` emits `TokenUsage(input_tokens=0, output_tokens=0)` and `CostSummary(usd=0.0)` on every step — cost telemetry is fiction, and the E0 "within cost budget" gate criterion is unmeasurable. | `kernel/governor.py` (no callers of `record_spend`), `agency/run_loop.py:205-216` | **Critical** |
| **H3** | **Block-5 scaffolding stubs return fabricated success.** `ContainerSandbox.apply_edit()` returns `EditResult(hunks=(HunkResult(applied=True, …),), syntax_valid=True)` without touching anything; `write()` is `pass`; `MCPClientDriver.invoke_tool()` returns `""`. A stub that lies is worse than an absent adapter — if ever bound by a config typo, the agent believes its edits landed. Same class of defect the project's own D2 (cassette silent-repeat) review condemned. | `adapters/sandbox/container.py:34-40`, `adapters/mcp/driver.py:29-32` | High |
| **H4** | **`syntax_valid` is a constant `True`.** The tool catalog normatively claims "a structurally broken edit is rejected before the language server sees it" via a Tree-sitter check; `LocalWorkspace.apply_edit` hardcodes `syntax_valid=True` on both the success and failure paths. This is also the field the A4 adjudication relied on when rejecting pre-execution AST gating — the *placement* argument stands, but the check itself must now actually be built. | `adapters/workspace/local.py:74,85` | High |

Additional code-level defects folded into the plan below: benchmark-specific path hack in a production tool handler (`builtins.py` `apply_edit` strips `app/` prefixes — §2.3), `apply_edit` misclassified `IDEMPOTENT` (re-applying a landed search/replace does **not** converge: the anchor is gone → `anchor_not_found`; catalog says `D`), schema drift between `composition.py`'s hand-written `ToolSchema` literals and `builtins.py`'s `BUILTIN_SCHEMAS` (composition's `apply_edit` schema omits `expected_occurrences` — live drift, exactly the "contract stated in two places" failure the docs warn about), `Kernel.workspace` typed as concrete `LocalWorkspace` instead of the `Workspace` port, lossy resume (`_reconstruct_history` silently drops assistant text-only turns — steps persist only `tool_calls`/`tool_results`, so a resumed run's request digest can never match a recorded one), and the dead `ShortTermMemory` Protocol whose adapter was deleted (R7) while the port text survived.

---

## 1. Port Deprecation & Merge Ledger (`src/sagiha/ports/`)

Consolidation 21 → 15 per Spec §1.2. `tests/contracts/test_port_shape.py` enumerates ports **dynamically** (`pkgutil` + `importlib.import_module(f"sagiha.ports.{info.name}")` — verified at line 35), so file deletions self-heal the shape suite; no test edits needed for removals. Grep-verified: none of the deleted Protocols is imported by `composition.py`, `run_loop.py`, `dispatch.py`, or any adapter — deletion breaks no execution flow.

| Path | Action | Details & blast radius |
| :--- | :--- | :--- |
| `ports/reviewer.py` (21 LOC) | **DELETE** | Zero adapters, zero imports outside the file. Semantics (frontier judge ≠ generator, soft-score-never-gates) move to `ports/search.py` docstring + the new `score()` method (§2.9). `domain/work.py::ReviewReport` **stays** — it becomes `CandidateSearch.score()`'s return type; the `events.py` event carrying it stays with it. |
| `ports/advisory.py` (29 LOC) | **REWRITE** — 3 Protocols → 1 | Replace `RewardPredictor` / `FailurePredictor` / `CostPerformanceEstimator` with:<br>`class Advisory(Protocol):`<br>`    async def predict(self, kind: PredictionKind, task: TaskSpec, branch_id: str | None = None) -> Prediction: ...`<br>`PredictionKind = Literal["reward", "failure", "cost_performance"]` added to `domain/work.py`. `PORT_VERSION = 2`. Zero adapters exist; zero call sites; `aoi/__init__.py` is 4 LOC of nothing — no breakage possible. |
| `ports/embedding.py` (18 LOC) | **DELETE** | Zero adapters, zero importers (grep-verified: only `ports/embedding.py` itself mentions `EmbeddingProvider`). ADR-0014 already defers the dense tier; the Protocol is re-created *inside* the future dense `Memory`/`Indexer` adapter when the recall@10 trigger fires. Record the deletion + re-promotion condition as ADR-0019. |
| `ports/memory.py` | **EDIT** — delete `ShortTermMemory` Protocol (lines 17-23), keep `Memory` | The adapter was deleted 2026-07-30 (R7; `adapters/memory/short_term.py` docstring confirms); the Protocol is now a contract with no implementation and no consumer — precisely the "dead second path" D12 named. `RunLoop` history stays loop-local. Remove the `TrajectoryStep` import that only it used. |
| `ports/model.py`, `ports/tool_registry.py`, `ports/search.py` | **VERSION-BUMPED EDITS** | Not deletions — S2 changes specified in §2. All three are `provisional`; the versioning policy permits breaking bumps with a one-line migration note. |
| All other port files | **KEEP UNCHANGED** | `policy.py`, `governor.py`, `trajectory.py`, `workspace.py`, `evaluator.py`, `orchestrator.py`, `indexer.py`, `code_graph.py`, `lsp.py`, `toolchain.py`, `benchmark.py`, `meta_improver.py` (dormant per Spec §2.3 Tier C — keep the Protocol, it costs 22 LOC). |

**Resulting count:** 21 Protocols → 15 (`ShortTermMemory`, `Reviewer`, `EmbeddingProvider`, and 3 predictors removed; 1 `Advisory` added). Add the rent rule to `docs`: any port with zero non-test adapters for two consecutive blocks auto-demotes to `experimental`.

---

## 2. Surgical Modifications List (per file)

Ordered by the Spec's action-plan priority, not by directory.

### 2.1 `outer_loop/evaluator/gate_evaluator.py` — make the gates real (H1) — **do this first**

The TCB's only implementation currently vouches for properties it never checks. Minimal honest v1, no new ports:

- **`tests_unmodified`**: constructor gains `test_paths: tuple[str, ...] = ("tests/",)` and `base_ref: str = "HEAD"`. Evaluate runs `["git", "diff", "--name-only", base_ref, "--", *test_paths]` through the existing `dispatch()` path (same as criteria checks); gate = output empty. Until worktrees land (Block 3), `base_ref` is the checkpoint commit taken at run start — which requires `RunLoop` to call `workspace.checkpoint("run-start")` before step 1 and pass the sha through `RunContext` (add field `base_commit: str | None = None` to `domain/control.py::RunContext`; frozen model, additive default — non-breaking).
- **`diff_within_bounds`**: `["git", "diff", "--numstat", base_ref]` → sum adds+dels ≤ `config.gates.max_diff_lines`. Constructor gains `max_diff_lines: int`.
- **`no_new_suppressions`**: `git diff base_ref -U0` filtered for added lines matching `(# type: ignore|# noqa|# pragma: no cover|pytest.mark.skip)` → gate = zero new matches. Deterministic, cheap, closes the exploit the LSP port docstring names.
- **`coverage_not_decreased`**: the only gate that legitimately cannot be honest yet (no `Toolchain` adapter, no baseline measurement). Set it to **`None` with `profile != coding-full`** semantics — but since `GateReport.admitted` correctly refuses `None`, introduce `GatesConfig.require_coverage_not_decreased: bool` gating whether it's evaluated (`False` ⇒ field stays `None` **and** the coding profile's admitted-set shrinks accordingly via a new `GateReport.required_gates: frozenset[str]` — see §2.10). Honest `None` + explicit config beats fabricated `True`.
- Emit per-gate results into `CriterionResult`-style entries so the E0 reporter can attribute failures.

**Proving tests** (extend `tests/unit/test_sprint3a_e2e.py`): a run that edits a file under `tests/` must produce `tests_unmodified=False` and `admitted=False`; a run whose diff exceeds `max_diff_lines` must fail `diff_within_bounds`.

### 2.2 `agency/run_loop.py` + `kernel/governor.py` + `ports/model.py` — resurrect budget accounting (H2)

- **`ports/model.py` → v2:** `complete()` returns a new `domain/trajectory.py::Completion(message: Message, usage: TokenUsage, model: str)` instead of bare `Message`. This is the minimal shape that lets the loop stop inventing zeros. (`Message` gaining an optional `usage` field was considered and rejected: usage is a property of the *call*, not the message, and it would leak into history/cassette digests.) Cassette entries store `Completion`; existing fixture cassettes migrate with a 20-line script in `scripts/` (wrap recorded message, `usage=TokenUsage(0,0)` for legacy entries — replay determinism unaffected because digests hash the *request*).
- **`adapters/model/openai.py`:** populate `usage` from the provider response (`response.usage.prompt_tokens/completion_tokens` — the adapter already receives them and drops them).
- **`agency/run_loop.py`:** after each completion — `usage` → real `ModelCallCompleted`; cost = `usage × price` where price comes from a new `domain/config.py::PricingConfig` (per-tier `usd_per_1m_input/output`, default `0.0` for local); call `await self._governor.record_spend(ctx.run_id, cost_usd)`. The existing `remaining_budget <= 0` break becomes live for the first time. Also fix the pre-existing hazard on the stuck-break path: when `stuck` triggers mid-blocks, the assistant message with unanswered `tool_use` blocks is already in `history` — append synthetic `is_error=True` `ToolResultBlock`s for the skipped calls before breaking, so a later resume reconstructs provider-valid history.
- **`kernel/governor.py`:** add `max_wall_clock_s` and step-token ceilings from `GovernorConfig` (fields exist in config, unenforced); enforce `max_concurrent_sandboxes` in `acquire()` for `kind="sandbox"` (currently a constructor arg stored and never read).

### 2.3 `adapters/tools/builtins.py` — de-hack, complete, reclassify

- **Delete the benchmark hack** (lines in `apply_edit` handler): `if path.startswith("app/"): path = path[4:]` / `elif path.startswith("./app/")…` — a fixture-repo-specific rewrite living in the production tool path, invisible to policy (the grant is minted for the *pre*-stripped path, then the handler mutates a *different* path than the one authorized — a genuine, if small, grant-scope integrity violation). If the fixture repo needs it, fix the fixture.
- **Add `write_file`** `(path, content) -> EditResult`, `EffectClass.DESTRUCTIVE`, `x-sagiha-path` on `path` — the catalog specifies it, and today the agent cannot create a file (`apply_edit` → `read_text` on a missing path → error). Description text per the catalog: "new files and full rewrites only."
- **Reclassify `apply_edit` → `EffectClass.DESTRUCTIVE`** (currently `IDEMPOTENT`, line 152). Re-application after success yields `anchor_not_found`, not convergence; the catalog itself lists it `D`. Under the current class, replay is *permitted* to re-run it — a live replay-correctness bug once `replay --verify` re-executes idempotent calls.
- Return structured payloads (`EditResult`/`CommandResult` JSON already done; `list_dir`/`grep` return `str(list)` — switch to `model_dump_json` of `DirEntry`/`Match` models that already exist in `domain/content.py` and are currently unused).

### 2.4 `adapters/workspace/local.py` — real `syntax_valid` (H4)

In `apply_edit`, before the final `write_text`: if `target.suffix == ".py"`, run `ast.parse(text)` (stdlib — Tree-sitter is the Block-4 multi-language upgrade, not a prerequisite for honesty); on `SyntaxError`, **do not write**, return `EditResult(hunks=…applied=False, reason=f"syntax_error:{e.lineno}", syntax_valid=False)`. Non-Python files: `syntax_valid=True` is legitimate (no claim made). This closes H4 at the exact boundary the catalog promised, and gives the A4-adjudication footnote (per-file validity map) its data source for free.

### 2.5 `kernel/policy/effects.py` — **NEW** — per-invocation PURE allowlist (Spec §2.1.C)

Placed under `kernel/policy/` deliberately: the `tcb-isolation` import-linter contract already forbids `agency`/`aoi`/`adapters` imports here, making the allowlist TCB-protected by the existing mechanism.

```python
# kernel/policy/effects.py
PURE_ARGV: Final[frozenset[str]] = frozenset({"ls", "cat", "head", "tail", "wc", "git"})
PURE_GIT_OPS: Final[frozenset[str]] = frozenset({"status", "diff", "log", "show", "blame"})

def classify_command(argv: Sequence[str], declared: EffectClass) -> EffectClass:
    """Narrow run_command's declared DESTRUCTIVE to PURE for allowlisted read-only argv.
    Never widens; anything unmatched keeps `declared`. bash -lc is never narrowed."""
```

Wiring: `DefaultToolRegistry.dispatch` is the wrong place (adapters are not TCB). Instead `agency/run_loop.py` (and `GateEvaluator`) construct `ToolCall.effect` via `classify_command(args["command"], registry_effect)` when `tool_name == "run_command"`. `ToolCall.effect` is already recorded per-call in the trajectory (verified: `domain/content.py::ToolCall.effect`), so **replay needs zero changes** — it reads the recorded per-call class; `sagiha replay --verify` simply starts re-executing the newly-PURE majority. `ToolRegistry` port additionally gains `async def effect_for_call(self, call_args) -> EffectClass` as the extension seam (`PORT_VERSION = 2`); default implementation delegates to `get_effect_class` + `classify_command`.

**Proving test:** record a cassette containing `["git","status"]` and `["rm","x"]`; `replay --verify` must re-execute the first and serve the second from the recording.

### 2.6 `kernel/policy/engine.py` + `domain/content.py` + `kernel/dispatch.py` — TaintGate v1 (Spec §1.1, R1-amended)

Hook point resolved by reading the code: the choke point already has everything needed — no new gate framework.

1. **`domain/content.py`:** `ToolResult` gains `trusted: bool = False` (additive, default-safe for cassettes). **`adapters/tools/registry.py`:** `register_handler` gains `trusted_output: bool`; `dispatch` stamps `result.trusted` from registration. Builtins: `read_file`/`list_dir`/`grep`/`run_command` register `trusted_output=False` (they surface repo content — untrusted per the catalog); `apply_edit`/`write_file` `True`.
2. **`kernel/policy/engine.py`:** add `self._tainted_runs: set[str]`. In `record_outcome(grant_id, result)` — the grant is still in `self._active_grants` at that moment (verified: pop happens in this same method) — resolve `run_id` from the grant and, if `not result.trusted`, add it. **Monotonic**: nothing removes entries until the run terminates (R1). Expose `def is_tainted(self, run_id) -> bool` as a concrete-class helper (like `get_grant`, deliberately not on the Protocol — taint is Control-internal state).
3. **`authorize()`:** new pre-grant check: `if run tainted and tool ∈ MUTATION_TOOLS ({apply_edit, write_file, run_command}) → Decision(allowed=False, requires_human=True, reason="tainted-context mutation requires approval")` — at every autonomy level, per the amended spec. `MUTATION_TOOLS` lives in `kernel/policy/effects.py` (TCB).
4. **`kernel/dispatch.py`:** wrap untrusted results' text content in the `<untrusted-data source=…>` envelope before returning to the loop (currently the envelope exists only in docs), and emit a new `TaintIntroduced` event (add to `domain/events.py` + regenerate the event catalog via the existing `scripts/gen_event_catalog.py --check` gate).

Interactive-mode ergonomics: `requires_human=True` denials already flow back as `is_error` tool results the model can see; the CLI's approval loop is B5c work — until then, tainted mutations fail closed, which is the correct pre-sandbox posture.

### 2.7 `composition.py` — de-duplicate, de-concretize, order canonically

- **Delete the 60-line hand-written `tool_schemas` tuple** (drift confirmed: its `apply_edit` schema lacks `expected_occurrences` that `BUILTIN_SCHEMAS` declares). Derive: `tool_schemas = tuple(ToolSchema(name=n, description=TOOL_DESCRIPTIONS[n], parameters=s) for n, s in sorted(BUILTIN_SCHEMAS.items()))` — `sorted()` gives the canonical alphabetical ordering the prompt-architecture doc makes a cache-stability requirement; `TOOL_DESCRIPTIONS` joins the schemas in `builtins.py` as the single source.
- **`Kernel.workspace: LocalWorkspace` → `Workspace`** (port type). One-line change; nothing accesses `LocalWorkspace`-only members through the kernel (grep-verified: `workspace.root` is used only inside `builtins.py`, which receives the concrete instance directly at registration — acceptable, it *is* the adapter layer).
- Thread `PricingConfig` into the governor/loop (§2.2) and `trusted_output` flags into registration (§2.6).
- Judge-separation refusal (Spec §4.3): extend `Config.validate_security_invariants` — `if search.enabled and roles["judge"] resolves to the same (provider, model) tuple as roles["execution"] → ValueError`. Note the validator already exists and already refuses three insecure states; this is additive.

### 2.8 `adapters/sandbox/container.py`, `adapters/mcp/driver.py`, `adapters/telemetry/otel.py` — stop the lying stubs (H3)

Every not-yet-implemented method body becomes `raise NotImplementedError("Block 5 — see STATUS.md")`. Keep the files (placement is fine, and `test_block5_scaffolding.py` pins their existence); change that test to assert the methods **raise** — a scaffold that fails loud is a contract, one that fakes success is a booby trap. `MCPClientDriver.list_tools` returning `[]` may keep its shape (empty discovery is a truthful null), `invoke_tool` may not.

### 2.9 `ports/search.py` + `adapters/search/sequential.py` — Block 3 readiness (S2 bump)

Verified gap: `evaluate(branch_id)` and `select(branch_ids)` cannot reach a worktree, a task, or a gate — the N=1 adapter returns `None`/first-element accordingly. Block 3 cannot be built on this shape. Since the port is `provisional` and has one stub adapter and zero external consumers, take the break now, before Block 3 starts:

```python
class CandidateSearch(Protocol):  # PORT_VERSION = 2
    async def propose(self, task: TaskSpec, ctx: RunContext, n: int) -> list[str]: ...
    async def evaluate(self, branch_id: str, task: TaskSpec, ctx: RunContext) -> GateReport | None: ...
    async def score(self, branch_id: str, task: TaskSpec, report: GateReport) -> ReviewReport: ...  # absorbs Reviewer; S-0 deterministic proxy first (further_improvements A1)
    async def select(self, candidates: dict[str, GateReport | None]) -> str: ...
```

Early-pruning (`prune_on_first_gate_fail`) is adapter behavior inside `evaluate`, requiring no further port surface. `SearchConfig` gains `prune_on_first_gate_fail: bool = True`.

### 2.10 `domain/` — additive models for Blocks 3–4 (verified non-breaking)

Confirmed clean by inspection: `StepId(run_id, branch_id, seq, parent)` is already a DAG identity; `TaskSpec.parent_task_id` exists; `RunLoop` hardcoding `branch_id="main"` becomes a constructor parameter (one line). Required additions, all additive:

- `domain/work.py`: `PRDSpec`, `StorySpec` (with `depends_on: tuple[str, ...]` and `file_closure: tuple[str, ...]`), `StoryBoard`; `PredictionKind` (§1); `GateReport.required_gates: frozenset[str]` (default = current four) so `admitted` computes over the honestly-evaluable set (§2.1) instead of hardcoding field names.
- `domain/control.py`: `RunContext.base_commit: str | None = None` (§2.1); `FrozenRunState` per `further_improvements` §A3 — **grants field absent by design**; add `tests/contracts/` assertion that no field of `FrozenRunState` is `Grant`-typed (extends the existing `test_no_grant_in_any_public_signature` pattern).
- `domain/events.py`: `TaintIntroduced`, `ProviderFailover`, `CompactionApplied`, `RecoveryEscalated` (+ catalog regen).
- Known defect to record, fix optional in this pass: `_reconstruct_history` cannot reproduce assistant text-only turns (steps don't persist them) — either persist the full assistant `Message` on `TrajectoryStep` (schema addition, upcaster per `domain/upcasters.py` pattern) or document resume as digest-breaking. Recommend the former; it is also what the §6 dataset exporter needs.

---

## 3. New Module Placement Plan

The brief's directive 2 presumes `src/sagiha/agency/context/` exists — **it does not** (verified: `agency/` contains only `run_loop.py`). Prompt assembly is inline in `RunLoop.run()` (a `ModelRequest` literal) and `_reconstruct_history`. "Seed-only Layer 6" is therefore not an edit but a construction constraint on a new module — enforceable by shape: the assembler receives its retrieval seed exactly once, at construction, and exposes no refresh method.

```
src/sagiha/agency/context/
├── __init__.py
├── assembler.py      # ContextAssembler
└── compactor.py      # ExchangeCompactor
src/sagiha/kernel/policy/effects.py   # §2.5 — PURE_ARGV, MUTATION_TOOLS, classify_command
src/sagiha/ports/advisory.py          # rewritten — §1
```

**`assembler.py`** (agency layer — may import `domain`, `ports`, `kernel`; import-linter's existing `car-layering` contract already covers it):

```python
class AssembledPrompt(BaseModel):
    request: ModelRequest
    prefix_digest: str          # layers 1–7 hash — cache-stability regression signal
    tail_tokens: int

class ContextAssembler:
    def __init__(self, *, system_prompt: str, tool_schemas: tuple[ToolSchema, ...],
                 task: TaskSpec, retrieval_seed: tuple[RetrievalHit, ...] = (),  # Layer 6: set once, frozen
                 config: ContextConfig) -> None: ...
    def append_exchange(self, assistant: Message, results: tuple[Message, ...]) -> None: ...
    def anchored(self) -> AnchoredState: ...     # plan, open-file set, unresolved diagnostics
    def assemble(self, role: str) -> AssembledPrompt: ...   # triggers compaction check pre-assembly
```

`RunLoop` delegates its inline `history` list and `ModelRequest` construction here; `_reconstruct_history` moves in as `ContextAssembler.from_trajectory(...)`. Tool schemas are consumed in the canonical order from §2.7. Seed-only enforcement test: `pyright` + a contract test asserting `ContextAssembler` has no public method accepting `RetrievalHit` post-construction.

**`compactor.py`** (Spec §2.2, `further_improvements` R1):

```python
class Exchange(BaseModel):            # unit of compaction — never split
    assistant: Message                 # incl. tool_use / signed reasoning blocks
    results: tuple[Message, ...]       # paired tool_result turns
    tokens: int
    tainted: bool                      # R1: taint survives into the summary

class ExchangeCompactor(Protocol):     # agency-internal protocol, not a hexagonal port
    async def compact(self, exchanges: Sequence[Exchange], *, keep_first: int,
                      keep_last_tokens: int) -> tuple[Exchange, ...]:
        """Middle span → one synthetic Exchange (role=user, single TextBlock summary,
        tagged via CompactionApplied event; wrapped <untrusted-data> if any source tainted).
        Whole-exchange granularity ⇒ provider block-pairing preserved by construction."""
```

Two adapters: `TruncatingCompactor` (deterministic, no model call — v1 default, ships with the module) and `ModelCompactor` (uses the `compaction` role — lands when the fast tier is wired). `ContextConfig` changes: `compact_at_headroom: 0.15 → 0.20` (align with the R9 normative default), add `keep_first_exchanges: int = 2`, `keep_last_tokens: int = 24_000`; token counting via a `len(text)//4` estimator behind a single function so a real tokenizer swaps in later. **Conformance tests:** post-compaction request validates against `Message` pairing rules (no orphan `tool_result` `call_id`s); tainted-span summary carries the envelope; `total ≤ keep budgets ⇒ no-op`.

**TaintGate** needs **no new module** — §2.6 showed the choke point + policy engine already provide the hook; creating a separate gate class would add a second authorization path, which is the one thing the architecture forbids.

---

## 4. Validation Checklist

Regression protocol per phase (each numbered §2 change is one commit/PR):

1. **Frozen baseline (already captured in this audit):** `PYTHONPATH=src python -m pytest tests/ -q` → **127 passed**. Re-run after every phase; the count only goes up.
2. **Static gates:** `uv run lint-imports` (5 contracts, incl. `tcb-isolation` which now protects `kernel/policy/effects.py` for free) · `uv run pyright src/sagiha` (strict, 0 errors) · `uv run ruff check`.
3. **Replay integrity:** `uv run sagiha replay verify --verify --cassette tests/fixtures/replay_smoke/cassette.json --workspace tests/fixtures/replay_smoke/workspace --trajectory-db /tmp/replay_check.db` — must stay green through §2.2 (cassette `Completion` migration: run the migration script on the committed fixture in the same PR) and §2.5 (new PURE re-execution: add the two-command proving cassette).
4. **E0 noise floor (the brief's `bench --aa`):** `sagiha harvest --repo <target>` → `sagiha bench --suite <pinned> --aa` **before** §2.1 lands and **after** — expect the post-H1 pass-rate to *drop* (fabricated gates stop admitting); record both numbers. A refactor that makes the score fall because the grader became honest is a success and must be documented as such, or the next reader reverts it as a regression.
5. **New proving tests per phase:** §2.1 tests-modified⇒not-admitted; §2.2 spend recorded ⇒ budget break reachable (unit: governor with $0.01 cap aborts step 2); §2.4 syntax-broken edit not written; §2.5 PURE re-exec / DESTRUCTIVE served; §2.6 tainted-run mutation denied with `requires_human=True`, envelope present, `test_external_provenance` extended to summaries; §2.8 stub methods raise; §3 compactor pairing/taint/no-op invariants.
6. **Event catalog anti-drift:** `python scripts/gen_event_catalog.py --check` after every `domain/events.py` addition.
7. **Environment note for CI:** the suite passes on 3.12 despite the `>=3.13` pin (verified here); either the pin is doing no work or CI's 3.13 masks a latent 3.12 incompatibility — pick one deliberately (recommend keeping the pin and adding a 3.13 matrix assertion, since ADR-0009 binds it).

**Sequencing:** §2.1 (H1) and §2.2 (H2) land before anything else — every later measurement is uninterpretable while gates are constants and cost is zero. Then §1 deletions (zero-risk, shrink the surface), §2.3–2.8 in any order, §3 (compactor — the Spec's action-plan #1, and R1 requires taint plumbing from §2.6 to precede it), §2.9–2.10 last, immediately ahead of the Block 3 sprint they unblock.

**Verdict on directive 4 (Blocks 3–5 readiness):** domain identity (`StepId` DAG, `parent_task_id`) is already shaped for `StoryDAG` and best-of-N — **no breaking changes to Sprint 1–3 domain abstractions are required**; the breaks that are required (`ModelProvider` v2, `ToolRegistry` v2, `CandidateSearch` v2) are all on `provisional` ports with ≤1 stub adapter each, which is precisely the window the port-stability policy created for taking them. Taking them now, before Block 3 writes real consumers, is the cheapest they will ever be.
