---
status: rationale
updated: 2026-08-01
retrieval: excluded
---
> [!NOTE]
> **LLM / AI AGENT NOTICE**: This file is a historical rationale, research reference, or benchmark log (`retrieval: excluded`). It is excluded from active search indexing and context retrieval. Do not cite this file as normative status or active code contracts.


# SOTA Autonomous AI Coding Agents, Harness Infrastructure & Benchmark Report

## 1. Executive Summary & Industry Landscape

This document serves as the authoritative architectural and benchmark reference for **SAGIHA / AETHER**, documenting state-of-the-art (SOTA) open-source and commercial autonomous coding agent harnesses, LLM model combinations, execution runtimes, and benchmark evaluation results.

Evaluating autonomous software engineering systems requires distinguishing between:
1. **The Underlying LLM Engine** (e.g., Claude Opus 5, Claude Sonnet 5, DeepSeek V4 Pro, Grok 4.5, Kimi K3, GPT-5.5, Gemini 3.5 Flash).
2. **The Harness / Scaffolding Infrastructure** (context engines, AST graph tools, sandboxed execution, capability policy engines, and test-driven evaluation gates).

Empirical benchmark data demonstrates that **harness infrastructure accounts for a 30% to 40%+ difference in resolution rates** on identical LLM models.

---

## 2. 2026 Frontier LLM + Agent Harness Benchmark Leaderboards

### 2.1. Hardest Real-World GitHub Benchmark: **SWE-bench Pro**

> *SWE-bench Pro measures multi-file GitHub issue resolution on active, non-contaminated 2026 repositories.*

| Rank | LLM Model | Agent Harness / Tool | SWE-bench Pro (% Resolved) | SWE-bench Verified (% Resolved) | Architecture & Deployment Notes |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **1** | **Claude Opus 5** | **Claude Code CLI** | **79.2%** | **92.4%** | Anthropic flagship model + autonomous terminal CLI loop. |
| **2** | **Claude Opus 4.8** | **Claude Code CLI** | **69.2%** | **88.6%** | High reasoning effort, multi-file refactoring engine. |
| **3** | **Grok 4.5** | **xAI Agent Harness** | **64.7%** | **84.0%** | xAI flagship model, high token efficiency & fast inference. |
| **4** | **Claude Sonnet 5** | **Claude Code CLI / Cursor** | **63.2%** | **82.5%** | Balanced speed/cost frontier model for daily engineering. |
| **5** | **DeepSeek V4 (Pro)** | **OpenHands / mini-SWE-agent** | **55.4%** | **80.6%** | Top open-weights frontier model; native MoE architecture. |
| **6** | **Gemini 3.5 Flash** | **Antigravity CLI (`agy`)** | **55.1%** | **78.5%** | Google's sub-second flash model with 2M+ token context. |
| **7** | **Claude Sonnet 4.5 / 4.6**| **Aider / OpenHands** | **48.0%** | **75.4% – 77.2%** | Reliable workhorse for git diff editing & pair programming. |

---

### 2.2. Terminal Autonomy Benchmark: **Terminal-Bench 2.1**

> *Terminal-Bench 2.1 evaluates multi-step shell command execution, environment configuration, debugging, and terminal tool usage.*

| Rank | Agent Harness / Tool | LLM Model Combo | Terminal-Bench 2.1 Score | Tool License | Primary Focus |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **1** | **Codex CLI** | **GPT-5.5** (OpenAI) | **83.4%** | Commercial | Terminal automation & shell execution. |
| **2** | **Open Agent / Hermes** | **Kimi K3** (Moonshot AI - 2.8T) | **80.9%** | Open Source | Open-weights 2.8T parameter reasoning model. |
| **3** | **Claude Code CLI** | **Claude Opus 4.8 / Opus 5** | **78.9%** | Commercial | Deep terminal autonomy, background jobs, git. |
| **4** | **OpenHands Agent** | **GPT-5.5** | **76.4%** | Open Source (MIT) | EventStream containerized sidecar runtime. |
| **5** | **Antigravity CLI (`agy`)** | **Gemini 3.5 Flash** | **76.2%** | Commercial (Google) | High-speed Go-binary CLI with 2M context. |
| **6** | **Aider** | **Claude Sonnet 5 / DeepSeek V4** | **74.8%** | Open Source (Apache) | Git-native tree-sitter diff generator. |

---

## 3. Commercial vs. Open-Source Tools & Harnesses: Deep Dive

### 3.1. Commercial / Paid Tools

