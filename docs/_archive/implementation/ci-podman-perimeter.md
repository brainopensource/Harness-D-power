---
status: rationale
updated: 2026-08-01
retrieval: excluded
---
# CI Podman Perimeter Job (TCB — human-authored)

`.github/workflows/ci.yml` is Trusted Computing Base — `AGENTS.md` §1, and `ci.yml`'s own
`tcb-check` job lists `.github/workflows` among `TCB_PATHS`. Agents propose this diff; **a human
authors the commit.** This file is the proposal, kept ready to apply.

> **Status: not yet applied.** Audit defect **M-2** stays open until a human commits the job below.
> The eleven `@pytest.mark.podman` tests pass locally (verified 2026-08-01, Podman 5.8.4) and run
> in no CI job. Everything else W8 asked for has landed — see *Already landed* below.

## Already landed (agent-authored, non-TCB)

| Step | Change | Where |
| :--- | :--- | :--- |
| **8.2** | `SAGIHA_REQUIRE_PODMAN=1` turns an absent Podman or a missing image from a **skip** into a hard **failure**. A perimeter test that silently skips is an unenforced perimeter wearing a green checkmark — that is half of M-2 | `tests/podman_support.py` (new); consumed by `tests/integration/test_perimeter_canary.py` and `tests/contracts/test_workspace_conformance.py` |
| **8.3** | The egress canary now asserts the allowlist **permits** an allowlisted host, not only that it denies others. Previously a proxy that denied *everything* — or an allowlist that matched nothing — passed this canary. Asserted against `EgressProxy.allowed`, so the runner needs no real outbound egress | `tests/integration/test_perimeter_canary.py::test_non_allowlisted_egress_denied` |
| **8.4** | `verify.sh` prints Podman presence as a host fact and reports it in the STATUS table footer | `scripts/verify.sh` |

## The job to add

Add a required job alongside `tests`. The main `tests` job must exclude the `podman` mark so
contributors without Podman stay green locally.

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
        # SAGIHA_REQUIRE_PODMAN=1 is the whole point of this job: on a runner
        # that is supposed to have Podman, a skip is a false green (defect M-2).
        # Without it a broken image build reports success having tested nothing.
        env:
          SAGIHA_REQUIRE_PODMAN: "1"
        run: |
          pytest -m podman -v \
            tests/contracts/test_workspace_conformance.py \
            tests/integration/test_perimeter_canary.py

  tests:
    # existing job — add to the pytest invocation:
    #   pytest ... -m "not podman"
```

## Verification before committing

```bash
# The job's own command, locally:
podman build -t sagiha/runtime:latest -f containers/runtime/Containerfile containers/runtime
SAGIHA_REQUIRE_PODMAN=1 uv run pytest -m podman -v      # expect 11 passed

# Prove the gate fails rather than skips when the image is absent:
podman image rm sagiha/runtime:latest
SAGIHA_REQUIRE_PODMAN=1 uv run pytest -m podman -q      # expect FAILED, not skipped
```

## Local

```bash
podman build -t sagiha/runtime:latest -f containers/runtime/Containerfile containers/runtime
uv run pytest -m podman -v
```
