---
status: historical
retrieval: excluded
---
# CRITICAL GAP ANALYSIS & AUDIT — SAGIHA (`Harness-D-power`)

**Auditor role:** Senior Tech Lead, external adversarial review
**Scope:** Full `docs/` tree (~100 files, ~147k words), `src/sagiha` (~5.7k LOC, 84 files), ADR log (18), sprint records, internal reviews (2026-07-28 architecture review, 2026-07-29 foundation review, 2026-07-30 final review)
**Method:** Docs read against code, code read against claims, claims read against the competitive frontier (Claude Code, Grok Build, Cursor, Aider, Devin, OpenHands). Every verdict below is falsifiable against a file path or a measurement.

---

## 1. Executive Architectural Audit

### 1.1 Verdict in one paragraph

SAGIHA is the best-documented pre-product agent harness this reviewer has audited, and that is both its distinction and its pathology. The epistemics are genuinely superior to most shipped competitors: A/A noise-floor gating, multiple-comparison correction, commit-replay benchmark harvesting, capability grants verified at a single dispatch choke point, a Trusted Computing Base excluded from the self-improvement surface, cache-stability-ordered prompt layout, and record/replay determinism with `EffectClass`-aware safety. These are correct, SOTA-adjacent decisions that Claude Code and Grok Build do not publicly formalize. But the ratio is inverted: **~26 words of specification per line of code**, a Runtime layer that is an empty package, 21 ports backed by a handful of adapters, LSP/MCP/sandbox/retrieval/System-2/RHI all deferred, and a loop that first closed against a live model on 2026-07-30 — the day before this audit. The system's dominant risk is not any architectural flaw; it is **spec-mass outrunning empirical contact**, a failure mode the project's own foundation review named ("under-demonstrated at the core, over-specified at the periphery") and then partially repeated (seven frontend sprint documents exist; the sandbox does not).

### 1.2 What is architecturally sound (validated, keep)

| Decision | Assessment |
| :--- | :--- |
| **CAR layering + capability grants + single dispatch choke point** | Correct and mechanically enforced (`import-linter` contracts, `verify_grant` mandatory at point of effect, grants never crossing port signatures). This is stronger than the ambient-authority model of every mainstream CLI agent, where the loop process holds full user privileges and "permissions" are UX prompts. |
| **Best-of-N + sequential repair, not MCTS (ADR-0005)** | Correct cost analysis. One expansion = full agent run + test suite; UCT's guarantees assume cheap rollouts. Verifier-guided BoN dominates shallow tree search at this cost profile. The PRM-as-prerequisite gating is the right dependency ordering. |
| **Cache-stability-ordered context layout** | The rejection of percentage-based per-turn allocators is exactly right; byte-identical prefix economics dominate token-count economics by up to ~10× on input price. Few competitors document this; Claude Code's harness observably behaves this way, Aider's does not. |
| **Record/replay determinism (ADR-0012) with digest-keyed cassettes + `EffectClass`** | The honest determinism claim (replay, not reproducible generation) plus DESTRUCTIVE-never-re-executed is the only sound way to make an agent kernel CI-testable at zero API cost. D2 (silent cassette index replay) was found and fixed internally — good immune system. |
| **Evaluation architecture (E0)** | Pristine injected read-only tests, `tests_unmodified` as a hard gate, gates-admit/scores-rank separation, A/A noise floor before any accept/reject, commit-replay private split. This is more rigorous than the published evaluation practice of any competitor and is the project's genuine moat. |
| **Split code-graph / episodic-graph (ADR-0011)** | Correct epistemics: deterministic facts from Tree-sitter/git must not pass through LLM extraction; bi-temporality only where facts actually age. "Git is already a bi-temporal store" is the sharpest sentence in the tree. |
| **Threat model (T1–T6)** | Sandbox-is-the-perimeter, command-blocklisting-is-not-security, provenance tracking against memory laundering with a conformance test, deny-by-default durable approval gates. Above industry median. |
| **Error taxonomy** | Typed errors, four dispositions, `EditRejected` as ordinary-not-exceptional. Most harnesses never specify this and abort runs one retry from success. |

### 1.3 Structural weaknesses & anti-patterns

#### W1 — Documentation as a load-bearing anti-pattern (severity: high, systemic)

147k words of normative prose maintained against 5.7k LOC. The tree is explicitly designed to be read by retrieval ("a status note in a README does not survive chunking"), i.e., the docs are themselves the primary context payload for the LLM maintainer. Consequences:

