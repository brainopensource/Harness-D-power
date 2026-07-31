import { describe, expect, it } from "vitest";
import { type HarnessEvent, MockEventSimulator } from "./simulator.js";

describe("MockEventSimulator", () => {
  it("emits events to subscribers when started or stepped", () => {
    const simulator = new MockEventSimulator({ runId: "test-run-1" });
    const events: HarnessEvent[] = [];
    const unsubscribe = simulator.subscribe((event) => {
      events.push(event);
    });

    const emitted = simulator.emitNextEvent();
    expect(emitted.run_id).toBe("test-run-1");
    expect(events[0]).toBeDefined();
    expect(events[0]?.type).toBe("StepCompleted");

    unsubscribe();
  });
});
