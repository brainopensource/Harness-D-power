---
status: rationale
updated: 2026-08-06
---

# SCHEMAS_AND_CONTRACTS — Pre-Phase 1 Engineering Specification

**Owners**: Tech Leads
**Standing**: these are the draft schemas for the three declarative runtime asset classes. On landing, the JSON Schema files under `src/aether/workflow/schemas/` and `src/aether/measurement/schemas/` become the contract; this document navigates.

**Common rules for all three schemas**
- JSON Schema **Draft 2020-12**, authored as YAML, `additionalProperties: false` everywhere (unknown keys are drift, and drift fails closed).
- Every instance carries `schema_version` (semver). Validators accept `major == supported`, reject otherwise — schema evolution is an explicit migration, never silent tolerance.
- **TCB placement differs by asset**: `manifest` and `family` instances are TCB *data* (immutable once pinned; changes are new files with new hashes). `workflow` instances are **mutable-surface data** (ADR-0006/0014) — the *schema and validator* are TCB, the topologies are not.
- Hashing: an asset's identity is `sha256` over its canonical JSON form (keys sorted, no insignificant whitespace); the YAML file is for humans, the canonical hash is for machines. All cross-references between assets are **by hash**, never by filename.

---

## 1. `workflow_schema.yaml` — declarative topologies (ADR-0014)

Encodes the five static checks of Diagram 5. What the schema can express structurally it expresses structurally (bounded iteration, declared fan-out, budget annotations); what needs graph analysis (socket compatibility, evaluator termination, acyclicity outside `repair` blocks) is named under `x-static-checks` and enforced by `TopologyValidator` — the schema documents the full contract even where jsonschema cannot check it alone.

```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
$id: "aether://schemas/workflow/1.0.0"
title: AETHER Workflow Topology
type: object
additionalProperties: false
required: [schema_version, topology_id, description, nodes, edges]

properties:
  schema_version: { type: string, pattern: '^1\.\d+\.\d+$' }
  topology_id:
    type: string
    pattern: '^[a-z][a-z0-9_]{2,63}$'
    description: Stable human id. Machine identity is the canonical-JSON sha256.
  description: { type: string, minLength: 1, maxLength: 500 }
  ancestry:
    type: object
    additionalProperties: false
    description: >
      Provenance for meta-loop-proposed variants: which topology this mutated
      from, and the admission record that let it in (M5 gates G5.2/G5.3;
      rollback = re-pinning parent_hash).
    properties:
      parent_hash: { type: string, pattern: '^sha256:[0-9a-f]{64}$' }
      admitted_by_family: { type: string, pattern: '^sha256:[0-9a-f]{64}$' }
      proposer: { type: string, enum: [human, meta_loop] }

  nodes:
    type: array
    minItems: 2
    items:
      type: object
      additionalProperties: false
      required: [id, kind, budget]
      properties:
        id: { type: string, pattern: '^[a-z][a-z0-9_]{1,63}$' }
        kind:
          type: string
          description: >
            Must resolve to a WorkflowStep registered at composition (I6).
            Topologies reference kinds, never classes; an unknown kind is a
            validation error, not a late import.
          examples: [retrieve, generate, apply, evaluate, repair, rank]
        params:
          type: object
          description: >
            Kind-specific configuration, validated against the step's own
            declared params schema (two-phase validation).
        budget:
          $ref: '#/$defs/budget_dims'
          description: >
            Reservation ceiling for this node per execution (static check 5:
            every effectful node carries one; the executor reserves before
            dispatch — reserve/commit/release, spec §5).

  edges:
    type: array
    minItems: 1
    items:
      type: object
      additionalProperties: false
      required: [from, to]
      properties:
        from: { type: string }
        to: { type: string }
        when:
          type: string
          enum: [always, on_pass, on_fail, on_instrument_error]
          default: always
          description: >
            Conditional routing keyed to the tri-state GateReport of the source
            node. on_instrument_error MUST route to a terminal flag node, never
            into repair — an instrument failure is not a repair candidate (B4).

  repair:
    type: object
    additionalProperties: false
    description: >
      Bounded repair loops (the ADR-0013 amendment). Executed as a static
      unroll — a cycle with a bound is still a DAG. Absent block = no repair.
    required: [from_node, via_nodes, back_to, max_iterations]
    properties:
      from_node: { type: string, description: "evaluate-kind node whose on_fail feeds the loop" }
      via_nodes: { type: array, minItems: 1, items: { type: string } }
      back_to: { type: string }
      max_iterations: { type: integer, minimum: 1, maximum: 16 }
      budget_per_iteration: { $ref: '#/$defs/budget_dims' }

  fan_out:
    type: array
    description: Declared Best-of-N sites (static check 4; ADR-0010 sequencing).
    items:
      type: object
      additionalProperties: false
      required: [node, n, cache_sequencing]
      properties:
        node: { type: string }
        n: { type: integer, minimum: 2, maximum: 32 }
        cache_sequencing:
          type: string
          enum: [warm_first_then_parallel, fully_sequential]
          description: >
            warm_first_then_parallel = candidate 1 issued alone to warm the
            shared prefix, then 2..N in parallel. Naive parallel over a cold
            prefix is a large cost multiple and is not expressible here.
        rank_by:
          type: string
          description: >
            Optional learned/proxy ranker id. Rankers ORDER candidates and may
            never ADMIT one (I9) — admission is the evaluate node, always.

$defs:
  budget_dims:
    type: object
    additionalProperties: false
    properties:
      usd_micros: { type: integer, minimum: 0 }
      prompt_tokens: { type: integer, minimum: 0 }
      completion_tokens: { type: integer, minimum: 0 }
      wall_clock_ms: { type: integer, minimum: 0 }
      concurrency_slots: { type: integer, minimum: 0 }

x-static-checks:   # enforced by TopologyValidator (TCB); schema-adjacent contract
  - socket_compatibility: >
      For every edge (a→b): a.output_type must be assignable to b.input_type,
      using the WorkflowStep[In, Out] socket types registered for each kind.
  - evaluator_termination: >
      Every path from every entry node terminates at a node of kind `evaluate`
      (structural I7 — no topology routes around the judge). `on_instrument_error`
      terminal flag nodes are the sole exemption.
  - acyclicity: The graph excluding declared `repair` blocks is a DAG.
  - repair_reachability: repair.via_nodes and back_to lie on a path re-entering
      the from_node's evaluate; unrolled depth = max_iterations.
  - fanout_join: every fan_out node has a declared join (rank or first-pass) —
      unjoined fan-out leaks worktrees and leases.
```

