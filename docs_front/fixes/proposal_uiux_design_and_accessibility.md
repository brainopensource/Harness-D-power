---
status: normative
---

# AETHER Frontend UI/UX, Design, and Accessibility Audit Report

## 1. Executive Summary

This report outlines critical, high, medium, and low severity defects related to User Interface (UI), User Experience (UX), Design System implementation, and Accessibility within the AETHER frontend ecosystem (comprising the React Desktop GUI and Ink CLI). The current state indicates a lack of unified design tokens, poor empty/loading/error state management, and significant accessibility oversights. Implementing the fixes proposed herein is essential for providing a usable, accessible, and robust developer experience.

## 2. Severity Distribution Table

| Category      | Critical | High | Medium | Low | Total |
|---------------|----------|------|--------|-----|-------|
| UI/UX         | 0        | 3    | 3      | 1   | 7     |
| Design System | 1        | 2    | 2      | 1   | 6     |
| Accessibility | 0        | 2    | 2      | 2   | 6     |
| **Total**     | **1**    | **7**| **7**  | **4**| **19**|

## 3. UI/UX Defects

### UX1. Hardcoded Mock Fallbacks Instead of Empty States (High)
**Description:** Components fall back to hardcoded mock data instead of showing proper empty or loading states.
**Files Affected:**
- Desktop `MonacoDiffEditor.tsx` (hardcoded diff strings)
- Desktop `MetricsDashboard.tsx` (hardcoded `mockABResult`)
- Desktop `TaintAuditPanel.tsx` (hardcoded `mockSpans`)
**Fix Recommendation:** Show skeleton loaders or empty state messages ("No diffs available", "Waiting for metrics...") when data is absent.

### UX2. No Loading States or Skeleton UI (High)
**Description:** No component across CLI or Desktop shows loading indicators when connecting to the backend, loading a cassette, or waiting for the first event.
**Fix Recommendation:** Add `<Spinner>` (Ink) or skeleton components (Desktop) during connection and loading phases.

### UX3. No Error State UI (High)
**Description:** When WebSocket disconnects, events fail validation, or a cassette fails to load — there's no user-visible error feedback.
**Fix Recommendation:** Display inline error banners, toast notifications, or status bar warnings.

### UX4. TurnLogStream Shows Raw Payloads (Medium)
**Description:** Renders `JSON.stringify(event.payload)` directly. This is developer-facing, not user-friendly.
**Files Affected:** CLI `TurnLogStream.tsx`
**Fix Recommendation:** Format payloads based on `eventType` — show human-readable summaries for each event type.

### UX5. No Keyboard Navigation in Desktop GUI (Medium)
**Description:** Desktop GUI relies entirely on mouse interaction. No keyboard shortcuts for tab switching, canvas navigation, or diff review.
**Fix Recommendation:** Add keyboard shortcuts with a help overlay (Ctrl+1/2/3 for tabs, etc.).

### UX6. No Confirmation for Destructive Actions (Medium)
**Description:** AcceptDiff/RejectDiff buttons have no confirmation dialog. In a production coding harness, accidentally accepting a bad patch is costly.
**Fix Recommendation:** Add confirmation modal or undo mechanism.

### UX7. Tab Navigation Doesn't Indicate Active State Visually (Low)
**Description:** Tabs use inline conditional styles. The active tab indicator is a simple border change with no animation or transition.
**Files Affected:** Desktop `App.tsx`
**Fix Recommendation:** Add clear visual indicators and transitions for active tabs.

## 4. Design System Defects

### D1. No Design System or Theme Tokens (Critical)
**Description:** Colors, spacing, typography, and sizing are defined inline throughout every component. No shared CSS variables, theme object, or Tailwind config despite Tailwind being listed as a dependency.
**Fix Recommendation:** Create a centralized theme system with design tokens (colors, spacing scale, typography scale, shadows, radii).

### D2. Inconsistent Color Palette (High)
**Description:** CLI uses Ink colors (yellow, green, cyan, red, gray). Desktop uses hex literals scattered across components. No shared color semantics between CLI and Desktop.
**Fix Recommendation:** Define semantic color tokens (success, error, warning, info, surface, text) in `@aether/core` or `@aether/ui-components`.

### D3. ui-components Package Is Skeletal (High)
**Description:** Only 3 components (Badge, Button, Card) with minimal styling. Desktop components don't even import from this package — they recreate styles inline.
**Fix Recommendation:** Build out the design system library with all shared primitives and use them consistently across Desktop and CLI (where applicable).

