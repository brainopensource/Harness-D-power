---
status: rationale
retrieval: excluded
updated: 2026-07-30
---
# **SAGIHA Frontend — Tech Stack**

Every choice below is made against one constraint: **the mocked phase and the backend-integrated phase
must be the same codebase**, differing only in which transport adapter is bound. That rules out
throwaway prototyping stacks (a Streamlit demo, a static Figma-to-code export) even though they'd be
faster to stand up — they'd be rebuilt, not extended, the day a real event stream exists.

## **Monorepo & Language**

**TypeScript, everywhere, in a single pnpm + Turborepo monorepo.**

| Alternative | Why not |
| :--- | :--- |
| Go (Bubble Tea) for CLI, TS for GUI | Two languages means the domain model (`RunContext`, `ToolCall`, event union) is defined and hand-synced twice. Every event-shape change in the backend becomes two PRs in the frontend instead of one. It also means CLI and GUI can't share a mock-data engine, a fixtures package, or design tokens without a translation layer. |
| Rust (Ratatui) for CLI | Same duplication problem, plus a smaller ecosystem of the specific widgets this UI needs (streaming diff render, animated timeline). Rust's strengths (memory safety, raw perf) aren't the bottleneck for a TUI that renders event streams at human-readable rates. |
| Python (Textual) for CLI, matching backend language | Tempting for language parity with the backend, but the backend explicitly treats every cockpit as a client over a language-agnostic stream ([Entry Points](../../02-architecture/entry-points-and-piloting.md): SSE/ndjson over the wire). Coupling the CLI's language to the backend's re-creates exactly the coupling this plan exists to avoid, and forecloses the GUI sharing any code with it. |

One language lets `@sagiha/protocol` (the typed event/domain model), `@sagiha/mock-engine` (the fake
run generator), and `@sagiha/ui` (design tokens + primitives) be genuine shared packages, not parallel
implementations that drift.

**Package manager: pnpm** (workspaces, strict node_modules, fast, disk-efficient — the default for
TS monorepos in 2026). **Build orchestration: Turborepo** (task caching and dependency-graph-aware
builds across the packages below; the alternative, Nx, is heavier and its plugin model is unneeded
here).

## **CLI — Ink (React for the terminal)**

**Chosen: [Ink](https://github.com/vadimdemedes/ink) + React 18 + TypeScript, over Bubble Tea (Go)
and Textual (Python).**

Why Ink specifically:

* **Same component model as the GUI.** Both cockpits render the same event stream through components
  that think in props/state/effects. An engineer who builds the approval-gate component for the GUI
  can port the interaction logic to the CLI's equivalent without relearning a paradigm (Bubble Tea's
  Elm-style `Update`/`Msg` loop, for instance, is a genuinely different mental model).
* **Shares the domain-model package.** `@sagiha/protocol` types (the TS mirror of `RunContext`,
  `Event`, `Decision`, etc.) and `@sagiha/mock-engine` import directly into both `apps/cli` and
  `apps/gui` with no FFI or serialization boundary between them.
* **Mature terminal-UI ecosystem for exactly this shape of problem**: `ink-spinner`, `ink-table`,
  `ink-gradient`/`ink-big-text` for a startup banner, `ink-testing-library` for component tests, and
  community packages for scrollable lists and syntax-highlighted code blocks (paired with `cli-highlight`
  or a Shiki-in-terminal renderer for diffs).
* **Full-color, animated terminal output is a solved problem in this ecosystem** via `chalk` (v5,
  ESM) for styling and `cli-spinners` / custom Ink hooks for the "agent is thinking" and streaming-token
  states — meeting the "great use of color/hierarchy/animation" bar without hand-rolling ANSI escape
  handling.

Why not Bubble Tea: excellent framework, best-in-class for a pure-Go binary, but it forces the
second-language duplication problem above and the team gets nothing back for it — there is no
performance requirement here that Node/Ink can't meet at human-perceptible terminal frame rates (this
is not a game loop).

Why not Textual: ties the CLI's implementation language to the backend's, which is precisely the
coupling [Entry Points](../../02-architecture/entry-points-and-piloting.md) designs against — cockpits
are clients over a stream, and the reference client should prove that boundary holds by being able to
live in a different repo or language entirely. It also can't share code with the GUI.

**Supporting CLI libraries:**

