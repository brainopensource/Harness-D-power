#!/usr/bin/env python3
"""Scan SWE-agent repository to categorize core harness code, docs, and bloat."""

import json
import os
from pathlib import Path

SWE_AGENT_DIR = Path(__file__).resolve().parent.parent / "src" / "swe-agent"


def scan_repo() -> None:
    if not SWE_AGENT_DIR.exists():
        print(f"Directory {SWE_AGENT_DIR} does not exist yet.")
        return

    all_files = list(SWE_AGENT_DIR.rglob("*"))
    files = [f for f in all_files if f.is_file() and not any(part.startswith(".") for part in f.relative_to(SWE_AGENT_DIR).parts)]

    keep_harness: list[str] = []
    keep_docs: list[str] = []
    remove_bloat: list[str] = []

    for f in sorted(files):
        rel = str(f.relative_to(SWE_AGENT_DIR))
        # Documentation & specs
        if rel.endswith(".md") or rel.startswith("docs/") or rel.startswith("docs"):
            keep_docs.append(rel)
        # Core agent harness code
        elif rel.startswith("sweagent/agent") or rel.startswith("sweagent/environment") or rel.startswith("sweagent/tools"):
            keep_harness.append(rel)
        elif rel.startswith("sweagent/api") or rel.startswith("sweagent/run"):
            keep_harness.append(rel)
        # Bloat to remove: web, tests, benchmarks, github workflows, dockerfiles, assets, configs
        else:
            remove_bloat.append(rel)

    print("\n=======================================================")
    print("        SWE-AGENT REPOSITORY SCAN & BRIEFING")
    print(f"        Path: {SWE_AGENT_DIR}")
    print("=======================================================\n")

    print(f"Total Files Scanned: {len(files)}")
    print(f"  - Core Agent Harness Code (KEEP)   : {len(keep_harness)} files")
    print(f"  - Documentation & Specs (KEEP)      : {len(keep_docs)} files")
    print(f"  - Bloat / Tests / Web UI (TO REMOVE): {len(remove_bloat)} files")

    print("\n--- 1. CORE HARNESS CODE (TO KEEP) ---")
    for item in keep_harness[:25]:
        print(f"  [KEEP] {item}")
    if len(keep_harness) > 25:
        print(f"  ... and {len(keep_harness) - 25} more core files")

    print("\n--- 2. DOCUMENTATION & SPECS (TO KEEP) ---")
    for item in keep_docs[:20]:
        print(f"  [KEEP] {item}")
    if len(keep_docs) > 20:
        print(f"  ... and {len(keep_docs) - 20} more docs")

    print("\n--- 3. BLOAT & UNRELATED FILES (TO REMOVE) ---")
    for item in remove_bloat[:30]:
        print(f"  [REMOVE] {item}")
    if len(remove_bloat) > 30:
        print(f"  ... and {len(remove_bloat) - 30} more bloat files")


if __name__ == "__main__":
    scan_repo()
