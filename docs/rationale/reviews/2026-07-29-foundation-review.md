---
status: historical
retrieval: excluded
date: 2026-07-29
scope: Full tree — 74 docs (~8,400 lines), src/ (~2,800 lines), tests/ (16 tests), CI, sprint plan. Sprint 2 in progress at review time (HEAD 0f61d5a).
---
# **Foundation Review & Deep Audit — Architecture, Code, Docs & Delivery Sequencing**

**Purpose.** SAGIHA's goal is an autonomous agent with an LLM as the brain and the harness as the
body: perception (retrieval, diagnostics), memory (STM/LTM), motor control (tools through a
capability choke point), and a conscience (gates, policy, audit). This audit judges whether the
current foundation can *grow into that without a rewrite* — and therefore focuses in depth on what
is broken, drifted, or unproven. What is good is summarized briefly for reference (§2).

**Audit method.** Every finding was mechanically confirmed, not inferred from prose:

```
uv run pytest -q            # 16 passed
uv run pyright              # 0 errors (strict, src/)
uv run ruff check           # clean
uv run lint-imports         # 5 contracts kept; 1 vacuous warning (agency/ empty)
uv run python - <<'PY'      # D1 reproduction: tool_use parses as ToolUseBlock; ToolCall rejected
...Message.model_validate({'role':'assistant','content':[{'kind':'tool_use',...}]})...
PY
rg <symbol> src/            # dead-code confirmations (get_effect_class, record_spend, min_provenance, schemas)
```

**Finding IDs** follow the convention in [reviews/README](./README.md): `D` defect, `G` gap,
`U` unproven assumption, `X` documentation remediation. IDs are stable;
[Sprint 3](../sprints/sprint-3.md) references them.

---

## **1. Executive Verdict**

**Coherent, disciplined, demonstration-poor — and the core loop is broken.** The code is *not*
overbuilt (~2,800 lines, mostly contracts) and the boundaries are genuinely clean, but the system
has never executed an autonomous step that used a tool: the ReAct loop's tool-dispatch branch is
structurally dead code (D1), the composition root binds a replay stub in every mode (D3), the tool
registry is constructed empty, and the CLI exposes only `version`. The 21 ports are backed by 4
adapters. Capability security is currently ceremony on a happy path nothing exercises
adversarially (D8). The audit trail is write-only (D6). Nothing is measured (G6).

The sharpest problem is **sequencing**, not architecture: the project's own 2026-07-28 review named
the measurement layer as the moat and E0 as the first slice; Sprint 2 built kernel plumbing
instead, and its next steps (MCP, OTel) extended the periphery further while the core was broken
and unmeasured. Verdict per category: **not overbuilt (code), not prematurely coupled, but
under-demonstrated at the core and over-specified at the periphery.** The correct next move is one
closed, measured, defect-free loop — Sprint 3.

---

## **2. Validated Capabilities (brief — for reference)**

| ID | Capability | Evidence |
| :--- | :--- | :--- |
| V1 | Layering structurally enforced | `.importlinter`: 5 contracts kept (CAR contract vacuous until `agency/` has code) |
| V2 | Ports wire-safe by construction | `tests/contracts/test_port_shape.py`: async-only, serializable payloads, no `dict[str, Any]`, no `Grant` on signatures, aware datetimes — a genuine asset |
| V3 | Config refuses insecure states | `domain/config.py::validate_security_invariants` + `tests/contracts/test_composition.py` |
| V4 | Dispatch choke point, fail-closed interceptors | `kernel/dispatch.py`, `kernel/bus.py`; happy path unit-tested; denial requires a minted `grant_id` |
| V5 | Append-only SQLite-WAL trajectory persistence | `adapters/trajectory/sqlite.py`, DAG `StepId` |
| V6 | Typed event schema (32 events) with anti-drift CI gate | `domain/events.py`, `scripts/gen_event_catalog.py --check` |
| V7 | Type/lint hygiene | pyright strict on `src/`, ruff, 16 tests < 1s |
| V8 | Decision discipline | ADRs 0005/0008/0010/0012/0014/0016 are correct calls with reversal conditions |

**Not validated by anything**: an agent loop, a model-initiated tool execution, a `GateReport`,
a replay verification, a policy denial in flight, retrieval quality, resume, any cost/latency
number.

---

## **3. Deep Defect Audit (code-verified)**

Each finding: evidence → impact chain → required fix → the test that must exist.

### D1 — The ReAct loop can never dispatch a tool *(critical)*

**Evidence**: `src/sagiha/kernel/react.py:63-66` scans `model_response.content` for
`isinstance(block, ToolCall)`. But `Message.content` is `list[ContentBlock]`
(`domain/content.py:72-81`) — a discriminated union on `kind` containing `ToolUseBlock`, **not**
`ToolCall`. Confirmed at runtime: a `{"kind": "tool_use", ...}` block validates as `ToolUseBlock`
(`isinstance ToolCall: False`); a raw `ToolCall` payload is **rejected** by Pydantic (no `kind`
discriminator). The branch is unreachable for any validated message — from a cassette or a live
provider alike.

