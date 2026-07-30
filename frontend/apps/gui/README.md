# @sagiha/gui

Tauri v2 + React + Vite desktop cockpit for SAGIHA's mocked phase. See
`docs/frontend/architecture.md` and `docs/sprints/sprint-fe-1.md` onward for scope.

## Requirements

- Node 22+, pnpm (via `corepack enable`)
- Rust toolchain (stable) + Cargo — required to build/run the Tauri shell. Tauri's own
  [prerequisites](https://tauri.app/start/prerequisites/) list any OS-level webview/dev
  dependencies (e.g. `libwebkit2gtk` on Linux).

## Dev

```sh
pnpm --filter @sagiha/gui tauri dev
```

As of FE-1 this opens a blank window rendering "SAGIHA" in both light and dark OS theme —
no feature code, no `RunClient` wiring (that starts in FE-2).
