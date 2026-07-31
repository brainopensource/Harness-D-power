import React from "react";
import { Box, Text } from "ink";
import { ConnectionState, SystemMetrics } from "@sagiha/protocol";
import { StatusBadgeTui } from "./TuiAdapters.js";

export interface HeaderBarProps {
  connectionState: ConnectionState;
  systemMetrics: SystemMetrics;
  status: "idle" | "running" | "frozen" | "tainted" | "error";
  totalPromptTokens: number;
  totalCompletionTokens: number;
  totalCostUsd: number;
  activeTab: "logs" | "control";
  focusedPane: "content" | "prompt";
}

export const HeaderBar: React.FC<HeaderBarProps> = ({
  connectionState,
  systemMetrics,
  status,
  totalPromptTokens,
  totalCompletionTokens,
  totalCostUsd,
  activeTab,
  focusedPane,
}) => {
  const connectionColor =
    connectionState === "Connected" ? "green" : connectionState === "Reconnecting" ? "yellow" : "red";

  const totalTokens = totalPromptTokens + totalCompletionTokens;

  return (
    <Box flexDirection="column" marginBottom={1}>
      {/* Top Banner & Status */}
      <Box justifyContent="space-between" alignItems="center" paddingX={1} borderStyle="single" borderColor="cyan">
        <Box gap={1}>
          <Text bold color="cyan">
            SAGIHA CONTROL CENTER
          </Text>
          <Text color="dim">|</Text>
          <Text color={connectionColor} bold>
            ● {connectionState.toUpperCase()}
          </Text>
        </Box>

        <Box gap={2}>
          <Text color="gray">
            CPU: <Text color="yellow">{systemMetrics.cpuUsagePct}%</Text>
          </Text>
          <Text color="gray">
            RAM: <Text color="blue">{systemMetrics.memoryMb} MB</Text>
          </Text>
          <Text color="gray">
            SPEND: <Text color="green">${totalCostUsd.toFixed(4)}</Text>
          </Text>
          <Text color="gray">
            TOKENS: <Text color="magenta">{totalTokens}</Text>
          </Text>
          <StatusBadgeTui status={status === "error" ? "failure" : status} />
        </Box>
      </Box>

      {/* Tabs Navigation Bar */}
      <Box justifyContent="space-between" paddingX={1} marginTop={1}>
        <Box gap={1}>
          <Box borderStyle={activeTab === "logs" ? "bold" : "single"} borderColor={activeTab === "logs" ? "magenta" : "gray"} paddingX={1}>
            <Text color={activeTab === "logs" ? "magenta" : "gray"} bold={activeTab === "logs"}>
              [1] LIVE LOGS & TRAJECTORY
            </Text>
          </Box>
          <Box borderStyle={activeTab === "control" ? "bold" : "single"} borderColor={activeTab === "control" ? "magenta" : "gray"} paddingX={1}>
            <Text color={activeTab === "control" ? "magenta" : "gray"} bold={activeTab === "control"}>
              [2] CONTROL PANEL & DIAGNOSTICS
            </Text>
          </Box>
        </Box>
        <Box>
          <Text color="dim">
            Focus: <Text color="white">{focusedPane.toUpperCase()}</Text> | Press <Text color="cyan">Tab</Text> to switch view/focus
          </Text>
        </Box>
      </Box>
    </Box>
  );
};
