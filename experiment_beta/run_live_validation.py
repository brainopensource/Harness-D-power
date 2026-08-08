#!/usr/bin/env python3
"""Live validation: qwen2.5:1.5b via Ollama, real generations, parsed with
`ImprovedWholeFileCodeblockFormat`, written to real files, and graded by
actually running each task's test.

Independent of src/aether/engine — talks to Ollama directly and reuses only
the harness's system-prompt text (`GenerateStep.build_system_text` +
`EditFormat.instructions()`, read-only imports) so the model sees exactly the
prompt it would see in a real run. This isolates one variable: does the
*parser* fix change the outcome, holding the model and prompt fixed?

Run: uv run python3 experiment_beta/run_live_validation.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from aether.workflow.edit_format import WholeFileCodeblockFormat  # noqa: E402
from aether.workflow.nodes.generate import build_system_text  # noqa: E402
from improved_edit_format import ImprovedWholeFileCodeblockFormat  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
MODEL = "qwen2.5:1.5b"
BASE_URL = "http://127.0.0.1:11434/v1"


@dataclass(frozen=True)
class Task:
    name: str
    entry_file: str
    instructions: str
    test_code: str


TASKS = [
    Task(
        name="is_even",
        entry_file="main.py",
        instructions="Write a function is_even(n: int) -> bool in main.py that returns True if n is even, False otherwise.",
        test_code="import main\nassert main.is_even(4) is True\nassert main.is_even(3) is False\nprint('PASSED')\n",
    ),
    Task(
        name="add",
        entry_file="main.py",
        instructions="Write a function add(a: int, b: int) -> int in main.py that returns a + b.",
        test_code="import main\nassert main.add(2, 3) == 5\nassert main.add(-1, 1) == 0\nprint('PASSED')\n",
    ),
    Task(
        name="reverse_string",
        entry_file="main.py",
        instructions="Write a function reverse_string(s: str) -> str in main.py that returns the string reversed.",
        test_code="import main\nassert main.reverse_string('abc') == 'cba'\nassert main.reverse_string('') == ''\nprint('PASSED')\n",
    ),
]


def call_ollama(system: str, user: str) -> str:
    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
    }
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]


def run_task(task: Task) -> dict[str, object]:
    task_dir = OUTPUT_DIR / task.name
    task_dir.mkdir(parents=True, exist_ok=True)
    entry_path = task_dir / task.entry_file
    entry_path.write_text(f"# TODO: {task.entry_file} -- see task instructions\n", encoding="utf-8")
    (task_dir / "run_tests.py").write_text(task.test_code, encoding="utf-8")

    original_fmt = WholeFileCodeblockFormat()
    system = build_system_text(original_fmt.instructions())
    user = f"{task.instructions}\n\n=== {task.entry_file} ===\n{entry_path.read_text()}\n"

    raw = call_ollama(system, user)

    original_parsed = original_fmt.parse(raw)
    improved_fmt = ImprovedWholeFileCodeblockFormat(
        known_files=(task.entry_file,), test_paths=("run_tests.py",)
    )
    improved_parsed = improved_fmt.parse(raw)

    result: dict[str, object] = {
        "task": task.name,
        "raw_output": raw,
        "original_parsed_files": [f.repo_rel_path for f in original_parsed.files],
        "original_errors": list(original_parsed.errors),
        "improved_parsed_files": [f.repo_rel_path for f in improved_parsed.files],
        "improved_errors": list(improved_parsed.errors),
        "test_passed": False,
        "test_output": "",
    }

    if improved_parsed.files:
        for f in improved_parsed.files:
            (task_dir / f.repo_rel_path).write_text(f.text, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, "run_tests.py"],
            cwd=task_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        result["test_passed"] = proc.returncode == 0 and "PASSED" in proc.stdout
        result["test_output"] = (proc.stdout + proc.stderr).strip()

    return result


def main() -> int:
    print(f"Live validation: {MODEL} @ {BASE_URL}, {len(TASKS)} tasks\n")
    results = []
    for task in TASKS:
        print(f"--- {task.name} ---")
        result = run_task(task)
        results.append(result)
        orig_ok = bool(result["original_parsed_files"])
        imp_ok = bool(result["improved_parsed_files"])
        print(f"  original parser : {'PASS' if orig_ok else 'FAIL'} {result['original_errors'] or ''}")
        print(f"  improved parser : {'PASS' if imp_ok else 'FAIL'} {result['improved_errors'] or ''}")
        print(f"  test result     : {'PASSED' if result['test_passed'] else 'FAILED/NOT RUN'}")
        print()

    original_wins = sum(1 for r in results if r["original_parsed_files"])
    improved_wins = sum(1 for r in results if r["improved_parsed_files"])
    tests_passed = sum(1 for r in results if r["test_passed"])

    print("=" * 60)
    print(f"SUMMARY ({MODEL}, N={len(TASKS)})")
    print(f"  original parser admitted : {original_wins}/{len(TASKS)}")
    print(f"  improved parser admitted : {improved_wins}/{len(TASKS)}")
    print(f"  tests actually passed    : {tests_passed}/{len(TASKS)}")
    print(f"  output written to        : {OUTPUT_DIR}")

    (OUTPUT_DIR / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 0 if tests_passed == len(TASKS) else 1


if __name__ == "__main__":
    sys.exit(main())