- **Context-rot exposure is self-inflicted.** The agent maintaining this repo must retrieve from a corpus 25× larger than the code it edits. Every doc is an attention tax and a drift surface. The SSOT discipline (contracts live only in `src/`) mitigates contract drift but not rationale drift — and rationale is 90% of the mass.
- **The review culture recurses.** Reviews of reviews (`reviews/todo/`, `reviews/doing/`, `reviews/done/`, a review of the review naming conventions) consume the same finite build effort the reviews correctly diagnose as misallocated. The 2026-07-29 review's sharpest finding — "sequencing, not architecture" — applies to the review process itself.
- **Recommendation:** hard cap normative doc mass (e.g., ≤15k words normative; everything else moves to `rationale/` and is excluded from agent retrieval by default), and adopt a *docs-shrink gate*: a sprint that adds N normative words must delete N elsewhere. The ADR log is the exception; it is cheap and high-value.

#### W2 — The differentiating capabilities are all in the deferred set (severity: critical)

The features that would distinguish SAGIHA from a naive tool loop — LSP diagnostics (`get_diagnostics`, `find_references`), the code graph (`impacted_by`), FTS5 retrieval, worktree-parallel System 2, container sandbox, MCP, sub-agents, compaction — are **uniformly Planned (Blocks 3–5)**. What exists today is: five built-in tools over a path-confined local workspace, a single-threaded ReAct loop, cassette replay, and one OpenAI-compatible provider adapter. That is approximately Aider circa 2023 minus the repo map, with vastly better plumbing. The architecture guarantees the deferrals are *cheap to reverse* (ports pre-shaped, conformance suites waiting) — that part is real — but the competitive matrix in §2 must be read with this in mind: **SAGIHA currently competes on evaluation honesty and security architecture, not on agent capability.**

#### W3 — The context-layout model contradicts the agentic-retrieval reality (severity: high, design flaw)

`prompt-architecture.md` places "Retrieved repository context" as semi-stable Layer 6, refreshed "when retrieval genuinely changes." But in the ReAct loop the harness actually runs, retrieval arrives as *tool results in the append-only tail* (`grep`, `read_file`, `find_symbols`) — the model pulls context agentically, exactly as Claude Code does and exactly as the tool catalog steers it to. Two problems follow:

1. **Layer 6 is vestigial at runtime.** Pre-assembled retrieval competes with agentic retrieval for the same job; if both operate, tokens are paid twice and the model receives near-duplicate context with different freshness. The doc never specifies which mechanism is authoritative when.
2. **Refreshing Layer 6 mid-task invalidates the cache for Layers 6–8** — the entire conversation tail — which is the single most expensive cache event possible, worse than compaction (which at least reclaims window). The doc's own logic ("order by stability") argues for demoting pre-assembled retrieval to *initial seeding only*, with all subsequent retrieval agentic and tail-resident. This should be made normative.

#### W4 — Compaction spec is numerically concrete but structurally naive (severity: medium-high)

The R9 numbers (20% headroom, keep-first-2, keep-last-6) are a welcome escape from prose, but:

- **Turns are not token-uniform.** Keep-last-6 verbatim can be 60k tokens of test logs or 600 tokens of chat; a turn-count policy has unbounded variance in what it preserves. The keep policy must be token-budgeted (e.g., keep-last up to X tokens, whole-turn granularity), or the 20% headroom trigger will fire immediately after its own compaction.
- **Provider block-pairing constraints are unaddressed.** Anthropic- and OpenAI-class APIs reject a `tool_result` whose paired `tool_use` was summarized away (and signed reasoning blocks, which the tree elsewhere correctly says must round-trip verbatim, cannot survive a summarization boundary mid-sequence). The compaction boundary must fall only on *complete* assistant→tool_result exchange units. The doc that gets reasoning-block transport exactly right (`context-and-cache-engineering.md`) does not connect that constraint to the compactor.
- **No anchored-artifact model.** SOTA compaction (observable in Claude Code) preserves *typed artifacts* — the plan, the file-set under edit, unresolved diagnostics — as structured state outside the summarized transcript. Layer 7 (plan state) does this for plans only; open-file set and diagnostic state should be lifted to the same status rather than hoping the summary retains them.

#### W5 — `EffectClass` granularity is per-tool, and it is wrong for the most-used tool (severity: medium)

