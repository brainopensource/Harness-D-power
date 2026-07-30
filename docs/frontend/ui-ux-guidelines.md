---
status: draft
updated: 2026-07-30
---

# **SAGIHA Frontend — UI/UX Guidelines**

Design bar: Linear's information density without clutter, Warp's terminal-native speed and keyboard
fluency, Vercel dashboard's restraint with color and motion. The failure mode to avoid is generic
admin-template dashboard: card grids of stat tiles, default component-library chrome, decorative icons,
color used for decoration instead of meaning.

## **Design Principles**

1. **Color is a signal, not decoration.** Every non-neutral color maps to a specific meaning (state,
   severity, effect class) defined once in the token system below and used identically in CLI and GUI.
   If a color doesn't map to a defined meaning, it shouldn't be used.
2. **Density with hierarchy, not density with clutter.** A trajectory can have hundreds of steps. The
   default view shows structure (collapsed steps, summarized tool calls) with progressive disclosure
   into detail — never a wall of undifferentiated text, never hidden-by-default detail that requires
   more than one action to reach.
3. **Keyboard-first, mouse-optional, never mouse-only.** Every action reachable via approval buttons,
   tabs, or menus has a keyboard equivalent. The GUI is a superset of the CLI's interaction
   affordances, not a replacement requiring different muscle memory.
4. **Motion communicates state change, not decoration.** Animation exists to answer "what just
   happened" (a new step arrived, an approval resolved, a diff expanded) — never a gratuitous
   entrance animation on static content.
5. **The system never lies about what's real.** A mocked run must not visually claim capabilities the
   real system doesn't have yet (no fake "verified" badges, no invented telemetry). Where the mock
   phase's data is scripted rather than live, internal/dev-mode affordances (scenario picker) are
   visually distinct from the product surface.

## **Design Tokens**

Defined once in `@sagiha/ui` (`tokens.css` for the GUI, a parallel `tokens.ts` chalk-color map for the
CLI) and consumed by both — this is what makes the two cockpits feel like one product.

### Color — Semantic, Not Palette-First

| Token | Meaning | Light | Dark | CLI (chalk) |
| :--- | :--- | :--- | :--- | :--- |
| `--sg-neutral-{0-12}` | Structural grays, 13-step scale | `#ffffff` → `#0a0a0b` | inverted | `white`/`gray`/`black` via 256-color ramp |
| `--sg-accent` | Primary interactive accent (links, active tab, focus ring) | indigo `#4f46e5` | indigo `#818cf8` | `cyan` (terminal-safe substitute) |
| `--sg-success` | `ToolCallCompleted` ok, `GateReport.admitted=true`, `ApprovalResolved(approved=true)` | green `#16a34a` | `#4ade80` | `green` |
| `--sg-warning` | `BudgetWarning`, `requires_human`, degraded/retry | amber `#d97706` | `#fbbf24` | `yellow` |
| `--sg-danger` | `ToolCallFailed`, `ToolCallDenied`, `RunFailed`, `GateReport` criterion failed | red `#dc2626` | `#f87171` | `red` |
| `--sg-info` | Reasoning/streaming text, informational events | blue `#2563eb` | `#60a5fa` | `blue` |
| `--sg-pending` | Awaiting approval, in-flight tool call | violet `#7c3aed` | `#a78bfa` | `magenta` |
| `--sg-effect-pure` | `EffectClass.PURE` badge | neutral | neutral | `dim white` |
| `--sg-effect-idempotent` | `EffectClass.IDEMPOTENT` badge | `--sg-info` | `--sg-info` | `blue` |
| `--sg-effect-destructive` | `EffectClass.DESTRUCTIVE` badge | `--sg-danger` | `--sg-danger` | `red bold` |

No other colors are introduced without extending this table. Both themes are WCAG AA-checked (4.5:1
minimum for body text, 3:1 for large text/icons) — see Accessibility below.

### Typography

* **UI text (GUI):** Inter (variable font) — neutral, high-legibility at small sizes, matches the
  Linear/Vercel reference bar. Fallback stack: `Inter, -apple-system, "Segoe UI", sans-serif`.
* **Monospace (both):** JetBrains Mono for GUI code/diff/log rendering; the CLI inherits the user's
  terminal font (no control over this, by design — never fight the terminal).
