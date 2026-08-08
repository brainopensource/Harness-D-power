#!/usr/bin/env python3
"""Build the B3 evaluation image and print its **digest** (TASK-016).

The tag exists only so the build has somewhere to land. What the evaluator is
handed is the `sha256:` image ID this script resolves — `containers/eval/`
documents why: a tag is a mutable pointer, and an evaluation whose environment
can be re-pointed under it is not reproducible (measurement.md §6).

Usage:
    python3 scripts/build_eval_image.py                 # podman, build + print digest
    python3 scripts/build_eval_image.py --runtime docker
    python3 scripts/build_eval_image.py --digest-only   # resolve an already-built image
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTAINERFILE = REPO_ROOT / "containers" / "eval" / "Containerfile"
DEFAULT_TAG = "aether/eval:build"


def build(runtime: str, tag: str) -> int:
    cmd = [runtime, "build", "-t", tag, "-f", str(CONTAINERFILE), str(CONTAINERFILE.parent)]
    print("$", " ".join(cmd), file=sys.stderr)
    return subprocess.run(cmd).returncode


def resolve_digest(runtime: str, tag: str) -> str | None:
    result = subprocess.run(
        [runtime, "image", "inspect", "-f", "{{.Id}}", tag], capture_output=True, text=True
    )
    if result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        return None
    digest = result.stdout.strip()
    # Podman prints a bare hex id; Docker prints `sha256:<hex>`.
    if digest and not digest.startswith("sha256:"):
        digest = f"sha256:{digest}"
    return digest or None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", default="podman", choices=["podman", "docker"])
    parser.add_argument("--tag", default=DEFAULT_TAG)
    parser.add_argument("--digest-only", action="store_true")
    args = parser.parse_args(argv)

    if shutil.which(args.runtime) is None:
        print(f"{args.runtime} is not on PATH", file=sys.stderr)
        return 2

    if not args.digest_only and build(args.runtime, args.tag) != 0:
        return 1

    digest = resolve_digest(args.runtime, args.tag)
    if digest is None:
        return 1
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