`run_command` is statically DESTRUCTIVE, so `ls`, `cat`, `pytest --collect-only` are never re-executed on replay. This is *safe* but degrades replay from "re-verify" to "re-read" for the majority of real steps, weakening the strongest verification asset the system has. Effect classification should be per-invocation where cheaply decidable (argv[0] allowlist for PURE re-execution: `ls`, `cat`, `git status`, read-only test collection), with DESTRUCTIVE as the undecidable default. The audit log already captures argv as a list — the input needed for this is free.

#### W6 — RHI outer loop is economically dead at this project's scale (severity: high, strategic)

The tree itself computes the cost: hundreds of tasks × dollars × k≥3 × many candidates = **thousands of dollars per outer-loop iteration**. For a single-maintainer OSS project this is not "scheduled, not continuous" — it is *never*. The mutation-search framing (Meta-Improver proposes, four-tier gauntlet verifies, human signs off) is a research program wearing a feature's clothes. The salvageable 90%-of-value at 1%-of-cost:

- **Prompt regression testing** (prompts are already versioned artifacts): every prompt PR runs the pinned 30-task suite once, paired against baseline, reported against the A/A floor. Cheap, continuous, catches regressions — no mutation search.
- **Trace mining, not trace mutation:** harvest successful trajectories into (a) few-shot exemplars injected per-task-class and (b) SFT/DPO export (see W7). Both are one-directional pipelines with no gradient-hacking surface, so the TCB machinery guarding the Meta-Improver becomes mostly unnecessary.
- Keep the RHI *spec* as a rationale document with a trigger condition ("when a funded eval budget ≥ $X/month exists"), consistent with the tree's own trigger-not-calendar doctrine.

#### W7 — The trace→fine-tuning pipeline does not exist, even as a spec (severity: high vs. stated vision)

The task brief's Focus Area 5 — converting high-performing execution traces into fine-tuning datasets for open-weight models — has **no owner anywhere in the tree**. The ingredients are all present (append-only `TrajectoryStore` with typed steps, `GateReport` ground-truth labels, `StepScored` events, prompt versioning, Tier-4 local model slot, Qwen setup guide) and no document composes them. This is the highest-leverage missing spec in the repository: gate-admitted trajectories are *verified* training data — the scarcest commodity in code-model post-training — and SAGIHA's evaluation rigor makes its traces more valuable than a typical harness's. Specified in Deliverable 2, §6.

#### W8 — Injection defense has no output-side taint control (severity: medium, security)

T1 mitigations are input-side (envelopes, provenance, egress allowlist, credential exclusion). But the canonical modern attack is *write-through*: untrusted content (issue text, web page, dependency README) instructing the model to embed a payload **in the diff itself** — a weakened validator, a malicious URL in a lockfile, an exfiltrating test. The gates check tests-pass/tests-unmodified/coverage/diff-size; none inspects diff *content* against provenance. At `interactive` autonomy the human is the control; at `autonomous` (the design target) nothing is. Minimum viable mitigation: taint annotation on `EditRequest`s produced within N steps of EXTERNAL-provenance context, forcing those diffs through `request_approval` regardless of autonomy level; plus a diff-content lint gate (new network endpoints, new deps, disabled checks) as a *hard gate*, not a score.

#### W9 — Remoteable-ports purity taxes the hot path (severity: low-medium, tension to manage)

"Every port implementable over a wire" (all-async, Pydantic-serializable, no `Path`/handles) is elegant and buys future sidecars — but `read_file`/`grep`/`get_skeleton` are the highest-frequency calls in the system, and mandatory model-validation + async dispatch on a local FS read is measurable overhead in a tight tool loop. Not a reversal recommendation — the discipline has already paid for itself in the conformance suite — but the spec should permit adapter-internal fast paths (zero-copy within the adapter, validation at the boundary only) and the benchmark suite should report tool-dispatch latency so the tax stays measured rather than assumed.

#### W10 — The "DAG" is a linear pipeline; parallel story execution is unspecified (severity: medium vs. brief)

`workflow-orchestration-and-dags.md` specifies Prompt→PRD→StoryBoard→CodingStep→Verifier with a return edge — a cycle-bearing *chain*, not a DAG. `StorySpec`s carry "disjoint file-set closure," which is precisely the precondition for parallel execution across worktrees, and nothing exploits it: no dependency edges between stories, no concurrent `CodingStep` scheduling under the `ResourceGovernor`, no merge/rebase policy when closures were computed against a base that a sibling story just moved. ADR-0018's gate (planning must beat no-planning in an E0 ablation before the layer ships) is exemplary epistemics — keep it — but the spec that would ship should be a genuine story-DAG (Deliverable 2, §5).

