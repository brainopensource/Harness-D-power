import React, { useState, useEffect } from "react";
import {
  useAetherStream,
  useBudget,
} from "@aether/core";
import {
  MockCassettePlayer,
  sweBenchPassCassette,
  repairLoopAblationCassette,
} from "@aether/mock-server";

import { HeaderControls } from "./components/HeaderControls";
import { WorkflowCanvas } from "./components/canvas/WorkflowCanvas";
import { LiveTraceInspector } from "./components/trace/LiveTraceInspector";
import { TaintAuditPanel } from "./components/trace/TaintAuditPanel";
import { MonacoDiffEditor } from "./components/diff/MonacoDiffEditor";
import { MetricsDashboard } from "./components/metrics/MetricsDashboard";
import { Button, ErrorBoundary } from "@aether/ui-components";

export function App() {
  const [player] = useState(() => new MockCassettePlayer());
  const [cassetteIndex, setCassetteIndex] = useState(0);
  const [activeTab, setActiveTab] = useState<"canvas" | "diff" | "metrics">("canvas");
  const [mode, setMode] = useState<"mock" | "live">("mock");

  const cassettes = [
    { name: "swe_bench_pass.json", data: sweBenchPassCassette },
    { name: "repair_loop_ablation.json", data: repairLoopAblationCassette },
  ];

  useEffect(() => {
    if (mode === "mock") {
      player.loadCassetteData(cassettes[cassetteIndex].data);
      return () => {
        player.stop();
      };
    }
  }, [cassetteIndex, mode, player]);

  useAetherStream(mode === "mock" ? player : undefined);
  const { reserved, committed, remaining } = useBudget();

  const handlePlay = (speed: number) => {
    player.play(speed);
  };

  const handlePause = () => {
    player.pause();
  };

  const handleStep = () => {
    player.stepForward();
  };

  const handleSwitchCassette = () => {
    setCassetteIndex((prev) => (prev + 1) % cassettes.length);
  };

  const formatUsd = (micros: number) => `$${(micros / 1000000).toFixed(4)}`;

  return (
    <ErrorBoundary title="AETHER Desktop Application Shell Error">
      <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "#090d16", color: "#f8fafc", fontFamily: "Inter, system-ui, sans-serif" }}>
        <HeaderControls
          player={player}
          activeMode={mode}
          cassetteName={cassettes[cassetteIndex].name}
          onPlay={handlePlay}
          onPause={handlePause}
          onStep={handleStep}
          onSwitchCassette={handleSwitchCassette}
          onToggleMode={() => setMode((m) => (m === "mock" ? "live" : "mock"))}
        />

        {/* Top Tab Bar & Real-time Budget Bar */}
        <div style={{ height: "44px", background: "#0f172a", borderBottom: "1px solid #1e293b", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 20px" }}>
          <div style={{ display: "flex", gap: "8px" }}>
            <Button variant={activeTab === "canvas" ? "primary" : "ghost"} size="sm" onClick={() => setActiveTab("canvas")}>
              🕸️ Visual DAG Canvas & Trace
            </Button>
            <Button variant={activeTab === "diff" ? "primary" : "ghost"} size="sm" onClick={() => setActiveTab("diff")}>
              📝 Monaco Patch Diff
            </Button>
            <Button variant={activeTab === "metrics" ? "primary" : "ghost"} size="sm" onClick={() => setActiveTab("metrics")}>
              📊 McNemar Dashboard
            </Button>
          </div>
          <div style={{ fontSize: "12px", color: "#94a3b8", display: "flex", gap: "16px" }}>
            <span>Reserved: <strong style={{ color: "#fbbf24" }}>{formatUsd(reserved.usdMicros)}</strong></span>
            <span>Committed: <strong style={{ color: "#4ade80" }}>{formatUsd(committed.usdMicros)}</strong></span>
            <span>Remaining: <strong style={{ color: "#38bdf8" }}>{formatUsd(remaining.usdMicros)}</strong></span>
          </div>
        </div>

        {/* Main View Area with Error Boundaries per Tab */}
        <main style={{ flex: 1, overflow: "hidden", display: "flex" }}>
          {activeTab === "canvas" && (
            <>
              <div style={{ flex: 1, position: "relative" }}>
                <ErrorBoundary title="DAG Canvas Exception">
                  <WorkflowCanvas />
                </ErrorBoundary>
              </div>
              <div style={{ width: "380px", borderLeft: "1px solid #1e293b", background: "#0b1120", padding: "16px", overflowY: "auto" }}>
                <ErrorBoundary title="Trace Inspector Exception">
                  <LiveTraceInspector />
                </ErrorBoundary>
                <ErrorBoundary title="Taint Audit Panel Exception">
                  <TaintAuditPanel />
                </ErrorBoundary>
              </div>
            </>
          )}

          {activeTab === "diff" && (
            <div style={{ flex: 1, padding: "20px" }}>
              <ErrorBoundary title="Monaco Diff Editor Exception">
                <MonacoDiffEditor />
              </ErrorBoundary>
            </div>
          )}

          {activeTab === "metrics" && (
            <div style={{ flex: 1, padding: "20px", overflowY: "auto" }}>
              <ErrorBoundary title="Metrics Dashboard Exception">
                <MetricsDashboard />
              </ErrorBoundary>
            </div>
          )}
        </main>
      </div>
    </ErrorBoundary>
  );
}

export default App;