#### A. Claude Code CLI (Anthropic)
* **LLM Engine:** Claude Opus 5, Opus 4.8, Sonnet 5.
* **Architecture:** Terminal-native agent built with background bash execution, compact context compression, and automatic multi-file test-driven repair loops.
* **Pros:** Top-tier reasoning (79.2% SWE-bench Pro); handles deep multi-file refactoring; excellent error recovery.
* **Cons:** Closed-source; locked to Anthropic models; high API token cost for long runs.
* **When & How to Use:** Use for complex, multi-file feature implementations or refactoring tasks where accuracy is paramount and cost is secondary.

#### B. Antigravity CLI (`agy`) / Gemini CLI (Google)
* **LLM Engine:** Gemini 3.5 Flash, Gemini 3.1 Pro.
* **Architecture:** Compiled Go binary providing sub-second CLI command dispatch and 2M+ token context ingestion.
* **Pros:** Extreme speed; 2M token context window; strong Terminal-Bench score (76.2%).
* **Cons:** Closed-source binary; proprietary Google infrastructure.
* **When & How to Use:** Use for large-codebase exploration, log parsing, or rapid terminal command automation where massive context windows are required.

#### C. Cursor (Composer) (Anysphere / xAI)
* **LLM Engine:** Claude Sonnet 5, GPT-5.5, Custom C++ Indexer.
* **Architecture:** Custom VS Code fork featuring Merkle-tree codebase indexing, shadow worktrees for candidate edits, and multi-file specifier generation.
* **Pros:** Unmatched interactive IDE user experience; fast inline diff reviews; real-time autocomplete.
* **Cons:** Closed-source; IDE-dependent (not headless CLI); higher subscription costs.
* **When & How to Use:** Use during active, interactive pair-programming sessions where human developer oversight is continuous.

---

### 3.2. Open-Source Tools & Harnesses