#### W11 — Episodic knowledge-net will be empty in practice (severity: medium)

Links are written "by whoever creates the record" and automatic link inference is deliberately not built. Manual-write knowledge systems have a universal fate: unwritten. The neighbor/backlink queries the design celebrates are only as good as edge density, and edge density under manual writes rounds to zero. Cheap fix that respects the "wrong links are worse than absent" principle: *deterministic* auto-links only (record→files-touched from the trajectory, record→task, record→superseding-record on invalidation) — derivable without LLM extraction, hence not hallucination-bearing — with LLM-inferred links remaining out.

#### W12 — No first-run repo onboarding (severity: medium, competitive)

`sagiha init` is "Planned — not scheduled." Claude Code's `/init` (generating CLAUDE.md), Cursor's indexing pass, and Aider's repo map all solve the cold-start problem in the first minute of use. SAGIHA's prompt Layer 4 *consumes* AGENTS.md verbatim but nothing *produces* one, and the code graph that would seed it is Block 4. For a harness whose thesis is "context quality is the intelligence," shipping without the context bootstrapper is shipping without the thesis.

---

## 2. Competitive Capabilities Gap Matrix

Legend: ✅ shipped/working · 🟡 partial or spec-only · ❌ absent · **[Sx/Bx]** SAGIHA's planned block. SAGIHA column reflects **implementation truth per STATUS.md 2026-07-30**, not the docs' target state — that distinction is the point of the matrix.