**Reference instance — the M1a walking skeleton plus the M2 repair amendment:**

```yaml
schema_version: "1.0.0"
topology_id: linear_repair_v1
description: "retrieve → generate → apply → evaluate, repair bounded at 3 (M1a+/M2)"
nodes:
  - { id: retrieve, kind: retrieve, budget: { wall_clock_ms: 120000 } }
  - { id: generate, kind: generate,
      budget: { usd_micros: 400000, prompt_tokens: 120000, completion_tokens: 8000 } }
  - { id: apply,    kind: apply,    budget: { wall_clock_ms: 30000 } }
  - { id: evaluate, kind: evaluate, budget: { wall_clock_ms: 900000, concurrency_slots: 1 } }
  - { id: repair,   kind: repair,
      budget: { usd_micros: 250000, prompt_tokens: 90000, completion_tokens: 6000 } }
edges:
  - { from: retrieve, to: generate }
  - { from: generate, to: apply }
  - { from: apply,    to: evaluate }
repair:
  from_node: evaluate
  via_nodes: [repair, apply]
  back_to: evaluate
  max_iterations: 3
  budget_per_iteration: { usd_micros: 300000, wall_clock_ms: 960000 }
```

---

## 2. `manifest_schema.yaml` — pinned task manifests (TCB data)

The manifest is a **benchmark definition and therefore immutable TCB** (spec §6 extension; closes the C18 phantom-suite class). B1's repo cache is *generated from* manifests — the repo list is derived, never hard-coded. Split assignment (DEV/HOLDOUT/SEALED) lives here so it is pinned with the tasks it partitions.

