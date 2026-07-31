import React, { useEffect, useState } from "react";
import { Box, useApp, useInput } from "ink";
import { MockEventSimulator } from "@sagiha/mock-engine";
import { backendBridge, TrajectoryStep, useHarnessStore } from "@sagiha/protocol";
import { HeaderBar } from "../components/HeaderBar.js";
import { LogStreamView } from "../components/LogStreamView.js";
import { ControlPanelView } from "../components/ControlPanelView.js";
import { CommandPrompt } from "../components/CommandPrompt.js";

export const CockpitView: React.FC = () => {
  const { exit } = useApp();
  const {
    connectionState,
    systemMetrics,
    status,
    setStatus,
    steps,
    addStep,
    logs,
    logFilter,
    setLogFilter,
    activeTab,
    setActiveTab,
    commandHistory,
    addCommandToHistory,
    controlCards,
    toggleControlCard,
    setSystemMetrics,
    totalPromptTokens,
    totalCompletionTokens,
    totalCostUsd,
    addLog,
  } = useHarnessStore();

  const [focusedPane, setFocusedPane] = useState<"content" | "prompt">("prompt");

  useEffect(() => {
    setStatus("running");
    const simulator = new MockEventSimulator({ runId: "run-cli-001", intervalMs: 1200 });

    const unsubscribe = simulator.subscribe((event) => {
      if (event.type === "TelemetryTick" && event.payload) {
        setSystemMetrics({
          cpuUsagePct: (event.payload.cpuUsagePct as number) || 25,
          memoryMb: (event.payload.memoryMb as number) || 190,
        });
      } else if (event.type === "StepCompleted" && event.payload.step) {
        addStep(event.payload.step as TrajectoryStep);
      } else if (event.type === "CompactionApplied") {
        addLog({
          id: `log-compact-${Date.now()}`,
          timestamp: new Date().toISOString(),
          level: "info",
          message: `Exchange Compactor applied: saved ${event.payload.saved_tokens} tokens`,
          source: "compactor",
        });
      } else if (event.type === "TaintIntroduced") {
        addLog({
          id: `log-taint-${Date.now()}`,
          timestamp: new Date().toISOString(),
          level: "warn",
          message: `Taint introduced from untrusted envelope: mutation paused`,
          source: "taintgate",
        });
      } else if (event.type === "ProviderFailover") {
        addLog({
          id: `log-failover-${Date.now()}`,
          timestamp: new Date().toISOString(),
          level: "warn",
          message: `Failover: ${event.payload.from_provider} -> ${event.payload.to_provider}`,
          source: "provider",
        });
      }
    });

    simulator.start();

    return () => {
      simulator.stop();
      unsubscribe();
    };
  }, [setStatus, addStep, setSystemMetrics, addLog]);

  // Global key bindings: Tab to toggle pane focus, Esc to cancel / exit
  useInput((input, key) => {
    if (key.tab) {
      setFocusedPane((prev) => (prev === "prompt" ? "content" : "prompt"));
    }
    if (key.escape) {
      if (status === "running") {
        setStatus("frozen");
        addLog({
          id: `log-pause-${Date.now()}`,
          timestamp: new Date().toISOString(),
          level: "warn",
          message: "Execution paused via ESC key.",
          source: "tui",
        });
      }
    }
  });

  const handleCommandSubmit = (command: string) => {
    addCommandToHistory(command);

    if (command === "/pause") {
      setStatus("frozen");
      addLog({ id: `cmd-${Date.now()}`, timestamp: new Date().toISOString(), level: "info", message: "Kernel execution paused.", source: "user" });
    } else if (command === "/resume") {
      setStatus("running");
      addLog({ id: `cmd-${Date.now()}`, timestamp: new Date().toISOString(), level: "info", message: "Kernel execution resumed.", source: "user" });
    } else if (command === "/restart") {
      setStatus("running");
      addLog({ id: `cmd-${Date.now()}`, timestamp: new Date().toISOString(), level: "info", message: "Restarting orchestration run context...", source: "user" });
    } else if (command.startsWith("/logs")) {
      setActiveTab("logs");
      if (command.includes("error")) setLogFilter("error");
      else if (command.includes("warn")) setLogFilter("warn");
      else if (command.includes("tool")) setLogFilter("tool");
      else setLogFilter("all");
    } else if (command === "/status") {
      addLog({
        id: `cmd-${Date.now()}`,
        timestamp: new Date().toISOString(),
        level: "info",
        message: `Status: ${status} | CPU: ${systemMetrics.cpuUsagePct}% | RAM: ${systemMetrics.memoryMb}MB | Tokens: ${totalPromptTokens + totalCompletionTokens}`,
        source: "system",
      });
    } else if (command === "/help") {
      addLog({
        id: `cmd-${Date.now()}`,
        timestamp: new Date().toISOString(),
        level: "info",
        message: "Available slash commands: /status, /logs [all|error|warn|tool], /pause, /resume, /restart, /help",
        source: "system",
      });
    } else {
      addLog({
        id: `cmd-${Date.now()}`,
        timestamp: new Date().toISOString(),
        level: "info",
        message: `[Task Prompt Submitted] ${command}`,
        source: "user",
      });

      const isReplay = command.includes("--replay");
      const goal = command.replace("--replay", "").trim();
      backendBridge.runTask({
        goal,
        mode: isReplay ? "replay" : "live",
        cassette: isReplay ? "tests/fixtures/replay_smoke/cassette.json" : undefined,
      });
    }
  };

  return (
    <Box flexDirection="column" padding={1} width={100} minHeight={24}>
      {/* 1. Header & Telemetry Status Bar */}
      <HeaderBar
        connectionState={connectionState}
        systemMetrics={systemMetrics}
        status={status}
        totalPromptTokens={totalPromptTokens}
        totalCompletionTokens={totalCompletionTokens}
        totalCostUsd={totalCostUsd}
        activeTab={activeTab}
        focusedPane={focusedPane}
      />

      {/* 2. Main Content Area (Tabbed View) */}
      <Box flexDirection="column" flexGrow={1} minHeight={12}>
        {activeTab === "logs" ? (
          <LogStreamView
            logs={logs}
            steps={steps}
            filter={logFilter}
            onFilterChange={setLogFilter}
            isFocused={focusedPane === "content"}
          />
        ) : (
          <ControlPanelView
            cards={controlCards}
            onToggleCard={toggleControlCard}
            isFocused={focusedPane === "content"}
          />
        )}
      </Box>

      {/* 3. Interactive Command / Prompt Bar */}
      <CommandPrompt
        onSubmit={handleCommandSubmit}
        history={commandHistory}
        isFocused={focusedPane === "prompt"}
      />
    </Box>
  );
};
