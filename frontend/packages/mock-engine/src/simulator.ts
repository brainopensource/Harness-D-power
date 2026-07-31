import type { GateReport, TokenUsage, TrajectoryStep } from "@sagiha/protocol";

export type HarnessEventType =
  | "StepCompleted"
  | "TelemetryTick"
  | "CompactionApplied"
  | "TaintIntroduced"
  | "GateEvaluated"
  | "ProviderFailover";

export interface HarnessEvent {
  type: HarnessEventType;
  run_id: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

export interface SimulatorOptions {
  intervalMs?: number;
  runId?: string;
}

export class MockEventSimulator {
  private runId: string;
  private intervalMs: number;
  private intervalId: ReturnType<typeof setInterval> | null = null;
  private stepSeq = 1;
  private listeners: ((event: HarnessEvent) => void)[] = [];

  constructor(options: SimulatorOptions = {}) {
    this.runId = options.runId || "run-mock-101";
    this.intervalMs = options.intervalMs || 1000;
  }

  public subscribe(listener: (event: HarnessEvent) => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  public start(): void {
    if (this.intervalId) return;
    this.intervalId = setInterval(() => {
      this.emitNextEvent();
    }, this.intervalMs);
  }

  public stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  public emitNextEvent(): HarnessEvent {
    const event = this.generateEvent();
    for (const listener of this.listeners) {
      listener(event);
    }
    return event;
  }

  private generateEvent(): HarnessEvent {
    const now = new Date().toISOString();
    const eventTypes: HarnessEventType[] = [
      "StepCompleted",
      "TelemetryTick",
      "StepCompleted",
      "TelemetryTick",
      "CompactionApplied",
      "TaintIntroduced",
      "GateEvaluated",
      "ProviderFailover",
    ];
    const type = eventTypes[(this.stepSeq - 1) % eventTypes.length] || "StepCompleted";

    let payload: Record<string, unknown> = {};

    if (type === "TelemetryTick") {
      payload = {
        cpuUsagePct: Math.floor(18 + Math.random() * 40),
        memoryMb: Math.floor(180 + Math.random() * 60),
      };
    } else if (type === "StepCompleted") {
      const step: TrajectoryStep = {
        step_id: { run_id: this.runId, branch_id: "main", seq: this.stepSeq },
        kind: "tool_execution",
        timestamp: now,
        tool_name: this.stepSeq % 2 === 0 ? "apply_edit" : "run_command",
        arguments:
          this.stepSeq % 2 === 0
            ? { target_file: "src/sagiha/agency/run_loop.py", count: 1 }
            : { command: "cargo test --quiet" },
        output: "Finished execution cleanly.",
        token_usage: {
          prompt_tokens: 1200,
          completion_tokens: 150,
          total_tokens: 1350,
          cost_usd: 0.002,
        },
        tainted: this.stepSeq > 3,
      };
      payload = { step };
      this.stepSeq++;
    } else if (type === "CompactionApplied") {
      payload = {
        compacted_turns: 4,
        headroom_percent: 24.5,
        saved_tokens: 3400,
      };
    } else if (type === "TaintIntroduced") {
      payload = {
        source_envelope: "<untrusted-data>External web scrape payload</untrusted-data>",
        requires_human: true,
        tool_call: "apply_edit",
      };
    } else if (type === "GateEvaluated") {
      const report: GateReport = {
        criteria: [
          {
            description: "Require unit tests",
            check: "cargo test",
            passed: true,
            required: true,
            output: "test result: ok",
            duration_ms: 450,
          },
        ],
        no_new_suppressions: true,
        tests_unmodified: true,
        diff_within_bounds: true,
        required_gates: ["no_new_suppressions", "tests_unmodified", "diff_within_bounds"],
        admitted: true,
      };
      payload = { gate_report: report };
    } else if (type === "ProviderFailover") {
      payload = {
        from_provider: "anthropic-claude-3-5-sonnet",
        to_provider: "openai-gpt-4o",
        reason: "rate_limit_exceeded",
      };
    }

    return {
      type,
      run_id: this.runId,
      timestamp: now,
      payload,
    };
  }
}