#### A. OpenHands (Formerly OpenDevin)
* **Repository:** [`All-Hands-AI/OpenHands`](https://github.com/All-Hands-AI/OpenHands) (MIT)
* **LLM Engine:** Model-agnostic (Claude 3.7/5, DeepSeek V4, GPT-5.5, Kimi K3).
* **Architecture:** Decoupled EventStream architecture emitting typed `Action` and `Observation` events, with isolated Docker container sidecar execution.
* **Pros:** Highly extensible; active open-source community; top open-source SWE-bench Verified score (72.0%+).
* **Cons:** Resource-heavy container orchestration; complex setup for local dev environments.
* **When & How to Use:** Use when building custom autonomous developer agents or server-side background coding runners requiring complete Docker isolation.

#### B. mini-SWE-agent & SWE-agent (Princeton / Stanford)
* **Repository:** [`princeton-nlp/mini-swe-agent`](https://github.com/princeton-nlp/mini-swe-agent) (MIT)
* **LLM Engine:** Model-agnostic (OpenAI o3-mini, DeepSeek V4, Claude Sonnet 4.5).
* **Architecture:** `mini-SWE-agent` provides a minimal 100-line Python execution loop; original `SWE-agent` provides an Agent-Computer Interface (ACI) with custom file-viewing tools.
* **Pros:** Industry-standard evaluation baseline; zero architectural bloat; light footprint.
* **Cons:** Lacks multi-file candidate tree exploration or long-horizon mission scheduling.
* **When & How to Use:** Use for benchmarking LLMs or implementing bare-bones ReAct execution loops.

#### C. Aider
* **Repository:** [`aider-chat/aider`](https://github.com/aider-chat/aider) (Apache 2.0)
* **LLM Engine:** Model-agnostic (Claude Sonnet 5, DeepSeek R1/V4, GPT-5.5).
* **Architecture:** Uses Tree-sitter AST repository maps to inject minimal code headers into prompts, paired with a unified git diff parser and automatic commit manager.
* **Pros:** Unmatched token efficiency; fast pass@1 performance; clean git commit history output.
* **Cons:** Designed for human-in-the-loop pair programming rather than fully autonomous multi-day background runs.
* **When & How to Use:** Use for terminal-native pair-programming or fast feature additions on existing git repositories.

#### D. AutoCodeRover (National University of Singapore)
* **Repository:** [`nus-apr/auto-code-rover`](https://github.com/nus-apr/auto-code-rover) (MIT)
* **LLM Engine:** Claude Sonnet 3.5 / 4.5.
* **Architecture:** Combines Tree-sitter AST symbol resolution with Spectrum-Based Fault Localization (SBFL) to locate suspicious methods before prompting the LLM.
* **Pros:** Highly targeted context retrieval; avoids sending whole files into prompt.
* **Cons:** Requires existing test suites; struggles on open-ended feature creation without tests.
* **When & How to Use:** Use for automated bug-fixing on projects with high test coverage.

#### E. Agentless (UIUC / NUS)
* **Repository:** [`OpenAutoCoder/Agentless`](https://github.com/OpenAutoCoder/Agentless) (MIT)
* **LLM Engine:** GPT-4o, Claude Sonnet 3.5/4.5.
* **Architecture:** Replaces ReAct loops with a 3-step pipeline: **Hierarchical Localization $\rightarrow$ Candidate Patch Generation $\rightarrow$ Regression Validation**.
* **Pros:** 1/10th the cost of ReAct agents; zero risk of infinite loops; high accuracy on fixed-bug benchmarks.
* **Cons:** Cannot perform interactive terminal commands or multi-step environment setup.
* **When & How to Use:** Use for high-volume, low-cost bug repair pipelines in CI/CD.

#### G. Hermes Agent (Nous Research)
* **Repository:** [`NousResearch/hermes-agent`](https://github.com/NousResearch/hermes-agent) / [`hermes-agent-self-evolution`](https://github.com/NousResearch/hermes-agent-self-evolution) (Apache 2.0 / MIT)
* **LLM Engine:** Kimi K3 (2.8T), Hermes 3 (Llama-based), DeepSeek R1/V4.
* **Architecture:** Persistent cross-session memory graph, experience-based skill creation loop, DSPy/GEPA prompt evolution, multi-platform support (CLI, Discord, Slack, Paperclip adapter).
* **Pros:** #2 on Terminal-Bench 2.1 (80.9%); open-source autonomous self-evolution loop; skill compilation from execution traces.
* **Cons:** Requires fine-tuning / DSPy setup for self-evolution loops; higher setup complexity.
* **When & How to Use:** Use as a primary reference for experience-based skill creation, persistent long-term memory, and self-improving prompt evolution.

#### H. Goose (Block / Linux Foundation)
* **Repository:** [`block/goose`](https://github.com/block/goose) (Apache 2.0)
* **LLM Engine:** Model-agnostic via Model Context Protocol (MCP).
* **Architecture:** Native MCP client driver supporting stdio and HTTP tool sidecars.
* **Pros:** Native MCP tool integration; strong desktop and CLI UX.
* **Cons:** Lacks rootless container sandbox boundaries out of the box.
* **When & How to Use:** Use as a template for building MCP client drivers and extensible tool engines.

---

## 4. Key Takeaways & Blueprint for SAGIHA Harness Engineering

1. **Adopt Open-Weights Models for Cost & Privacy**:
   - Models like **Kimi K3 (2.8T)** and **DeepSeek V4 Pro** score **>80%** on Terminal-Bench and SWE-bench Verified.
   - *SAGIHA Implementation:* Ensure SAGIHA's model adapter layer supports local vLLM / Ollama backends alongside Anthropic/OpenAI APIs.

2. **Benchmark against SWE-bench Pro**:
   - SWE-bench Verified has reached saturation (top models at 88%–92%).
   - *SAGIHA Implementation:* Use **SWE-bench Pro** tasks in Sprint `v2-S7a` and `v2-S10` evaluation suites to ensure honest, un-contaminated evaluation.

3. **Hybrid Architectural Blueprint**:
   - **Context Layer:** Combine Aider's **Tree-sitter repo maps** with Agentless's **hierarchical localization**.
   - **Kernel Layer:** Implement OpenHands' **typed EventStream** with SAGIHA's **CAR Capability Policy Engine**.
   - **Perimeter Security:** Use rootless Podman execution (`ContainerSandbox`) with egress CONNECT proxy allowlists.
   - **System 3 Conductor:** Use `FrozenRunState` process hibernation to support multi-day missions across host reboots.

---

## 5. Master Comparative Leaderboard: Coding Agent Harness + LLM Combinations

*Organized strictly by Benchmark Suite, listing ONLY explicit **(Coding Agent Harness + LLM Model)** combinations.*

### 5.1. Benchmark: **SWE-bench Pro** (Real-World 2026 GitHub Repositories)

> *Evaluates multi-file GitHub issue resolution on active, non-contaminated 2026 repositories.*

| Rank | Coding Agent Harness | LLM Model | SWE-bench Pro Score (% Resolved) | Harness Category | Notes & Specialization |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **1** | **Claude Code CLI** | **Claude Opus 5** | **79.2%** | Commercial | Terminal CLI + auto test-repair loop |
| **2** | **Claude Code CLI** | **Claude Opus 4.8** | **69.2%** | Commercial | Deep multi-file reasoning engine |
| **3** | **xAI Agent Harness** | **Grok 4.5** | **64.7%** | Commercial | xAI native evaluation harness |
| **4** | **Claude Code CLI / Cursor** | **Claude Sonnet 5** | **63.2%** | Commercial | Balanced daily engineering harness |
| **5** | **OpenHands** | **DeepSeek V4 Pro** | **55.4%** | Open Source | EventStream + Docker container sidecar |
| **6** | **Antigravity CLI (`agy`)** | **Gemini 3.5 Flash** | **55.1%** | Commercial | Go binary CLI + 2M token context |
| **7** | **OpenHands / Aider** | **Claude Sonnet 4.5** | **48.0%** | Open Source | Tree-sitter repo map + git diff parser |

---

### 5.2. Benchmark: **SWE-bench Verified** (500 Human-Validated GitHub Tasks)

> *Human-verified subset measuring Python bug resolution across popular open-source repos.*

| Rank | Coding Agent Harness | LLM Model | SWE-bench Verified Score | Harness Category | Notes & Specialization |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **1** | **Claude Code CLI** | **Claude Opus 5** | **92.4%** | Commercial | Top tier benchmark score |
| **2** | **Claude Code CLI** | **Claude Opus 4.8** | **88.6%** | Commercial | Anthropic official CLI loop |
| **3** | **xAI Agent Harness** | **Grok 4.5** | **84.0%** | Commercial | xAI agent scaffold |
| **4** | **Claude Code CLI** | **Claude Sonnet 5** | **82.5%** | Commercial | High-speed Sonnet harness |
| **5** | **OpenHands / mini-SWE-agent**| **DeepSeek V4 Pro** | **80.6%** | Open Source | Open-weights MoE reasoning harness |
| **6** | **Antigravity CLI (`agy`)** | **Gemini 3.5 Flash** | **78.5%** | Commercial | Google Antigravity Go-CLI |
| **7** | **Claude Code CLI** | **Claude Sonnet 4.5** | **77.2%** | Commercial | Anthropic Sonnet baseline |
| **8** | **OpenHands** | **Claude Sonnet 4.5** | **72.0%+** | Open Source | All-Hands AI containerized agent |
| **9** | **mini-SWE-agent** | **OpenAI o3-mini (high)** | **71.7%** | Open Source | Princeton 100-line minimal scaffold |
| **10** | **Aider** | **Claude Sonnet 5 / 4.5** | **70.0%** | Open Source | Tree-sitter git diff pair programmer |
| **11** | **AutoCodeRover** | **Claude Sonnet 3.5** | **52.0%** | Open Source | AST symbol graph + SBFL fault localization |
| **12** | **Agentless** | **GPT-4o** | **45.0%** | Open Source | 3-step non-agentic repair pipeline |

---

### 5.3. Benchmark: **Terminal-Bench 2.1** (Multi-Step Shell & Terminal Autonomy)

> *Evaluates shell command execution, environment configuration, debugging, and CLI tool usage.*

| Rank | Coding Agent Harness | LLM Model | Terminal-Bench 2.1 Score | Harness Category | Notes & Specialization |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **1** | **Codex CLI** | **GPT-5.5** | **83.4%** | Commercial | OpenAI terminal automation CLI |
| **2** | **Open Agent / Hermes** | **Kimi K3** (Moonshot 2.8T) | **80.9%** | Open Source | Open-weights 2.8T reasoning agent |
| **3** | **Claude Code CLI** | **Claude Opus 4.8 / 5** | **78.9%** | Commercial | Anthropic background bash CLI |
| **4** | **OpenHands Agent** | **GPT-5.5** | **76.4%** | Open Source | Open-source Docker sidecar agent |
| **5** | **Antigravity CLI (`agy`)** | **Gemini 3.5 Flash** | **76.2%** | Commercial | Sub-second Go CLI agent |
| **6** | **Aider** | **Claude Sonnet 5 / DeepSeek V4**| **74.8%** | Open Source | Terminal git diff assistant |

---

### 5.4. Benchmark: **HumanEval / HumanEval-XL** (Function-Level Code Generation)

> *Evaluates single-function synthesis, docstring completion, and unit-test pass@1 efficiency.*

| Rank | Coding Agent Harness | LLM Model | HumanEval Score (% Pass@1) | Harness Category | Notes & Specialization |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **1** | **Aider (Architect Mode)** | **Claude Opus 5** | **94.8%** | Open Source | Dual-model architect + editor pattern |
| **2** | **Claude Code CLI** | **Claude Opus 4.8** | **93.2%** | Commercial | Syntax-checked ReAct loop |
| **3** | **mini-SWE-agent** | **OpenAI o3-mini (high)** | **92.0%** | Open Source | Function-level generation loop |
| **4** | **OpenHands** | **DeepSeek R1 / V4** | **90.5%** | Open Source | Multi-turn reasoning agent |
| **5** | **Aider** | **Claude Sonnet 4.5 / 5** | **89.4%** | Open Source | Single-shot diff editor |