**Impact**: the harness has never executed a model-initiated tool call. Everything downstream —
dispatch auditing, policy denials, trajectory tool records — has only ever been exercised by
hand-constructed unit-test inputs. `tests/unit/test_kernel_sprint2.py::test_react_engine_execution`
passes because it asserts only `step_id` fields.

**Fix**: the loop collects `ToolUseBlock`s and resolves each to a `ToolCall` at the registry
boundary, taking `effect` from `ToolRegistry.get_effect_class(tool_name)` (see D11).
**Proving test**: a cassette response containing a `tool_use` block must produce a dispatched tool
and a recorded `ToolResult` in the step.

### D2 — Cassette replay ignores the request *(critical for the replay claim)*

**Evidence**: `adapters/model/cassette.py:54-65`. Replay serves entries by insertion index; when
exhausted it **silently repeats the last entry**. No request digest, no mismatch detection, no
failure mode.

**Impact**: "byte-for-byte deterministic replay" (AGENTS.md invariant 3) is untestable as built. A
drifted prompt replays the wrong response with no error — replay-based CI would go green on garbage.
Worse, the infinite-last-entry behavior masks loop bugs (an agent stuck in a loop replays forever).

**Fix**: key entries on a canonical `ModelRequest` digest; raise `CassetteMismatchError` on miss or
exhaustion. Record the digest into `ModelCallStarted.request_digest` (the event field already
exists and is currently never emitted). **Proving test**: replay with a mutated prompt must fail
loudly; exhaustion must fail loudly.

### D3 — `build_kernel` ignores `model.mode` *(critical for trust in config)*

**Evidence**: `src/sagiha/composition.py:65-74` — both branches of the `if config.model.mode ==
"replay"` construct the **same** replay-mode `CassetteModelProvider` at a hardcoded path.
`config.model.tiers` and `config.model.roles` are never read by composition (see G10).

**Impact**: a user configuring `mode="live"` gets a silent stub. The config contract
(`live`/`record`/`replay`) is a fiction at the exact place the docs call the single point of
adapter truth (`composition-and-configuration.md`).

**Fix**: `live` binds a real provider adapter per role→tier; `record` wraps it in the cassette
recorder; `replay` requires an explicit cassette path; anything unbindable **fails at composition**.
**Proving test**: composition with `mode="live"` and no provider extra installed must raise, not
degrade.

### D4 — `EffectClass` is never consulted

**Evidence**: `rg get_effect_class src/` → one definition (`adapters/tools/registry.py:38`), zero
callers. Neither `kernel/dispatch.py` nor the cassette path reads effect class.

**Impact**: ADR-0012's central replay-safety mechanism — never re-execute `DESTRUCTIVE`, always
serve from recorded observation — is decorative. The docstring on `EffectClass` itself warns
"without it, replaying a recorded trajectory re-executes `git push`," and that is exactly the
current state.

**Fix**: dispatch resolves effect from the registry (D11) and the replay path branches on it.
**Proving test**: replaying a recorded run containing a `DESTRUCTIVE` call must not invoke the
handler.

### D5 — Failure signaling is incoherent

**Evidence** (three compounding pieces):
1. `kernel/dispatch.py:103-119`: `ToolCallCompleted` is emitted iff `not result.truncated`; a
   truncated result emits `ToolCallFailed(error_kind="execution_error", disposition="SURFACE")`.
   Truncation is a *success with overflow* (`ToolResult.full_output_uri` exists for exactly this),
   not a failure.
2. `adapters/tools/registry.py:49-55` and `kernel/dispatch.py:88-95`: handler exceptions are
   converted to ordinary `ToolResult`s whose only failure signal is prose (`"Tool handler error:
   ..."`). `ToolResult` has no `is_error` field — only the never-produced `ToolResultBlock` does.
3. The `Disposition` taxonomy (`RETRY`/`DEGRADE`/`SURFACE`/`ABORT`, `domain/events.py:29`) is never
   populated from a real error classification anywhere.

**Impact**: the agent cannot distinguish a failed tool from a successful tool returning error-shaped
text — a direct miss on the product requirement to separate *failed tool / failed hypothesis /
missing context / failed gate*. The audit stream misclassifies large successful reads as failures.

**Fix**: add `is_error: bool = False` to `ToolResult`; dispatch emits `ToolCallFailed` on
`is_error`, `ToolCallCompleted` otherwise, truncation notwithstanding; map the error taxonomy doc
(`error-taxonomy.md`) to `Disposition` at the choke point.
**Proving tests**: truncated-success emits `Completed`; raising handler yields `is_error=True` and
`Failed`; unknown tool yields `is_error=True`.

