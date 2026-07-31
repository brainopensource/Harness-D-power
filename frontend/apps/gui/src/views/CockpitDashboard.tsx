import React, { useState, useEffect } from "react";
import { useHarnessStore, backendBridge, TrajectoryStep } from "@sagiha/protocol";
import { Button, MetricCard, StatusBadge, TokenGauge } from "@sagiha/ui";

export const CockpitDashboard: React.FC = () => {
  const {
    status,
    setStatus,
    steps,
    addStep,
    logs,
    totalPromptTokens,
    totalCompletionTokens,
    totalCostUsd,
    isTainted,
    latestGateReport,
    runContext,
  } = useHarnessStore();

  const [goal, setGoal] = useState("");
  const [acceptance, setAcceptance] = useState("true");
  const [mode, setMode] = useState<"live" | "replay">("live");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleRunTask = async () => {
    if (!goal.trim()) return;
    setIsSubmitting(true);

    try {
      await backendBridge.runTask({
        goal: goal.trim(),
        mode,
        acceptance: acceptance.trim() ? [acceptance.trim()] : ["true"],
        cassette: mode === "replay" ? "tests/fixtures/replay_smoke/cassette.json" : undefined,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-slate-100 font-sans">
      {/* Top Banner & Status Header */}
      <div className="flex justify-between items-center bg-slate-900/80 backdrop-blur-md p-5 rounded-2xl border border-slate-800 shadow-xl">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-gradient-to-tr from-cyan-600 to-indigo-600 rounded-xl shadow-lg shadow-indigo-500/20">
            <span className="text-xl font-bold font-mono">⚡ SAGIHA</span>
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide">AUTONOMOUS CODING ORCHESTRATOR</h1>
            <p className="text-xs font-mono text-slate-400">
              Microkernel Dispatch • Capability Security (CAR Model) • Live Trajectory Execution
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <StatusBadge status={isTainted ? "tainted" : status === "error" ? "failure" : status} />
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setStatus("running")}
              disabled={status === "running"}
            >
              ▶ RESUME
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={() => setStatus("frozen")}
              disabled={status === "frozen"}
            >
              ❄ PAUSE
            </Button>
          </div>
        </div>
      </div>

      {/* Task Prompt Dispatcher Box */}
      <div className="bg-slate-900/90 p-5 rounded-2xl border border-indigo-500/30 shadow-2xl space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-sm font-bold font-mono text-cyan-400 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
            DISPATCH NEW CODING TASK TO BACKEND KERNEL
          </h2>
          <div className="flex items-center gap-3 text-xs font-mono">
            <label className="text-slate-400">Mode:</label>
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as "live" | "replay")}
              className="bg-slate-950 border border-slate-800 text-slate-200 px-3 py-1 rounded-lg outline-none focus:border-cyan-500"
            >
              <option value="live">Live Execution (Ollama / Local Model)</option>
              <option value="replay">Deterministic Cassette Replay</option>
            </select>
          </div>
        </div>

        <div className="space-y-3">
          <textarea
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="Describe your coding task (e.g. 'Create a Python script date.py that prints today's date and write a test for it')"
            className="w-full h-24 bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm font-mono text-slate-100 placeholder-slate-600 outline-none focus:border-cyan-500 transition-colors"
          />

          <div className="flex gap-4 items-center">
            <input
              type="text"
              value={acceptance}
              onChange={(e) => setAcceptance(e.target.value)}
              placeholder="Acceptance check command (e.g. 'python3 -m pytest')"
              className="flex-grow bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-xs font-mono text-slate-200 outline-none focus:border-cyan-500"
            />
            <button
              onClick={handleRunTask}
              disabled={isSubmitting || !goal.trim()}
              className={`px-6 py-2 rounded-xl text-xs font-bold font-mono transition-all shadow-lg ${
                isSubmitting || !goal.trim()
                  ? "bg-slate-800 text-slate-500 cursor-not-allowed"
                  : "bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white shadow-cyan-500/25 active:scale-95"
              }`}
            >
              {isSubmitting ? "EXECUTING TASK..." : "🚀 RUN BACKEND TASK"}
            </button>
          </div>
        </div>
      </div>

      {/* Real-time Metrics Dashboard */}
      <div className="grid grid-cols-4 gap-4">
        <MetricCard
          title="EXECUTION STEPS"
          value={steps.length}
          subtitle={runContext?.run_id ? `Run: #${runContext.run_id.slice(0, 8)}` : "Inner-loop steps"}
        />
        <MetricCard
          title="CODING GATES"
          value={latestGateReport ? (latestGateReport.admitted ? "ADMITTED" : "REJECTED") : "PENDING"}
          subtitle={latestGateReport ? `${latestGateReport.criteria.length} criteria checks` : "tests_unmodified & diff bounds"}
        />
        <MetricCard
          title="TAINT GATE"
          value={isTainted ? "TAINTED" : "CLEAN"}
          subtitle="Monotonic untrusted containment"
        />
        <TokenGauge
          usedTokens={totalPromptTokens + totalCompletionTokens}
          maxTokens={100000}
          costUsd={totalCostUsd}
        />
      </div>

      {/* Live Trajectory & System Log Stream */}
      <div className="grid grid-cols-3 gap-6">
        {/* Step Trajectory Feed */}
        <div className="col-span-2 bg-slate-900/90 p-5 rounded-2xl border border-slate-800 space-y-3 shadow-xl">
          <div className="flex justify-between items-center">
            <h2 className="text-xs font-bold font-mono text-slate-300">LIVE TRAJECTORY TOOL CALLS ({steps.length})</h2>
            <span className="text-xs font-mono text-slate-500">Dispatch Choke Point Active</span>
          </div>

          <div className="space-y-2 max-h-96 overflow-y-auto pr-2">
            {steps.length === 0 ? (
              <div className="p-8 text-center text-slate-600 font-mono text-xs border border-dashed border-slate-800 rounded-xl">
                No tool steps executed yet. Enter a task above and click "RUN BACKEND TASK".
              </div>
            ) : (
              steps.map((step) => (
                <div
                  key={`${step.step_id.run_id}-${step.step_id.seq}`}
                  className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl space-y-2 text-xs font-mono"
                >
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-2">
                      <span className="text-cyan-400 font-bold">#{step.step_id.seq}</span>
                      <span className="px-2 py-0.5 bg-indigo-950 text-indigo-300 rounded border border-indigo-800 font-bold">
                        {step.tool_name || step.kind}
                      </span>
                    </div>
                    <StatusBadge status={step.tainted ? "tainted" : "success"} />
                  </div>

                  {Boolean(step.arguments) && (
                    <div className="p-2 bg-slate-900 rounded-lg text-slate-400 text-[11px] overflow-x-auto">
                      <span className="text-slate-500">args:</span> {JSON.stringify(step.arguments)}
                    </div>
                  )}

                  {Boolean(step.output) && (
                    <div className="p-2 bg-slate-900/50 rounded-lg text-slate-300 text-[11px] max-h-24 overflow-y-auto">
                      <span className="text-slate-500">output:</span> {String(step.output).slice(0, 300)}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Real-time System Logs */}
        <div className="bg-slate-900/90 p-5 rounded-2xl border border-slate-800 space-y-3 shadow-xl flex flex-col">
          <div className="flex justify-between items-center">
            <h2 className="text-xs font-bold font-mono text-slate-300">KERNEL EVENT LOG</h2>
            <span className="text-xs font-mono text-slate-500">{logs.length} events</span>
          </div>

          <div className="flex-grow space-y-2 max-h-96 overflow-y-auto pr-1">
            {logs.map((log) => {
              const levelColor =
                log.level === "error"
                  ? "text-red-400 bg-red-950/40 border-red-900"
                  : log.level === "warn"
                  ? "text-amber-400 bg-amber-950/40 border-amber-900"
                  : log.level === "tool"
                  ? "text-cyan-400 bg-cyan-950/40 border-cyan-900"
                  : "text-slate-300 bg-slate-950 border-slate-800";

              return (
                <div key={log.id} className={`p-2.5 rounded-lg border text-[11px] font-mono space-y-1 ${levelColor}`}>
                  <div className="flex justify-between text-[10px] opacity-75">
                    <span>[{log.level.toUpperCase()}]</span>
                    <span>{log.source}</span>
                  </div>
                  <div className="break-words">{log.message}</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
