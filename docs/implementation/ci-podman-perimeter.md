---
status: rationale
updated: 2026-07-31
retrieval: excluded
---
# CI Podman Perimeter Job (TCB — human-authored)

`.github/workflows/ci.yml` is Trusted Computing Base. Agents propose this diff; a human
authors the commit.

## Proposed job

Add a required job alongside `tests` that installs Podman, builds `sagiha/runtime:latest`,
and runs `@pytest.mark.podman` suites. The main `tests` job should exclude that mark so
contributors without Podman stay green locally (tests skip when the image is missing).

```yaml
  podman-perimeter:
    name: Podman Perimeter (v2-S5)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Install Podman
        run: |
          sudo apt-get update
          sudo apt-get install -y podman
      - run: pip install uv && uv pip install --system -e ".[dev]"
      - name: Build runtime image
        run: podman build -t sagiha/runtime:latest -f containers/runtime/Containerfile containers/runtime
      - name: Perimeter + Workspace container conformance
        run: pytest -m podman -v tests/contracts/test_workspace_conformance.py tests/integration/test_perimeter_canary.py

  tests:
    # existing job — add to pytest invocation:
    #   pytest ... -m "not podman"
```

## Local

```bash
podman build -t sagiha/runtime:latest -f containers/runtime/Containerfile containers/runtime
uv run pytest -m podman -v
```
