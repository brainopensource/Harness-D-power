---
status: reference
updated: 2026-08-03
companion_to: PLANNING.md
shelf_life: short — see §13 Refresh Triggers
---

# Useful Information for Development

Reference companion to [`PLANNING.md`](./PLANNING.md). **`PLANNING.md` states the decisions; this
document holds the reasoning, the numbers, and the arithmetic behind them.** When a decision in the
charter looks arbitrary, the justification is here.

**Everything in this file has a shelf life.** Model prices, leaderboard positions, and the
scaffold-lift figure all move. §13 lists what invalidates each section. Numbers marked **[MODELED]**
are derived from token arithmetic, not measured — treat them as ±2× until this project measures its own.

---

## 1. The central thesis: what ages well

> **Model capability is rising, and rising capability erodes the value of harness cleverness. What
> survives is everything the model does not give you for free.**

The friction a harness removes — bad localization, no verification, wasted context, no repair loop —
gets progressively internalized by the models themselves. A scaffold that was worth ~20 points on
2024-era models is worth closer to 10–15 on frontier tiers today, and that number keeps compressing.

**Therefore: do not build a business or an architecture on raw resolve-rate lift.** It is the one
property guaranteed to shrink.

| Property | Trajectory | Why |
| :--- | :--- | :--- |
| **Raw capability lift** (harness makes model correct) | **Erodes** | Models internalize the scaffolding |
| **Cost per resolved task** | **Holds or grows** | Routing, caching, and search efficiency are engineering, not model properties |
| **Long-horizon autonomy** (8h+, hibernate, resume) | **Grows** | Longer-running models raise the ceiling *and* raise the cost of a crash |
| **Auditability & determinism** (replay, gates, trajectories) | **Grows** | The more autonomous the agent, the more the audit trail is the product |
| **Safety perimeter** (capability grants, sandbox, taint) | **Grows** | Autonomy raises the blast radius of a mistake |
| **Measurement honesty** (noise floor, contamination control) | **Grows** | Nobody can tell a real gain from noise without it |

**Design consequence, stated once and applied everywhere:** every architectural decision in this
project should be judged against the bottom five rows, not the first. The first row is what sells a
demo; the rest is what survives three model generations.

---

## 2. Benchmark landscape (as of 2026-08-03)

### The target moved — verify before committing to any number

| Benchmark | State | Verdict |
| :--- | :--- | :--- |
| **SWE-bench Verified** | **Saturating.** Top ~96% (Claude Opus 5); frontier tier clustered within ~1 point (Mythos 5 ~95.5%, Fable 5 ~95%). OpenAI stopped reporting it in early 2026. | **Dead as a headline metric.** 80% here is *below* an unscaffolded frontier call. |
| **SWE-bench Pro** | **Unsaturated, industry-preferred.** Leader ~69.2% (Opus 4.8). | **The real target.** 80% here would be genuine SOTA. |
| **SWE-bench Lite** | Small, cheap, heavily contaminated by age. | Fast smoke signal only. Never a headline claim. |

### Two facts that constrain every claim we make

1. **Scaffold-attributable lift is ~10–20 points on a fixed model.** That is the documented ceiling
   of what harness engineering buys. **Absolute score is dominated by model tier.**
2. **Verification is weak.** Roughly **1 of ~100** leaderboard entries carries an independent
   verification badge; the rest are vendor self-reported. Any number we publish must be
   independently reproducible or it is worthless in diligence.

### What this means for the claim we sell

> **Primary claim: scaffold-attributable lift on a fixed model**, with confidence intervals against
> a measured A/A noise floor, plus **cost and wall-clock per resolved task**.
> **Secondary: absolute SWE-bench Pro score.**

Lift-on-fixed-model survives a model swap, a leaderboard reshuffle, and a hostile review. Absolute
score does not. **Sell the lift, report the absolute.**

---

## 3. Harness vs. model — who contributes what

