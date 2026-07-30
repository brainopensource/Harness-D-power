import { describe, expect, it } from "vitest";
import { RunStartedSchema } from "./events.js";

const validRunStarted = {
  event: "run.started" as const,
  schema_version: 1,
  run_id: "run-001",
  step_id: null,
  timestamp: new Date("2026-07-30T00:00:00Z"),
  task: {
    task_id: "task-001",
    revision: 0,
    goal: "Fix the failing test in tests/test_parser.py",
    acceptance: [
      {
        description: "tests/test_parser.py passes",
        check: "pytest tests/test_parser.py",
        required: true,
      },
    ],
    profile: "coding",
    status: "submitted" as const,
  },
  run_context: {
    run_id: "run-001",
    autonomy_level: "hybrid" as const,
    workspace_root: "mock://repo",
    budget_remaining_usd: 5.0,
  },
  profile: "coding",
  extension_manifest: [],
};

describe("RunStarted schema", () => {
  it("validates a hand-built payload matching the real event shape", () => {
    expect(() => RunStartedSchema.parse(validRunStarted)).not.toThrow();
  });

  it("rejects a payload with a wrong field name (shape drift caught at parse time)", () => {
    const { task, ...rest } = validRunStarted;
    const drifted = { ...rest, taskSpec: task };
    expect(() => RunStartedSchema.parse(drifted)).toThrow();
  });
});