* **Type scale (GUI):** 12/14/16/20/24/32px, one weight per size step (400 body, 500 emphasis, 600
  headings) — no more than 3 weights in the whole app.
* **CLI hierarchy without font control:** achieved entirely through `chalk` bold/dim, color, and
  Unicode box-drawing/indentation — the CLI's equivalent of a type scale is a well-defined indent +
  weight + color ladder, specified in `@sagiha/ui/tokens.ts` as named styles (`heading`, `label`,
  `value`, `muted`, `code`).

### Spacing & Layout

* 4px base unit, scale: 4/8/12/16/24/32/48/64.
* GUI primary layout: fixed-width sidebar (never resizable in v1 — resizing is a distraction from the
  actual product), fluid main pane, max content width 1280px centered on ultrawide displays (agent
  output, especially diffs, degrades badly at unconstrained line length).
* CLI layout: full terminal width, minimum supported width 80 columns with graceful reflow; a
  responsive breakpoint at 120 columns unlocks a two-column layout (timeline + detail side by side) —
  below that, single column with drill-in navigation.

### Motion

* Durations: 100ms (micro — hover/focus), 200ms (standard — panel expand/collapse, tab switch), 320ms
  (emphasis — modal/approval gate entrance).
* Easing: `cubic-bezier(0.16, 1, 0.3, 1)` (“ease-out-expo”-ish) for entrances, `ease-in` for exits —
  things arrive with energy, leave quickly, matching Linear's feel.
* Respect `prefers-reduced-motion`: all entrance/exit animation collapses to an opacity crossfade
  ≤80ms; layout-shift animations (reordering) are disabled outright.
