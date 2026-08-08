#!/usr/bin/env python3
"""Build `internal-medium-01` — the tier-1 suite (Sprint 3.5).

Twelve two-to-three file tasks derived from the playlist/storage modules in
`Aether-D-bench`, which are real code with a real test file rather than a
generated one-liner. Each task carries **one** defect in an otherwise correct
codebase, and every defect requires reading a *second* module to fix: the
caller cannot be repaired without knowing the store's API.

That is the tier's whole purpose. Tier 0's single-line bugs cannot distinguish
"the harness carried the task" from "the model guessed a plausible one-line
change"; these can, because a guess that ignores `storage.py` does not pass.

The manifest is the static, reproducible truth — all twelve, pinned, screened
by the same bidirectional canary as everything else. Run flags downsample it;
the suite itself never changes to suit a run.

    python3 scripts/build_medium_manifest.py
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
import textwrap
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from aether.adapters.sandbox.podman import ContainerSandbox, runtime_available  # noqa: E402
from aether.measurement.evaluator import RealEvaluator  # noqa: E402
from aether.measurement.manifest import (  # noqa: E402
    TaskCandidate,
    assign_splits,
    build_manifest,
    dump_manifest,
    manifest_hash,
    screen_all,
)
from aether.measurement.validity import WorktreeValidityInstrument  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from build_floor_manifest import GIT_ENV, eval_image_digest  # noqa: E402

DEFAULT_WORKDIR = Path.home() / ".cache" / "aether" / "internal_medium"
DEFAULT_OUT = REPO_ROOT / "benchmarks" / "manifests"
TEST_COMMAND = "python3 run_tests.py"

# --------------------------------------------------------------- the base

STORAGE = '''"""Storage layer: cache and persistence for playlists."""


class StorageEngine:
    def __init__(self):
        self._cache = {}

    def set_cache(self, playlist_id, tracks):
        self._cache[playlist_id] = tracks

    def get_cache(self, playlist_id):
        return self._cache.get(playlist_id)

    def clear_cache_for_playlist(self, playlist_id):
        self._cache.pop(playlist_id, None)
'''

SMART_RULES = '''"""Smart rules evaluation engine."""


class SmartRuleEvaluator:
    def refresh_smart_rules(self, playlist_id, tracks):
        """Exclude tracks whose title marks them deleted."""
        return [t for t in tracks if "DELETED" not in t.get("title", "")]
'''

PLAYLIST = '''"""Playlist track management."""

from storage import StorageEngine
from smart_rules import SmartRuleEvaluator


class Playlist:
    def __init__(self, playlist_id, storage: StorageEngine):
        self.playlist_id = playlist_id
        self.storage = storage
        self.tracks = []

    def add_track(self, track):
        if not track.get("id"):
            raise ValueError("Track must have an id")
        self.tracks.append(track)
        self.storage.clear_cache_for_playlist(self.playlist_id)

    def remove_track(self, track_id):
        self.tracks = [t for t in self.tracks if t.get("id") != track_id]
        self.storage.clear_cache_for_playlist(self.playlist_id)

    def reorder_tracks(self, new_order):
        self.tracks = list(new_order)
        self.storage.clear_cache_for_playlist(self.playlist_id)


class SmartPlaylist(Playlist):
    def __init__(self, playlist_id, storage: StorageEngine, evaluator: SmartRuleEvaluator):
        super().__init__(playlist_id, storage)
        self.evaluator = evaluator

    def get_tracks(self):
        return self.evaluator.refresh_smart_rules(self.playlist_id, self.tracks)
'''

BASE = {"storage.py": STORAGE, "smart_rules.py": SMART_RULES, "playlist.py": PLAYLIST}

_HEADER = (
    "import sys\n"
    "from storage import StorageEngine\n"
    "from smart_rules import SmartRuleEvaluator\n"
    "from playlist import Playlist, SmartPlaylist\n\n\n"
    "def main():\n"
)
_FOOTER = (
    "\n\nif __name__ == '__main__':\n"
    "    try:\n"
    "        main()\n"
    "    except AssertionError as exc:\n"
    "        print('FAIL:', exc, file=sys.stderr)\n"
    "        sys.exit(1)\n"
    "    sys.exit(0)\n"
)


def _tests(body: str) -> str:
    """Plain asserts, no pytest: the B3 evaluation image is python-slim plus
    git, and a task that needs a pip install is a task whose environment is not
    pinned."""
    dedented = textwrap.dedent(body).strip()
    indented = "\n".join(f"    {line}" if line.strip() else "" for line in dedented.splitlines())
    return _HEADER + indented + _FOOTER


#: (shape, {file: broken source}, test body). Everything not named here is the
#: correct base, so each task is one defect in otherwise working code.
VARIANTS: list[tuple[str, dict[str, str], str]] = [
    (
        "cache_clear_add",
        {
            "playlist.py": PLAYLIST.replace(
                "        self.tracks.append(track)\n"
                "        self.storage.clear_cache_for_playlist(self.playlist_id)",
                "        self.tracks.append(track)",
            )
        },
        """
        storage = StorageEngine()
        storage.set_cache("p1", [{"id": "t1"}])
        pl = Playlist("p1", storage)
        pl.add_track({"id": "t2", "title": "Song"})
        assert storage.get_cache("p1") is None, "cache not cleared after add_track"
        """,
    ),
    (
        "cache_clear_remove",
        {
            "playlist.py": PLAYLIST.replace(
                '        self.tracks = [t for t in self.tracks if t.get("id") != track_id]\n'
                "        self.storage.clear_cache_for_playlist(self.playlist_id)",
                '        self.tracks = [t for t in self.tracks if t.get("id") != track_id]',
            )
        },
        """
        storage = StorageEngine()
        pl = Playlist("p1", storage)
        pl.add_track({"id": "t1"})
        storage.set_cache("p1", [{"id": "t1"}])
        pl.remove_track("t1")
        assert storage.get_cache("p1") is None, "cache not cleared after remove_track"
        assert pl.tracks == []
        """,
    ),
    (
        "cache_clear_reorder",
        {
            "playlist.py": PLAYLIST.replace(
                "        self.tracks = list(new_order)\n"
                "        self.storage.clear_cache_for_playlist(self.playlist_id)",
                "        self.tracks = list(new_order)",
            )
        },
        """
        storage = StorageEngine()
        pl = Playlist("p1", storage)
        pl.add_track({"id": "a"})
        pl.add_track({"id": "b"})
        storage.set_cache("p1", [{"id": "a"}])
        pl.reorder_tracks([{"id": "b"}, {"id": "a"}])
        assert storage.get_cache("p1") is None, "cache not cleared after reorder_tracks"
        assert [t["id"] for t in pl.tracks] == ["b", "a"]
        """,
    ),
    (
        "smart_refresh",
        {
            "playlist.py": PLAYLIST.replace(
                "        return self.evaluator.refresh_smart_rules(self.playlist_id, self.tracks)",
                "        return self.tracks",
            )
        },
        """
        spl = SmartPlaylist("sp1", StorageEngine(), SmartRuleEvaluator())
        spl.add_track({"id": "t1", "title": "Good Song"})
        spl.add_track({"id": "t2", "title": "DELETED Track"})
        titles = [t["title"] for t in spl.get_tracks()]
        assert "DELETED Track" not in titles, "smart rules were not applied"
        assert "Good Song" in titles
        """,
    ),
    (
        "missing_validation",
        {
            "playlist.py": PLAYLIST.replace(
                '        if not track.get("id"):\n            raise ValueError("Track must have an id")\n',
                "",
            )
        },
        """
        pl = Playlist("p1", StorageEngine())
        try:
            pl.add_track({"title": "no id here"})
        except ValueError:
            pass
        else:
            raise AssertionError("add_track accepted a track with no id")
        pl.add_track({"id": "t1"})
        assert len(pl.tracks) == 1
        """,
    ),
    (
        "remove_by_wrong_key",
        {"playlist.py": PLAYLIST.replace('if t.get("id") != track_id', 'if t.get("title") != track_id')},
        """
        pl = Playlist("p1", StorageEngine())
        pl.add_track({"id": "t1", "title": "Keep"})
        pl.add_track({"id": "t2", "title": "Drop"})
        pl.remove_track("t2")
        assert [t["id"] for t in pl.tracks] == ["t1"], "remove_track matched the wrong field"
        """,
    ),
    (
        "rule_filter_inverted",
        {
            "smart_rules.py": SMART_RULES.replace(
                'return [t for t in tracks if "DELETED" not in t.get("title", "")]',
                'return [t for t in tracks if "DELETED" in t.get("title", "")]',
            )
        },
        """
        spl = SmartPlaylist("sp1", StorageEngine(), SmartRuleEvaluator())
        spl.add_track({"id": "t1", "title": "Good Song"})
        spl.add_track({"id": "t2", "title": "DELETED Track"})
        titles = [t["title"] for t in spl.get_tracks()]
        assert titles == ["Good Song"], f"filter kept the wrong tracks: {titles}"
        """,
    ),
    (
        "reorder_appends",
        {"playlist.py": PLAYLIST.replace("self.tracks = list(new_order)", "self.tracks.extend(new_order)")},
        """
        pl = Playlist("p1", StorageEngine())
        pl.add_track({"id": "a"})
        pl.add_track({"id": "b"})
        pl.reorder_tracks([{"id": "b"}, {"id": "a"}])
        ids = [t["id"] for t in pl.tracks]
        assert ids == ["b", "a"], f"reorder appended instead of replacing: {ids}"
        """,
    ),
    (
        "clear_scope",
        {
            "storage.py": STORAGE.replace(
                "        self._cache.pop(playlist_id, None)", "        self._cache.clear()"
            )
        },
        """
        storage = StorageEngine()
        storage.set_cache("p1", ["a"])
        storage.set_cache("p2", ["b"])
        storage.clear_cache_for_playlist("p1")
        assert storage.get_cache("p1") is None
        assert storage.get_cache("p2") == ["b"], "clearing one playlist wiped the whole cache"
        """,
    ),
    (
        "unencapsulated_store",
        {
            "storage.py": '''"""Storage layer: cache and persistence for playlists."""


class StorageEngine:
    def __init__(self):
        self.raw_db_cache = {}

    def get_raw_cache(self):
        return self.raw_db_cache

    def clear_cache_for_playlist(self, playlist_id):
        if playlist_id in self.raw_db_cache:
            del self.raw_db_cache[playlist_id]
''',
            "playlist.py": PLAYLIST.replace(
                "        self.storage.clear_cache_for_playlist(self.playlist_id)\n\n    def remove_track",
                "        if self.playlist_id in self.storage.raw_db_cache:\n"
                "            del self.storage.raw_db_cache[self.playlist_id]\n\n    def remove_track",
            ),
        },
        """
        storage = StorageEngine()
        storage.set_cache("p1", [{"id": "t1"}])
        assert storage.get_cache("p1") == [{"id": "t1"}]
        assert not hasattr(storage, "raw_db_cache"), "the raw cache is still public"
        pl = Playlist("p1", storage)
        pl.add_track({"id": "t2"})
        assert storage.get_cache("p1") is None
        """,
    ),
    (
        "get_cache_raises_on_missing",
        {
            "storage.py": STORAGE.replace(
                "return self._cache.get(playlist_id)", "return self._cache[playlist_id]"
            )
        },
        """
        storage = StorageEngine()
        assert storage.get_cache("never-set") is None, "get_cache raised instead of returning None"
        storage.set_cache("p1", ["x"])
        assert storage.get_cache("p1") == ["x"]
        """,
    ),
    (
        "smart_refresh_wrong_args",
        {
            "playlist.py": PLAYLIST.replace(
                "return self.evaluator.refresh_smart_rules(self.playlist_id, self.tracks)",
                "return self.evaluator.refresh_smart_rules(self.tracks)",
            )
        },
        """
        spl = SmartPlaylist("sp1", StorageEngine(), SmartRuleEvaluator())
        spl.add_track({"id": "t1", "title": "Good Song"})
        tracks = spl.get_tracks()
        assert [t["title"] for t in tracks] == ["Good Song"]
        """,
    ),
]


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=GIT_ENV
    ).stdout


def generate_task(workdir: Path, index: int) -> TaskCandidate:
    shape, broken, test_body = VARIANTS[index % len(VARIANTS)]
    instance_id = f"medium__{shape}-{index:03d}"
    repo = workdir / instance_id

    if not (repo / ".git").is_dir():
        repo.mkdir(parents=True, exist_ok=True)
        _git("init", "-q", "-b", "main", cwd=repo)
        for name, source in BASE.items():
            (repo / name).write_text(broken.get(name, source))
        (repo / "run_tests.py").write_text(_tests(test_body))
        (repo / "README.md").write_text(
            f"# {instance_id}\n\nA playlist library: `storage.py`, `smart_rules.py`, "
            f"`playlist.py`. One of them is wrong.\n"
        )
        _git("add", ".", cwd=repo)
        _git("commit", "-q", "-m", f"{instance_id}: base", cwd=repo)

    base_commit = _git("rev-parse", "HEAD", cwd=repo).strip()

    # Gold patch = restore every mutated file to the correct base.
    for name in broken:
        (repo / name).write_text(BASE[name])
    gold_patch = _git("diff", cwd=repo)
    for name in broken:
        _git("checkout", "--", name, cwd=repo)

    return TaskCandidate(
        instance_id=instance_id,
        repo=f"internal/{shape}",
        base_commit=base_commit,
        environment_image_digest="",
        test_command=TEST_COMMAND,
        gold_patch=gold_patch,
        split="dev",
    )


async def build(args: argparse.Namespace, workdir: Path, out_dir: Path) -> int:
    sandbox = None
    digest = "sha256:" + "0" * 64
    if not args.uncontained:
        if not runtime_available(args.runtime):
            print(f"{args.runtime} not on PATH; use --uncontained", file=sys.stderr)
            return 2
        resolved = eval_image_digest(args.runtime)
        if resolved is None:
            print("aether/eval:build missing; run scripts/build_eval_image.py", file=sys.stderr)
            return 2
        digest = resolved
        sandbox = ContainerSandbox(args.runtime)

    candidates = [
        generate_task(workdir, i).model_copy(update={"environment_image_digest": digest})
        for i in range(args.n)
    ]
    print(f"generated {len(candidates)} tasks in {workdir}\nscreening…")

    verdicts = []
    for candidate in candidates:
        instrument = WorktreeValidityInstrument(
            repo_path=str(workdir / candidate.instance_id),
            worktrees_root=str(workdir / "_worktrees"),
            evaluator=RealEvaluator(
                str(workdir / "_worktrees"),
                resolve_command=lambda spec: TEST_COMMAND,
                sandbox=sandbox,
            ),
            timeout_ms=args.timeout_ms,
        )
        verdict = (await screen_all([candidate], instrument))[0]
        verdicts.append(verdict)
        print(
            f"  {'admit ' if verdict.admitted else 'EXCLUDE'} {candidate.instance_id:34}"
            f" ({verdict.reason or 'gold passes, empty fails'})"
        )

    admitted = [v.instance_id for v in verdicts if v.admitted]
    splits = assign_splits(admitted, seed=args.split_seed)
    candidates = [
        c.model_copy(update={"split": splits[c.instance_id]}) if c.instance_id in splits else c
        for c in candidates
    ]

    manifest = build_manifest(
        manifest_id=args.manifest_id,
        suite="internal",
        candidates=candidates,
        verdicts=verdicts,
        instrument_contained=sandbox is not None,
        instrument_runtime=args.runtime if sandbox is not None else None,
        instrument_image_digest=digest if sandbox is not None else None,
        created_at=datetime.now(UTC),
    )
    out_path = out_dir / f"{args.manifest_id}.yaml"
    out_path.write_text(dump_manifest(manifest), encoding="utf-8")
    print(f"\nadmitted {len(manifest['tasks'])}, excluded {len(manifest['validity_gate']['exclusions'])}")
    print(f"manifest: {out_path}\nhash:     {manifest_hash(manifest)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=len(VARIANTS))
    parser.add_argument("--manifest-id", default="internal-medium-01")
    parser.add_argument("--workdir", default=str(DEFAULT_WORKDIR))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--runtime", default="docker", choices=["podman", "docker"])
    parser.add_argument("--uncontained", action="store_true")
    parser.add_argument("--timeout-ms", type=int, default=120_000)
    parser.add_argument("--split-seed", type=int, default=7)
    args = parser.parse_args(argv)
    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    return asyncio.run(build(args, workdir, out_dir))


if __name__ == "__main__":
    raise SystemExit(main())
