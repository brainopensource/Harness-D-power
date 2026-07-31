import { MockEventSimulator } from "@sagiha/mock-engine";
import type { TrajectoryStep } from "@sagiha/protocol";
import { useHarnessStore } from "@sagiha/protocol";
import { Button, CodeSnippet, MetricCard, StatusBadge, TokenGauge } from "@sagiha/ui";
import type React from "react";
import { useEffect } from "react";

export const CockpitDashboard: React.FC = () => {
  const {
    status,
    setStatus,
    steps,
    addStep,
    totalPromptTokens,
    totalCompletionTokens,
    totalCostUsd,
    isTainted,
  } = useHarnessStore();

  useEffect(() => {
    setStatus("running");
    const simulator = new MockEventSimulator({ runId: "gui-run-202", intervalMs: 1200 });
    const unsubscribe = simulator.subscribe((event) => {
      if (event.type === "StepCompleted" && event.payload.step) {
        addStep(event.payload.step as TrajectoryStep);
      }
    });
    simulator.start();

    return () => {
      simulator.stop();
      unsubscribe();
    };
  }, [setStatus, addStep]);

  return (
    <div className="p-6 space-y-6">
      {/* Header Controls */}
      <div className="flex justify-between items-center bg-gray-950 p-4 rounded-xl border border-gray-800">
        <div className="flex items-center gap-4">
          <StatusBadge status={isTainted ? "tainted" : status === "error" ? "failure" : status} />
          <div>
            <h1 className="text-lg font-bold font-mono text-gray-100">RUN #gui-run-202</h1>
            <p className="text-xs font-mono text-gray-400">
              Target: Refactor microkernel dispatch & gate checks
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="secondary" size="sm" onClick={() => setStatus("running")}>
            ▶ RESUME
          </Button>
          <Button variant="danger" size="sm" onClick={() => setStatus("frozen")}>
            ❄ PAUSE (FREEZE)
          </Button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-4 gap-4">
        <MetricCard title="COMPLETED STEPS" value={steps.length} subtitle="Inner-loop tool calls" />
        <MetricCard title="AUTONOMY LEVEL" value="AUTONOMOUS" subtitle="CAR Policy Active" />
        <MetricCard
          title="TAINT STATUS"
          value={isTainted ? "TAINTED" : "CLEAN"}
          subtitle="Monotonic T7 Envelope"
        />
        <TokenGauge
          usedTokens={totalPromptTokens + totalCompletionTokens}
          maxTokens={100000}
          costUsd={totalCostUsd}
        />
      </div>

      {/* Execution Feed */}
      <div className="bg-gray-950 p-4 rounded-xl border border-gray-800 space-y-3">
        <h2 className="text-sm font-bold font-mono text-gray-300">LIVE AGENT TRAJECTORY FEED</h2>
        <div className="space-y-2 max-h-80 overflow-y-auto pr-2">
          {steps.map((step) => (
            <div
              key={`${step.step_id.run_id}-${step.step_id.seq}`}
              className="p-3 bg-gray-900 border border-gray-800 rounded-lg flex justify-between items-center text-xs font-mono"
            >
              <div>
                <span className="text-purple-400 font-bold">#{step.step_id.seq}</span>{" "}
                <span className="text-gray-200">{step.tool_name || step.kind}</span>
                {step.arguments && (
                  <span className="text-gray-500 ml-2">{JSON.stringify(step.arguments)}</span>
                )}
              </div>
              <StatusBadge status={step.tainted ? "tainted" : "success"} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