### D6 — Stored events deserialize lossy: the audit trail is write-only

**Evidence**: `adapters/trajectory/sqlite.py:121-135` — `events_for_run` calls
`Event.model_validate_json(...)` against the **base class**. Pydantic drops unknown fields by
default, so every subclass payload (`ToolCall`, `Decision`, `GateReport`, usage, cost…) is
silently discarded on read.

**Impact**: replay verification, audit, trajectory mining, and the future MetaImprover substrate
all read through this path. Every run recorded before the fix is *readable only as bare envelopes*.
This is the steepest "cheap now, expensive later" item together with D10.

**Fix**: deserialize through a discriminator lookup built from `ALL_EVENTS` (`domain/events.py:405`
already enumerates every type and each carries a `Literal` `event` field). Add an upcaster hook
keyed on `(event, schema_version)` while the store is still empty.
**Proving test**: round-trip every event type in `ALL_EVENTS` through the store and assert payload
equality.

### D7 — `min_provenance` accepted, silently ignored

**Evidence**: `domain/memory.py:45` defines `RecallQuery.min_provenance`;
`adapters/memory/short_term.py:54-66` filters `kinds` and `valid_to` only. `as_of` is honored for
invalidation but provenance is never checked.

**Impact**: the provenance trust model — the doc-level answer to memory poisoning
(`neural-symbolic-memory.md`, "trust travels the links") — is unenforced at the only implemented
recall path. A caller asking for `HARNESS`-or-better receives `EXTERNAL` records with no warning.
Combined with G7 (no `<untrusted-data>` wrapping at render), there is currently **no** enforcement
point for provenance anywhere in the system.

**Fix**: honor the filter; define the provenance ordering explicitly (`OPERATOR > HARNESS > MODEL >
EXTERNAL`) in `domain/memory.py` rather than implying it. **Proving test**: recall with
`min_provenance=HARNESS` must exclude `EXTERNAL` records.

### D8 — Authorization is ceremony

**Evidence** (five compounding pieces):
1. `kernel/policy/engine.py:34-41`: everything not name-listed in `always_gate` is allowed.
2. `engine.py:44-48`: `scope_paths` are **guessed** from argument key names (`"path"`,
   `"file_path"`, `"target_file"`, `"dir"`); a tool passing `filename=` or `paths=[...]` escapes
   scoping entirely.
3. The minted `Grant` is stored (`engine.py:61`) and popped at `record_outcome` — but **never
   checked**: `get_grant` (the expiry check, `engine.py:24-32`) has no caller on the dispatch path;
   no code compares executed paths against `scope_paths`.
4. `kernel/governor.py:21-25`: `acquire()` unconditionally grants a lease;
   `max_concurrent_sandboxes` is stored and never read. Admission control does not admit or deny —
   it counts.
5. `rg record_spend src/` → defined twice (port + impl), called zero times. `RunContext.
   budget_remaining_usd` is a static snapshot nothing updates.

**Impact**: "secure by construction" currently means "structured to become secure." Acceptable
mid-Sprint 2 — dangerous to leave untested as tools become real, because the *structure* (choke
point, grants, leases) will look finished while enforcing nothing.

**Fix path** (Sprint 3 tests the flows; Block 3 hardens): deny-path/approval/expiry behavioral
tests now; schema-declared path parameters (not key-name guessing), lease admission, and spend
integration in Block 3. **Proving tests**: named in Sprint 3 §C and Block 3 acceptance.

### D9 — Run state is unresumable

**Evidence**: `kernel/react.py:43,47-48` — step sequence lives in `ReActEngine._step_sequence`
(process memory), never derived from the `TrajectoryStore`. There is no `runs` table; `TaskStatus`
exists in the domain (`control.py:16`) but nothing persists it.

**Impact**: interrupt/resume — an explicit product requirement ("recover", A2A `TaskStatus`
mirroring) — is impossible. A resumed run recomputes `seq=1` and collides with
`PRIMARY KEY (run_id, branch_id, seq)` (`sqlite.py:28-35`), i.e., resume doesn't just lose
context, it crashes.

**Fix**: persist run records (run_id, task revision, status, updated_at); derive next `seq` from
`MAX(seq)` per branch. **Proving test**: kill after step N, resume, assert steps N+1… append with
no collision and no duplicate.

### D10 — `ModelRequest` cannot describe a real request *(steepest contract risk)*

**Evidence**: `domain/content.py:91-92` — `ModelRequest` carries only `messages`. No system prompt,
no tool schemas, no `max_tokens`/`temperature`, no model/role reference. Meanwhile
`config.py` specifies tiers with `thinking` budgets that nothing can request, and
`ports/model.py`'s own docstring demands a conformance test (`test_reasoning_block_round_trip…`)
that cannot be written against this shape.

