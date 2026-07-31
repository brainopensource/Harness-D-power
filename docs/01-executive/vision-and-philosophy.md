---
status: rationale
retrieval: excluded
updated: 2026-07-29
---
# **Vision & Foundational Design Philosophy**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

## **Core Thesis**
All intelligence, planning, and creative decision-making reside in the frontier LLMs. The harness is a modular, evolvable environment supplying context, structured memory, tool contracts, coordination, verification gates, and self-improvement mechanisms. The harness stays deliberately dumb; the models stay in charge.

## **Foundational Principles**

1. **LLM-Centric Intelligence**: Models own reasoning and goals. The harness owns context assembly, policy enforcement, and execution boundaries.

2. **Hexagonal Boundary Isolation**: Zero coupling between domain logic and infrastructure — but only if ports are written in *domain* language. A port phrased in storage terms (`store_vector(key, vector)`) is a driver wearing a Protocol: it forces the core to own the embedding model and cannot accept an adapter that takes text instead of vectors. Boundaries are enforced by conformance suites and CI import contracts, never by discipline.

3. **Day-Zero Decoupling**: Every component is interchangeable from day one, which is what makes deferral free. A query-shaped `Indexer` accepts a compiled sidecar later without touching a consumer; a domain-shaped `Memory` accepts a temporal graph without a caller noticing. Drawing the seams correctly at Day Zero is precisely what permits building the simple thing first.

4. **Boring Components First**: The failure mode for an ambitious harness is building the exotic parts first. Quantization, tree search, and compiled sidecars are legible and satisfying to design; what determines whether a coding agent works is the model port, context and cache layout, chunking, edit application, feedback latency, and error recovery. Every advanced component carries a **trigger condition** rather than a scheduled slot.

5. **Explicit Composition over DI Containers**: Wiring is one `build_kernel(config)` function. Dynamic containers and plugin discovery defeat static analysis — type checkers cannot see runtime-registered implementations, and neither can "go to definition." Since this codebase's principal maintainer is an LLM navigating it through a language server, **static navigability is an architectural requirement**, not a style preference. The system's own purpose argues for designing its source for the agent's comprehension.

6. **Dual-Process Loops**: Fast System 1 ReAct paired with deliberate System 2 best-of-N and sequential repair over parallel worktrees. Routing between them is a deterministic escalation ladder, which also generates the labelled data a learned router later trains on.

7. **Model–Harness Co-Evolution, Bounded**: Scaffolding is an editable artifact optimized under held-out evaluation — with the evaluator, gates, policy engine, and benchmark definitions placed permanently outside the improver's reach. A system that can edit its own grader has a trivial optimum.

8. **Generator–Evaluator Separation, Made Real**: Separation only counts if the generator cannot reach the evaluator's inputs. Since an agent has full filesystem access to its own worktree, tests are injected pristine and read-only, and modifying them fails a hard gate.

9. **Honest Measurement**: A stochastic system produces anecdotes, not results, when reported as single numbers. Metrics carry variance across repeated runs, comparisons are judged against a measured A/A noise floor, and repeated screening is corrected for multiple comparisons.

10. **Untrusted by Default**: Repository and web content is data, never instruction. Autonomy multiplies the blast radius of indirect prompt injection, so defense rests on the sandbox boundary, credential exclusion, and egress allowlisting — never on the model's judgment.
