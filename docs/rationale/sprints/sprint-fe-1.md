---
status: rationale
retrieval: excluded
---
# **Sprint FE-1: Monorepo Scaffold**

> **Status**: done
> **Source**: [Frontend Roadmap — Phase 0](../frontend/roadmap.md#phase-0--scaffold)
> **Target**: an installable, lintable, typecheckable, testable monorepo with empty apps and empty
> shared packages. No feature code. This sprint exists so every later sprint is additive.
> **Reads first**: [`docs/frontend/tech-stack.md`](../frontend/tech-stack.md),
> [`docs/frontend/architecture.md`](../frontend/architecture.md).

---

## A. Workspace setup

- [ ] **1.** Initialize pnpm workspace at repo root (or under a `frontend/` subtree if the team wants
  the Python backend and TS frontend cleanly separated at the top level — pick one and record the
  choice in this file's header before proceeding).
  - [ ] `pnpm-workspace.yaml` listing `apps/*` and `packages/*`.
  - [ ] Root `package.json` with `turbo` as a devDependency, `packageManager` pinned.
- [ ] **2.** `turbo.json` with pipeline tasks: `build`, `dev`, `lint`, `typecheck`, `test` — each
  declaring correct `dependsOn` (`build` depends on `^build`, etc.) so Turborepo's cache is
  meaningful from day one, not bolted on later.
- [ ] **3.** `packages/config`: shared `tsconfig.base.json` (strict mode on), Biome config
  (`biome.json`) covering lint + format for the whole tree.

## B. Empty shared packages

- [ ] **4.** `packages/protocol` — package.json, tsconfig extending base, empty `src/index.ts`,
  `zod` dependency declared. No types yet.
- [ ] **5.** `packages/mock-engine` — package.json depending on `@sagiha/protocol` (workspace
  protocol), empty `src/index.ts`.
- [ ] **6.** `packages/ui` — package.json, Tailwind v4 configured, empty `tokens.css` and
  `tokens.ts` files (content lands in FE-1 item 8, not this item — this item is wiring only).

## C. Empty apps

- [ ] **7.** `apps/cli` — Ink + React + TypeScript scaffold, `commander`-based entry (`src/cli.tsx`)
  that only supports `sagiha-mock --version` and `sagiha-mock --help`. Bundled via `tsup`.
- [ ] **8.** `apps/gui` — Tauri v2 + React + Vite scaffold via `pnpm create tauri-app`, default
  template pared down to a blank window rendering "SAGIHA" — no feature code. Rust toolchain
  requirement documented in the app's own README.

## D. Design tokens (content, not just wiring)

- [ ] **9.** Populate `packages/ui/tokens.css` and `tokens.ts` from the full token table in
  [`ui-ux-guidelines.md`](../frontend/ui-ux-guidelines.md) (semantic colors, light+dark, spacing
  scale, type scale, motion durations). No components consume them yet — this sprint just makes the
  tokens exist and be importable, and is the natural place to catch token-table mistakes before
  three sprints of components depend on them.
  - [ ] A tiny throwaway HTML/Storybook-less swatch page (`packages/ui/tokens.preview.html`, not
    shipped) to eyeball light/dark contrast before moving on — delete or keep as a dev aid, team's
    call.

## E. CI

- [ ] **10.** GitHub Actions workflow (new file, does not touch the existing Python `ci.yml`) running
  `pnpm install --frozen-lockfile`, `pnpm turbo lint typecheck test build` on push/PR to any
  `apps/**`, `packages/**`, or the new workflow file itself (path-filtered so backend-only PRs don't
  pay for a frontend CI run and vice versa).

---

## ✅ Exit test

`pnpm install && pnpm turbo build lint typecheck test` succeeds from a clean clone. `apps/cli`
responds to `--version`/`--help`. `apps/gui` opens a window showing "SAGIHA" in both light and dark
OS theme. CI is green on a PR touching only `packages/ui/tokens.css`.

## 🚫 Non-goals

Any `EventSource`/`RunClient` code (FE-2). Any real component beyond the blank shell. Any mock
scenario content. Any design token consumer.

## ⛓️ Dependency

None — this is the first frontend sprint. Can start immediately; does not block on backend work.