```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
$id: "aether://schemas/manifest/1.0.0"
title: AETHER Pinned Task Manifest
type: object
additionalProperties: false
required: [schema_version, manifest_id, suite, created_at, validity_gate, tasks]

properties:
  schema_version: { type: string, pattern: '^1\.\d+\.\d+$' }
  manifest_id: { type: string, pattern: '^[a-z][a-z0-9_-]{2,63}$' }
  suite:
    type: string
    enum: [swe_bench_verified, swe_bench_pro, terminal_bench, internal]
  created_at: { type: string, format: date-time }
  parent_manifest: { type: string, pattern: '^sha256:[0-9a-f]{64}$' }

  validity_gate:
    type: object
    additionalProperties: false
    description: >
      The per-task bidirectional canary policy applied when this manifest was
      built: gold patch must pass AND empty patch must fail on OUR instrument.
      Exclusions are published, never silent — silent exclusion is the
      overfitting vector.
    required: [gold_pass_required, empty_fail_required, exclusions]
    properties:
      gold_pass_required: { type: boolean, const: true }
      empty_fail_required: { type: boolean, const: true }
      exclusions:
        type: array
        items:
          type: object
          additionalProperties: false
          required: [instance_id, reason]
          properties:
            instance_id: { type: string }
            reason: { type: string, enum: [gold_patch_fails, empty_patch_passes,
                                           image_unbuildable, flaky_tests, upstream_retracted] }
            detail: { type: string }

  tasks:
    type: array
    minItems: 1
    items:
      type: object
      additionalProperties: false
      required: [instance_id, repo, base_commit, environment_image_digest,
                 test_command_hash, split]
      properties:
        instance_id: { type: string, minLength: 1 }
        repo:
          type: string
          pattern: '^[\w.-]+/[\w.-]+$'
          description: Upstream org/name. The B1 cache clones the distinct set of these.
        base_commit: { type: string, pattern: '^[0-9a-f]{40}$' }
        environment_image_digest:
          type: string
          pattern: '^sha256:[0-9a-f]{64}$'
          description: Evaluation container created from digest, never tag (sandbox §3.1).
        test_command_hash:
          type: string
          pattern: '^sha256:[0-9a-f]{64}$'
          description: >
            Hash of the exact test invocation. The Evaluator verifies the
            command it is about to run against this hash — a drifted command
            is an instrument error (GateStatus.NONE), not a test result.
        fail_to_pass: { type: array, items: { type: string } }
        pass_to_pass: { type: array, items: { type: string } }
        split:
          type: string
          enum: [dev, holdout, sealed]
          description: >
            dev = ablations, burn freely · holdout = admission decisions,
            ≤1 evaluation per candidate mechanism · sealed = publication runs
            only, every touch logged. Assignment is pinned here (TCB) so it
            cannot drift per-run.
        perturbed_of:
          type: string
          description: >
            If set, this instance is a surface-rewritten variant of the named
            instance_id (contamination indicator set); paired reporting only,
            never mixed into the primary pool.
        flaky:
          type: boolean
          default: false
          description: Marked from within-arm discordance across seeded passes;
            analyzed with-and-without, never silently dropped.
```

---

## 3. `family_schema.yaml` — pre-registered gate families (ADR-0003 rev.2)

The family file is committed to the TCB **before any arm runs**; `statistics.py` refuses to compute corrected p-values for an undeclared family (enforcement over discipline). This is the anti-p-hacking contract: hypotheses, N, α-spending, and the cost margin are all fixed before data exists.

