import { MockEventSimulator } from "@sagiha/mock-engine";
import type { TrajectoryStep } from "@sagiha/protocol";
import { useHarnessStore } from "@sagiha/protocol";
import { Box, Text, useApp } from "ink";
import type React from "react";
import { useEffect } from "react";
import { StatusBadgeTui, TokenGaugeTui } from "../components/TuiAdapters.js";
import { SteerInput } from "./SteerInput.js";

export const CockpitView: React.FC = () => {
  const { exit } = useApp();
  const {
    status,
    setStatus,
    steps,
    addStep,
    totalPromptTokens,
    totalCompletionTokens,
    totalCostUsd,
  } = useHarnessStore();

  useEffect(() => {
    setStatus("running");
    const simulator = new MockEventSimulator({ runId: "run-cli-001", intervalMs: 1500 });
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
    <Box flexDirection="column" padding={1} width={80}>
      <Box justifyContent="space-between" marginBottom={1}>
        <Text bold color="magenta">
          SAGIHA :: AUTONOMOUS AGENT COCKPIT (TUI)
        </Text>
        <StatusBadgeTui status={status === "error" ? "failure" : status} />
      </Box>

      <Box marginBottom={1}>
        <TokenGaugeTui
          usedTokens={totalPromptTokens + totalCompletionTokens}
          maxTokens={100000}
          costUsd={totalCostUsd}
        />
      </Box>

      <Box
        flexDirection="column"
        borderStyle="single"
        borderColor="gray"
        paddingX={1}
        minHeight={8}
        marginBottom={1}
      >
        <Text bold color="yellow">
          LIVE EXECUTION STEP LOG ({steps.length} steps)
        </Text>
        {steps.slice(-5).map((step) => (
          <Box key={`${step.step_id.run_id}-${step.step_id.seq}`} justifyContent="space-between">
            <Text color="dim">
              [#{step.step_id.seq}] {step.tool_name || step.kind}
            </Text>
            <Text color={step.tainted ? "green" : "white"}>
              {step.tainted ? "[TAINTED]" : "[CLEAN]"}
            </Text>
          </Box>
        ))}
      </Box>

      <SteerInput
        onPause={() => setStatus("frozen")}
        onResume={() => setStatus("running")}
        onSteer={(_msg) => {}}
        onApproveTaint={() => {}}
        onQuit={() => exit()}
      />
    </Box>
  );
};