### What the model contributes (harness cannot substitute)

- Reasoning about unfamiliar code semantics
- Correct localization in a large, unseen repository
- Writing a patch that is *right*, not merely test-passing
- Judgment under ambiguity

### What the harness contributes (model does not get for free)

| Contribution | Mechanism | Worth |
| :--- | :--- | :--- |
| **Retries against a verifier** | Best-of-N + sequential repair over isolated worktrees | Largest single lift source on test-verifiable tasks |
| **Correct context** | AST-bounded retrieval, code graph, skeletons | Prevents editing the wrong file |
| **Cost control** | Prefix-stable caching, mixed-tier routing, compaction | 2–5× on total spend (§7, §8) |
| **Long-horizon survival** | Hibernation, resumable state, budget governor | Enables the 8h+ run at all |
| **Safety** | Capability grants, sandbox perimeter, taint tracking | Makes autonomy legal to ship |
| **Truth** | Real gates, noise floor, deterministic replay | Makes every other number believable |

### The asymmetry that matters

**Harness lift is largest exactly where the grader is machine-checkable.** SWE-bench is the friendly
case: tests decide, so the loop can keep trying until one candidate passes. On tasks with no
automatic verifier, Best-of-N degenerates into "generate N things and guess" — the lift mostly
vanishes.

**Corollary:** our advantage is strongest on verifiable engineering work and weakest on
taste-dependent work. Scope the product accordingly.

---

## 4. Theoretical limits — how far can a harness push a weak model?

### The frame

**A harness converts generation into search + verification.** With per-attempt success probability
*p* and *k* attempts, P(at least one success) = 1 − (1−p)ᵏ → 1 as k → ∞.

In theory, unlimited tokens and time drive success to certainty. Two walls stop this, and both are hard.

### Wall 1 — the p = 0 tail (dominant)

For many hard tasks a weak model's per-attempt success probability is not small, it is **zero**. It
cannot localize the bug, or it fundamentally misreads the semantics. **Sampling a zero-probability
event a million times yields zero.**

> **The real ceiling is the fraction of tasks where p > 0 — and that fraction is a property of the
> model, not the harness.**

### Wall 2 — verifier fidelity, and it inverts

SWE-bench tests are incomplete. As *k* grows, you increasingly select for *"patches that pass an
imperfect test suite"* rather than *"patches that are correct."* Past some *k*, extra sampling
**actively degrades precision** — you are optimizing the proxy.

This is the formal justification for charter invariant **I9: hard gates admit, proxies rank.** A
learned scorer may order candidates; it may never admit one.

### Empirical shape

pass@k curves flatten fast. Most of the gain lands in the **first ~10 samples**; there is very
little past ~50. Best-of-N should be sized accordingly — **N in the 5–10 range is where the
economics live**, not N=100.

### The honest summary

> The harness converts *"can the model do this reliably"* into *"can it do this once in k tries."*
> That conversion is worth **10–20 points and it saturates.** It cannot manufacture capability that
> is not there.

---

## 5. Pricing reference (verified 2026-08-03)

| Model | Input /M | Output /M | Cache read /M | Cache write /M (5-min) | Context | Cache minimum |
| :--- | ---: | ---: | ---: | ---: | :--- | ---: |
| **Claude Fable 5** | $10.00 | $50.00 | $1.00 | $12.50 | 1M | 512 tok |
| **Claude Opus 5** | $5.00 | $25.00 | $0.50 | $6.25 | 1M | 512 tok |
| **Claude Sonnet 5** | $3.00 | $15.00 | $0.30 | $3.75 | 1M | 1024 tok |
| ↳ *intro through 2026-08-31* | *$2.00* | *$10.00* | *$0.20* | *$2.50* | | |
| **Claude Haiku 4.5** | $1.00 | $5.00 | $0.10 | $1.25 | 200K | 4096 tok |