```yaml
$schema: "https://json-schema.org/draft/2020-12/schema"
$id: "aether://schemas/family/1.0.0"
title: AETHER Statistical Gate Family (pre-registration)
type: object
additionalProperties: false
required: [schema_version, family_id, registered_at, manifest_hash, model_fingerprint,
           outcome, alpha_family, correction, sample, power, arms, hypotheses, cost_criterion]

properties:
  schema_version: { type: string, pattern: '^1\.\d+\.\d+$' }
  family_id: { type: string, pattern: '^[a-z][a-z0-9_-]{2,63}$' }
  registered_at: { type: string, format: date-time }
  registered_commit:
    type: string
    pattern: '^[0-9a-f]{40}$'
    description: The commit that landed this file — provably before any arm ran.
  manifest_hash: { type: string, pattern: '^sha256:[0-9a-f]{64}$' }
  model_fingerprint:
    type: string
    description: Provider + model id + endpoint fingerprint, identical across arms.

  outcome:
    type: object
    additionalProperties: false
    required: [primary, aggregation]
    properties:
      primary: { type: string, const: resolve_pass_at_1 }
      aggregation:
        type: string
        const: first_seeded_pass
        description: >
          Primary outcome = pass@1 on the FIRST seeded pass (D14 rule).
          Additional passes estimate within-arm flakiness, reported separately,
          never merged post hoc.
      extra_passes_per_arm: { type: integer, minimum: 0, maximum: 4 }

  alpha_family: { type: number, exclusiveMinimum: 0, maximum: 0.1, default: 0.05 }
  correction: { type: string, const: holm_bonferroni }

  sample:
    type: object
    additionalProperties: false
    required: [tier, n, split]
    properties:
      tier:
        type: string
        enum: [smoke, admission, publication]
        description: smoke (directional only — NEVER admits) · admission · publication.
      n: { type: integer, minimum: 50 }
      split:
        type: string
        enum: [dev, holdout, sealed]
        description: >
          Binding pairs — smoke:dev, admission:holdout, publication:sealed.
          The validator rejects mismatches (a smoke run on sealed data burns
          the publication set for nothing).

  power:
    type: object
    additionalProperties: false
    description: >
      The D1 amendment: N is DERIVED, not asserted. The discordance assumption
      comes from the A/A floor + baseline runs and is named here; the power
      simulation (stdlib Monte-Carlo, seeded) is re-runnable from these fields.
    required: [minimal_effect_pts, assumed_p01, assumed_p10, target_power, simulation_seed]
    properties:
      minimal_effect_pts: { type: number, exclusiveMinimum: 0 }
      assumed_p01: { type: number, minimum: 0, maximum: 1 }
      assumed_p10: { type: number, minimum: 0, maximum: 1 }
      target_power: { type: number, minimum: 0.7, maximum: 0.99, default: 0.8 }
      simulation_seed: { type: integer }
      sequential:
        type: object
        additionalProperties: false
        description: Optional group-sequential design (early stop for large true effects).
        required: [looks, alpha_spending]
        properties:
          looks: { type: array, minItems: 1, items: { type: integer, minimum: 25 } }
          alpha_spending: { type: string, enum: [obrien_fleming, pocock] }

  arms:
    type: array
    minItems: 2
    items:
      type: object
      additionalProperties: false
      required: [arm_id, harness_id, config_hash]
      properties:
        arm_id: { type: string }
        harness_id:
          type: string
          description: HarnessUnderTest id — bare_model, aether, open_hands, ...
        config_hash: { type: string, pattern: '^sha256:[0-9a-f]{64}$' }
        topology_hash:
          type: string
          pattern: '^sha256:[0-9a-f]{64}$'
          description: Required when harness_id == aether (ADR-0014 identity).

  hypotheses:
    type: array
    minItems: 1
    description: >
      The declared family Holm–Bonferroni corrects across. Adding a hypothesis
      after registration = a NEW family file (new hash); there is no amend.
    items:
      type: object
      additionalProperties: false
      required: [hypothesis_id, arm_a, arm_b, direction, statistic]
      properties:
        hypothesis_id: { type: string }
        arm_a: { type: string }
        arm_b: { type: string }
        direction: { type: string, enum: [b_gt_a, two_sided] }
        statistic: { type: string, const: exact_mcnemar }
        ci: { type: object, properties: { method: { const: seeded_bootstrap },
                                          iterations: { type: integer, const: 2000 },
                                          seed: { type: integer } },
              required: [method, iterations, seed], additionalProperties: false }

  cost_criterion:
    type: object
    additionalProperties: false
    description: >
      The D11 reconciliation: admission requires cost-per-resolved-task
      non-inferior within the declared margin — not raw cost flat.
    required: [metric, max_increase_pct]
    properties:
      metric: { type: string, const: usd_per_resolved_task }
      max_increase_pct: { type: number, minimum: 0, maximum: 100, default: 20 }
```

**Reference instance — the first admission family (repair-loop ablation, per the refined roadmap):**

```yaml
schema_version: "1.0.0"
family_id: m2_repair_ablation_01
registered_at: "2026-09-15T00:00:00Z"
registered_commit: "<landed-before-any-arm-runs>"
manifest_hash: "sha256:<pinned verified+pro manifest>"
model_fingerprint: "openai_compatible:qwen3-coder-local:ep-a1"
outcome: { primary: resolve_pass_at_1, aggregation: first_seeded_pass, extra_passes_per_arm: 1 }
alpha_family: 0.05
correction: holm_bonferroni
sample: { tier: admission, n: 150, split: holdout }
power:
  minimal_effect_pts: 10
  assumed_p01: 0.12          # from A/A floor + baseline discordance, cited in PR
  assumed_p10: 0.02
  target_power: 0.8
  simulation_seed: 7
arms:
  - { arm_id: repair_off, harness_id: aether, config_hash: "sha256:...",
      topology_hash: "sha256:<linear_v1>" }
  - { arm_id: repair_on,  harness_id: aether, config_hash: "sha256:...",
      topology_hash: "sha256:<linear_repair_v1>" }
hypotheses:
  - hypothesis_id: repair_lifts_resolve
    arm_a: repair_off
    arm_b: repair_on
    direction: b_gt_a
    statistic: exact_mcnemar
    ci: { method: seeded_bootstrap, iterations: 2000, seed: 7 }
cost_criterion: { metric: usd_per_resolved_task, max_increase_pct: 20 }
```

---

## Validator wiring (all three schemas)

| Asset | Validated by | When | On failure |
|:--|:--|:--|:--|
| workflow topology | `workflow/validator.py` (jsonschema + 5 static checks) | load time, every run | executor refuses; typed error names the check |
| task manifest | `measurement/manifest.py` | manifest build + run start (incl. digest & test-command hash re-verification) | run does not start; instrument error, never a result |
| gate family | `measurement/statistics.py` gatekeeper | before the first arm executes | `PairedRunner` refuses; "undeclared family" is unrepresentable as data |

Each validator ships with a **test proving it can fail** (one malformed fixture per rule) — the house gate rule, applied to the gates' own gatekeepers.
