---
status: historical
retrieval: excluded
date: 2026-07-30
audience: SAGIHA maintainers
purpose: External Principal Engineer review — foundation audit + forward mandate
basis: pitch.md · prompt_review.md · docs/STATUS.md · docs/reviews/doing/2026-07-29-foundation-review.md · docs/sprints/sprint-3.md · src/sagiha/ (~2,804 LOC) · ADRs 0001–0018
method: Code-verified against HEAD; prior D1–D18 accepted unless challenged; new findings carry file:line. §§1–10 initial pass; §11 deep pass over docs/01–06, shipping-harness refs, link/SSOT audit.
---
# Final Review — SAGIHA Concept & Plan

## 0. Plain-Language Summary

The project has a good idea, but it is trying to run before it can walk.

The core safety and testing pieces need to be built first — containment that is actually checked, gates that cannot silently pass, replay that fails loudly, and a measured noise floor — otherwise the system cannot be trusted.

The team should focus on making **one small loop work end to end**: plan, do, check, and learn from results. Only after that should it try bigger ideas like self-improvement (RHI) or multi-agent systems.

In simple terms: **make it work safely and prove it works before making it smarter.**

Everything below is the engineering detail behind that sentence.

---

## 1. Verdict

I would **not** stake my name on this foundation *as currently sequenced and claimed*, but I **would** stake it on the four properties in §1 of the review request — containment, replay, measurement, honest grading — if you treat the next 4–6 weeks as a demolition-and-rebuild of the *runnable core*, not as documentation Sprint 0 continuing.

The architecture is coherent and unusually disciplined for a pre-product codebase. The code is not overbuilt (~2.8k LOC of contracts + stubs). The failure mode is **inverted ambition**: you have specified L3 (meta-loop) and L4 (swarm) while sitting at L0.3 with a structurally dead tool path (D1), an unverified capability system (D8), and zero lines of evaluation harness.

**The single change that flips my verdict:** ship Sprint 3's exit test *narrowed* — one cassette-driven fix of a failing test through a grant-verified dispatch choke point, with digest replay and a real `GateReport` — and refuse every peripheral doc, port, and dependency that does not serve that sentence. Until that green line exists, every other claim is speculative literature.

| Axis | Score (coarse) | Note |
| :--- | :---: | :--- |
| Specification maturity | **7.5 / 10** | Coherent thesis; over-specified periphery; dual vocabularies (Blocks vs S0–S4; DMARTIC 5 vs 8) |
| Implementation completeness | **1.5 / 10** | Contracts + import-linter + config refusals are real; the agent loop is not |

---

## 2. The Eight Dimensions

Ratings: **Spec** / **Impl**. Prior D1–D18 are assumed known; this section judges direction.

### 5.1 Architecture & Decoupling — Spec 8 / Impl 4

**GOOD.** Hexagonal ports with meta-conformance (`tests/contracts/test_port_shape.py`) are a genuine asset. `import-linter` layering, pure domain, and "fail at composition" as a stated rule are the right instincts. Keeping contracts in `src/` (not markdown) is correct and mostly enforced after the 2026-07-29 X3 pass.

**BAD.** CAR (Control / Agency / Runtime) currently costs more than it buys. `agency/` and `runtime/` are empty stubs; the CAR forbidden-import contract is **vacuous** (`.importlinter:17-20` admits this). You are maintaining two vocabularies — hexagonal rings and CAR layers — for one boundary that has never been exercised by agency code. That is not "two systems"; it is one system with a costume.

**CHANGE.** Keep the packages (amputation voids the contracts — prior rejection holds). Do not spend another sprint documenting CAR. Put the first real planner/prompt-assembly code in `agency/` in Sprint 3 so the import contract becomes non-vacuous, then flip `unmatched_ignore_imports_alerting` to `error`. Drop "CAR" from pitch/README marketing until then — say "capability-gated hexagonal kernel."

### 5.2 Capability Security & Threat Model — Spec 7 / Impl 1

**GOOD.** One choke point (`kernel/dispatch.py`), Grant never on port signatures, config refusals for subprocess+autonomous / host network / `tests_unmodified=False` — the *shape* is right.

**BAD.** The design is insufficient as written, not merely unimplemented.

1. **"Unforgeable" is a slogan.** `Grant` is a UUID string in a process-local dict (`kernel/policy/engine.py:51-61`). In Python with full introspection, forgeability is not a crypto property — reachability is. The docs should say that honestly (module structure + import-linter), not "unforgeable token."
2. **Grant is never verified at the point of effect.** `dispatch.py:64-65` checks `decision.allowed` and `grant_id is not None`; `get_grant()` (expiry) has **zero callers** on the dispatch path. Confirmed.
3. **Path scoping cannot see `EditRequest.path`.** Key-name guessing (`"path"`, `"file_path"`, …) at `engine.py:45-48` never opens nested tool payloads. The primary mutation tool gets empty `scope_paths` by construction.
4. **Sandbox-as-perimeter (ADR-0006) is correct** — and therefore Block 5 is load-bearing earlier than the roadmap admits once autonomy leaves `interactive`. Shipping `run_command` in Sprint 3 under subprocess without at least workspace-root confinement is a known gap; document it as a hard product constraint, not a footnote.

**CHANGE.** Sprint 3 must verify grant-at-effect (call `get_grant` before `registry.dispatch`, reject expired/unknown). Schema-declared path params for the five built-in tools cannot wait for Block 3 if `apply_edit` ships in Block 1 — that is a sequencing error, not a polish item. See **C1**.

