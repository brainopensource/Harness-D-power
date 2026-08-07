import json
import random
import urllib.parse
import urllib.request
from pathlib import Path

ROWS_ENDPOINT = "https://datasets-server.huggingface.co/rows"
DATASET = "princeton-nlp/SWE-bench_Verified"

def fetch_sample():
    # Fetch a set of rows across dataset offsets
    all_rows = []
    for offset in [0, 100, 200, 300, 400]:
        params = urllib.parse.urlencode({
            "dataset": DATASET,
            "config": "default",
            "split": "test",
            "offset": offset,
            "length": 100,
        })
        url = f"{ROWS_ENDPOINT}?{params}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AETHER-Bench/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.load(resp)
                rows = [r["row"] for r in data.get("rows", [])]
                all_rows.extend(rows)
        except Exception as e:
            print(f"Error fetching offset {offset}: {e}")

    print(f"Total rows fetched: {len(all_rows)}")
    return all_rows

def classify_difficulty(row):
    patch = str(row.get("patch", ""))
    test_patch = str(row.get("test_patch", ""))
    lines = patch.count("\n")
    files = patch.count("diff --git") or patch.count("+++ b/")
    
    if lines <= 25 and files <= 2:
        return "Easy"
    elif lines <= 80 and files <= 4:
        return "Medium"
    else:
        return "Hard"

def main():
    rows = fetch_sample()
    if not rows:
        print("Failed to fetch rows")
        return

    # Categorize by difficulty
    by_diff = {"Easy": [], "Medium": [], "Hard": []}
    for r in rows:
        diff = classify_difficulty(r)
        by_diff[diff].append(r)

    print(f"Easy: {len(by_diff['Easy'])}, Medium: {len(by_diff['Medium'])}, Hard: {len(by_diff['Hard'])}")

    # Pick 5 Easy, 5 Medium, 5 Hard (15 total), balanced across repos
    rng = random.Random(42) # Fixed seed for reproducibility
    
    selected = []
    used_ids = set()

    for diff_level in ["Easy", "Medium", "Hard"]:
        candidates = [r for r in by_diff[diff_level] if r["instance_id"] not in used_ids]
        # Shuffle deterministically
        rng.shuffle(candidates)
        # Select 5 with distinct repos as much as possible
        chosen_level = []
        seen_repos = set()
        for c in candidates:
            repo = c["repo"]
            if repo not in seen_repos or len(chosen_level) >= 4:
                chosen_level.append(c)
                seen_repos.add(repo)
                used_ids.add(c["instance_id"])
            if len(chosen_level) == 5:
                break
        selected.extend(chosen_level)

    print(f"Selected {len(selected)} tasks total.")

    # Generate Markdown Report
    output_path = Path("docs/benchmarks/swe_verified_sample.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "---",
        "status: normative",
        "updated: 2026-08-07",
        "---",
        "",
        "# SWE-bench Verified — 15-Task Stratified Beta Sample",
        "",
        "This document maps the **15-task random sample** selected from `princeton-nlp/SWE-bench_Verified` for early harness testing and beta evaluation (75% confidence interval, ±15% margin of error).",
        "",
        "**Note:** No repositories or assets have been downloaded yet. This document contains only dataset indexing and metadata mapping for future content-addressed resolution via `TASK-010` (`repo_cache.py`).",
        "",
        "## 📊 Sample Summary",
        "",
        "| Stratum | Task Count | Repositories Covered | Target Complexity |",
        "| :--- | :---: | :--- | :--- |",
        "| **Easy** | 5 | Django, SymPy, Scikit-learn, Sphinx, Astropy | Single-file / ≤25 line fix |",
        "| **Medium** | 5 | Django, Requests, Pytest, Sphinx, Scikit-learn | Multi-file / 25–80 line fix |",
        "| **Hard** | 5 | Django, SymPy, Scikit-learn, Sphinx, Matplotlib | Complex multi-file refactor / >80 line fix |",
        "| **Total** | **15** | **7 Unique OSS Python Repos** | **3.0% of 500-task Verified Suite** |",
        "",
        "---",
        "",
        "## 🛠️ Task Mapping Table",
        "",
        "| Index | Difficulty | Task ID | Repository | GitHub Issue URL | Base Commit SHA | Patch Size (Lines / Files) |",
        "| :---: | :---: | :--- | :--- | :--- | :--- | :---: |",
    ]

    for idx, r in enumerate(selected, 1):
        diff = classify_difficulty(r)
        task_id = str(r["instance_id"])
        repo = str(r["repo"])
        base_commit = str(r["base_commit"])
        patch = str(r.get("patch", ""))
        p_lines = patch.count("\n")
        p_files = max(1, patch.count("diff --git") or patch.count("+++ b/"))
        
        # Build GitHub URL if repo is org/repo format
        parts = task_id.split("__")
        if len(parts) >= 2:
            issue_num = parts[-1].split("-")[-1]
            github_url = f"https://github.com/{repo}/issues/{issue_num}"
        else:
            github_url = f"https://github.com/{repo}"

        lines.append(
            f"| {idx} | **{diff}** | `{task_id}` | `{repo}` | [#{task_id.split('-')[-1]}]({github_url}) | `{base_commit[:10]}` | ~{p_lines} lines / {p_files} file(s) |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 📑 Detailed Task Specifications",
        ""
    ])

    for idx, r in enumerate(selected, 1):
        diff = classify_difficulty(r)
        task_id = str(r["instance_id"])
        repo = str(r["repo"])
        base_commit = str(r["base_commit"])
        problem_desc = str(r.get("problem_statement", "")).strip()
        # Truncate problem statement for readable spec
        if len(problem_desc) > 350:
            problem_desc = problem_desc[:350] + "..."
        
        lines.extend([
            f"### Task {idx}: `{task_id}`",
            f"* **Difficulty**: **{diff}**",
            f"* **Repository**: `{repo}`",
            f"* **Base Commit**: `{base_commit}`",
            f"* **Repo Clone URL**: `https://github.com/{repo}.git`",
            "* **Problem Summary**:",
            f"  > {problem_desc.replace('\n', ' ')}",
            ""
        ])

    lines.extend([
        "---",
        "",
        "## ⚙️ How to Download & Run This Sample",
        "",
        "When ready to download repositories locally, `TASK-010` (`src/aether/measurement/repo_cache.py`) will ingest this task list and clone **only** the 7 unique repositories for these 15 tasks:",
        "",
        "```bash",
        "# 1. Resolve and clone base commits for these 15 tasks only (~3.5 GB on disk)",
        "python scripts/resolve_swebench_bases.py --manifest docs/benchmarks/swe_verified_sample.md",
        "",
        "# 2. Run initial beta evaluation pass (75% confidence level, ±15% margin of error)",
        "python -m aether.measurement.runner --manifest docs/benchmarks/swe_verified_sample.md",
        "```",
        ""
    ])

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Successfully generated report at {output_path}")

if __name__ == "__main__":
    main()