**Cache multipliers:** read **0.1×** base input. Write **1.25×** (5-min TTL) or **2×** (1-hour TTL).

**Break-even on a cache write:** 5-min TTL pays off at **2 requests** (1.25 + 0.1 = 1.35 vs 2.0);
1-hour TTL needs **3** (2 + 0.2 = 2.2 vs 3.0). Agent loops re-send the prefix dozens of times, so
caching is always worth it there — the question is only whether the prefix is byte-stable enough to hit.

> ⚠️ **Sonnet 5 intro pricing expires 2026-08-31 — 4 weeks from this document's date.** Any cost
> model built on $2/$10 must be re-baselined at $3/$15 before that date. Flag this in the client budget.

### Price ratios (the numbers that decide routing)

| Pair | Ratio | Consequence |
| :--- | ---: | :--- |
| Fable 5 → Opus 5 | 2.0× | Opus 5 is the default; Fable only for the genuinely hardest work |
| **Opus 5 → Sonnet 5** | **1.67×** (2.5× at intro) | **Too narrow for search-based substitution — see §7** |
| Opus 5 → Haiku 4.5 | 5.0× | Real arbitrage, but only where Haiku's *p* > 0 |

---

## 6. Cost model per task **[MODELED]**

### Stated assumptions (change these and the table changes)

- One SWE-bench-Pro-class task: **30–60 model calls**
- Context grows ~20k → ~150k tokens; **average ~60–100k per turn**
- Prefix re-sent every turn ⇒ total input re-sent ≈ turns × average context
- Cache hit rate **85–90%** with a byte-stable prefix
- Output with adaptive thinking at high effort: **3–5k tokens/turn**

### Modeled cost, Opus 5

| Config | Input | Output | **Total / attempt** |
| :--- | ---: | ---: | ---: |
| Single-shot, well-cached | ~$4 | ~$4 | **~$8** |
| Single-shot, **caching broken** | ~$12 | ~$4 | **~$16** |
| Best-of-5 + repair, well-cached | ~$18 | ~$14 | **~$25–35** |
| Best-of-5 + repair, caching broken | ~$50 | ~$14 | **~$60–80** |

### Cost per *resolved* task — the metric that matters

At a 65% resolve rate, **cost per resolved task = cost per attempt ÷ 0.65.**

> **Budget guidance: to land 60–70% on SWE-bench Pro, plan ~$30–50 per resolved task.**

**A correction to an earlier estimate in this project's discussion:** caching was described as a
"5–10× cost lever." That overstates it. Accurately: caching is worth **up to ~5× on the input
component** and **~2–4× on total task cost** — output tokens are priced 5× higher than input and are
not cached, which caps the total saving. It remains the single largest cost lever, just not by that
margin.

---

## 7. The substitution arithmetic — why "cheap model + more tries" usually fails

### The rule

> **Substitution pays only when: price ratio > attempt ratio.**
> If the cheaper model needs *k*× more attempts and is only *r*× cheaper, you win only when r > k.

### Applied to the actual price table

| Swap | Price ratio | Attempts needed to match | Verdict |
| :--- | ---: | :--- | :--- |
| Opus 5 → Sonnet 5 | 1.67× | ≥2 realistically | **Loses money.** 2 Sonnet attempts cost more than 1 Opus attempt, and add latency |
| Opus 5 → Haiku 4.5 | 5.0× | Many — and *p* ≈ 0 on hard tasks | **Cannot reach the score at any k** (Wall 1) |
| Open-weight self-hosted | 10–50× | Same *p* problem | Same wall, cheaper wall |

**Conclusion: there is no arbitrage between adjacent frontier tiers.** The price gaps are too narrow
for search-based substitution to pay.

### What a SOTA harness actually buys you

> **Approximately one model tier, not two.**
> Average model + great harness ≈ frontier model naive (~50 on Pro).
> It is a real, valuable trade — same result, meaningfully cheaper. It is **not** a substitute for
> frontier capability at the top of the range.