**Impact**: no real provider adapter can be built. And because cassettes serialize
`CassetteEntry(request=ModelRequest, ...)` (`cassette.py:17-19`), **every cassette recorded before
this changes is invalidated by the change**. The same applies to any `ModelCallStarted.
request_digest` computed over the old shape.

**Fix**: `ModelRequest` v2 (system, tools, sampling params, role) **before any cassette fixture is
committed**. **Proving test**: the OpenAI-compatible adapter (Sprint 3 B3) round-trips a request
with tools and a system prompt.

### D11 — Effect-classification authority is inverted

**Evidence**: `domain/content.py:95-103` — `ToolCall.effect: EffectClass` is asserted by whoever
constructs the call, which after D1's fix is the parser of *model output*. The registry's
classification (`register(..., effect=...)`) is the trustworthy source and is never consulted (D4).

**Impact**: a model could label `git push` as `PURE`, and replay (once implemented) would happily
re-execute it. This is a security-relevant field with the wrong writer.

**Fix**: `effect` is resolved at dispatch from the registry; remove it from model-facing
construction or treat any incoming value as advisory-only and overwrite.
**Proving test**: a `ToolCall` claiming `PURE` for a tool registered `DESTRUCTIVE` dispatches (and
replays) as `DESTRUCTIVE`.

### D12 — Short-term memory exists twice and is wired zero times

**Evidence**: `adapters/memory/short_term.py:20-40` implements `ShortTermMemoryAdapter`; nothing
imports it. `composition.py` binds only `InMemoryMemory` to the durable `Memory` port; the
`Kernel` dataclass has **no field** for `ShortTermMemory` at all.

