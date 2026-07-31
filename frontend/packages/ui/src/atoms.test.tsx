import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, expect, it } from "vitest";
import { Button, CodeSnippet, MetricCard, StatusBadge, TokenGauge } from "./atoms.js";

describe("Atomic Components", () => {
  it("renders StatusBadge with correct status and glyph", () => {
    render(<StatusBadge status="running" label="RUNNING" />);
    const badge = screen.getByTestId("status-badge");
    expect(badge).toBeDefined();
    expect(badge.getAttribute("data-status")).toBe("running");
  });

  it("renders TokenGauge correctly", () => {
    render(<TokenGauge usedTokens={500} maxTokens={1000} costUsd={0.05} />);
    const gauge = screen.getByTestId("token-gauge");
    expect(gauge).toBeDefined();
    expect(screen.getByText(/500 \/ 1,000/)).toBeDefined();
  });

  it("renders MetricCard", () => {
    render(<MetricCard title="ACTIVE STEPS" value={42} subtitle="+5 from last run" />);
    expect(screen.getByText("ACTIVE STEPS")).toBeDefined();
    expect(screen.getByText("42")).toBeDefined();
  });

  it("renders CodeSnippet", () => {
    render(<CodeSnippet code="console.log('test')" language="typescript" />);
    const snippet = screen.getByTestId("code-snippet");
    expect(snippet.getAttribute("data-language")).toBe("typescript");
  });

  it("renders Button", () => {
    render(<Button variant="danger">PAUSE</Button>);
    expect(screen.getByText("PAUSE")).toBeDefined();
  });
});
