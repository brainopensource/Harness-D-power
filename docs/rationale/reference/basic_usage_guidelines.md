---
status: rationale
retrieval: excluded
---
# 📖 SAGIHA Basic Usage Guidelines & SOTA Challenge Prompting

This reference guide provides standard usage patterns, prompt engineering best practices, and a production-ready template for executing autonomous coding tasks with **SAGIHA** with maximum quality, token efficiency, and reliable verification.

---

## 1. SAGIHA Execution Pipeline

SAGIHA operates as an autonomous coding microkernel:

1. **Workspace Scoping (`-w / --workspace`):** Keeps all file edits, script creations, and test runs strictly isolated inside the specified target directory.
2. **Model Mode (`-m / --mode`):**
   - `replay`: Replays deterministic cassettes (`.sagiha/cassettes/default.json`).
   - `live`: Connects to live LLMs via local Ollama (`qwen2.5-coder:7b`) or remote OpenRouter / OpenAI compatible APIs.
   - `record`: Executes live calls and records a cassette.
3. **Acceptance Criteria (`-a / --acceptance`):** Passes shell verification commands (e.g. `pytest app3`) that MUST pass before the `GateEvaluator` will admit the candidate (`admitted=True`).
4. **Trajectory Store (`.sagiha/trajectories.db`):** Records every step, tool authorization grant, diff hunk, and event log in an immutable SQLite database.

---

## 2. Standard CLI Usage Examples

### A. Run a Simple 1-Shot Script Task with Acceptance Gate
```bash
uv run sagiha run "Create sum_odd.py with a function sum_odd_numbers(numbers) returning the sum of odd numbers, and test_sum_odd.py using pytest." \
  --workspace ./app \
  --acceptance "pytest ./app" \
  --mode live \
  --model-name qwen2.5-coder:7b \
  --max-steps 5
```

### B. Run a Complex Task with OpenRouter & Strict Test Gate
```bash
OPENROUTER_API_KEY=$(grep OPENROUTER_API_KEY .env | cut -d= -f2) uv run sagiha run \
  "Create calculator.py supporting add, subtract, multiply, divide with error handling, and test_calculator.py. Ensure all tests pass." \
  --workspace ./app \
  --acceptance "pytest ./app/test_calculator.py" \
  --mode live \
  --model-name deepseek/deepseek-chat \
  --base-url https://openrouter.ai/api/v1 \
  --max-steps 10
```

### C. Verify Deterministic Cassette Replay
```bash
uv run sagiha replay verify --verify --cassette tests/fixtures/replay_smoke/cassette.json --workspace tests/fixtures/replay_smoke/workspace
```

---

## 3. Core Lessons & Anti-Pattern Prevention

When instructing SAGIHA or AI Agents running SAGIHA, avoid these critical failure modes:

### ⚠️ Anti-Pattern 1: Omitting `--acceptance` (False Positive Gate Admission)
- **Problem:** Omitting `--acceptance` causes SAGIHA to default to `["true"]`. `/bin/true` always exits 0, resulting in `admitted=True` even if generated code is broken, empty, or un-parseable.
- **Fix:** **ALWAYS** specify explicit acceptance checks (e.g., `--acceptance "pytest app3"` or `--acceptance "python3 app3/script.py"`).

### ⚠️ Anti-Pattern 2: Omitting Test Suite Requirements in Prompt Goal
- **Problem:** Prompting only *"Create script.py"* results in 0 unit tests. Without tests, regression detection is impossible on complex codebases.
- **Fix:** **ALWAYS** include test creation in the goal prompt (e.g., *"Create script.py and test_script.py using pytest"*).

### ⚠️ Anti-Pattern 3: Escaped Newline Literals (`\n` String Bug)
- **Problem:** Some LLMs output raw `\n` text literals instead of actual newline bytes in `apply_edit` JSON payloads. If the file starts with `#`, Python treats the entire 1-line file as a comment, rendering it non-executable.
- **Fix:** Enforce test-suite execution in `--acceptance`. If `python3` or `pytest` runs against a single-line commented file, the test execution will fail immediately and force the agent to fix the formatting in step 2.

---

## 4. SOTA Prompt Engineering Principles for Token Efficiency & Quality

To minimize token usage and maximize code quality:

1. **Be File-Path Explicit:** Specify exact relative file paths in the prompt (e.g., `"Create app3/script.py and app3/test_script.py"`). This prevents the agent from wasting LLM turns on directory discovery (`list_dir` or `mkdir`).
2. **Require Self-Verification:** Instruct the agent in the system/goal prompt to run its test suite using `run_command` before completing its turn.
3. **Absolute Workspace Paths:** Always resolve workspace paths (`str(Path(workspace).resolve())`) to prevent policy boundary denials (`Path escapes workspace root`).
4. **Tool-Capable Models:** For remote execution via OpenRouter, use models with native tool calling support (e.g., `deepseek/deepseek-chat` or `qwen2.5-coder:7b`).

---

## 5. Production Prompt Template for AI Agents

Use this prompt template when instructing an AI agent to run and evaluate custom coding challenges using SAGIHA:

```markdown
You are an AI Developer testing the SAGIHA Autonomous Coding Harness on a custom coding challenge.

Follow these steps precisely:

1. **Inspect Harness Capabilities:**
   - Read `docs/STATUS.md` and `src/sagiha/cli.py` to understand available options.
   - Run `uv run sagiha run --help` to see CLI options (`--workspace`, `--acceptance`, `--mode`, `--model-name`, `--max-steps`).

2. **Define the Challenge with Mandatory Tests:**
   - Create a clean target workspace directory (e.g. `./challenge_workspace`).
   - Formulate a precise goal requesting BOTH implementation and test files (e.g. "Create string_utils.py module with reverse_string and is_palindrome functions, and test_string_utils.py using pytest").
   - Define strict shell acceptance criteria (e.g. `-a "pytest challenge_workspace/test_string_utils.py"`).

3. **Execute SAGIHA Task:**
   - Run the task via SAGIHA CLI with explicit acceptance gates:
     ```bash
     uv run sagiha run "<YOUR_CHALLENGE_GOAL>" \
       --workspace ./challenge_workspace \
       --acceptance "pytest ./challenge_workspace" \
       --mode live \
       --model-name deepseek/deepseek-chat \
       --base-url https://openrouter.ai/api/v1 \
       --max-steps 10
     ```

4. **Inspect Trajectory & Gate Admission:**
   - Query the trajectory database (`.sagiha/trajectories.db`) or inspect the run output:
     - Check `run_id`, `steps`, and `admitted` status (`True` / `False`).
     - Verify event sequence (`run.started` -> `step.started` -> `tool.call_authorized` -> `gate.evaluated`).

5. **Verify & Report Results:**
   - Confirm generated files exist in `./challenge_workspace` and contain valid multiline code.
   - Execute the test suite directly in shell to confirm 100% pass rate.
   - Provide a score from 0 to 10 based on correctness, clean code structure, test coverage, and gate admission.
```

