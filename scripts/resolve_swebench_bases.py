#!/usr/bin/env python3
"""Resolve upstream repository base commits for benchmark manifests (TASK-010, Blocker B1).

Usage:
    python scripts/resolve_swebench_bases.py --suite swe-ver
    python scripts/resolve_swebench_bases.py --suite swe-pro
    python scripts/resolve_swebench_bases.py --suite swe-ver --dry-run
    python scripts/resolve_swebench_bases.py --manifest docs/benchmarks/swe_verified_sample.md
"""

import sys
from pathlib import Path

# Add src/ to python path so aether module is importable
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))

from aether.measurement.repo_cache import main

if __name__ == "__main__":
    raise SystemExit(main())