| Concern | Library | Notes |
| :--- | :--- | :--- |
| Argument parsing / subcommands | `commander` or `@commander-js` (or `citty` if we want a lighter, TS-first parser) | Mirrors the target `sagiha run` / `sagiha replay` / `sagiha trajectory show` surface from [Entry Points](../../02-architecture/entry-points-and-piloting.md), against mock handlers. |
| Terminal rendering | `ink` v5, `react` v18 | Ink v5 targets React 18's concurrent-safe reconciler. |
| Styling | `chalk` v5 | ESM-only; color/dim/bold hierarchy for the design system in [`ui-ux-guidelines.md`](./ui-ux-guidelines.md). |
| Diff rendering | `diff` (compute) + a Shiki-based or `cli-highlight`-based terminal syntax highlighter | Same diff data shape the GUI's Monaco/CodeMirror diff view consumes — see [`architecture.md`](./architecture.md). |
| Tables/lists | `ink-table`, custom `ink` scroll components | Tool-call timeline, trajectory step list. |
| Testing | `ink-testing-library`, `vitest` | Snapshot the rendered frame tree for key states (approval pending, diff shown, run failed). |
| Packaging | `tsup` → single Node ESM bundle, or `pkg`/`nexe` later for a dependency-free binary | `tsup` is enough for local dev and internal distribution during the mocked phase; native binary packaging is a [`roadmap.md`](./roadmap.md) item. |

## **GUI — Tauri + React + TypeScript**

