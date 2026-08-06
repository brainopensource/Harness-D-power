import React from "react";
import { Box, Text } from "ink";
import { useEngineStore, useWorkflowStore } from "@aether/core";

export const Header: React.FC = () => {
  const status = useEngineStore((state) => state.status);
  const activeRunId = useEngineStore((state) => state.activeRunId);
  const topologyId = useWorkflowStore((state) => state.topologyId);

  const getStatusColor = () => {
    switch (status) {
      case "connected":
        return "green";
      case "connecting":
        return "yellow";
      case "error":
        return "red";
      default:
        return "gray";
    }
  };

  return (
    <Box flexDirection="column" borderStyle="single" borderColor="cyan" paddingX={1}>
      <Box justifyContent="space-between">
        <Text bold color="cyan">
          ⚡ AETHER Orchestrator TUI CLI
        </Text>
        <Text color={getStatusColor()}>
          [{status.toUpperCase()}]
        </Text>
      </Box>
      <Box gap={2}>
        <Text color="gray">Run ID: <Text color="white">{activeRunId ?? "none"}</Text></Text>
        <Text color="gray">Topology: <Text color="white">{topologyId ?? "linear_repair_v1"}</Text></Text>
      </Box>
    </Box>
  );
};