### D4. No Typography System (Medium)
**Description:** No Google Fonts integration, no type scale, no heading hierarchy. Desktop uses system fonts implicitly.
**Fix Recommendation:** Add Inter/Roboto font, define type scale (xs, sm, base, lg, xl, 2xl), and use CSS custom properties.

### D5. Workflow Canvas Nodes Lack Visual Hierarchy (Medium)
**Description:** All node types (retrieval, generation, application, evaluation) look similar — only distinguished by status color, not by shape or icon.
**Files Affected:** Desktop `CustomNode.tsx`
**Fix Recommendation:** Use distinct node shapes/icons per kind (database icon for retrieval, gear for generation, etc.).

### D6. No Dark/Light Theme Support (Low)
**Description:** Desktop is hardcoded dark. No theme toggle.
**Fix Recommendation:** Introduce theme management and toggle capabilities.

## 5. Accessibility Defects

### ACC1. Buttons Missing aria-label (High)
**Description:** Icon-only buttons have no `aria-label`, making them invisible to screen readers.
**Files Affected:** Desktop `HeaderControls.tsx` (all button elements)
**Fix Recommendation:** Add descriptive `aria-label` to every icon-only button.

### ACC2. No ARIA Roles on Interactive Canvas Elements (High)
**Description:** xyflow canvas nodes are not announced to assistive technology.
**Files Affected:** Desktop `WorkflowCanvas.tsx`, `CustomNode.tsx`
**Fix Recommendation:** Add `role="listitem"` to nodes, `role="list"` to the canvas, and `aria-selected` for focused nodes.

### ACC3. Monaco Editor Missing Accessibility Config (Medium)
**Description:** Monaco supports `accessibilitySupport: 'on'` option but it's not set.
**Files Affected:** Desktop `MonacoDiffEditor.tsx`
**Fix Recommendation:** Add `options={{ accessibilitySupport: 'on' }}` to the Monaco editor configuration.

### ACC4. Color Contrast Issues (Medium)
**Description:** Several text-on-background combinations (gray text on dark backgrounds, yellow on white) likely fail WCAG 2.1 AA contrast ratios.
**Fix Recommendation:** Audit all color pairs against WCAG 2.1 AA (4.5:1 for normal text, 3:1 for large text) and adjust as necessary.

### ACC5. No Focus Management on Tab Switches (Low)
**Description:** When switching tabs in the Desktop app, focus doesn't move to the new tab panel content.
**Fix Recommendation:** Use `tabIndex` and `useRef` to manage focus on tab change.

### ACC6. CLI TaintAuditBadge Lacks Fallback for Unknown Enums (Low)
**Description:** Unknown provenance values default to gray with no text label.
**Files Affected:** CLI `TaintAuditBadge.tsx`
**Fix Recommendation:** Provide a clear fallback text label for unknown values.

## 6. Design System Proposal

A cohesive design system is required to unify the AETHER frontend ecosystem. The proposed system should include:

1. **Design Tokens:** Centralized CSS custom properties or Tailwind configuration for colors, spacing, typography, and shadows.
2. **Component Library:** A robust `@aether/ui-components` package providing accessible, reusable primitives (Buttons, Inputs, Modals, Tabs, Badges, Loaders).
3. **Semantic Theming:** Shared semantic definitions for Success, Error, Warning, and Info states that map appropriately to both Desktop UI and CLI TUI.
4. **Accessibility First:** All primitives must enforce ARIA attributes, keyboard navigation, and contrast requirements by default.

## 7. Prioritized Remediation Roadmap

1. **Phase 1: Critical & High Design Foundation (Weeks 1-2)**
   - Fix D1 & D2: Establish core design tokens and semantic colors.
   - Fix D3: Expand `@aether/ui-components` and integrate into Desktop.
2. **Phase 2: Core UX Improvements (Weeks 3-4)**
   - Fix UX1, UX2, & UX3: Replace mocks with real loading, empty, and error states.
   - Fix ACC1 & ACC2: Ensure core interactions are accessible to screen readers.
3. **Phase 3: Refinement & Accessibility (Weeks 5-6)**
   - Fix UX4, UX5, & UX6: Implement keyboard navigation, formatting, and safety checks.
   - Fix D4, D5, ACC3, & ACC4: Polish typography, node visuals, and contrast ratios.
4. **Phase 4: Low Priority Polish (Ongoing)**
   - Fix UX7, D6, ACC5, ACC6.