**Impact**: dead code presented as a delivered Sprint 2 item ("ShortTermMemory & Memory Adapters —
done"), and the loop that would use it (history packing) doesn't exist (D18). Either wire it in
Sprint 3's prompt assembly or delete it until needed.

### D13 — Tool input schemas are registered and never validated

**Evidence**: `adapters/tools/registry.py` stores `self._schemas` at registration; `dispatch()`
(`registry.py:41-55`) never reads them — arguments pass to handlers unvalidated.

**Impact**: the review-scope requirement "tool inputs are validated, bounded, audited" fails at the
first step. Malformed model-generated arguments reach handlers raw; with subprocess tools coming in
Sprint 3, unvalidated `run_command` arguments are the exact input a policy engine needs shaped.

**Fix**: validate `call.arguments` against the registered JSON Schema at dispatch; a validation
failure is an `is_error=True` result (D5), never an exception escaping the choke point.
**Proving test**: an argument violating the registered schema is rejected without handler
invocation.

### D14 — A partially wired kernel is representable and silent

**Evidence**: `composition.py:32-48` — every `Kernel` field except `config`/`bus` defaults to
`None`, including ports that no profile makes optional (`model_provider`, `policy_engine`,
`resource_governor`, `tool_registry`, `trajectory_store`).

**Impact**: pyright cannot catch a composition bug; consumers either sprinkle `assert ... is not
None` or crash at depth. Profile-optional ports (`evaluator`, `workspace`, `indexer`, `lsp_adapter`,
`code_graph`, `worktree_manager`) are legitimately `| None`; the mandatory five are not.

**Fix**: make mandatory ports non-optional constructor arguments; `build_kernel` fails at
composition if it cannot bind them (consistent with the "fail at composition, not at first call"
rule in `composition-and-configuration.md`).

### D15 — Cassette `stream()` fabricates a non-conformant stream

**Evidence**: `adapters/model/cassette.py:78-85` — yields a single `BlockDelta(index=0,
text=str(msg.content))` (a Python `repr` of a list of blocks!) then `StreamEnd(stop_reason=
"end_turn")` unconditionally. No `BlockStart`/`BlockEnd`, no `UsageReported` — the exact invariant
`ports/model.py` names (`test_stream_emits_exactly_one_usage_before_end`) is violated by the only
existing implementation, and the named conformance test exists nowhere.

**Impact**: any consumer written against the documented stream contract breaks on the first
adapter. **Disposition**: streaming is not needed for Block 1 — either fix it to synthesize a
conformant frame sequence from the recorded message, or make it raise `NotImplementedError`
honestly. Do not leave a lying implementation.

### D16 — Dispatch emits two different `ToolCallRequested` events

**Evidence**: `kernel/dispatch.py:40-45` — `emit(ToolCallRequested(...))`, then constructs a
**second** `ToolCallRequested` instance for `intercept("pre_tool", ...)`. Distinct objects,
distinct `timestamp`s (default factory).

**Impact**: the audited event and the event interceptors judged are not the same object; a
timestamp-keyed correlation or digest over events diverges. Trivial now; confusing in every audit
later. **Fix**: construct once, use for both.

### D17 — EventBus behavior drifts from its own normative doc

**Evidence** vs `docs/02-architecture/event-bus-and-hooks.md`:
1. Doc: observers run "concurrently, **with a hard timeout**"; an observer that raises "is
   **disabled for the remainder of the run**." Code (`kernel/bus.py:59-78`): no timeout on
   observers; failures are logged and the observer stays subscribed.
2. Doc: eight hook points (`pre_model`, `post_model`, `pre_tool`, `post_tool`, `pre_edit`,
   `post_edit`, `pre_gate`, `post_run`). Code: only `pre_tool` is ever invoked
   (`kernel/dispatch.py:43`).
3. Convention: AGENTS.md mandates `anyio` structured concurrency; `kernel/bus.py` uses
   `asyncio.gather`/`asyncio.wait_for` directly — breaks under a trio backend and contradicts the
   stated stack.

**Impact**: the doc is the spec; the implementation quietly under-delivers on exactly the property
the doc calls load-bearing ("a slow or broken observer must never be able to break an agent run" —
today a *hanging* observer blocks `emit` forever). **Fix**: observer timeout + quarantine, anyio
primitives, and either implement the remaining hook points as the loop grows (Sprint 3 adds
`pre_model`/`post_tool` naturally) or mark them "reserved" in the doc.

### D18 — Each step is memoryless: no history enters the prompt

**Evidence**: `kernel/react.py:57-59` — every step builds
`ModelRequest(messages=[Message(role="user", content=[TextBlock(text=prompt)])])` from the raw
`prompt` argument alone. No system prompt, no prior steps, no tool results fed back.

**Impact**: even with D1 fixed, a multi-step run cannot work — the model never sees what its tools
returned. This is the concrete, code-level face of G1/G7 and the reason "close the loop" is a
sprint, not a patch.

---

## **4. Critical Gaps**

| ID | Gap | Detail |
| :--- | :--- | :--- |
| G1 | No run loop | `step()` only; no `run()` with stop conditions (end_turn / max_steps / budget / cancellation), no verify stage, no `Orchestrator` implementation, no escalation ladder. The understand→plan→act→verify→reflect loop exists only in DMARTIC prose. |
| G2 | Zero built-in tools | `DefaultToolRegistry()` constructed empty in composition; the `analysis`/`review`/`chat` profile tool lists in `config.py` name tools (`read_file`, `grep`, `recall`, …) that exist nowhere. |
| G3 | No Evaluator | No `GateReport` has ever been produced; `outer_loop/evaluator/` is an empty package; "hard gates admit" is aspirational. |
| G4 | No CLI run path | `sagiha version` is the entire user surface (`cli.py`); getting-started's Day-Zero story is aspirational until Sprint 3 exits. |
| G5 | CI does not run the tests | `.github/workflows/ci.yml`: conformance job runs `pytest tests/contracts/` **only** — `tests/unit/` never runs in CI; `fail_under = 80` coverage is configured and never executed; the replay job is an always-skip stub; `detect-secrets` exists only in pre-commit. The cheapest high-value fix in the repo. |
| G6 | No measurement substrate (E0) | No harvested tasks, no A/A noise floor, no baseline numbers — despite the roadmap ordering E0 first and the prior review naming it the moat. Every future claim ("routing helps", "retrieval helps") is unfalsifiable until this exists. |
| G7 | No prompt assembly | No system prompt, no tool-schema rendering, no history packing, no `<untrusted-data>` wrapping of `EXTERNAL` provenance (the injection defense), no compaction, no cache breakpoints. `src/sagiha/prompts/` does not exist. |
| G8 | No live model adapter | Anthropic/OpenAI/Google SDKs declared as extras, imported nowhere; no Ollama adapter despite `ollama-qwen-coder-setup.md` and the local-benchmarking commit history. |
| G9 | The loop is not traceable | `ReActEngine` emits zero events — no `StepStarted`/`StepCompleted`/`ModelCallStarted`/`ModelCallCompleted`. Only dispatch emits. Even the implemented slice cannot be traced end-to-end. |
| G10 | Composition consumes a fraction of the config contract | Consumed today: `telemetry.trajectory_db`, `autonomy.always_gate`, `governor.max_spend_usd_per_run`, `governor.max_concurrent_sandboxes`, `model.mode` (and that one incorrectly, D3). **Ignored entirely**: `model.tiers`, `model.roles`, `profiles`, `workspace`, `sandbox`, `retrieval`, `context`, `search`, `gates`, `aoi`, `mcp_servers`, `hooks`, the rest of `governor`, the rest of `telemetry`. `config.example.toml` therefore documents a product surface ~90% of which is inert. Fine mid-build — but the gap must shrink with every sprint, and composition must fail on config it cannot honor rather than silently ignoring it. |

---

## **5. Documentation Audit (X findings)**

Doc-level defects found by this audit, with disposition. The repo rule is explicit: *contracts live
in `src/`; a `Protocol` or `BaseModel` defined in a `.md` file is a bug* (AGENTS.md,
`contracts-to-code.md`).

| ID | Finding | Disposition |
| :--- | :--- | :--- |
| X1 | `development-plan-and-prompts.md` Phase 4 said "hybrid BM25 + **dense** retrieval," contradicting [ADR-0014](../../08-decisions/0014-defer-dense-retrieval.md) (dense deferred behind a measured trigger). Two locations (matrix row + Sprint 4 prompt). | **Fixed 2026-07-29** — both now defer the dense tier per ADR-0014. |
| X2 | `rhi-outer-loop.md` §Cycle said span log and trajectory store are "one source of truth, one derived from the other" — regressing the settled model (EventBus is the source; both are independent subscribers; 2026-07-28/D7). | **Fixed 2026-07-29** — sentence now states the EventBus model and links `microkernel-and-bus.md`. |
| X3 | Seven docs still **defined** contracts in markdown: `task-and-acceptance.md` (`AcceptanceCriterion`, `TaskSpec`), `neural-symbolic-memory.md` (`Memory` — worse: with `neighbors`/`backlinks` methods **absent from the real port**, i.e. two incompatible contracts), `car-model.md` (`PolicyEngine`, `Workspace`), `event-bus-and-hooks.md` (`Observer`, `Interceptor`), `lsp-interface.md` (`LSPAdapter`), `aoi-coprocessors.md` (`Prediction`, with defaults the real model doesn't have), `indexing-and-retrieval.md` (`RetrievalHit`). | **Fixed 2026-07-29** — all replaced with references to `src/`; the `neighbors`/`backlinks` divergence is now an explicit, flagged port-change proposal for S2 instead of a silent contradiction. |
| X4 | `car-model.md` dispatch pseudocode still showed `registry.dispatch(call, decision.grant)` — the grant-crossing pattern superseded after 2026-07-28/D1 and contradicted by both `ports/tool_registry.py` and the shipped `kernel/dispatch.py`. | **Fixed 2026-07-29** — now describes the actual choke-point sequence; grant never crosses the registry. |
| X5 | `security-and-threat-model.md` T2 said the container perimeter is "required from the first slice," contradicting ADR-0006, the migration matrix (container lands in S1), getting-started, and the config validator that explicitly permits dev-mode subprocess at `interactive` autonomy. | **Fixed 2026-07-29** — states S1 timing and the config-enforced pre-S1 constraint. |
| X6 | Sprint sequencing contradicted the project's own E0-first strategy, and Sprint 2's remaining scope (MCP, OTel) extended periphery over core. | **Addressed 2026-07-29** — Sprint 2 closed with a scope-change note; [Sprint 3](../sprints/sprint-3.md) closes the loop; measurement (E0-lite) is Block 2, immediately after — a deliberate deviation from strict E0-first, recorded in §9: a measured loop needs a loop to measure. |
| X7 | The 2026-07-28 review's remediation table is stale in places (e.g., G6 still shows ADR-0015 pending sign-off; ADR-0015 is Accepted with the target repo named). | **Not edited** — reviews are historical per [reviews/README](./README.md); recorded here instead. |
| X8 | `reference/design-derivation.md` retains superseded narratives (TurboQuant/tqdb et al.) under warning banners. Safe for humans; hazardous for retrieval — a chunker that strips the banner serves reversed decisions as current. | **Fixed 2026-07-30** — strengthened `status: rationale` banners; agent retrieval must exclude `docs/reference/` and `docs/reviews/`. |
| X9 | `README.md` / getting-started describe a runnable Day-Zero story (`sagiha run`, replay) that does not exist; the real surface is `sagiha version`. | **Fixed 2026-07-30** — [STATUS.md](../../STATUS.md); Planned banners on CLI examples; getting-started / v0.1 retargeted to Sprint 3. |
| X10 | `config.example.toml` documents a surface composition ignores (G10 details). | **Fixed 2026-07-30** — consumption table in [configuration-reference.md](../../05-tech-stack/configuration-reference.md); Sprint 3 must shrink it. |

| X11 | The generated event catalog was **stale at HEAD `0f61d5a`**: `gen_event_catalog.py --check` failed on the committed tree because the generated file had been hand-edited (profile-conditional table rows reworded, disclaimer rewrapped). The CI drift gate was therefore already red on main — hand edits to a generated file are exactly the failure mode the generator exists to prevent. | **Fixed 2026-07-29** — regenerated from `domain/events.py`; `--check` green. Rule reminder: prose changes to the catalog belong in the generator's hand-authored sections, never in the output file. |

The generate-from-code + check-in-CI pattern is the model X3 items should follow wherever a doc
wants to display a contract — but X11 shows it only works if the generated file is treated as
read-only.

---

## **6. Unproven Assumptions**

| ID | Assumption | Risk if false | Smallest proving experiment |
| :--- | :--- | :--- | :--- |
| U1 | The dispatch choke point actually constrains agency code | Capability security is a diagram | Behavioral security tests (Sprint 3 §C): deny path, `always_gate` approval, expired/forged grant, out-of-scope write. The CAR import contract becomes non-vacuous only when `agency/` has code — add a canary module then. |
| U2 | Deterministic replay is achievable at useful fidelity | Replay-based CI and evaluation collapse | Record a 5-step run against local Ollama; replay with digest verification (needs D2, D10 first). Define **graded fidelity** (§11) instead of promising byte-for-byte. |
| U3 | The 21 port shapes survive contact with real adapters | Churn in "stable" contracts; invalidated cassettes and suites | Write two real adapters (ModelProvider, Workspace) before labeling more ports `stable`. `ModelRequest` (D10) already proves the risk; the 2026-07-28 review proved it before that. |
| U4 | SQLite event capture is cheap enough on the hot path | The trace pipeline becomes the bottleneck it warns about | Benchmark events/sec on a 200-step synthetic run before adding OTel double-writes. Measure once, stop worrying. |
| U5 | Best-of-N, AOI, RHI will pay for themselves | Expensive machinery, no measured lift | Already correctly gated behind E0 + A/A noise floor. Build none of it before Block 2 exists. |

---

## **7. Safe Deferrals**

All sit behind already-typed ports or additive event consumers and can wait without harming the
core: RHI/MetaImprover, AOI coprocessors, dense retrieval (ADR-0014), System-2 best-of-N N>1,
A2A/remote pilots, performance sidecars, Graphiti-class episodic memory, container sandbox
(dev-mode subprocess is acceptable at `interactive` autonomy — the config invariant refuses the
dangerous combination), warm LSP pool, streaming (D15 disposition), **and the two items Sprint 2
listed as next steps: the stdio MCP driver and the OTel exporter**. MCP multiplies tool surface
before one tool works end-to-end; OTel duplicates an event stream already persisted to SQLite.

---

## **8. Rewrite Risks — cheap now, expensive later**

Ordered by cost-curve steepness:

1. **`ModelRequest` shape (D10)** — every cassette embeds it. Fix before any fixture is committed.
2. **Typed event reads + upcasters (D6)** — every stored trajectory embeds event JSON. Fix while the store is empty.
3. **Resume identity (D9)** — retrofitting a `runs` table later means migrating trajectory semantics.
4. **Effect-class ownership (D11) + schema-declared path scoping (D8, D13)** — one line per tool now, a security audit later.
5. **CI gap (G5)** — silent regressions compound into archaeology.
6. **Dual storage of steps** (steps table + `StepCompleted` events) — acceptable, but declare the steps table the single authoritative read path now, or "one source of truth" erodes.
7. **Kernel optionality (D14)** — every consumer written against `Kernel | None` fields bakes in `assert`s that a later tightening must unwind.

---

## **9. Minimal Target Architecture (first autonomous, measurable loop)**

Keep exactly what exists, fix D1–D18, add the smallest closing set:

```
Config → build_kernel ──► Kernel { bus, policy, governor, registry, trajectory, model }   (mandatory, non-optional)
                              │
             sagiha run ──► RunLoop (new): while not stopped and within budget:
                              assemble prompt: system + tool schemas + step history   ← G7 minimal, D18
                              ModelProvider.complete                                   ← Ollama adapter + fixed cassette
                              ToolUseBlock → ToolCall (registry-resolved effect)       ← D1, D11
                              dispatch() choke point (validated inputs)                ← D13
                              append step; emit step/model events                      ← G9
                              stop: end_turn | max_steps | budget | cancellation
                              verify: Evaluator.evaluate → GateReport                  ← subprocess acceptance checks
             sagiha replay ─► same loop, digest-verified cassette                      ← D2
```

Components: the existing kernel; **one** run loop; **five** built-in tools (`read_file`,
`list_dir`, `grep`, `apply_edit`, `run_command`) over a dev-mode subprocess `Workspace`; **two**
model adapters (cassette fixed + OpenAI-compatible/Ollama); a minimal `Evaluator` shelling out
acceptance checks; two CLI verbs. Everything else in `ports/` stays as typed contracts with
stability markers and **no conformance suites until an adapter exists**.

**Sequencing decision (records X6)**: strict E0-first would build the grader before the gradee.
The chosen order — Block 1 closes the loop, Block 2 measures it immediately — keeps the prior
review's intent (nothing ships unmeasured past Block 2) without a sprint spent grading agents that
cannot run.

---

## **10. Incremental Roadmap**

**Block 1 — Close the loop** ([Sprint 3](../sprints/sprint-3.md))
- *Capability*: `sagiha run` fixes a failing test in a fixture repo end-to-end on a cassette in CI, and against local Ollama manually; `sagiha replay --verify` passes on the recording.
- *Contracts*: `ModelRequest` v2; registry-resolved `EffectClass`; typed event read path; `runs` table + resume; `is_error` on `ToolResult`.
- *Acceptance*: e2e cassette test green in CI; replay digest-verify green; full `pytest` + coverage in CI; security deny-path tests green.
- *Non-goals*: MCP, OTel, sandbox, retrieval, streaming, best-of-N, routing.
- *Depends on*: nothing.

**Block 2 — Measure (E0-lite)**
- *Capability*: `sagiha bench` runs 10–30 tasks harvested from the ADR-0015 repo; report: task success, gate pass rate, cost/success, latency, steps; A/A noise floor on ≥3 tasks.
- *Contracts*: benchmark task format (TaskSpec + fixture commit + checks); report schema.
- *Acceptance*: committed baseline JSON; cassette re-run reproduces within noise floor.
- *Depends on*: Block 1.

**Block 3 — Enforce authority**
- *Capability*: schema-declared path scoping enforced at dispatch; blocking `ApprovalRequested` flow; governor admission (deny at `max_concurrent`); spend recorded from real `TokenUsage` and enforced.
- *Acceptance*: PolicyEngine conformance suite (deny, expiry, scope violation, forged grant); out-of-workspace write refused in e2e.
- *Depends on*: Block 1.

**Block 4 — Retrieve and remember**
- *Capability*: FTS5 lexical index + code-graph expansion (no dense tier, ADR-0014); SQLite-backed `Memory` with provenance enforced end-to-end (D7 + `<untrusted-data>` render wrapping); `neighbors`/`backlinks` port decision (X3); recall@10 on a labelled query set; retrieval on/off ablation via Block 2.
- *Depends on*: Blocks 1–2 (retrieval lift must be measurable or it doesn't ship).

**Block 5 — Isolate and integrate**
- *Capability*: worktree manager, container sandbox + egress allowlist (rootless Podman, ADR-0016), then MCP driver and OTel exporter.
- *Depends on*: Block 3 (the sandbox is the perimeter; policy must already be real).

---

## **11. Measurement Plan**

All metrics derive from the persisted event log — the architecture's genuine advantage; no separate
metrics pipeline is needed. (Prerequisites: D6 typed reads, G9 loop events.)

| Metric | Source | Definition |
| :--- | :--- | :--- |
| Task success | `RunCompleted.gate_report` | `admitted == True`; plus per-criterion gate pass rate. |
| Cost per successful task / per step | `ModelCallCompleted.cost`, `TokenUsage` | Sum per run ÷ successes; per-step distribution. |
| Latency | `RunStarted`→`RunCompleted`; `StepStarted`→`StepCompleted` | Wall-clock p50/p95. |
| Retrieval quality & contribution | Labelled query set (Block 4); Block-2 ablation | recall@10, MRR; contribution = success delta with retrieval off. |
| Cache effectiveness | `TokenUsage.cache_read_tokens / input_tokens` | Alert < 0.80 once prompt caching exists. |
| Replay fidelity (graded) | `sagiha replay --verify` | **L0** event count+types match; **L1** step sequence and tool calls match by digest; **L2** byte-identical payloads for `replay_relevant` events. Report the level achieved; do not promise L2 globally. |
| Tool-policy denials & safety | `ToolCallDenied`, `ApprovalRequested/Resolved` | Denials by reason; approval latency; zero out-of-scope writes in e2e suites. |
| Recovery | Scripted kill at step N + `sagiha run --resume` | Resume success rate; duplicate-step count must be zero (D9). |

---

## **12. Direct Recommendations**

**Keep**: domain models; port meta-conformance suite; import-linter contracts; config refusals;
dispatch choke-point structure; event catalog generation; the ADR discipline.

**Fix now** (Sprint 3, in this order): D1, D10, D2, D3, D6, D5, D9, D11, D13, D16, D18; CI running
the full suite with coverage (G5); D7; D12 (wire or delete); D14.

**Simplify**: sprint definitions of done — a demonstrated capability, not adapter count. Declare
the steps table the authoritative trajectory read path.

**Redesign**: failure signaling (D5); replay matching (D2); EventBus observer isolation to match
its own spec (D17).

**Postpone**: MCP, OTel, sandbox, LSP, dense retrieval, best-of-N N>1, AOI, RHI, streaming — all
behind measured triggers or later blocks.

**Delete / already deleted**: the seven markdown contract definitions (X3, done); the superseded
dispatch pseudocode (X4, done). Delete `ShortTermMemoryAdapter` if Sprint 3 does not wire it (D12).

---

*Judged by demonstrated autonomous capability, safety, maintainability, and measured improvement:
the foundation earns its contracts but has not yet earned its second layer of ambition. Close the
loop, measure it, then grow.*