### 5.3 Tech Stack & ADR Choices — Spec 8 / Impl 5

**GOOD.** ADR-0005 (best-of-N not MCTS), 0008 (no LiteLLM), 0012 (record/replay ≠ reproducible generation), 0014 (defer dense), 0016 (Podman) are sound with usable reversal conditions. Python 3.13 + uv + anyio is fine for a control plane.

**BAD — highest-regret candidates:**

| ADR / choice | Risk | Reversal already met? |
| :--- | :--- | :--- |
| Core deps include `mcp`, `opentelemetry-*`, `watchfiles`, `lsprotocol` while STATUS defers MCP/OTel/LSP | Install surface claims a product you do not have; slows CI; invites premature wiring | **Yes for intent** — deferred in STATUS, still in `pyproject.toml` dependencies |
| `<8,000 LOC` target | Slogan until a loop exists; currently ~2.8k of which ~half is unused port/event surface | Not yet — keep as a pressure, not a gate |
| Native Workflow DAG (ADR-0018) before L1 | Config-as-strategy is the macro thesis, but zero `WorkflowStep` code and no measured loop to reconfigure | Not met — **do not implement until Block 2 exists** |
| "Byte-for-byte replay" as absolute claim | ADR-0012 already softens this; pitch/AGENTS still overclaim | Graded fidelity (prior §11) should be normative everywhere |

**CHANGE.** Move MCP/OTel/lsprotocol/watchfiles to optional extras until Block 5. Demote ADR-0018 from "Accepted near-term" to "Accepted, gated on Block 2 ablation showing planning beats no-planning." Rewrite pitch §8 / AGENTS invariant 3 to graded replay L0/L1/L2.

### 5.4 Cross-Document Consistency — Spec 5 / Impl n/a

**GOOD.** `STATUS.md` as implementation SSOT is the right move. 2026-07-29 review fixed many X-findings.

**BAD (high value only):**

1. **Dual roadmaps.** `phased-migration-matrix.md` speaks E0/S0–S4; foundation review / STATUS speak Blocks 1–5. Same intent, different names — every new contributor will mis-schedule. Pick one.
2. **DMARTIC means two things.** Glossary / `dmartic-inner-loop.md`: 8 stages (Design→…→Self-Reflect). `pitch.md` §3: "understand, plan, act, verify, reflect" (5). Foundation review G1 uses the 5-step vernacular. The 8-stage version is mostly a relabeled ReAct+gates+reflect — Measure/Analyze/Review are ports that do not exist yet.
3. **Port count drift.** Prompt says 22; foundation review said 21; code has **22 Protocol classes** across `ports/` (including 3 AOI predictors in `advisory.py`). Test floor is `>= 18`. Harmless, but it signals nobody owns the inventory.
4. **Event catalog CI is date-fragile.** `scripts/gen_event_catalog.py` stamps `updated:` with today's date; `--check` fails solely because the committed file says `2026-07-29` and today is `2026-07-30`. Confirmed by regenerating. **This will go red in CI every calendar day the job runs** unless the stamp is fixed or excluded from the diff. New finding **D19**.

**CHANGE.** One roadmap vocabulary. Collapse public DMARTIC to "ReAct + verify + reflect"; keep 8-stage as internal optional checklist. Fix catalog date handling (**C2**).

### 5.5 Workflow & Loop Mechanics — Spec 6 / Impl 0.5

**GOOD.** Dual-process (System 1 ReAct / System 2 best-of-N) with an explicit anti-MCTS rationale is excellent. Gates-admit / scores-rank / absence-must-not-be-pass is the project's best idea. Escalation ladder as future label generator is mature thinking.

**BAD.** DMARTIC's eight stages are not eight mechanisms — they are prose over a missing `RunLoop`. Termination, stuck detection, iteration budget, and mid-turn steering are underspecified relative to shipping-harness reality (Claude Code / OpenCode survive on interruptibility and compact error surfaces). `GateReport.admitted` treats `None` as non-blocking (`work.py:74-81`: `g is not False`). That is intentional for profile N/A — and **catastrophic** if Sprint 3's evaluator leaves `tests_unmodified=None` by forgetting to compute it. Absence becomes pass. New finding **D20**.

**CHANGE.** Sprint 3 evaluator must set every coding-profile gate to `True`/`False`, never `None`. Add a conformance assert: under `gates=full`, `admitted` requires all four code gates non-`None`. Defer Workflow DAG and StoryBoard until one TaskSpec loop is measured.

### 5.6 Sprint Planning & Code Evolution — Spec 7 / Impl plan-only

**GOOD.** Sprint 3's one-sentence exit test is the right DoD. Ordering `ModelRequest` v2 before cassette fixtures (D10) is correct and load-bearing. Block 1 → measure (Block 2) before RHI is correct.

**BAD.** Sprint 3 is a **kitchen sink**: D1–D18 kernel fixes + RunLoop + five tools + Ollama adapter + Evaluator + CLI + resume + bus rewrite + CI coverage. That is 2–3 sprints of work labeled as one. Risk: you "close" Sprint 3 with a green cassette that never exercised deny-path, provenance, or multi-step history packing — then declare the loop closed.

**Is any D-fix entrenching a design flaw?** Yes, two:

* **D8 "tests not machinery" in Sprint 3 C** while shipping `apply_edit` without schema path scope — tests a ceremony that cannot constrain the real mutation tool. Fixing "add behavioral tests" without fixing path declaration **entrenchs** the key-guessing design.
* **D5 `is_error` on `ToolResult` without `call_id` on completion events** — `ToolCallCompleted`/`ToolCallFailed` carry no `call_id` (`events.py:199-216`); `ToolResult` has no `call_id` either (`content.py:106-111`). Multi-tool steps cannot be audited or mined. Fixing D5 as specified without correlation IDs **entrenchs** an unmineable event shape. New finding **D21**.

**CHANGE.** Split Sprint 3 into **3a** (ModelRequest v2, D1/D11, digest cassette, history packing, five tools, minimal evaluator, CLI run/replay, CI full pytest) and **3b** (resume, bus anyio+timeout, D14 kernel required ports, security deny-path, provenance). Do not call the loop "closed" until 3a exit test is green.

### 5.7 Quality of Results & Verifiability — Spec 8 / Impl 0

**GOOD.** A/A noise floor, pristine injected tests, commit-replay harvesting (ADR-0015), paired k≥3 with multiple-comparison correction (`rhi-outer-loop.md` Tier 0–3) — this is the actual moat *as a slogan*, and it is ahead of peers who ship vibes.

**BAD.** The moat is **not executable as specified.**

1. Tier 0 says run the unmodified harness **twice** and treat the score-delta as the floor (`rhi-outer-loop.md` Tier 0). n=2 does not estimate a distribution; it estimates a single difference. Tier 3 asks k≥3 and "corrected for multiple comparisons" but names **no test** (paired t? bootstrap CI? Wilcoxon?), **no α**, and **no formal predicate** for "clears the noise floor."
2. For a 10–30 task E0-lite suite, k=3 has almost no power to detect a 5% absolute lift. The cost note (thousands of dollars per outer-loop iteration) is honest — and implies full RHI is a research schedule until the suite is tiny and local (Ollama).
3. **ADR-0015 contradicts its own rubric.** The ADR recommends Class C (public A + private B, reported separately) as the way to *measure* contamination; the Decision adopts Class B only (`brainopensource/Harness-D-power`). Consequences then claim "Anyone can re-run it" — which Class B explicitly cannot promise. New finding **G14**.

Best-of-N at depth one is sufficient for v1; do not reopen ADR-0005.

**CHANGE.** Before Block 2: one-page stats appendix — estimator, α, MDE, k, and the exact accept/reject rule. Make E0-lite local-first. Re-open ADR-0015 far enough to either add a Class A public twin or strike the "anyone can re-run" claim and accept private-only as deliberate.

### 5.8 Extensibility & Protocol Universality — Spec 7 / Impl 3

**GOOD.** Async + Pydantic wire rule + port meta-suite is the right bar. Entry-point registration (ADR-0013) beats filesystem plugin scanning.

**BAD.** Known violation: `WorktreeManager.allocate() -> Workspace` returns a live Protocol (`ports/workspace.py:40`). Meta-suite explicitly exempts this (`test_port_shape.py:79-83`) — so the suite **cannot catch** the class of bug it was sold to prevent. Inference: there may be no second violation today because almost no adapters exist; the exemption is the risk.

`ModelProvider` marked `STABILITY = "stable"` while `ModelRequest` cannot describe a real request (D10) — **stability labels are lying.**

**CHANGE.** Introduce `WorkspaceRef` (opaque id) before any WorktreeManager adapter. Relabel all ports `draft` until two adapters exist (U3 still holds). Do not freeze compatibility promises.

---

## 3. New Findings

Prior D1–D18 / G1–G10 / U1–U5 stand. Additions only.

### Defects

| ID | Finding | Evidence | Impact |
| :--- | :--- | :--- | :--- |
| **D19** | Event-catalog `--check` fails on date stamp alone | `scripts/gen_event_catalog.py` writes `updated: <today>`; committed catalog has `2026-07-29`; regenerating on 2026-07-30 differs by one line. `uv run python scripts/gen_event_catalog.py --check` fails on a clean tree | CI quality-gates job will fail daily or force pointless regenerations; the drift gate loses signal |
| **D20** | `GateReport.admitted` treats unset code gates as pass | `src/sagiha/domain/work.py:73-81` — `all(g is not False for g in …)` | A Sprint 3 evaluator that forgets `tests_unmodified` admits cheaters; contradicts "absence must never be representable as pass" |
| **D21** | Tool completion events cannot correlate to a call | `ToolCallCompleted` / `ToolCallFailed` (`events.py:199-216`) have no `call_id`; `ToolResult` (`content.py:106-111`) has none either | Multi-tool steps, audit, and RHI trajectory mining are structurally lossy even after D5/D6 |

### Gaps