**Chosen: [Tauri](https://tauri.app) v2 (Rust shell) + React 18 + TypeScript + Vite, over Electron and
over a web-only SPA.**

| Alternative | Why not |
| :--- | :--- |
| Electron | Ships a full Chromium + Node runtime per app (~150-250MB), has materially higher idle memory (~100MB+ vs Tauri's ~10-30MB baseline), and every IPC boundary is a bespoke `ipcMain`/`ipcRenderer` contract. For a tool whose entire value proposition is "watch an agent work with low-latency streaming," a heavier idle footprint and slower cold start work directly against the product. |
| Web-only SPA (no desktop shell) | Loses local process affinity (spawning/monitoring a local `sagiha` process once the real backend lands is in scope per [`roadmap.md`](./roadmap.md)), OS-native notifications for `ApprovalRequested` while the window isn't focused, and a persistent local cache/keychain for run history without standing up a backend service just to serve static assets. A desktop shell is the right default for a dev tool that needs to run a local agent. |
| Tauri + Svelte | A reasonable second choice — smaller runtime footprint than React, genuinely fast. Rejected only for **ecosystem and team-leverage reasons**: React lets `apps/gui` share not just types but actual component logic and testing patterns with the wider TS/React ecosystem this team already knows from Ink, and gives access to mature libraries for the two hardest GUI surfaces here — virtualized long lists (`@tanstack/react-virtual`) and diff/code rendering (Monaco or CodeMirror 6, both React-friendly via maintained wrapper packages). Svelte's equivalents exist but are thinner. |

Why Tauri specifically, beyond "not Electron": a Rust shell gives a real, low-overhead path to future
backend integration — the Rust side can eventually own the local process supervision of a real `sagiha`
subprocess and stream its stdout/SSE into the webview over Tauri's IPC, without a Node runtime in
between. That is exactly the seam [`roadmap.md`](./roadmap.md) plans to use.

**Core GUI libraries:**

| Concern | Library | Notes |
| :--- | :--- | :--- |
| App shell | `@tauri-apps/api` v2, Rust `tauri` crate | Desktop shell, window management, native notifications for `approval.requested`. |
| UI framework | `react` 18, `react-dom` 18 | Concurrent rendering matters for a high-frequency `model.delta` stream — see [`architecture.md`](./architecture.md) on scheduling. |
| Build tool | `vite` 5 | Native ESM dev server, instant HMR — non-negotiable for iterating on animation/interaction feel. |
| Language | `typescript` 5.x, strict mode | Shared `tsconfig.base.json` across all packages. |
| Styling | Tailwind CSS v4 + CSS variables for theming | Utility-first for velocity, CSS variables for the light/dark token system in [`ui-ux-guidelines.md`](./ui-ux-guidelines.md). No CSS-in-JS runtime cost. |
| Component primitives | Radix UI (unstyled, accessible) | Dialog (approval modal), Tabs, Tooltip, ScrollArea, Collapsible — accessibility (focus trap, ARIA, keyboard nav) built in rather than reimplemented. Styled with Tailwind, not a pre-themed component kit (avoids the "generic admin template" look explicitly ruled out). |
| State management | Zustand (client/UI state) + TanStack Query-style cache pattern for run/event data (backed by the mock engine, not HTTP, during this phase) | See [`architecture.md`](./architecture.md) for the state boundary between "UI state" and "trajectory/event state." Avoids Redux's boilerplate; avoids plain Context for anything high-frequency (`model.delta` deltas would over-render Context consumers). |
| Animation | Framer Motion | Timeline entrance/exit, approval modal transitions, streaming-token cursor — the "great use of animation" bar, with layout animations that don't require hand-tuned CSS keyframes. |
| Diff viewer | `@monaco-editor/react` (Monaco) as default; `@uiw/react-codemirror` (CodeMirror 6) as the lighter alternative if Monaco's bundle size proves an issue in Tauri's webview | Monaco gives VS Code-grade diff rendering (inline/side-by-side, minimap, syntax highlighting for every language the backend's toolchain touches) with minimal integration work. |
| Virtualized lists | `@tanstack/react-virtual` | Tool-call timeline and log pane must stay smooth at thousands of trajectory steps. |
| Terminal/log rendering | `xterm.js` (`@xterm/xterm`) for the raw command-output pane (mirrors `command.executed` payloads) | Gives real ANSI rendering for `CommandResult.stdout`/`stderr` instead of a plain `<pre>`. |
| Icons | `lucide-react` | Consistent, minimal, matches the Linear/Vercel visual language; avoids mixed icon sets. |
| Testing | `vitest` + `@testing-library/react` for units; `@tauri-apps/cli`'s dev harness + Playwright (via `tauri-driver`) for e2e smoke of the packaged app | |

## **Shared Packages**

| Package | Purpose | Key deps |
| :--- | :--- | :--- |
| `@sagiha/protocol` | Hand-maintained TS mirror of the backend's Pydantic domain models (`domain/control.py`, `domain/work.py`, `domain/content.py`, `domain/trajectory.py`) and the full `Event` union from `domain/events.py`. Zod schemas for runtime validation of mock fixtures (and, later, real wire payloads). | `zod` |
| `@sagiha/mock-engine` | Deterministic, seedable fake run generator: given a scenario name, emits a scripted or randomized sequence of `@sagiha/protocol` events on a timer, simulating streaming latency. This is the thing that gets deleted (or demoted to a dev/test fixture) when the real transport lands. | none beyond `@sagiha/protocol` |
| `@sagiha/ui` | Design tokens (color, spacing, type scale, motion durations) as CSS variables + a TS token export for Ink's `chalk` color mapping; shared, framework-agnostic where possible, React components where not (GUI only — Ink components live in `apps/cli`). | `tailwindcss`, `class-variance-authority` |
| `@sagiha/config` | Shared `tsconfig`, `eslint`, `prettier`/`biome` configs. | `typescript-eslint` or `biome` |

## **Tooling Baseline**

* **Linting/formatting: Biome.** Single fast tool for lint + format across the whole monorepo,
  replacing the ESLint+Prettier combo — fewer config files, one config surface, materially faster on a
  monorepo this size. (If the team already standardizes on ESLint/Prettier elsewhere in the org, that's
  an acceptable substitution; the reasoning is speed and config-count, not a hard dependency on Biome
  specifically.)
* **Type checking:** `tsc --noEmit` per package, run through Turborepo's task graph so only affected
  packages re-check.
* **Testing:** `vitest` (unit/component) everywhere; Playwright for GUI e2e; `ink-testing-library` for
  CLI component snapshots.
* **Git hooks:** `lefthook` (or `husky`) running `biome check` + `tsc` on staged files pre-commit.
* **Versioning/changelog (once packages are actually published/distributed):** `changesets` — deferred
  until [`roadmap.md`](./roadmap.md)'s packaging milestone; not needed while everything lives in one
  monorepo with no external consumers.
* **CI:** GitHub Actions, Turborepo remote caching optional but recommended once build times grow.

## **Versions to Pin at Scaffold Time**

Exact patch versions should be pinned by `pnpm add` at scaffold time (this doc will drift from
`package.json` the moment it's written), but majors are fixed here as the compatibility baseline:
Node 22 LTS, TypeScript 5.6+, React 18.3+, Ink 5, Tauri 2, Vite 5, Tailwind 4, Zustand 4.