* CLI "animation" is spinner/cursor-blink cadence (steady 80ms frame interval for spinners, matching
  `cli-spinners`' `dots` timing) and incremental token rendering — no CLI equivalent of easing curves,
  but cadence consistency matters just as much.

## **Layout Patterns**

### GUI: Run View

```
┌─────────────┬──────────────────────────────────────────────────────────┐
│  Sidebar     │  Run header: goal, autonomy badge, budget meter, status  │
│  (run list,  ├──────────────────────────────────────────────────────────┤
│  history)    │  ┌ Plan/Steps timeline ─┐ ┌ Detail pane ─────────────┐   │
│              │  │ ● step 1  ✓          │ │ Tool call: read_file      │  │
│              │  │ ● step 2  ⋯ running  │ │  args: {path: "..."}      │  │
│              │  │   └ tool: apply_edit │ │  effect: IDEMPOTENT        │ │
│              │  │ ○ step 3  pending    │ │  result / diff view here  │  │
│              │  └───────────────────────┘ └───────────────────────────┘ │
│              ├──────────────────────────────────────────────────────────┤
│              │  Log / raw event stream (collapsible drawer, off by      │
│              │  default; the debug view, not the primary surface)       │
└─────────────┴──────────────────────────────────────────────────────────┘
```

The timeline is the spine of the view — every other pane is "more detail about the selected timeline
item," never a competing primary navigation.

### GUI: Approval Gate

A **non-dismissible-by-accident** modal (Radix `AlertDialog`, not `Dialog` — no click-outside-to-close)
because approving a destructive action by mis-click is the one interaction this product must never
allow. Shows, in this fixed order: the action + `blast_radius` (largest text, colored by severity —
`--sg-danger` for destructive scope, `--sg-warning` otherwise), the `rationale` the policy engine gave,
the specific `scope` paths/tools affected, and only then Approve/Deny buttons — Deny is the visually
lighter action (matches "default to caution"), Approve requires either a click or an explicit `Enter`
keypress with the dialog focused (never a global hotkey that could fire accidentally).

### CLI: Approval Gate

Blocks the line, renders the same information hierarchy as the GUI modal in terminal form, and requires
an explicit `y`/`n` keypress — no bare `Enter` defaults to approve. Under `--autonomy scheduled` (per
[Entry Points](../02-architecture/entry-points-and-piloting.md)), the mock scenario for this state
shows the CLI printing that the approval routed to a notifier instead of blocking, so the UX for
"approval happened somewhere else" is designed, not just the interactive case.

### Diff Viewer (Both)

* Default: **unified view** with syntax highlighting, matching the target user's likely terminal
  workflow habits (`git diff` mental model). Side-by-side is a toggle, not the default, in the GUI.
* Hunk-level status badges (`ok` / `anchor_not_found` / `ambiguous_anchor` / `skipped_after_failure` /
  `syntax_invalid`) rendered directly against each hunk — mirroring `HunkResult.reason` exactly, so a
  partially-applied edit is never presented as if it fully succeeded.
* A failed/partial edit is visually distinct at the file-list level (not just inside the diff) so
  scanning a multi-file change surfaces problems without opening every file.

### Tool-Call Timeline Entry

Each entry shows, left to right: status icon (requested/authorized/denied/completed/failed, distinct
glyphs not just colors — see Accessibility), tool name, one-line argument summary, effect-class badge,
duration. Expands in place (no navigation) to show full arguments, full result content, and — for
denials — the `Decision.reason`.

## **Interaction Patterns**

* **Command palette (GUI, `Cmd/Ctrl+K`):** jump to any run, switch mock scenario (dev mode), toggle
  theme, focus the approval queue. Matches the Linear/Vercel expectation that power users never touch
  the mouse for navigation.
* **CLI keybindings:** `j`/`k` or arrow keys to move through the timeline, `Enter` to expand/collapse,
  `y`/`n` for approvals, `q` to quit, `/` to filter the timeline by tool name or status — a deliberately
  small, memorizable set, documented in a `?`-triggered help overlay in both apps.
* **Streaming text** (`model.delta`, reasoning blocks) renders with a blinking block cursor at the
  write head in both CLI and GUI, and auto-scrolls only while the viewport is already at the bottom
  (never yanks focus away from a step the user scrolled up to inspect — a Warp/terminal-etiquette
  detail that's easy to get wrong).
* **Never block on network/mock latency without feedback.** Any action that awaits an event round-trip
  (submitting an approval, submitting a new task) shows a pending/spinner state within 100ms.

## **Accessibility**

* **Never color-only signaling.** Every semantic color pairs with an icon or text label (status glyphs:
  `✓` success, `✗` failure/denied, `⋯` in-progress, `○` pending, `!` warning) — required both for
  colorblind users and because terminals may not render color at all (`NO_COLOR` env var respected in
  the CLI; ANSI fallback to bold/underline for hierarchy when color is unavailable).
* **Full keyboard navigation** in the GUI: every interactive element reachable via `Tab`, visible focus
  ring using `--sg-accent`, focus trapped correctly inside the approval modal (Radix handles this by
  default — do not override).
* **Screen reader support (GUI):** live regions (`aria-live="polite"`) for streaming/status updates
  that shouldn't interrupt, `aria-live="assertive"` reserved solely for `ApprovalRequested` and
  `RunFailed` — a run failing silently to a screen-reader user is a correctness bug, not a polish gap.
* **Contrast:** both themes verified at WCAG AA (4.5:1 body / 3:1 large-text-and-icons) as part of the
  token definition, not spot-checked after the fact.
* **Motion:** `prefers-reduced-motion` honored as specified above.
* **CLI terminal compatibility:** degrade gracefully on terminals without truecolor (256-color and
  16-color fallbacks via `chalk`'s automatic level detection), and without Unicode (ASCII fallback
  glyphs: `[ok]`/`[x]`/`[...]`/`[ ]` when the terminal doesn't advertise UTF-8).

## **Theming**

* Light and dark are both first-class (not "dark mode as an afterthought") — token table above defines
  both from the start.
* GUI: theme follows OS preference by default, with a manual override persisted to local client state
  (see [`architecture.md`](./architecture.md) state boundaries).
* CLI: no "theme" per se, but the color mapping is truecolor/256-color/16-color/no-color adaptive as
  above, and a `--no-color` flag is always honored regardless of terminal detection.

## **Content & Copy Voice**

* Terse, factual, present-tense event descriptions matching the backend's own naming discipline
  (events are named `group.past_tense` because "they describe what happened, never what should
  happen" — [Event Bus & Hooks](../02-architecture/event-bus-and-hooks.md)). UI copy follows the same
  rule: "Applied edit to `parser.py`," not "Successfully editing the file for you now!"
  * No filler enthusiasm, no exclamation points, no anthropomorphizing the agent beyond what's
    functionally useful ("the agent is reasoning" is fine; "I'm thinking really hard about this!" is
    not).
* Error/denial copy states the reason plainly (surfacing `Decision.reason` / `GateReport` criterion
  text verbatim where it exists) rather than paraphrasing it into something vaguer.
