import { describe, expect, it } from "vitest";
import { useHarnessStore } from "./store.js";

describe("useHarnessStore", () => {
  it("manages step history and aggregates token usage correctly", () => {
    useHarnessStore.getState().reset();
    expect(useHarnessStore.getState().steps).toHaveLength(0);

    useHarnessStore.getState().addStep({
      step_id: { run_id: "run-1", branch_id: "main", seq: 1 },
      kind: "tool",
      timestamp: "2026-07-31T00:00:00Z",
      token_usage: {
        prompt_tokens: 100,
        completion_tokens: 50,
        total_tokens: 150,
        cost_usd: 0.001,
      },
    });

    const state = useHarnessStore.getState();
    expect(state.steps).toHaveLength(1);
    expect(state.totalPromptTokens).toBe(100);
    expect(state.totalCompletionTokens).toBe(50);
    expect(state.totalCostUsd).toBe(0.001);
  });
});
