# Sprint 0 Review — Docs & Planned Harness

You are reviewing our **docs and planned Harness design** (not an implementation audit). We are in **Sprint 0**. Be candid: say what is already strong, what is missing or weak for a world-class agent harness, and what we should fix **now** vs later.

## What we are building
A multi-purpose agent platform that can:
- act as a coding agent (plan, edit, test, fix bugs, explain code)
- specialize in documents, planning, task execution, and expert chat
- use an LLM as the reasoning core
- keep short-term and long-term memory
- search and index knowledge (code and docs), with retrieval / RAG as needed
- understand code structure deeply enough for precise edits and explanations
- run iterative agent loops, with solid orchestration and auditability
- cache aggressively where it matters for cost and latency
- maintain a knowledge graph where it earns its keep
- pilot other agents / channels from one core
- stay secure, measurable, and maintainable over years

## What we need from you
1. Are the docs and planned infra **good enough to call SOTA-bound**, or still early / incomplete?
2. What would you **change or add before we lock Sprint 0**?
3. What gaps, contradictions, or over-claims stand out?
4. What is fine to defer, and what is dangerous to defer?
5. Any blind spots for a harness meant to be both a coding agent and a general specialist?

Review `docs/` (and any related planning material). Judge by **capabilities and outcomes**, not by whether we chose a particular stack or pattern. Cite concrete gaps. Prefer judgment over praise.

---

# Sprint 0 Complement — Ecosystem Parity & Pluggable SOTA
Use this together with the previous Sprint 0 review. Same rules: docs + planned design only; candid; outcomes over stack religion; cite gaps; prefer judgment over praise.

Extra lens
Compare our planned harness against what leading open agent CLIs and methodologies already do well (and where they fail): Claude Code CLI, Grok Builder / Grok Code, Aider, Gemini CLI, OpenCode, OpenHands / SWE-agent, plus methodology kits like SpecKit, BMAD, GSD, and similar open agent frameworks. Ask: what world-class capabilities do those systems prove we still under-specify?

Capabilities to pressure-test (without prescribing our internals)
Flag if docs are weak, silent, or over-claiming on:

Speed & cost

Stable context / prompt-cache behavior so multi-step runs do not re-pay the full prefix
Tight repo maps and compact tool I/O (no dumping whole trees or raw terminals into the window)
Cheap local structure (AST / symbols) before expensive model calls
Model routing: fast/cheap vs strong/expensive only when needed
Compaction, truncation, and re-fetch of oversized outputs
Quality of results

Iterative plan → edit → verify loops with real gates (tests, diagnostics), not vibes
Parallel hypothesis exploration without corrupting the main workspace
Spec / acceptance clarity (methodology kits often win here — do we?)
Roles: planner, coder, reviewer, explainer, doc specialist — without forking the product
Hooks / skills / plugins that improve behavior without rewriting the core
Memory & knowledge

Session memory vs durable project memory vs searchable repo index
Retrieval that is measured (not “we have RAG” as a slogan)
Knowledge linking only where it improves recall or decisions
Control & safety

Deny-first permissions, sandbox perimeter, injectable-content treated as data
Auditable trajectories; replay for debugging cost and failures
Human approval paths that do not invent a second product surface
Plug-and-play evolution (critical)

Clear seams so hot paths can be replaced later without a rewrite — e.g. a fast indexer in Rust, a search service in Go, orchestration / LLM adapters in Python, sidecars for heavy work — if and when measurement justifies it
Contracts that let us swap providers, tools, channels, and memory backends
Extension points (skills, hooks, MCP/tools, peer agents) that cannot widen authority by accident
Local-first now, remote/distributed later, without locking the design to one binary or one language
Extra questions for you
Relative to that ecosystem, where are we ahead, parity, or behind on capabilities that matter for cost × quality?
Which missing capabilities would you add to Sprint 0 docs now so the framework stays evolvable?
Which “SOTA” features from other tools are fashion and should stay deferred?
Does the plan make polyglot / sidecar / swap-out evolution real (via boundaries), or only aspirational prose?
If we succeed, can a team improve indexing, search, orchestration, or model adapters independently without breaking the agent loop?
Still judge by capabilities and outcomes, not by whether we already named a language or pattern. Tell us what to lock, what to rewrite in the docs, and what to consciously skip before Sprint 0 closes.