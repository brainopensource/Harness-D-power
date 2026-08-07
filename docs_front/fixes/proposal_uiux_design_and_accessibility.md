---
status: normative
---

# AETHER Frontend UI/UX, Design, and Accessibility Audit Report

## 1. Executive Summary

This report documents User Interface (UI), User Experience (UX), Design System, and Accessibility status for the AETHER frontend ecosystem.

## 2. Status Overview

- **UX1**: `[ ] TODO` - Add empty state components for Monaco Diff and McNemar Dashboard when data is absent.
- **UX2**: `[ ] TODO` - Add visual loading indicators during WebSocket connection and cassette loading.
- **UX3**: `[ ] TODO` - Add inline error banner UI for connection drops and schema validation errors.
- **UX4**: `[ ] TODO` - Format `TurnLogStream.tsx` payloads into human-readable summaries.
- **UX5**: `[ ] TODO` - Add keyboard shortcuts for tab navigation (`Ctrl+1/2/3`).
- **UX6**: `[ ] TODO` - Add confirmation modal for destructive actions like patch rejection.
- **UX7**: `[ ] TODO` - Add animated active state indicator for tab navigation.
- **D1**: `[ ] TODO` - Create centralized design tokens system (colors, typography, spacing).
- **D2**: `[ ] TODO` - Standardize color palette across Ink TUI and React Desktop GUI.
- **D3**: `[ ] TODO` - Expand `@aether/ui-components` library with layout and input primitives.
- **D4**: `[ ] TODO` - Define typography scale and integrate Inter font.
- **D5**: `[ ] TODO` - Use distinct visual shapes/icons per node kind in `CustomNode.tsx`.
- **D6**: `[ ] TODO` - Add light/dark theme toggle for Desktop GUI.
- **ACC1**: `[ ] TODO` - Add `aria-label` to all icon-only buttons in `HeaderControls.tsx`.
- **ACC2**: `[ ] TODO` - Add ARIA list/listitem roles to `WorkflowCanvas.tsx` nodes.
- **ACC3**: `[ ] TODO` - Enable `accessibilitySupport: 'on'` in `MonacoDiffEditor.tsx`.
- **ACC4**: `[ ] TODO` - Audit text contrast ratios against WCAG 2.1 AA (4.5:1).
- **ACC5**: `[ ] TODO` - Manage focus auto-focus on tab panel switches.
- **ACC6**: `[ ] TODO` - Add text fallback for unknown provenance enums in `TaintAuditBadge.tsx`.

---

## 3. UI/UX Defects

### UX1. Hardcoded Mock Fallbacks Instead of Empty States — `[ ] TODO`
- **Files:** Desktop `MonacoDiffEditor.tsx`, `MetricsDashboard.tsx`, `TaintAuditPanel.tsx`
- **Status:** `[ ] TODO` — Display skeleton loaders or empty state cards.

### UX2. No Loading States or Skeleton UI — `[ ] TODO`
- **Status:** `[ ] TODO` — Add `<Spinner>` and loading overlays.

### UX3. No Error State UI — `[ ] TODO`
- **Status:** `[ ] TODO` — Add inline toast and error banners.

### UX4. TurnLogStream Shows Raw Payloads — `[ ] TODO`
- **File:** CLI `TurnLogStream.tsx`
- **Status:** `[ ] TODO` — Format JSON payloads into structured text lines.

### UX5. No Keyboard Navigation in Desktop GUI — `[ ] TODO`
- **Status:** `[ ] TODO` — Add shortcut key listeners for tab switching.

### UX6. No Confirmation for Destructive Actions — `[ ] TODO`
- **Status:** `[ ] TODO` — Add modal confirmation before patch rejection.

### UX7. Tab Navigation Active State — `[ ] TODO`
- **Status:** `[ ] TODO` — Add transition styling on tab bar.

---

## 4. Design System & Accessibility

All design system (D1–D6) and accessibility (ACC1–ACC6) enhancements are cataloged for implementation in Sprint FE-02 and FE-03.
