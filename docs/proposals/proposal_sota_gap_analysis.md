---
status: rationale
updated: 2026-08-07
---

# Evaluation: SOTA Gap Analysis — What the Four Reference Harnesses Do Not Show You

**Verdict up front.** The four investigations are largely *confirmatory*: almost every pattern
they recommend is already funded (`TASK-024` compaction, `TASK-056` cache pinning, the event bus,
the architect role as read-only plan mode). That is a useful result — it means the plan is not
missing the obvious.

But the report's framing — *combine these four and we outperform commercial competitors* — has a
blind spot, and it is the same blind spot in all four references because all four are **general
coding assistants**, not benchmark harnesses. **The single largest unfunded lever on SWE-bench
score is not in the report at all: the harness has no localization step.** Section 2.

---

## 0. Sourcing corrections — two investigations did not read the tree they cite

This matters here more than it would elsewhere, because this project draws a hard line between
*measured on our instrument* and *third-party claim* ([`spec.md` §9](../spec.md#9-standing-rules)).
The same discipline applies to architecture claims.

**S1 — `src/openhands` is the UI package, not the agent framework.** It is
`@openhands/agent-canvas` v1.10.0: **1,702 TypeScript files and 4 Python files**, with
`package.json`, `electron/`, `eslint.config.js`. `grep -rl "CmdRunAction" src/openhands` returns
**nothing**, and `grep -rln "EventStream" --include=*.py` returns nothing. Investigation 2's
"Detailed Code & Architectural Findings (src/openhands)" — `CmdRunAction`, `IPythonRunAction`,
`CmdOutputObservation`, the EventStream — describes the upstream OpenHands **Python** repo, which
is not in this tree. The findings may well be accurate about upstream; they were not read from
`src/openhands`.

**S2 — `src/claude_refs` contains zero source files.** `find src/claude_refs -name "*.ts"` returns
**0**. It holds `claude-code-analysis/DOCUMENTATION.md` and `claude-code-ultimate-guide/` —
third-party analysis prose about a closed-source product. So `QueryEngine.ts`,
`services/compact/microCompact.ts` and `sessionMemoryCompact.ts` are **file paths quoted from a
secondary source**, not observed. They may be real; we have not seen them.

**S3 — the two verified reads are Kimi CLI and Hermes.** `src/hermes_agent/trajectory_compressor.py`
is real and is **1,598 lines**. The Kimi findings were verified line-by-line in the previous
evaluation.

**Why this is worth writing down.** The conclusion — *"AETHER outperforms commercial competitors
in security, determinism, and cost per resolved task"* — is exactly the claim
[`measurement.md` §6](../measurement.md#6-what-a-claim-needs-before-it-is-published) forbids
without `TASK-015`'s comparative rig. Architecture read from source is a fact; architecture read
from a competitor's marketing-adjacent analysis doc is a hypothesis; *outperformance* is neither
until it runs through our evaluator. The comparison tables are a good design artifact and a bad
claim artifact, and they should be labelled as the first.

---

## 1. What the report gets right, briefly

| Report recommendation | Status here |
| :--- | :--- |
| Typed action/observation event stream | **Built.** `domain/events.py`, 8 typed events, catalog drift-checked, per-consumer drop policy |
| Sandbox isolation for all execution | **Built for the judge**, open for tools — `TASK-018`'s second half |
| Ground-truth eval outside model control | **Built and stronger.** Ours is structural: `check_evaluator_termination` proves *no topology can route around the judge*. OpenHands relies on the agent emitting `AgentFinishAction`; a model that never emits it is a hang, not a verdict |
| Micro-compaction of intermediate outputs | **`TASK-024`**, correctly scoped to L5 only |
| Cache breakpoint pinning | **`TASK-056`** |
| Plan mode / read-only planning | **Already structural.** The report is right that a topology enforces this better than a tool does — but see §5.2, because it is *not currently enforced*, only conventional |
| Pluggable execution backends | **Built.** `SandboxRunner` is a structural protocol over `domain/sandbox.py` |
| Trajectory compression | `TASK-024` — though Hermes's compressor targets *fine-tuning dataset generation*, a different goal from context economy. Do not port its XML shape |

**The one genuinely new idea in the report** is Hermes's explicit completion sentinel
(`echo "MINI_SWE_AGENT_FINAL_OUTPUT"`) replacing text heuristics. We do not need it — our
terminal condition is the gate, not the model — and adopting it would be a regression, because
letting the model declare completion is precisely the authority I7 withholds. Worth recording as
*considered and rejected for a reason*, not as an oversight.

---

## 2. The gap: there is no localization step, and this blocks SWE-bench entirely

### 2.1 The finding

`RetrieveStep` reads the files a **node's YAML params name** (`retrieve.py:57-65`,
`params.entry_files`). `Task` (`domain/task.py`) carries `task_id`, `repo`, `base_commit`,
`instructions`, `environment_image_digest`, `test_command_hash` — **and no file list**. The only
discovery mechanism in the tree is `scripts/run_local_check.py:56-62`:

```python
def auto_discover_entry_files(task_dir: Path) -> list[str]:
    files = []
    for p in task_dir.glob("**/*.py"):        # every .py under the task
        if p.name == "run_tests.py":
            continue
        files.append(str(p.relative_to(task_dir)))
    return sorted(files)
```

That works because the internal manifest's tasks are one synthetic directory with one `mod.py`.
**On a real SWE-bench instance it returns the entire repository** — django, sympy and astropy are
thousands of files — and `RetrieveStep`'s `max_bytes` ceiling truncates at the first N bytes in
`sorted()` order, i.e. alphabetically. The model would be shown whatever files sort first, and
`missing` would fill with *"byte budget exhausted"*.

### 2.2 Why this matters more than anything else in the report

`STATUS.md` records the SWE-bench floor as *"blocked on per-task environment images"*
(`TASK-036`). That is true and it is not the only blocker. **Even with every image built, the
harness would have no mechanism for deciding which files to open.** A localization step is not an
optimization on top of a working SWE-bench pipeline — it is a missing component of the pipeline.

This is also, on the available evidence, where score is won. The hypothesis — *most unresolved
SWE-bench instances fail because the agent edited the wrong location, not because it wrote bad
code* — is widely reported and **we have not measured it**, so under `spec.md` §9 it is a
hypothesis with a named experiment, not a fact. But the experiment is cheap and we can run it on
our own instrument the moment the floor exists: **for each failed task, did the gold patch's files
appear in the retrieved set?** That single number tells you whether to invest in retrieval or in
generation, and nothing else in the plan produces it.

### 2.3 Why none of the four references shows you this

All four are interactive assistants with a human in the loop, and **the human does the
localization.** The user says "fix the bug in `parser.py`", or the agent greps and the human
redirects it. Kimi, Claude Code and Hermes all have `grep`/`glob` tools and no localization
*policy* — because they do not need one. OpenHands is closest, since it runs SWE-bench, and even
there the agent explores with bash inside its own turn budget, spending inference tokens on
navigation.

**That last point is the token argument.** Exploring a repository by having the model issue
`grep`/`ls`/`cat` calls costs a model round trip per step, and every result re-enters context.
A deterministic localization step that runs *before* the model sees anything costs zero inference
tokens and produces a smaller prompt. This is the one place where "best benchmark score" and
"fewest tokens" point the same direction rather than trading off.

### 2.4 Proposed shape — it is a `ContextSource`, not new architecture

Localization slots into `TASK-054`'s protocol with no new port and no new node kind:

```
issue text ─┬─► LexicalSource   : identifiers/tracebacks in the issue → grep the repo
            ├─► SymbolSource    : TreeSitterIndexer.search()  ← already built, reachable by nothing
            ├─► TestPathSource  : the failing test's imports → the modules under test
            └─► HistorySource   : `git log -S<identifier>` → files that changed with this symbol
                        │
                        └─► rank, take top-K under the byte budget ─► RetrievedContext.files
```

Three properties this must have, all of which fall out of existing rules:

- **Deterministic and seedable.** It is part of the instrument; a retrieval set that varies run to
  run makes `measurement.md` §6's reproducibility requirement unsatisfiable.
- **It reports what it did not retrieve.** `RetrievedContext.missing` already exists for exactly
  this reason — *"the model was not shown the file" and "the model was shown the file and failed"
  are different diagnoses, and the second is only believable when the first is excluded."*
- **Each source is ablatable separately.** Four sources is four arms, which is what the capability
  layer is for.

**Sequencing:** the lexical + symbol sources are pure `ContextSource` implementations over
components that already exist, so they land with `TASK-054` in Sprint 5. Only the *ablation*
waits for the floor.

---

## 3. The second gap: candidates are generated but never selected

`workflow_schema.yaml:105-108` already declares `rank_by` on a fan-out site, with the correct
constraint written into the schema: *"Rankers ORDER candidates and may never ADMIT one (I9) —
admission is the evaluate node, always."* **There is no ranker.** `TASK-035` builds fan-out;
nothing builds selection, so N candidates would be generated and the first-pass one taken.

Best-of-N without a selector is an N× cost multiplier for a sub-N× score gain. The selector is
where the value is, and there is a cheap, I9-compliant one available:

**Execution-based ranking on the repository's own visible tests.** Run the repo's existing test
suite — *not* the hidden benchmark tests — against each candidate, and rank by how many pass.
Zero inference tokens; it is execution, not generation.

**The I7 question this raises, and its answer.** Does running tests to rank candidates give the
generator information about its judge? No, provided one rule holds: **the visible suite and the
hidden gate are different commands, and only the gate's result admits.** The manifest already
pins `test_command_hash` for the gate. A ranker running `pytest` broadly is doing what any
developer does before submitting; it never sees the gate's command and cannot modify it
(`TASK-049`'s `tests_unmodified` enforces that independently). The gate remains the sole admitter.

**The trap to avoid**, and it is subtle: if the ranker's suite happens to *include* the gate's
tests, the ranker becomes a shadow evaluator and the harness is selecting on the answer. The
manifest must therefore record the visible/hidden partition per task, and a task where they
cannot be separated is excluded **with a published reason**, exactly as `TASK-014` handles every
other exclusion.

---

## 4. Token economy: what actually reduces tokens, ranked

The report's token discussion is all compaction. Compaction is real but it is fourth on this list.

| # | Lever | Why it dominates | Status |
| :--- | :--- | :--- | :--- |
| **1** | **Not opening the wrong files** | A 3k-token prompt on the right file beats a 30k-token prompt containing it. Every downstream turn inherits the saving | §2 — unfunded |
| **2** | **Not paying frontier rates for transcription** | A plan is ~50 output tokens of reasoning; an edit is ~2,000 of transcription | `TASK-042`, blocked on the floor |
| **3** | **A third edit format** | Unified diff is fragile for small models (they emit well-formed diffs with wrong context lines); whole-file *"burns output tokens proportional to file size"* by the module's own admission. **SEARCH/REPLACE blocks are the middle** — no context lines to reproduce, output proportional to the *change* | Not funded. `edit_format.py`'s docstring already says a third format *"is a class here and a registry entry; no node changes"* |
| **4** | **Prefix stability** | Only pays where a provider caches; the local endpoint may expose nothing | `TASK-056` |
| **5** | **Compaction** | Matters on long tasks; most SWE-bench instances never approach the window | `TASK-024` |
| **6** | **Turn budget** | `generate.py:77` hard-codes `MAX_ROUNDS = 4`, with no loop detection. A model repeating the same failing tool call burns four round trips every time | Unfunded, ~1 day |

**Item 3 is the cheapest real win in this document.** One `EditFormat` class, one registry entry,
one conformance suite run — and it is directly ablatable, because the seam was built for exactly
this comparison. It is also the format most likely to lift small local models, which is what makes
the hybrid economics work.

---

## 5. Autonomy *and* human intervention — the "both worlds" ask

### 5.1 The mode distinction has to be in the config, not in the defaults

`RunConfig` (`TASK-058`) should carry an explicit mode, because the two modes have **opposite**
correctness requirements:

| | Benchmark mode | Interactive mode |
| :--- | :--- | :--- |
| An `ASK_*` policy decision | **Fails closed.** A human in the loop is a human in the measurement | Prompts the operator |
| Wall clock | Bounded by the lease, always | May block indefinitely |
| Localization / retrieval | Deterministic and seeded | May accept operator hints |
| Cross-task memory | Off, or split-scoped (contamination) | On |

The failure mode to design against: a benchmark run that stops to ask a human has an unbounded
wall-clock **and** a human contributing to the resolve rate. Both invalidate the number. So the
mode is a declared field that enters the config hash, and `measurement.md` §6's instrument tuple
records which mode produced a result.

### 5.2 Plan mode is *conventional*, not enforced — worth fixing

The report says AETHER's architect role natively enforces read-only planning. **It does not, yet.**
`ArchitectStep` simply never calls `dispatch.write` — a property of the code, not of the
architecture. Nothing prevents a future architect implementation, or a role declaration naming a
write-capable tool, from editing the worktree before the judge ever runs.

This is worth closing properly, because the mechanism is already specified and unused:
[ADR-0017](../decisions/0017-subagent-capability-attenuation.md) — *a sub-agent is a subgraph;
capabilities only narrow*. A `RoleSpec` should declare its permitted `effect_class` set, and the
`DispatchFacade` handed to that node should be **attenuated at construction** to exactly that set.
Then `ARCHITECT` is `{read, model}` by type, and a plan node that tries to write is denied at the
choke point rather than trusted not to try. That is the real version of Claude Code's plan mode,
and it is strictly stronger than a tool that toggles a session flag.

---

## 6. Proposed additions

| Task | Title | Cx | When | Rationale |
| :--- | :--- | :---: | :--- | :--- |
| **TASK-064** | Localization `ContextSource` set — lexical, symbol, test-path, history | **4** | Sprint 5 (with `TASK-054`) | §2. Without it SWE-bench is unrunnable regardless of `TASK-036`. Deterministic, seeded, reports `missing`, each source separately ablatable |
| **TASK-065** | Retrieval-recall diagnostic | **2** | Sprint 5 | *Did the gold patch's files appear in the retrieved set?* One number that decides whether to invest in retrieval or generation. Costs nothing — it is offline analysis over the trajectory store |
| **TASK-066** | `SearchReplaceFormat` — the third edit format | **2** | Sprint 5 | §4 item 3. The seam exists precisely for this; ablatable on arrival |
| **TASK-067** | Execution-based candidate ranker (`rank_by`) | **4** | M3, with `TASK-035` | §3. **I9: ranks, never admits.** Manifest must record the visible/hidden test partition; a task where they cannot be separated is excluded with a published reason |
| **TASK-068** | Capability attenuation per `RoleSpec` | **3** | Sprint 5 | §5.2. Implements ADR-0017 at the node level. `ARCHITECT` = `{read, model}` **by type**, denied at the choke point |
| **TASK-069** | Turn budget and loop detection | **2** | Sprint 5 | `MAX_ROUNDS = 4` hard-coded, no repeated-call detection. Belongs in `Inference` (`TASK-055`) |
| **TASK-070** | `RunConfig.mode` — benchmark vs interactive | **1** | Sprint 5 (with `TASK-058`) | §5.1. Benchmark mode fails closed on `ASK_*`; the mode enters the config hash |

**TASK-064 and TASK-066 are the two that most plausibly move score**, and neither is blocked on
the floor to *build* — only to *measure*.

---

## 7. What this evaluation does not claim

- **No competitive claim.** The report's conclusion — outperformance in security, determinism and
  cost per resolved task — is not established and cannot be until `TASK-015`'s OpenHands arm runs
  through our evaluator. Two of the four architecture reads did not come from the cited trees
  (§0), which makes even the *qualitative* comparison weaker than it appears.
- **No score claim for localization.** §2.2's premise is a widely-reported hypothesis we have not
  tested. `TASK-065` exists to test it on our own instrument, and the honest position until then
  is that we do not know the failure breakdown.
- **No token-saving percentages.** §4 ranks levers by argument, not by measurement. Every row is
  an ablation arm, and one that does not clear the floor is deleted rather than kept
  ([`spec.md` §7](../spec.md#7-measurement)).
- **Nothing here reorders Sprint 4.** The floor and the instrument repairs come first. Everything
  proposed above is buildable in Sprint 5 and measurable only after.