Worked example matching the numbers we've been discussing: a frontier model at ~50 naive reaches
~70 with a SOTA harness. An average model at ~30–35 raw, given the same +15–20 lift, reaches
**45–55 — not 70.**

### Where the real cost win lives: mixed-tier routing

Most turns in an agent loop are **cheap work**: planning, summarization, localization, candidate
ranking, compaction, commit messages. Route those to Haiku (5× cheaper); spend Opus 5 only on patch
generation and hard reasoning.

**Modeled saving [MODELED]:** if 60% of turns are cheap work,
`0.4 + (0.6 / 5) = 0.52` → **~48% total cost reduction**, with minimal resolve-rate loss, because
the cheap model is never asked to do the thing it cannot do.

> **This is the single highest-leverage cost decision in the project** — larger than model choice,
> larger than search strategy. It is charter open decision **Q3**.

---

## 8. Caching economics — the mechanical rules

Prompt caching is a **prefix match**. Any byte change anywhere in the prefix invalidates everything
after it. Render order is `tools` → `system` → `messages`.

### The layout invariant

```
tools → system → memory → static repo context → ‖cache breakpoint‖ → dynamic turns
        └────────── must be byte-stable ──────────┘
```

### Silent cache killers — audit for these

| Pattern | Effect |
| :--- | :--- |
| `datetime.now()` / timestamp in system prompt | Prefix differs every request — **zero** cache hits |
| UUID / request ID early in content | Same |
| Non-deterministic JSON serialization (unsorted keys, set iteration) | Prefix bytes differ |
| Tool set varying per user or per mode | Tools render at position 0 — nothing caches across users |
| Model switch mid-conversation | Caches are model-scoped — full rebuild |
| Editing the top-level system prompt mid-session | Invalidates the entire conversation history |

### Operational rules

- **Never mutate the prefix mid-session.** For mid-session operator instructions, append a
  `{"role": "system", ...}` message to `messages[]` rather than editing top-level `system` — it
  preserves the cached prefix. (Available on Opus 5 / Opus 4.8 / Fable 5 / Mythos 5.)
- **Track cache hit rate as a first-class metric** with an alert threshold. If
  `cache_read_input_tokens` is zero across repeated requests, a silent invalidator is present.
- **Sub-agents must inherit the parent's exact prefix** (`system`, `tools`, `model` verbatim) or they
  miss the parent's cache entirely.
- **Max 4 cache breakpoints per request.** Long agentic turns need an intermediate breakpoint every
  ~15 content blocks — a breakpoint only looks back 20 blocks for a prior entry.

---

## 9. Reference harness extraction — best of each

What to take from each cloned project, and what to deliberately reject. Scope discipline matters as
much as extraction: copying breadth we don't need is how the project bloats.

| Reference | **Take** | **Reject** |
| :--- | :--- | :--- |
| **Claude Code CLI** (`src/claude_code`) | Cache-stable prompt layout; pre/post-tool hooks; deny-first permissions; `CLAUDE.md` memory injection; JSONL trajectories; streaming TUI ergonomics; sub-agent delegation | TypeScript control plane; single-workspace model (no parallel candidates) |
| **Hermes** (`src/hermes_agent`) | **Closed learning loop** (agent-authored self-improving skills); FTS5 session search + LLM re-summarization; **RPC "code-mode" tool scripts** (collapse N round-trips into one context-cheap turn); serverless sandbox hibernation (Modal/Daytona); cron scheduler | Breadth over depth — six sandbox backends and six chat platforms are surface area we do not need |
| **Grok Build** (`src/grok_build`) | Rust crate layout for performance sidecars; git-worktree concurrency; codegen discipline | **Wholesale Rust core** — the workload is network-bound, not CPU-bound (§12, R4) |
| **OpenCode** (`src/open_code`) | Auto-compaction at context threshold; LSP integration shape; SQLite session persistence; TUI patterns | Architecture wholesale — archived project; its ReAct loop is less rigorous than ours |
| **SAGIHA** (`src/sagiha`) | CAR model; capability grants + dispatch choke point; port conformance suites; import-linter contracts; A/A noise floor; docs-budget CI gate; **the H1–H4 honesty audit as a permanent cautionary tale** | Anything measured before its instruments were verified |
| **Anthropic caching protocol** | Prefix-match invalidation semantics; explicit breakpoints; TTL tiers; write/read cost asymmetry; mid-conversation system messages | — |
| **DeepSeek** | Automatic prefix-caching economics; open-weight self-hosted tier for cheap bulk roles | Training-side techniques (MLA, GRPO) — we do not train models |