| ID | Finding | Detail |
| :--- | :--- | :--- |
| **G11** | Core dependency set contradicts deferral policy | `pyproject.toml:11-25` pins `mcp`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`, `lsprotocol`, `watchfiles` while `STATUS.md` Explicitly Deferred lists MCP, OTel, warm LSP |
| **G12** | Sprint 3 ships mutation tools under an unverifiable path scope | D8 path guessing cannot see `EditRequest.path`; Block 3 is "later" | First real writes are unconstrained by the capability model that justifies the project |
| **G13** | No owned inventory of ports / events / config consumption | Counts drift across docs; ~90% of `Config` ignored (prior G10) | Contributors cannot tell draft from load-bearing |
| **G14** | ADR-0015 adopted Class B against its own Class C recommendation | `0015-benchmark-target-repository.md` Decision vs "Recommended: C"; Consequences claim external re-runnability Class B forecloses | Headline S0/E0 numbers will be private-only; contamination unmeasured; reversal conditions do not name this inconsistency |

### Proposed Changes

| ID | Change | Why now |
| :--- | :--- | :--- |
| **C1** | Schema-declared path parameters for built-in tools in Sprint 3a; verify `get_grant` at dispatch | Cost of delay: every cassette and e2e test recorded against ceremony-security teaches the wrong invariant |
| **C2** | Stop putting `date.today()` in generated catalog frontmatter (fixed date from git, or exclude `updated:` from `--check`) | Cost of delay: CI signal death |
| **C3** | Split Sprint 3 → 3a (closed loop) / 3b (hardening) | Cost of delay: a false "loop closed" declaration |
| **C4** | Move MCP/OTel/LSP/watchfiles to extras | Cost of delay: dependency gravity pulls implementation toward periphery again (Sprint 2 failure mode) |
| **C5** | Smallest honest L3: one mutable prompt template + A/A on ≤15 local tasks; no AOI/MetaImprover package | Cost of delay: building RHI machinery before mining substrate (D6/D21) produces a self-improver that reads envelopes |

### Doc Remediations

| ID | Finding | Disposition |
| :--- | :--- | :--- |
| **X12** | Unify Block 1–5 vs E0/S0–S4 vocabulary | Pick Blocks as operational; keep S-slices as capability narrative *or* vice versa — one table mapping both |
| **X13** | Pitch/AGENTS "byte-for-byte" → graded L0/L1/L2 per foundation review §11 | Spec wrong relative to ADR-0012 intent |
| **X14** | Replace "unforgeable Grant" with "reachability-enforced capability id" | Spec overclaims |
| **X15** | Public DMARTIC = ReAct+verify+reflect; 8-stage optional | Spec / glossary conflict |
| **X16** | Mark `ModelProvider` / most ports `draft` until second adapter | Code stability markers wrong |

---

## 4. Challenges to Prior Verdicts

| Prior position | Challenge | Judgment |
| :--- | :--- | :--- |
| **Keep empty `agency/` / `runtime/`** (trap #1 — rejection holds) | Correct *not* to delete packages. Incorrect to treat emptiness as free. Vacuous import contracts are a false sense of security (U1). | **Rejection stands; urgency raised** — put code in `agency/` in 3a or the CAR story is theater |
| **Do not collapse 32 events** (trap #2) | Split Requested/Authorized is right. But 32 events with ~5 ever emitted, and completion events missing `call_id`, means the catalog is a **future schema tax**. Do not collapse groups; do **freeze new event types** until the loop emits the existing ones (G9). | **Rejection stands with a freeze** |
| **22 ports ≠ overengineering** (trap #3) | Declarations are cheap. Marking them `stable` and writing conformance promises for adapters that cannot exist (ModelRequest D10) **is** overengineering. | **Partial overturn** — keep ports; revoke stability; freeze new ports |
| **"Evaluator too rigid" already answered** (trap #4) | Normative policy in `task-and-acceptance.md` is fine. The real risk is D20 (`None` → admit), which is the rigidity *escaping through a side door*. | **Rejection stands; add D20 as the actual bug** |
| **2026-07-29: "not overbuilt"** | Code LOC is not overbuilt. **Documentation + dependency + event/port surface** is overbuilt relative to demonstrated capability. The review under-weighted that. | **Amend** — over-specified, under-demonstrated |
| **Sprint 3 as single Block 1** | Correct target; incorrect packing. | **Amend → C3** |
| **Strict E0-first → Block 1 then Block 2** | Right call. But **harvesting** (commit-replay task extraction) does not need a working agent — it can start in parallel with 3a and force honesty about TaskSpec/acceptance shapes early. | **Amend** — parallelize harvest scaffolding with 3a |
| **ADR-0015 Accepted / Class B** | Rubric recommended C; Decision took B; prose still implies publishable re-runs | **Re-open** — either add Class A or rewrite Consequences (G14) |
| **"Evaluator too rigid" dismissed because normative policy exists** | Policy text is fine; missing stop-detector / iteration-budget / stuck signatures (named in `proj_plan_design_and_docs_improvs.md` resilience debts) are the real backstop gap, not criterion rigidity | **Amend** — keep criteria policy; add loop-budget as Sprint 3a stop condition (already partly in checklist) — do not treat the trap dismissal as "resilience is handled" |

---

## 5. Delete List

We expect action. Ordered by value.

| Item | Action | Rationale |
| :--- | :--- | :--- |
| Near-term implementation of ADR-0018 Workflow DAG / StoryBoard docs-as-sprint-work | **Defer hard** — no code until Block 2 | Macro thesis without a measured micro loop is how Sprint 2 happened |
| `aoi/` package content ambitions + acting-mode docs as Sprint-near | **Keep stub; delete/archiving acting-mode from "next"** | U5 — no measured lift possible |
| `ports/advisory.py` (3 Protocols) + `ports/meta_improver.py` + `ports/embedding.py` as "part of the architecture you inherit" | **Relabel draft / move to `ports/_future/` or document as frozen stubs not in Kernel** | They expand the Kernel mental model and stability floor for zero runtime |
| `ShortTermMemoryAdapter` if not wired in 3a prompt assembly | **Delete** (prior D12) | Dead dual path |
| Cassette `stream()` lying implementation | **Raise `NotImplementedError`** (prior D15) | Honest > fake |
| Core deps: `mcp`, `opentelemetry-*`, `lsprotocol`, `watchfiles` | **Move to extras** (C4) | Match STATUS deferrals |
| Four execution profiles as Day-Zero product surface | **Ship `coding` only** until Block 2; keep others as config examples | Profile matrix multiplies unbound-port combinations |
| Public eight-stage DMARTIC branding | **Collapse messaging** (X15) | Acronym without mechanisms |
| Duplicate roadmap naming | **Delete one vocabulary** (X12) | Consistency |
| Reference harness trees under `src/{claude_code,grok_build,…}` if untracked / not part of package | **Confirm git policy** — only `src/sagiha` is packaged; keep references under `docs/reference/` or a `vendor/` that is clearly non-product | Avoid confusing "the codebase" |

**Do not delete:** domain models, port meta-suite, import-linter contracts, config security refusals, dispatch choke-point structure, event catalog *generator* pattern, ADR discipline, STATUS.md authority.

---

## 6. Sequencing Critique

```
Current plan:   Block1(loop) → Block2(measure) → Block3(authority) → Block4(retrieval) → Block5(sandbox/MCP/OTel)
Recommended:    Block1a(loop+grant-verify+path-scope-for-builtins) → Block1b(harden)
                ∥ harvest scaffolding
                → Block2(E0-lite, local-first) → Block3(remaining authority) → Block5(sandbox before autonomous)
                → Block4(retrieval only with ablation)
                → L3-min (prompt ratchet) long before full RHI
                → L4 never before measured L2
