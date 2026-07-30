/**
 * TS mirror of tokens.css for consumers that need token values as data — chiefly the
 * CLI, which has no CSS engine and maps these onto `chalk` calls instead of DOM styles.
 * Keep in sync with tokens.css by hand; there are few enough tokens that a build-time
 * codegen step is not worth it yet.
 */

export const spacing = {
  1: 4,
  2: 8,
  3: 12,
  4: 16,
  5: 24,
  6: 32,
  7: 48,
  8: 64,
} as const;

export const typeScale = {
  xs: 12,
  sm: 14,
  base: 16,
  lg: 20,
  xl: 24,
  "2xl": 32,
} as const;

export const motionDurationMs = {
  micro: 100,
  standard: 200,
  emphasis: 320,
} as const;

/** Semantic color -> terminal-safe chalk color name, per ui-ux-guidelines.md's CLI column. */
export const chalkColor = {
  accent: "cyan",
  success: "green",
  warning: "yellow",
  danger: "red",
  info: "blue",
  pending: "magenta",
  effectPure: "dim white" as const,
  effectIdempotent: "blue",
  effectDestructive: "red bold" as const,
} as const;

/** CLI's equivalent of a type scale: a named indent + weight + color ladder. */
export const cliStyle = {
  heading: { chalk: ["bold"] as const },
  label: { chalk: ["dim"] as const },
  value: { chalk: [] as const },
  muted: { chalk: ["dim"] as const },
  code: { chalk: ["cyan"] as const },
} as const;

/** Status glyphs — never color-only signaling; every color pairs with one of these. */
export const statusGlyph = {
  success: "✓",
  failure: "✗",
  inProgress: "⋯",
  pending: "○",
  warning: "!",
} as const;

/** ASCII fallback glyphs for terminals that don't advertise UTF-8. */
export const statusGlyphAscii = {
  success: "[ok]",
  failure: "[x]",
  inProgress: "[...]",
  pending: "[ ]",
  warning: "[!]",
} as const;