### The single most important inherited lesson

SAGIHA shipped **four gates hardcoded to `True`**, dead cost accounting, and stubs that fabricated
success. Every measurement taken over those instruments was uninterpretable and had to be discarded.

> **Instruments are built and verified before the capability they measure. A gate that cannot fail
> is a bug — and it is the most expensive class of bug this project can have.**

---

## 10. Budget planning

### Benchmark run costs **[MODELED]**

`Full suite cost = instances × cost-per-attempt`

| Suite size | @ $8/attempt (single-shot) | @ $25/attempt (BoN + repair) |
| ---: | ---: | ---: |
| 30 (smoke) | $240 | $750 |
| 500 | $4,000 | $12,500 |
| 1,000 | $8,000 | $25,000 |

### The finding that changes CI design

**Per-PR live benchmarking is economically infeasible at frontier prices.** A 30-instance live smoke
gate at $25/attempt is $750 per run; at 20 PRs/week that is **$15,000/week** — more than most teams'
entire model budget, spent on regression detection.

**Therefore the CI tiering is not a preference, it is forced:**

| Tier | Cadence | Mechanism | Cost |
| :--- | :--- | :--- | :--- |
| **Per-PR** | Every commit | **Deterministic cassette replay** — zero network, zero model spend | **$0** |
| **Nightly** | Daily | Small live suite (20–50 curated instances), single-shot | ~$200–400/night |
| **Pre-release** | Weekly / per milestone | Full live suite, full search config | $12k–25k/run |
| **Headline claim** | Rare, budgeted | Full SWE-bench Pro, independently reproducible | Own budget line |

This is why deterministic replay (charter T8) is a **core** capability and not a nice-to-have: it is
the only thing that makes a per-commit regression gate affordable at all.

### Budget lines to put in the client proposal

1. **Development-time model spend** — agents iterating during build (often underestimated; can rival benchmark spend)
2. **Nightly CI** — ~$6k–12k/month at the cadence above
3. **Pre-release full runs** — per-milestone, $12k–25k each
4. **Headline benchmark runs** — 2–4 over the engagement, budgeted explicitly
5. **Contamination-control private suite** — harvest + maintenance, mostly engineering time

---

## 11. Implications for sprints and sequencing

Each rule below is derived from a section above, not from preference.

| Rule | Derived from |
| :--- | :--- |
| **Instruments before capability.** Evaluator, noise floor, and cost accounting land before any capability sprint. | §9 (H1–H4 lesson); §2 (unverifiable claims are worthless) |
| **Caching correctness is a Phase 1 gate, not an optimization.** Cache hit rate is a tracked metric from the first live run. | §8; §6 (2–4× total cost) |
| **Mixed-tier routing is designed in from day one**, even if v1 routes everything to one tier. Retrofitting a routing seam is expensive. | §7 (~48% saving) |
| **Best-of-N sized at 5–10, never 50+.** | §4 (pass@k flattens); §6 (cost scales ~linearly) |
| **Deterministic replay is core, not deferred** — it is what makes per-commit CI affordable. | §10 |
| **A/A noise floor before any "must not regress" rule is enforced.** | §2; §4 |
| **Contamination-control private suite runs alongside every public number.** | §2 (weak verification) |
| **Rust sidecar only on measured evidence**, never on plan. Port only profiled hot paths behind an existing port. | §9 (Grok Build reject); network-bound workload |
| **Learned candidate scorer gated on corpus size**, never on a date — it must beat rank-by-tests-passed first. | §4 (Wall 2 — proxies degrade with k) |