```

| What is too early | What becomes load-bearing sooner than planned |
| :--- | :--- |
| Workflow DAG / PRD→StoryBoard | Grant verification + path scope (with first tools) |
| MCP, OTel, dense retrieval, AOI, RHI package | Typed event reads (D6) + call_id correlation (D21) — mining substrate |
| Four profiles | `GateReport` absence-as-fail (D20) |
| Multi-agent / A2A | Workspace root confinement for `run_command` |
| Stability-marked ports | `ModelRequest` v2 (D10) — still the steepest contract cliff |

**Sprint 3 exit test:** still the right DoD. Narrow the *checklist* so the exit test is reachable without boiling the ocean (C3).

---

## 7. Forward Mandate — Five Answers

### 7.1 Is L3 reachable from this foundation?

**Reachable as a thesis. Not reachable from the foundation as currently embodied.**

The RHI document specifies AOI ranking, OTel GenAI conventions, thousands of trajectories, multi-tier verification, and human sign-off. That is a **different system's maturity** wearing this vocabulary. What *is* reachable: a harness that (a) records complete trajectories, (b) measures A/A noise on a small private suite, (c) proposes a change to a **declared mutable file** (prompt template / tool description), (d) accepts only if lift clears the floor, (e) never touches TCB paths.

If you cannot do (a)–(e) on 10 tasks with a local model, full RHI is fantasy. The foundation's ports for MetaImprover/AOI do not help — they suggest completeness you have not earned.

### 7.2 What must be true at L1/L2 for L3?

Your list (total replay, rich trajectory store, noise floor) is necessary and incomplete. Add:

1. **Stable request shape** — `ModelRequest` v2 frozen before any corpus of cassettes (D10).
2. **What the model saw is reconstructible** — prompt assembly + history packing (D18/G7); otherwise you mine outcomes without inputs.
3. **Failure taxonomy that is machine-readable** — `is_error`, disposition, call correlation (D5/D21); prose errors are not train/mine features.
4. **Typed event round-trip** (D6) — envelope-only stores make MetaImprover impossible.
5. **Mutable surface allowlist enforced in CI** — already in ADR-0007 spirit; must be real before any auto-proposal.
6. **Affordable evaluation** — local or cassette-first suite; otherwise L3 never runs.

### 7.3 Is sequencing right?

**Mostly yes.** Measurement before self-improvement: correct. L4 before measured L2: a trap — agree strongly. Swarming an unmeasured error rate multiplies unknown variance; without a noise floor you cannot separate coordination bugs from stochasticity.

**Disagreements:**

* Authority (path scope + grant verify) is not cleanly "Block 3" if Block 1 ships writes — pull a slice forward (**C1**).
* Harvest scaffolding can parallelize with the loop (**§4 amend**).
* Full RHI (S4 in migration matrix) is years/dollars after E0-lite; do not let S4 prose set Sprint expectations.

### 7.4 Smallest system that proves the meta-loop is real?

**L3-min (one month after Block 2, not before):**

1. One file: `prompts/system_coding_v1.txt` (or equivalent) on the mutable allowlist.
2. Suite: 10–15 commit-replay tasks from ADR-0015 repo, runnable under cassette or local Ollama.
3. A/A: k≥5 on the suite; publish σ / CI.
4. Mutation: human or scripted edit to the prompt (MetaImprover can be a shell script).
5. A/B paired; accept iff mean lift > A/A floor after multiple-comparison correction for the one hypothesis.
6. CI rejects TCB path touches; deploy requires human sign-off.

No AOI. No event-mined proposal engine. No multi-parameter search. If this cannot beat noise, stop — the meta-loop hypothesis failed cheaply.

### 7.5 What would I throw away to get there faster?

Without sacrificing the four properties:

* Workflow DAG / StoryBoard near-term work
* AOI + MetaImprover packages as implementation targets
* MCP/OTel/LSP in the default install
* Eight-stage DMARTIC as a product concept
* Profile matrix beyond `coding`
* New ports and new events until the existing ones are emitted and round-tripped
* "Unforgeable" / "byte-for-byte" absolute language
* Any sprint whose DoD is adapter count or doc count

Keep: choke point, cassettes, gates vs scores, pristine tests, A/A discipline, hexagonal ports, STATUS honesty.

---

## 8. Rewrite Recommendations

~2,800 LOC is cheap. Recommended rewrites (not because the authors are wrong — because the shapes are wrong for the next adapter):

| Component | Recommendation |
| :--- | :--- |
| `ModelRequest` + cassette | **Rewrite shape first** (D10/D2) — do not patch around `messages`-only |
| `kernel/react.py` | **Replace with `RunLoop`** that owns history, stop conditions, and events; keep `step()` as a private helper or delete |
| `DefaultPolicyEngine` path scoping | **Rewrite** to schema-declared paths; delete key guessing |
| `ToolResult` / tool events | **Extend** with `call_id` + `is_error` before recording any production trajectory |
| `GateReport.admitted` | **Tighten** so coding profile cannot admit on `None` gates (D20) |
| `EventBus` | **Rewrite concurrency** to anyio + observer timeout/quarantine (D17) — small file, high correctness leverage |
| `composition.build_kernel` | **Rewrite** mode binding + required ports (D3/D14) — this is the trust boundary for config |
| Domain / most ports | **Keep** |
| Full kernel delete-and-rewrite | **Not justified** — defects are localized; a greenfield rewrite would reintroduce the same sequencing mistakes |

---

## 9. Documentation Shape

85 files is wrong for L0.3. You do not need 55 deletions on day one; you need a **reading order and a quarantine**.

**Keep normative & short (target ~25 actively maintained):**

* `STATUS.md`, `AGENTS.md`, `pitch.md` (trimmed), `README.md`
* `01-executive/`: glossary (fix DMARTIC), vision (trim), getting-started → STATUS
* `02-architecture/`: car-model (honest about grants), remoteable-ports, security (sandbox timing), prompt-architecture (minimal), microkernel-and-bus — **archive or mark speculative:** neural-symbolic-memory detail, performance-sidecars, AOI-adjacent
* `03-contracts/`: hexagonal-ports (inventory + stability truth), domain-schemas (pointers to src), task-and-acceptance, tool-catalog (five tools only), error-taxonomy
* `04-workflows/`: dmartic (collapsed), rhi (mark L3-min vs full), event-catalog (generated), git-worktree
* `05-tech-stack/`: composition, configuration-reference (consumption table), dependencies
* `08-decisions/`: all ADRs
* `sprints/sprint-3.md` (split 3a/3b), `implementation/contracts-to-code.md`
* `reviews/` as historical (no edits)

**Quarantine (do not delete yet; exclude from agent retrieval — already partially done for `reference/`):**

* Full RHI / AOI / sidecar / MCP / A2A deep specs until Block 2
* `06-guides` that describe non-existent CLI as if current (STATUS already patches some)
* Duplicate conceptual essays in `reference/conceptual-design.md` / `design-derivation.md`

**Merge candidates:** vision + pitch overlap; executive-summary + README; configuration-reference consumption vs composition doc.

---

## 10. What Would Change My Mind

| Top recommendation | Evidence that would prove me wrong |
| :--- | :--- |
| **C3 — Split Sprint 3; narrow exit** | A single PR lands the full Sprint 3 checklist *and* the exit test in ≤2 weeks with ≥80% coverage and deny-path tests green — then the packing was fine |
| **C1 — Path scope + grant verify in 3a** | You ship Sprint 3 tools as read-only (`read_file`/`grep`/`list_dir` only) with writes deferred to Block 3 — then authority delay is safe |
| **C5 — L3-min before full RHI; AOI/MetaImprover deferred** | A published A/A floor on ≥30 tasks and one accepted prompt mutation with paired stats — then investing in mining infrastructure has a payoff function |

---

## 11. Continuation — Full Deep Pass (2026-07-30)

This section extends §§1–10. Prior IDs stand. New evidence from a full walk of `01`–`06`, contracts, CI comments, and the four shipping-harness references.

### 11.1 Additional defects

| ID | Finding | Evidence | Impact |
| :--- | :--- | :--- | :--- |
| **D22** | Phantom type `ThinkingContent` in port docs | `hexagonal-ports.md` Model & Control mentions `ThinkingContent` / `ReasoningBlock`; domain has only `ReasoningBlock` (`content.py:30-37`) | Adapter authors implement a type that does not exist |
| **D23** | Stale "known Path violation" on Toolchain | `remoteable-ports.md` still says `Toolchain.detect(root: Path)` must become `str`; `ports/toolchain.py:22` already takes `str` (and its docstring says the violation was fixed) | Doc trains contributors to "fix" a non-bug |
| **D24** | Normative upcasters module does not exist | `port-stability-and-versioning.md` §Data Schema Versioning points at `sagiha/domain/upcasters.py` — **file absent** | D6 fix has nowhere to land per the project's own versioning contract; every pre-fix trajectory is stranded by design until this is created |
| **D25** | `domain-schemas.md` overclaims `GateReport.admitted` | Doc says admission requires all code gates; code uses `g is not False` (`work.py:73-81`) so `None` admits — same class as D20 | Spec and code disagree on the project's core honesty invariant; **code is wrong** (D20), doc currently describes the intended rule |

### 11.2 Additional gaps

| ID | Finding | Detail |
| :--- | :--- | :--- |
| **G15** | Guides present per-port behavioral conformance as load-bearing | `ci-and-quality-gates.md` Conformance Matrix, `port-conformance-testing.md`, glossary "Conformance suite" name suites/files that do not exist. Reality: `test_port_shape.py` + `test_composition.py` only; CI comment admits meta-only | Present-tense security theater |
| **G16** | Composition docs invent live provider binding | `composition-and-configuration.md` describes Anthropic/OpenAI registry + entry-point resolve; `composition.py` always binds cassette; no `entry_points` usage in `src/sagiha` | Same failure mode as D3, in prose |
| **G17** | Tool catalog claims ~20 tools "ship in the core binary" | `tool-catalog.md` intro + LSP/graph/web/spawn tools; STATUS: five tools in Sprint 3, none implemented | Inflates Day-Zero surface; conflicts with Sprint 3 non-goals |
| **G18** | `writing-adapters.md` still says adapters take a `Grant` | Contradicts CAR / port-shape rule (Grant never on signatures) | Will reintroduce the superseded grant-crossing pattern the 2026-07-28 review killed |
| **G19** | `benchmark-curation.md` clock stopped at "Sprint 1" | Project clock is Sprint 3 / Block 1 per STATUS | Harvest work will be scheduled against a dead phase name |
| **G20** | CLI / CI comments still say "lands at S0" | `cli.py:3-4`, `.github/workflows/ci.yml` replay stub comments | Dual vocabulary with STATUS (same family as X12) |
| **G21** | No stuck-loop / iteration-budget / stop-detector | Shipping harnesses have these (Hermes `ToolCallGuardrailController` + `IterationBudget`; Grok `goal_stop_detector`). SAGIHA: EffectClass (replay) + governor (spend) only — orthogonal to "is the agent stuck?" Comparison doc §2.8 / A3 / A4. Foundation review under-weighted this vs D1 | Runaway under `gates=none` or a broken cassette (D2 last-entry repeat) has no product backstop |
| **G22** | Compaction is policy without a procedure | Docs say "task boundaries or remaining headroom"; OpenCode uses ~95% window; Claude/Hermes have concrete algorithms. No N, %, summarizer role, or layer-8 steps in SAGIHA | Prompt assembly in Sprint 3 will invent ad-hoc truncation; cache prefix discipline will break immediately |
| **G23** | No mid-turn interrupt / interjection semantics | Events `UserMessageReceived` / `TaskRevised` exist; Grok has queue+merge rules; no SAGIHA merge semantics | Six-hour unattended claim without steering is a demo, not a product |
| **G24** | Interactive approval UX unspecified | Grants are structural (correct per ADR-0006); OpenCode/Claude/Hermes still ship session allow / modal HITL as *cockpit*. SAGIHA has durable async gates on paper only | `interactive` autonomy is paper until a cockpit can resolve `ApprovalRequested` |

### 11.3 Additional doc remediations

| ID | Finding | Disposition |
| :--- | :--- | :--- |
| **X17** | Six+ broken links to foundation review (omit `doing/`) | Fix in: `STATUS.md`, `docs/README.md`, `v0.1-user-guide.md`, `neural-symbolic-memory.md`, `port-stability-and-versioning.md`, `development-plan-and-prompts.md`, `sprint-2.md`, `sprint-3.md` → `reviews/doing/2026-07-29-foundation-review.md` |
| **X18** | SSOT still says contracts live in markdown / "until `src/` exists" | `docs/README.md`, `hexagonal-ports.md` headers, `AGENTS.md` §2 — **src/ exists**; say "code wins" |
| **X19** | `docs/README.md` claims 17 ADRs | Log has **18** (0001–0018) |
| **X20** | Mutation tool named `edit_file` in catalog vs `apply_edit` in STATUS/Sprint 3 | Port method is `Workspace.apply_edit` — **rename catalog to `apply_edit`** (or alias once; do not keep two names) |
| **X21** | EffectClass replay semantics disagree | Glossary / ADR-0012 / security: re-execute **only PURE**; `microkernel-and-bus.md` table lets IDEMPOTENT re-run under policy — align microkernel to ADR-0012 or amend the ADR deliberately |
| **X22** | TrajectoryStore called "source of truth" in hexagonal-ports | EventBus is normative SSOT; store is a subscriber — fix the port blurb |

**Markdown contract definitions remaining:** normative docs are clean (0 embedded Protocol/BaseModel classes). Only historical `reviews/done/2026-07-28-…` still embeds 14 classes — acceptable as archaeology; do not copy forward.

### 11.4 Shipping-harness gaps (priority for Sprint 3 / later)

| Mechanism | Who has it | SAGIHA today | When |
| :--- | :--- | :--- | :--- |
| Stuck detection (tool-call signature + result hash) | Hermes | Absent (G21) | **Sprint 3a** — especially with D2's silent last-entry repeat |
| Iteration budget + stop detector | Hermes, Grok | `max_steps_per_run` in config, unread by any loop | **Sprint 3a** — wire into RunLoop stop conditions |
| Continuous tool-output soft-trim | Grok | Truncation fields exist; no continuous prune (G22 adjacent) | Soft-trim policy in Sprint 3 prompt assembly; algorithm can be crude |
| Concrete compaction trigger (%, N, summarizer) | OpenCode, Claude, Hermes | Policy prose only (G22) | Specify in Sprint 3 before implementing assembly; implement later OK |
| NFS / non-local FS SQLite journal probe | Grok | WAL assumed; docs silent | **Sprint 3** — cheap; long runs will SIGBUS without it |
| Crash / process resume identity | Grok, Hermes | D9 | **Sprint 3b** |
| Mid-turn interrupt queue | Grok, Claude teammates | Event names only (G23) | Block 2+ |
| Session allow / modal approval UX | All four | Structural grants only (G24) | Block 2+ cockpit; **never** as security substitute |
| Sleep/wake / lid-close | Grok | Absent | Block 2+ |

**Under-weighted by the 2026-07-29 foundation review:** comparison §2.12 resilience ("no SAGIHA column"), §2.8 stuck detection, §2.2 ungated runaway, §2.3 soft-trim — all conceded there, treated as secondary to D1 in the foundation defect list. That framing was right for *unblocking the loop* and wrong for *what kills a six-hour run after the loop works*.

### 11.5 Expanded delete / merge / quarantine list

Additive to §5 and §9:

| Item | Action |
| :--- | :--- |
| `tool-catalog.md` present-tense "ships in core binary" + non-Sprint-3 tools | Rewrite as **planned inventory**; mark Sprint 3 five tools as v0.1; rest `deferred` |
| `writing-adapters.md` Grant-parameter guidance | **Delete that paragraph**; replace with "Grant never crosses ports" |
| `ci-and-quality-gates.md` / `port-conformance-testing.md` per-port suite matrix as current | Mark **aspirational**; point at meta-suite until first behavioral suite lands |
| `remoteable-ports.md` Toolchain Path "known violation" | **Delete** (D23 fixed in code) |
| Phantom `ThinkingContent` | **Delete** from hexagonal-ports (D22) |
| Broken foundation-review links | **Fix** (X17) — highest-leverage doc PR in the tree |
| Merge: `README.md` ↔ `executive-summary.md` ↔ `vision-and-philosophy.md` | One loud surface |
| Merge: `v0.1-user-guide.md` ↔ `getting-started.md` | Same planned UX |
| Merge: `rhi-outer-loop.md` ↔ `metrics-analytics-and-self-improvement.md` | One outer-loop measurement doc |
| Quarantine: `reference/conceptual-design.md` + `design-derivation.md` | Already partially quarantined; stop dual-maintaining against normative `02`/`03` |

### 11.6 Additional proposed changes

| ID | Change | Why now |
| :--- | :--- | :--- |
| **C6** | Sprint 3a RunLoop stop conditions must include: `max_steps_per_run`, budget exhausted, end_turn, **and** a minimal stuck signature (same tool+args hash N times → SURFACE) | Without this, D2 + empty tools produces infinite green CI on garbage |
| **C7** | Create `domain/upcasters.py` (even if identity-only) in the same PR as D6 typed reads | Otherwise the versioning contract is fiction the day the first event shape changes |
| **C8** | One doc PR: X17 links + X18 SSOT + X20 `apply_edit` rename + G17 catalog tense | Cheapest honesty win; unblocks every new contributor |
| **C9** | Wire `governor.max_steps_per_run` and `record_spend` in 3a (config already has the knobs) | Dead knobs are how G10 stays at 90% ignored |
| **C10** | Before prompt assembly ships: write the compaction trigger as three numbers (headroom %, keep-first-N, keep-last-M) in `prompt-architecture.md` — even if implementation is "not yet" | Prevents silent divergence between cache design and the first assembler |

### 11.7 Dimension deltas (after deep pass)

| Dimension | Spec Δ | Impl Δ | Note |
| :--- | :---: | :---: | :--- |
| 5.4 Consistency | 5 → **4** | — | X17–X22, G15–G20: STATUS is honest; surrounding guides are not |
| 5.5 Workflow / loop | 6 → **5** | 0.5 | G21–G23: termination and stuckness underspecified vs shipping peers |
| 5.7 Verifiability | 8 → **6.5** | 0 | Moat slogan intact; A/A not executable (already §5.7); G14 ADR-0015 |
| 5.1–5.3, 5.6, 5.8 | unchanged | — | Deep pass confirmed, did not overturn |

### 11.8 Revised near-term stack (authoritative for this review)

```
Doc PR (C8)          — broken links, SSOT, apply_edit, catalog tense
        │
