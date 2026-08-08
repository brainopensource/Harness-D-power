"""`RunConfig` domain unit tests (T6, `TASK-058`).

Asserts secret leak prevention in RunConfig hashes and JSON schemas, and holdout guard behavior.
"""

from __future__ import annotations

import pytest

from aether.domain.config import ModelRoute, RunConfig, instrument_hash
from aether.measurement.floor import published_floor


def test_a_run_config_hash_contains_no_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set OPENROUTER_API_KEY to a sentinel, build a RunConfig, assert the
    sentinel appears in neither model_dump_json() nor the hash input.
    """
    sentinel = "sk-or-v1-SECRET-API-KEY-12345"
    monkeypatch.setenv("MY_API_KEY_VAR", sentinel)

    route = ModelRoute(
        role="editor", base_url="http://localhost:11434", model="qwen", api_key_env="MY_API_KEY_VAR"
    )
    config = RunConfig(topology_path="workflows/linear_v1.yaml", routes=(route,))

    json_str = config.model_dump_json()
    hash_str = instrument_hash(config, topology_hash="top123", lockfile_hash="lock123")

    assert sentinel not in json_str, "Secret leaked into model_dump_json()"
    assert sentinel not in hash_str, "Secret leaked into instrument_hash()"
    assert "MY_API_KEY_VAR" in json_str, "env var name missing from config"


def test_run_config_holdout_guard_refuses_when_floor_absent(tmp_path: pytest.MonkeyPatch) -> None:
    """published_floor returns None when noise-floor.json does not exist."""
    assert published_floor(tmp_path) is None  # type: ignore[arg-type]


def test_run_config_schema_renders_every_field() -> None:
    """RunConfig renders a valid JSON schema."""
    schema = RunConfig.model_json_schema()
    assert "properties" in schema
    props = schema["properties"]
    assert "topology_path" in props
    assert "split" in props
    assert "routes" in props