---

## 12. Decision rules — the compressed heuristics

Pin these where they will be read during design arguments.

1. **Sell the lift, report the absolute.** Lift on a fixed model survives a model swap; absolute score does not.
2. **Cost per *resolved* task, not per attempt.** A config that adds 5 points and triples cost is usually worse.
3. **Substitution pays only when price ratio > attempt ratio.** Adjacent frontier tiers fail this test.
4. **A harness buys ~one model tier, not two.**
5. **Never sample past the point where the verifier's fidelity binds.** Hard gates admit; proxies rank.
6. **The prefix is sacred.** Any byte change costs 10× on every subsequent turn.
7. **Route cheap work to cheap models.** ~48% of spend is in turns that never needed a frontier model.
8. **A gate that cannot fail is a bug.**
9. **Empirical triggers, never calendar dates**, for `research`-tier components.
10. **Wire-serializable ports are free on day one and impossible to retrofit.** They are what let any
    component move to a sidecar, a container, or a remote peer without touching a caller.

---

## 13. Refresh triggers — when to re-verify this document

| Section | Invalidated by | Check |
| :--- | :--- | :--- |
| §2 Benchmark landscape | Any frontier model release; benchmark deprecation | Re-check Pro + Verified leaderboards **quarterly** |
| §5 Pricing | Any price change; **Sonnet 5 intro expiry 2026-08-31** | Re-verify **before any budget commitment**; never quote from memory |
| §6 Cost model | First real measured run | **Replace [MODELED] with measured** as soon as Phase 1b lands |
| §7 Substitution math | Any change to the price ratios in §5 | Recompute ratios whenever §5 changes |
| §3 / §4 Lift figures | New public scaffold-lift studies | Re-check **semi-annually**; expect the number to shrink |
| §10 Budget | §5 or §6 changing | Recompute from the formula |

> **Rule: never quote a price or a leaderboard position from this file into a client-facing document
> without re-verifying it first.** This file is a snapshot, not a source of truth.

---

## 14. Sources

Benchmark landscape (§2), retrieved 2026-08-03:

- [SWE-bench Verified Leaderboard (August 2026) — BenchLM](https://benchlm.ai/benchmarks/sweVerified)
- [SWE-bench Verified Leaderboard — Steel.dev](https://leaderboard.steel.dev/leaderboards/swe-bench-verified/)
- [SWE-bench Pro Leaderboard (2026) — MorphLLM](https://www.morphllm.com/swe-bench-pro)
- [SWE-bench Pro Public Leaderboard — Scale Labs](https://labs.scale.com/leaderboard/swe_bench_pro_public)
- [SWE-bench Verified — llm-stats](https://llm-stats.com/benchmarks/swe-bench-verified)
- [SWE-bench in 2026: Benchmarks vs Scaffolding Reality — Digital Applied](https://www.digitalapplied.com/blog/swe-bench-verified-june-2026-benchmark-vs-scaffolding-analysis)
- [SWE-bench Verified — Epoch AI](https://epoch.ai/benchmarks/swe-bench-verified)

Pricing and caching mechanics (§5, §8): Anthropic model catalog and prompt-caching documentation,
verified 2026-08-03 via the `claude-api` reference. Partner platforms (Bedrock, Vertex) are
separately priced.

> Leaderboard figures are predominantly **vendor self-reported**. Treat every number in §2 as a
> claim to be independently reproduced — including, eventually, our own.