Sprint 3a            — ModelRequest v2 → digest cassette → D1/D11 → history packing
                     — five tools + path-scope (C1) + grant verify
                     — RunLoop + max_steps + stuck signature (C6) + spend (C9)
                     — Evaluator with non-None coding gates (D20)
                     — CLI run/replay + full pytest in CI
                     — call_id on tool results/events (D21) + typed event reads (D6) + upcasters stub (C7)
        │
Harvest parallel     — ADR-0015 tasks; decide Class A twin or strike publishability (G14)
        │
Sprint 3b            — resume (D9), bus anyio+timeout (D17), deny-path tests, NFS journal probe
        │
Block 2 / E0-lite    — A/A with a written accept predicate; local-first
        │
L3-min (C5)          — one prompt file, paired lift vs floor
        │
Only then            — Workflow DAG, retrieval ablation, sandbox@autonomous, MCP/OTel, full RHI
```

---

## Closing

The four properties are worth building. The foundation's contracts are a good substrate. The project will fail the way most ambitious harnesses fail: by implementing the interesting layer (meta-loop, multi-agent, workflow DAG, MCP) before the boring layer that makes claims falsifiable.

Sprint 3's exit sentence is the correct north star. Everything in this review is subordinate to making that sentence true — and making sure that when it is true, the grant was real, the gate could not be None, the cassette matched the request, the trajectory carries call correlation an outer loop could mine, and the run stops when stuck rather than when the cassette runs out.

The deep pass did not change the verdict. It raised the price of ignoring resilience (stuck detection, step budgets, compaction triggers) and documentation honesty (broken authority links, tools/conformance claimed as shipping). Fix those in the same breath as the loop — or the first green e2e test will teach the wrong operational habits.

*Prefer judgment over praise; this document spent its budget accordingly.*
