#!/usr/bin/env python3
"""Reproduce ADR-0003 rev. 2's published power table (TASK-012).

The derived-N rule rests on that table, so the table has to be checkable, not
cited. Run this and diff the two columns:

    .venv/bin/python scripts/verify_power_table.py

Takes a couple of minutes at the ADR's own 20,000 iterations. The fast pinned
subset lives in tests/aether/measurement/test_statistics.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aether.measurement.statistics import simulate_power  # noqa: E402

# ADR-0003 rev. 2, "What rev. 2 corrects": α = 0.05, 20,000 iterations, seed 7,
# against a true +10-point lift.
PUBLISHED = {
    ("clean", 0.12, 0.02): {50: 0.32, 100: 0.73, 200: 0.97, 300: 1.00},
    ("noisy", 0.20, 0.10): {50: 0.18, 100: 0.38, 200: 0.70, 300: 0.88},
    ("very noisy", 0.30, 0.20): {50: 0.12, 100: 0.25, 200: 0.48, 300: 0.66},
}


def main() -> int:
    print(f"{'discordance':16} {'N':>5} {'simulated':>10} {'ADR-0003':>9} {'':>6}")
    worst = 0.0
    for (label, p01, p10), row in PUBLISHED.items():
        for n, published in row.items():
            simulated = simulate_power(
                n, p01=p01, p10=p10, effect=0.10, alpha=0.05, iterations=20_000, seed=7
            )
            delta = abs(simulated - published)
            worst = max(worst, delta)
            print(
                f"{label + f' ({p01}/{p10})':16} {n:5d} {simulated:10.2f} {published:9.2f} "
                f"{'ok' if delta <= 0.005 else 'DRIFT':>6}"
            )
    print(f"\nlargest deviation: {worst:.4f}")
    return 0 if worst <= 0.005 else 1


if __name__ == "__main__":
    raise SystemExit(main())