| Capability | Claude Code | Grok Build | Cursor (agent) | Aider | Devin | OpenHands | **SAGIHA (today)** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Closed agentic tool loop (live model) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (closed 07-30) |
| Streaming token/step UX, mid-run steering & interrupt | ✅ | ✅ | ✅ | 🟡 | ✅ | ✅ | ❌ [B5] |
| Plan mode / approval-gated planning | ✅ | 🟡 | ✅ | 🟡 | ✅ | 🟡 | 🟡 spec'd (durable async gates — stronger design, unbuilt) |
| Search/replace or diff edit format w/ syntax validation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (`apply_edit`, Tree-sitter `syntax_valid`) |
| LSP / code-intelligence tools (refs, diagnostics) | 🟡 (via tools/MCP) | 🟡 | ✅ | ❌ | 🟡 | 🟡 | ❌ [B4/B5] — spec is best-in-class, code absent |
| Repo map / structural retrieval | 🟡 agentic | 🟡 | ✅ index | ✅ PageRank map | ✅ | 🟡 | ❌ [B4] (FTS5+graph spec'd; skeleton tool spec'd) |
| Dense/semantic retrieval | ❌ (deliberate) | 🟡 | ✅ | ❌ | ✅ | 🟡 | ❌ deferred (ADR-0014 — defensible, matches Claude Code's stance) |
| Sub-agents / delegation | ✅ | 🟡 | 🟡 | ❌ | ✅ | ✅ | ❌ [B5] (`spawn_subagent` spec'd w/ grant-subset — stronger design) |
| MCP client (external tool ecosystem) | ✅ | 🟡 | ✅ | ❌ | 🟡 | ✅ | ❌ [B5] — **table stakes gap; deferring it defers the whole ecosystem** |
| Hooks / extensions / slash-commands / skills | ✅ | 🟡 | ✅ | 🟡 | ❌ | 🟡 | 🟡 extension model + entry-points spec'd (ADR-0013), unbuilt |
| OS sandbox / container isolation | ✅ (sandbox modes) | 🟡 | 🟡 | ❌ | ✅ VM | ✅ container | ❌ [B5] — **and SAGIHA's own threat model says this is the perimeter** |
| Capability-grant security model (non-ambient authority) | ❌ (permission UX) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ **unique differentiator, implemented** |
| Record/replay determinism, replayable trajectories | ❌ | ❌ | ❌ | ❌ | 🟡 internal | 🟡 | ✅ **unique differentiator, implemented + CI-enforced** |
| Verified evaluation harness w/ noise floor & stats | ❌ (internal) | ❌ | ❌ | 🟡 benchmarks | 🟡 internal | 🟡 SWE-bench | ✅ E0-lite shipped (`sagiha bench --aa`) — **unique** |
| Best-of-N / parallel candidate search | 🟡 (subagents) | ❌ | ❌ | ❌ | 🟡 | ❌ | ❌ [B3] — spec superior (gates+PRM), unbuilt |
| Long-term memory across sessions | ✅ (CLAUDE.md, memory) | 🟡 | 🟡 | 🟡 conventions | ✅ | 🟡 | 🟡 port + provenance implemented; graph/persistence [B4] |
| Compaction / context management | ✅ | ✅ | ✅ | 🟡 | ✅ | 🟡 | ❌ spec'd (R9), not implemented — **agent dies at window edge today** |
| Multimodal input (screenshots, images) | ✅ | ✅ | ✅ | 🟡 | ✅ | ✅ | ❌ — absent from spec entirely; no `ContentBlock` image kind noted |
| Browser / web interaction for verification | 🟡 | ✅ | 🟡 | ❌ | ✅ | ✅ | ❌ (web_fetch/search spec'd, net-scoped) [B5] |
| Multi-language toolchain | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ Python-only `Toolchain` v1 (deliberate; trigger-gated) |
| Cost accounting / model tiering per role | 🟡 | 🟡 | ✅ | ✅ | ❌ | 🟡 | 🟡 spec complete & correct (cost-per-resolved-task), partially wired |
| First-run repo onboarding (`init`) | ✅ | ✅ | ✅ | ✅ auto | ✅ | 🟡 | ❌ unscheduled (W12) |
| Trace→fine-tune data pipeline | ❌ public | ❌ | ❌ | ❌ | 🟡 internal | 🟡 | ❌ **absent even as spec, despite being uniquely positioned (W7)** |

**Reading of the matrix.** SAGIHA holds three genuine, implemented differentiators no competitor has: the capability-grant security architecture, digest-verified record/replay, and the statistical evaluation harness. It trails on essentially every *user-facing capability* — and the gap is concentrated in Block 5, a single mega-block (sandbox + MCP + OTel + LSP-warm + multi-agent + streaming) that is doing the work of four releases. Block 5 as scoped is the plan's largest schedule risk.

---

## 3. Technical Debt & Risk Register

| ID | Risk | Mechanism | Likelihood | Impact | Mitigation status |
| :--- | :--- | :--- | :---: | :---: | :--- |
| R-1 | **Spec debt / doc-code divergence** | 147k words normative prose vs 5.7k LOC; every implementation sprint invalidates prose faster than C-series doc PRs repair it | High | High | Partially mitigated (contracts-in-code SSOT); rationale mass unmitigated (W1) |
| R-2 | **Context exhaustion kills runs today** | Compaction spec'd, not implemented; `RunLoop` history is unbounded in-process; long tasks hit the window and die | High (any task >~50 steps) | High | None until R9 implementation lands; **should be pulled forward of Block 3** |
| R-3 | **Token bloat via double retrieval** | Layer-6 pre-assembly + agentic tool retrieval both active (W3) | Medium | Medium (cost ×1.5–2 on retrieval-heavy tasks) | Unrecognized in docs; needs a normative ruling |
| R-4 | **Cache forfeiture on mid-task Layer-6 refresh** | Any semi-stable refresh invalidates tail cache (W3) | Medium | High on long tails (10× input price on invalidated span) | Unrecognized |
| R-5 | **Replay weakening via blanket-DESTRUCTIVE `run_command`** | Pure reads never re-verified (W5) | Certain | Medium (verification claim overstated) | Unrecognized |
| R-6 | **Dev-mode = ambient authority** | Until Block 5, tool subprocesses run with full user privileges under path-containment only; `autonomous` is config-refused (good) but `interactive` humans habituate to approving | High | Critical if habituated approval meets injection | Acknowledged (R10); residual risk is human habituation, unaddressed |
| R-7 | **Write-through injection at autonomy** | No diff-content/taint gate (W8) | Medium | Critical | Unmitigated |
| R-8 | **State corruption at compaction boundaries** | Summarizing across tool_use/tool_result or signed-reasoning pairs produces provider-rejected requests (W4) | High once compaction ships | High (hard failures mid-run) | Unrecognized in R9 spec |
| R-9 | **Block 5 mega-scope** | Sandbox, MCP, OTel, LSP, multi-agent, streaming in one block; each alone is a sprint-plus | High | High (schedule) | Needs decomposition (Deliverable 2, roadmap) |
| R-10 | **Best-of-N spend amplification** | N parallel worktrees × full test suites; `ResourceGovernor` bounds concurrency but no early-termination/pruning policy is spec'd (kill candidates on first hard-gate failure signal; racing verifiers) | Medium | Medium-High ($) | Partially (governor); pruning unspec'd |
| R-11 | **RHI never runs; self-evolution narrative unfulfilled** | Economics (W6) | High | Strategic (credibility of "self-improving" claim) | Reframe per W6 |
| R-12 | **Empty knowledge net** | Manual-only link writes (W11) | High | Medium (memory tier underdelivers) | Deterministic auto-links proposed |
| R-13 | **Stuck-loop cost bleed** | `RunLoop` has stuck-signature detection (implemented — good) but no spec ties detection to a *budget-aware* disposition ladder (retry-with-rehydration → escalate System 2 → abort-and-checkpoint) | Medium | Medium | Partial |
| R-14 | **SQLite-WAL write contention under B3 parallelism** | One-writer-per-DB rule is specified; parallel candidates × per-step commits × trajectory appends will test it; NFS probe exists but no contention benchmark | Medium | Medium | Spec'd, unmeasured |
| R-15 | **Single-maintainer bus factor on a 21-port surface** | Conformance suites make ports cheap to *hold*, but 21 ports × versioning policy is governance overhead sized for a team | High | Medium | Consider port consolidation (merge `ShortTermMemory` — already deleted its adapter — collapse `Reviewer` into `CandidateSearch` scoring inputs) |

### 3.1 Prioritized findings (what actually matters, in order)

1. **Implement compaction now (R-2/R-8).** It is the only defect class that hard-kills runs today, and its spec has two latent structural bugs (token-uniformity, block-pairing) that are cheaper to fix before first implementation than after.
2. **Rule on retrieval authority (R-3/R-4, W3).** One sentence of normative text ("Layer 6 seeds; all mid-task retrieval is agentic and tail-resident") saves the cache economics the whole layout exists for.
3. **Decompose Block 5 (R-9)** into sandbox-first (it is the perimeter and the unblock for `autonomous`), then MCP, then the rest.
4. **Write the trace→dataset spec (W7).** Zero implementation cost today; it converts every benchmarked run from now on into an asset.
5. **Add the diff-taint gate (R-7, W8)** before any autonomy level above `interactive` is enabled outside a sandbox.
6. **Reframe RHI (W6, R-11)** as prompt-regression CI + trace mining; archive mutation search behind a funding trigger.
7. **Ship `sagiha init` (W12)** — smallest capability with the largest first-impression delta vs. every competitor.

---

## 4. Dialectical Close — Should This Architecture Survive?

**Thesis (keep and finish it).** The hexagon is real, not ceremonial: conformance suites are parametrized over adapters, import contracts fail CI, ports are wire-shaped, and the two implemented differentiators (grants, replay) fell out of the architecture rather than being bolted on. The evaluation harness is a moat no competitor has publicly matched, and the trigger-not-calendar deferral doctrine means the unbuilt 70% is pre-paid, not debt. Rewriting would discard the only parts that are both finished and unique.

**Antithesis (it is an over-engineered monument).** A single maintainer specified 21 ports, 18 ADRs, a four-tier statistical gauntlet, and a self-improvement loop costing thousands per iteration — before the agent could call one tool against a live model. The differentiators (security, replay, stats) are invisible to users; the visible surface trails a 2023 Aider. The doc tree's own retrieval-optimization admits the docs are the product's main consumer of its own scarce resource. By the tree's own doctrine — "boring components first," "measure before building" — most of `02-architecture/` should not exist yet.

**Synthesis.** Both are correct about different layers. The *contract layer* (ports, domain models, grants, replay, E0) is finished, cheap to hold, and should be frozen and defended — it is the return on the over-specification. The *prose layer* is where the antithesis bites: it should be aggressively shrunk and demoted from normative to rationale. The *capability layer* should be built in the competitive order (§3.1, and Deliverable 2's roadmap), not the block order — pulling compaction and sandbox forward, pushing frontend and RHI back. The architecture survives; the plan and the doc mass do not, unchanged. Boundary condition: if Block 3+4 measurements show best-of-N and graph retrieval failing to beat their ablation baselines beyond the A/A floor, the correct move is not more harness — it is conceding that the harness margin over a frontier model + 5 tools is thinner than the vision assumes, and pivoting the project's identity fully onto E0, the one artifact whose value is independent of that result.

---

*Companion document: `NEXT_GEN_HARNESS_ARCHITECTURE_SPEC.md` — the refined blueprint and prioritized action plan implementing the verdicts above.*
